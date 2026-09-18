"""SQLite-backed durable audit store. Persists only raw-value-safe data.

Schema follows Part I. ``audit_events`` is append-only, enforced by triggers
that abort any UPDATE or DELETE so admin actions can never be edited or erased
through the application (Part M).
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from frostglass.audit.models import RequestRecord

_SCHEMA = """

CREATE TABLE IF NOT EXISTS requests (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    team TEXT NOT NULL,
    user_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    action TEXT NOT NULL,
    blocked_reason TEXT,
    policy_version INTEGER NOT NULL,
    shadow INTEGER NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost_cents INTEGER,
    latency_ms INTEGER,
    provider_latency_ms INTEGER,
    status_code INTEGER,
    fallback_used INTEGER
);
CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    detector TEXT NOT NULL,
    confidence REAL NOT NULL,
    span_start INTEGER NOT NULL,
    span_end INTEGER NOT NULL,
    value_hash TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    matched_rule_id TEXT,
    was_shadow INTEGER NOT NULL,
    reason TEXT NOT NULL,
    false_positive_reported INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS captured_content (
    request_id TEXT PRIMARY KEY REFERENCES requests(id) ON DELETE CASCADE,
    masked_payload_encrypted BLOB NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    actor_user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    before_json TEXT,
    after_json TEXT,
    ts TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_requests_tenant_ts ON requests(tenant_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_requests_tenant_team_ts ON requests(tenant_id, team, ts DESC);
CREATE INDEX IF NOT EXISTS idx_requests_tenant_action_ts ON requests(tenant_id, action, ts DESC);
CREATE INDEX IF NOT EXISTS idx_findings_request ON findings(request_id);
CREATE INDEX IF NOT EXISTS idx_findings_entity_request ON findings(entity_type, request_id);
CREATE TRIGGER IF NOT EXISTS audit_events_no_update
    BEFORE UPDATE ON audit_events
    BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
    BEFORE DELETE ON audit_events
    BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;

"""

# Confidence thresholds the policy editor's per-rule slider snaps to. Each
# threshold reports how many findings of a type met it in the window, so a
# compliance officer sees the real impact of moving the slider (H.6.2 page 4).
_CONFIDENCE_THRESHOLDS = (0.5, 0.6, 0.7, 0.8, 0.9)


class AuditStore:
    """Repository for durable, raw-value-safe audit rows."""

    def __init__(self, database_path: str) -> None:
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(_SCHEMA)
        self._connection.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        """Expose the shared connection so the admin store can reuse it."""
        return self._connection

    def record_request(
        self, record: RequestRecord, sealed_capture: tuple[bytes, datetime] | None = None
    ) -> None:
        """Persist one request, its decision trace, and optional masked capture."""
        self._connection.execute(
            """
            INSERT INTO requests(
                id, tenant_id, team, user_id, ts, model, provider, action, blocked_reason,
                policy_version, shadow, prompt_tokens, completion_tokens, cost_cents,
                latency_ms, provider_latency_ms, status_code, fallback_used
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.tenant_id,
                record.team,
                record.user,
                record.ts.isoformat(),
                record.model,
                record.provider,
                record.action,
                record.blocked_reason,
                record.policy_version,
                int(record.shadow),
                record.prompt_tokens,
                record.completion_tokens,
                record.cost_cents,
                record.latency_ms,
                record.provider_latency_ms,
                record.status_code,
                None if record.fallback_used is None else int(record.fallback_used),
            ),
        )
        for entry in record.trace:
            self._connection.execute(
                """
                INSERT INTO findings(
                    id, request_id, entity_type, detector, confidence, span_start, span_end,
                    value_hash, action_taken, matched_rule_id, was_shadow, reason,
                    false_positive_reported
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    uuid.uuid4().hex,
                    record.id,
                    entry.entity_type,
                    entry.detector,
                    entry.confidence,
                    entry.span[0],
                    entry.span[1],
                    entry.value_hash,
                    entry.action,
                    entry.matched_rule_id,
                    int(entry.was_shadow),
                    entry.reason,
                ),
            )
        if sealed_capture is not None:
            blob, expires_at = sealed_capture
            self._connection.execute(
                """
                INSERT INTO captured_content(request_id, masked_payload_encrypted, expires_at)
                VALUES (?, ?, ?)
                """,
                (record.id, blob, expires_at.isoformat()),
            )
        self._connection.commit()

    def get_request(
        self, tenant_id: str, request_id: str, team: str | None = None
    ) -> sqlite3.Row | None:
        """Fetch one request scoped by tenant, and optionally by team (IDOR guard)."""
        query = "SELECT * FROM requests WHERE tenant_id = ? AND id = ?"
        params: list[object] = [tenant_id, request_id]
        if team is not None:
            query += " AND team = ?"
            params.append(team)
        return self._connection.execute(query, params).fetchone()

    def list_requests(
        self,
        tenant_id: str,
        *,
        team: str | None = None,
        action: str | None = None,
        limit: int = 50,
        cursor: tuple[str, str] | None = None,
    ) -> tuple[list[sqlite3.Row], tuple[str, str] | None]:
        """Return one keyset page ordered by (ts DESC, id DESC) plus the next cursor.

        ``team`` scopes the result for IDOR safety; ``cursor`` is the (ts, id) of
        the last row from the previous page. One extra row is fetched to decide
        whether a further page exists.
        """
        query = "SELECT * FROM requests WHERE tenant_id = ?"
        params: list[object] = [tenant_id]
        if team is not None:
            query += " AND team = ?"
            params.append(team)
        if action is not None:
            query += " AND action = ?"
            params.append(action)
        if cursor is not None:
            query += " AND (ts < ? OR (ts = ? AND id < ?))"
            params.extend([cursor[0], cursor[0], cursor[1]])
        query += " ORDER BY ts DESC, id DESC LIMIT ?"
        params.append(limit + 1)
        rows = self._connection.execute(query, params).fetchall()
        next_cursor: tuple[str, str] | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            last = rows[-1]
            next_cursor = (last["ts"], last["id"])
        return rows, next_cursor

    def request_trace(
        self, tenant_id: str, request_id: str, team: str | None = None
    ) -> list[sqlite3.Row]:
        """Return the decision trace (findings) for a tenant/team-scoped request."""
        if self.get_request(tenant_id, request_id, team) is None:
            return []
        return self._connection.execute(
            "SELECT * FROM findings WHERE request_id = ? ORDER BY span_start, id", (request_id,)
        ).fetchall()

    def report_false_positive(
        self, tenant_id: str, finding_id: str, team: str | None = None
    ) -> bool:
        """Flag a finding as a false positive, scoped by tenant and team."""
        row = self._connection.execute(
            """
            SELECT findings.id FROM findings
            JOIN requests ON requests.id = findings.request_id
            WHERE findings.id = ? AND requests.tenant_id = ?
            """
            + (" AND requests.team = ?" if team is not None else ""),
            [finding_id, tenant_id] + ([team] if team is not None else []),
        ).fetchone()
        if row is None:
            return False
        self._connection.execute(
            "UPDATE findings SET false_positive_reported = 1 WHERE id = ?", (finding_id,)
        )
        self._connection.commit()
        return True

    def captured_content(self, request_id: str) -> sqlite3.Row | None:
        """Fetch the sealed masked capture for a request, if any."""
        return self._connection.execute(
            "SELECT * FROM captured_content WHERE request_id = ?", (request_id,)
        ).fetchone()

    # -- dashboard aggregates (M6) --------------------------------------------
    # Every aggregate is tenant-scoped and, for team-scoped roles, team-scoped,
    # so a viewer never sees another team's traffic. Timestamps are stored as
    # ISO-8601 strings; lexical comparison equals chronological comparison, so
    # range windows and day bucketing use plain string comparisons on ts.

    def _scope(self, team: str | None) -> tuple[str, list[object]]:
        clause = " AND team = ?" if team is not None else ""
        params: list[object] = [team] if team is not None else []
        return clause, params

    def stats_overview(
        self,
        tenant_id: str,
        *,
        team: str | None = None,
        range: str = "7d",
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Return the Overview page aggregates in one round trip (H.6.2 page 1)."""
        moment = now or datetime.now(UTC)
        window_days = _range_days(range)
        scope, scope_params = self._scope(team)
        conn = self._connection

        def _count_since(days: int) -> int:
            since = (moment - timedelta(days=days)).isoformat()
            row = conn.execute(
                f"SELECT COUNT(*) AS n FROM requests WHERE tenant_id = ?{scope} AND ts >= ?",
                [tenant_id, *scope_params, since],
            ).fetchone()
            return int(row["n"])

        today_start = moment.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        totals = {
            "today": int(
                conn.execute(
                    f"SELECT COUNT(*) AS n FROM requests WHERE tenant_id = ?{scope} AND ts >= ?",
                    [tenant_id, *scope_params, today_start],
                ).fetchone()["n"]
            ),
            "last_7d": _count_since(7),
            "last_30d": _count_since(30),
        }

        window_start = (moment - timedelta(days=window_days)).isoformat()
        window = [tenant_id, *scope_params, window_start]

        by_action_rows = conn.execute(
            f"""
            SELECT action, COUNT(*) AS n FROM requests
            WHERE tenant_id = ?{scope} AND ts >= ?
            GROUP BY action
            """,
            window,
        ).fetchall()
        by_action = {row["action"]: int(row["n"]) for row in by_action_rows}
        windowed_total = sum(by_action.values())

        sparkline = [
            {"day": row["day"], "count": int(row["n"])}
            for row in conn.execute(
                f"""
                SELECT substr(ts, 1, 10) AS day, COUNT(*) AS n FROM requests
                WHERE tenant_id = ?{scope} AND ts >= ?
                GROUP BY day ORDER BY day
                """,
                window,
            ).fetchall()
        ]

        sensitive_requests = int(
            conn.execute(
                f"""
                SELECT COUNT(DISTINCT requests.id) AS n FROM requests
                JOIN findings ON findings.request_id = requests.id
                WHERE requests.tenant_id = ?{scope} AND requests.ts >= ?
                """,
                window,
            ).fetchone()["n"]
        )

        top_entity_types = [
            {"entity_type": row["entity_type"], "count": int(row["n"])}
            for row in conn.execute(
                f"""
                SELECT findings.entity_type AS entity_type, COUNT(*) AS n FROM findings
                JOIN requests ON requests.id = findings.request_id
                WHERE requests.tenant_id = ?{scope} AND requests.ts >= ?
                GROUP BY findings.entity_type ORDER BY n DESC, entity_type LIMIT 10
                """,
                window,
            ).fetchall()
        ]

        top_teams = [
            {
                "team": row["team"],
                "count": int(row["n"]),
                "flagged": int(row["flagged"]),
            }
            for row in conn.execute(
                f"""
                SELECT team, COUNT(*) AS n,
                       SUM(CASE WHEN action != 'allowed' THEN 1 ELSE 0 END) AS flagged
                FROM requests WHERE tenant_id = ?{scope} AND ts >= ?
                GROUP BY team ORDER BY n DESC, team LIMIT 10
                """,
                window,
            ).fetchall()
        ]

        spend_by_provider = [
            {"provider": row["provider"], "cost_cents": int(row["cost"] or 0)}
            for row in conn.execute(
                f"""
                SELECT provider, COALESCE(SUM(cost_cents), 0) AS cost FROM requests
                WHERE tenant_id = ?{scope} AND ts >= ?
                GROUP BY provider ORDER BY cost DESC, provider
                """,
                window,
            ).fetchall()
        ]
        spend_by_model = [
            {"model": row["model"], "cost_cents": int(row["cost"] or 0)}
            for row in conn.execute(
                f"""
                SELECT model, COALESCE(SUM(cost_cents), 0) AS cost FROM requests
                WHERE tenant_id = ?{scope} AND ts >= ?
                GROUP BY model ORDER BY cost DESC, model
                """,
                window,
            ).fetchall()
        ]

        # Preserve the M5 keys (range, sampled, by_action) so existing callers
        # and tests keep working; everything else is additive.
        return {
            "range": range,
            "sampled": windowed_total,
            "by_action": by_action,
            "totals": totals,
            "windowed_total": windowed_total,
            "sensitive_requests": sensitive_requests,
            "sensitive_pct": (sensitive_requests / windowed_total) if windowed_total else 0.0,
            "sparkline": sparkline,
            "top_entity_types": top_entity_types,
            "top_teams": top_teams,
            "top_users": self.top_users(tenant_id, team=team, range=range, now=moment),
            "spend_by_provider": spend_by_provider,
            "spend_by_model": spend_by_model,
        }

    def top_users(
        self,
        tenant_id: str,
        *,
        team: str | None = None,
        range: str = "7d",
        limit: int = 10,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Top users by flagged-request volume in the window (backs AC-M6-01).

        Ordered by flagged count desc, then total desc, so "who sent the most
        flagged prompts this week" is the first row.
        """
        moment = now or datetime.now(UTC)
        since = (moment - timedelta(days=_range_days(range))).isoformat()
        scope, scope_params = self._scope(team)
        rows = self._connection.execute(
            f"""
            SELECT user_id,
                   COUNT(*) AS n,
                   SUM(CASE WHEN action != 'allowed' THEN 1 ELSE 0 END) AS flagged
            FROM requests
            WHERE tenant_id = ?{scope} AND ts >= ?
            GROUP BY user_id
            ORDER BY flagged DESC, n DESC, user_id
            LIMIT ?
            """,
            [tenant_id, *scope_params, since, limit],
        ).fetchall()
        return [
            {"user": row["user_id"], "count": int(row["n"]), "flagged": int(row["flagged"])}
            for row in rows
        ]

    def detection_estimates(
        self,
        tenant_id: str,
        *,
        team: str | None = None,
        range: str = "7d",
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Per-entity-type match counts by confidence threshold (H.6.2 page 4).

        The policy editor's confidence slider shows how many findings of a type
        met each threshold in the window, so moving the slider has a visible,
        real impact estimate rather than an invented number.
        """
        moment = now or datetime.now(UTC)
        since = (moment - timedelta(days=_range_days(range))).isoformat()
        scope, scope_params = self._scope(team)
        rows = self._connection.execute(
            f"""
            SELECT findings.entity_type AS entity_type, findings.confidence AS confidence
            FROM findings JOIN requests ON requests.id = findings.request_id
            WHERE requests.tenant_id = ?{scope} AND requests.ts >= ?
            """,
            [tenant_id, *scope_params, since],
        ).fetchall()
        estimates: dict[str, dict[str, Any]] = {}
        for row in rows:
            entity_type = row["entity_type"]
            confidence = float(row["confidence"])
            bucket = estimates.setdefault(
                entity_type,
                {"total": 0, "at_confidence": {f"{t:.1f}": 0 for t in _CONFIDENCE_THRESHOLDS}},
            )
            bucket["total"] += 1
            for threshold in _CONFIDENCE_THRESHOLDS:
                if confidence >= threshold:
                    bucket["at_confidence"][f"{threshold:.1f}"] += 1
        return {"range": range, "by_entity_type": estimates}

    def false_positive_rate(
        self,
        tenant_id: str,
        *,
        team: str | None = None,
        range: str = "7d",
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """False-positive-report rate over findings in the window (H.6.2 page 3)."""
        moment = now or datetime.now(UTC)
        since = (moment - timedelta(days=_range_days(range))).isoformat()
        scope, scope_params = self._scope(team)
        row = self._connection.execute(
            f"""
            SELECT COUNT(*) AS total,
                   SUM(findings.false_positive_reported) AS reported
            FROM findings JOIN requests ON requests.id = findings.request_id
            WHERE requests.tenant_id = ?{scope} AND requests.ts >= ?
            """,
            [tenant_id, *scope_params, since],
        ).fetchone()
        total = int(row["total"] or 0)
        reported = int(row["reported"] or 0)
        return {
            "range": range,
            "total": total,
            "reported": reported,
            "rate": (reported / total) if total else 0.0,
        }

    def purge(self, *, audit_cutoff: datetime, now: datetime) -> None:
        """Purge expired captured content and audit rows older than the cutoff."""
        self._connection.execute(
            "DELETE FROM captured_content WHERE expires_at <= ?", (now.isoformat(),)
        )
        self._connection.execute("DELETE FROM requests WHERE ts < ?", (audit_cutoff.isoformat(),))
        self._connection.commit()


def _range_days(range: str) -> int:
    """Parse a range token like '24h', '7d', '30d' into a day window.

    Unknown or malformed tokens fall back to 7 days so a bad query parameter
    degrades to the default window rather than erroring.
    """
    token = (range or "").strip().lower()
    try:
        if token.endswith("h"):
            hours = int(token[:-1])
            return max(1, (hours + 23) // 24)
        if token.endswith("d"):
            return max(1, int(token[:-1]))
        if token.endswith("w"):
            return max(1, int(token[:-1]) * 7)
    except ValueError:
        return 7
    return 7

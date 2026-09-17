"""SQLite-backed durable audit store. Persists only raw-value-safe data.

Schema follows Part I. ``audit_events`` is append-only, enforced by triggers
that abort any UPDATE or DELETE so admin actions can never be edited or erased
through the application (Part M).
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

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

    def captured_content(self, request_id: str) -> sqlite3.Row | None:
        """Fetch the sealed masked capture for a request, if any."""
        return self._connection.execute(
            "SELECT * FROM captured_content WHERE request_id = ?", (request_id,)
        ).fetchone()

    def purge(self, *, audit_cutoff: datetime, now: datetime) -> None:
        """Purge expired captured content and audit rows older than the cutoff."""
        self._connection.execute(
            "DELETE FROM captured_content WHERE expires_at <= ?", (now.isoformat(),)
        )
        self._connection.execute(
            "DELETE FROM requests WHERE ts < ?", (audit_cutoff.isoformat(),)
        )
        self._connection.commit()

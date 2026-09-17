"""SQLite-backed Admin API store for access, configuration, and audit events.

Shares the audit database connection so that admin configuration, the request
audit trail, and the append-only ``audit_events`` log live in one durable
store. Every mutation writes an append-only audit event with the actor's
identity (Part M: insider misuse is deterred by an immutable admin log).
"""

from __future__ import annotations

import json
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from hmac import compare_digest
from typing import Any

from frostglass.admin.rbac import AdminIdentity, Role


_SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    team TEXT NOT NULL,
    role TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    disabled_at TEXT
);
CREATE TABLE IF NOT EXISTS teams (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    shadow_mode INTEGER NOT NULL DEFAULT 1,
    monthly_budget_cents INTEGER NOT NULL DEFAULT 0,
    rate_limit_rpm INTEGER NOT NULL DEFAULT 60,
    allowed_models TEXT NOT NULL DEFAULT '[]',
    content_capture_enabled INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    team TEXT NOT NULL,
    user_id TEXT,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE TABLE IF NOT EXISTS detectors (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    min_confidence REAL NOT NULL DEFAULT 0.5
);
CREATE TABLE IF NOT EXISTS dictionaries (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    match_mode TEXT NOT NULL,
    action TEXT NOT NULL,
    replacement TEXT,
    term_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS suggestions (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    proposed_rule_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS settings (
    tenant_id TEXT PRIMARY KEY,
    audit_retention_days INTEGER NOT NULL DEFAULT 90,
    capture_retention_days INTEGER NOT NULL DEFAULT 7,
    content_capture_enabled INTEGER NOT NULL DEFAULT 0,
    sso_enabled INTEGER NOT NULL DEFAULT 0,
    sso_provider TEXT,
    sso_client_id TEXT,
    vault_key_rotated_at TEXT
);
CREATE TABLE IF NOT EXISTS provider_credentials (
    tenant_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    key_last4 TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, provider)
);
"""

# Columns added after the initial M5 schema. SQLite has no IF NOT EXISTS for
# ADD COLUMN, so each is attempted and the duplicate-column error is ignored,
# letting an existing dev database migrate forward without a separate tool.
_MIGRATIONS = (
    "ALTER TABLE teams ADD COLUMN allowed_models TEXT NOT NULL DEFAULT '[]'",
    "ALTER TABLE settings ADD COLUMN sso_enabled INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE settings ADD COLUMN sso_provider TEXT",
    "ALTER TABLE settings ADD COLUMN sso_client_id TEXT",
    "ALTER TABLE settings ADD COLUMN vault_key_rotated_at TEXT",
)


@dataclass(frozen=True, slots=True)
class IssuedKey:
    """A freshly issued virtual key. The full value is shown exactly once."""

    id: str
    full_key: str
    key_prefix: str


class AdminStore:
    """Repository for admin access, configuration, and append-only events."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.executescript(_SCHEMA)
        for statement in _MIGRATIONS:
            try:
                self._connection.execute(statement)
            except sqlite3.OperationalError:
                # Column already present on a database created by this schema.
                pass
        self._connection.commit()

    # -- sessions and identity -------------------------------------------------
    def create_session(
        self, token: str, user_id: str, tenant_id: str, team: str, role: Role
    ) -> None:
        """Register an opaque session token, stored only as a hash."""
        self._connection.execute(
            """
            INSERT OR REPLACE INTO admin_sessions(token_hash, user_id, tenant_id, team, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sha256(token.encode()).hexdigest(), user_id, tenant_id, team, str(role)),
        )
        self._connection.commit()

    def resolve_session(self, token: str) -> AdminIdentity | None:
        """Resolve a session token to an identity using constant-time compare."""
        digest = sha256(token.encode()).hexdigest()
        for row in self._connection.execute(
            "SELECT token_hash, user_id, tenant_id, team, role FROM admin_sessions"
        ).fetchall():
            if compare_digest(row["token_hash"], digest):
                return AdminIdentity(
                    row["user_id"], row["tenant_id"], row["team"], Role(row["role"])
                )
        return None

    # -- append-only audit events ---------------------------------------------
    def record_event(
        self,
        identity: AdminIdentity,
        action: str,
        target: str,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        """Append one immutable admin audit event."""
        self._connection.execute(
            """
            INSERT INTO audit_events(id, tenant_id, actor_user_id, action, target,
                                     before_json, after_json, ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                identity.tenant_id,
                identity.user_id,
                action,
                target,
                None if before is None else json.dumps(before, separators=(",", ":")),
                None if after is None else json.dumps(after, separators=(",", ":")),
                datetime.now(UTC).isoformat(),
            ),
        )
        self._connection.commit()

    def list_events(self, tenant_id: str) -> list[sqlite3.Row]:
        return self._connection.execute(
            "SELECT * FROM audit_events WHERE tenant_id = ? ORDER BY ts DESC, id DESC",
            (tenant_id,),
        ).fetchall()

    # -- teams -----------------------------------------------------------------
    def upsert_team(
        self,
        tenant_id: str,
        name: str,
        *,
        shadow_mode: bool = True,
        monthly_budget_cents: int = 0,
        rate_limit_rpm: int = 60,
        allowed_models: list[str] | None = None,
    ) -> str:
        team_id = uuid.uuid4().hex
        self._connection.execute(
            """
            INSERT INTO teams(id, tenant_id, name, shadow_mode, monthly_budget_cents,
                              rate_limit_rpm, allowed_models)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                team_id,
                tenant_id,
                name,
                int(shadow_mode),
                monthly_budget_cents,
                rate_limit_rpm,
                json.dumps(allowed_models or [], separators=(",", ":")),
            ),
        )
        self._connection.commit()
        return team_id

    def get_team(self, tenant_id: str, team_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM teams WHERE tenant_id = ? AND id = ?", (tenant_id, team_id)
        ).fetchone()

    def update_team(
        self,
        tenant_id: str,
        team_id: str,
        *,
        shadow_mode: bool | None = None,
        monthly_budget_cents: int | None = None,
        rate_limit_rpm: int | None = None,
        allowed_models: list[str] | None = None,
    ) -> sqlite3.Row | None:
        current = self.get_team(tenant_id, team_id)
        if current is None:
            return None
        self._connection.execute(
            """
            UPDATE teams SET shadow_mode = ?, monthly_budget_cents = ?, rate_limit_rpm = ?,
                             allowed_models = ?
            WHERE tenant_id = ? AND id = ?
            """,
            (
                int(current["shadow_mode"] if shadow_mode is None else shadow_mode),
                current["monthly_budget_cents"]
                if monthly_budget_cents is None
                else monthly_budget_cents,
                current["rate_limit_rpm"] if rate_limit_rpm is None else rate_limit_rpm,
                current["allowed_models"]
                if allowed_models is None
                else json.dumps(allowed_models, separators=(",", ":")),
                tenant_id,
                team_id,
            ),
        )
        self._connection.commit()
        return self.get_team(tenant_id, team_id)

    def list_teams(self, tenant_id: str) -> list[sqlite3.Row]:
        return self._connection.execute(
            "SELECT * FROM teams WHERE tenant_id = ? ORDER BY name, id", (tenant_id,)
        ).fetchall()

    # -- users -----------------------------------------------------------------
    def create_user(self, tenant_id: str, email: str, name: str, role: Role) -> str:
        user_id = uuid.uuid4().hex
        self._connection.execute(
            """
            INSERT INTO users(id, tenant_id, email, name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, tenant_id, email, name, str(role), datetime.now(UTC).isoformat()),
        )
        self._connection.commit()
        return user_id

    def list_users(self, tenant_id: str) -> list[sqlite3.Row]:
        return self._connection.execute(
            "SELECT * FROM users WHERE tenant_id = ? ORDER BY email, id", (tenant_id,)
        ).fetchall()

    # -- api keys --------------------------------------------------------------
    def issue_key(self, tenant_id: str, team: str, name: str) -> IssuedKey:
        """Issue a virtual key. Return the full key once; store only its hash."""
        key_id = uuid.uuid4().hex
        full_key = f"fg-live-{secrets.token_urlsafe(24)}"
        self._connection.execute(
            """
            INSERT INTO api_keys(id, tenant_id, team, user_id, key_prefix, key_hash, name,
                                 created_at)
            VALUES (?, ?, ?, NULL, ?, ?, ?, ?)
            """,
            (
                key_id,
                tenant_id,
                team,
                full_key[:12],
                sha256(full_key.encode()).hexdigest(),
                name,
                datetime.now(UTC).isoformat(),
            ),
        )
        self._connection.commit()
        return IssuedKey(key_id, full_key, full_key[:12])

    def revoke_key(self, tenant_id: str, key_id: str) -> bool:
        cursor = self._connection.execute(
            "UPDATE api_keys SET revoked_at = ? "
            "WHERE tenant_id = ? AND id = ? AND revoked_at IS NULL",
            (datetime.now(UTC).isoformat(), tenant_id, key_id),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    def list_keys(self, tenant_id: str) -> list[sqlite3.Row]:
        return self._connection.execute(
            "SELECT id, tenant_id, team, key_prefix, name, created_at, revoked_at "
            "FROM api_keys WHERE tenant_id = ? ORDER BY created_at DESC, id DESC",
            (tenant_id,),
        ).fetchall()

    # -- detectors -------------------------------------------------------------
    def seed_detector(self, tenant_id: str, name: str, kind: str) -> str:
        detector_id = uuid.uuid4().hex
        self._connection.execute(
            "INSERT INTO detectors(id, tenant_id, name, kind) VALUES (?, ?, ?, ?)",
            (detector_id, tenant_id, name, kind),
        )
        self._connection.commit()
        return detector_id

    def list_detectors(self, tenant_id: str) -> list[sqlite3.Row]:
        return self._connection.execute(
            "SELECT * FROM detectors WHERE tenant_id = ? ORDER BY name, id", (tenant_id,)
        ).fetchall()

    def get_detector(self, tenant_id: str, detector_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM detectors WHERE tenant_id = ? AND id = ?", (tenant_id, detector_id)
        ).fetchone()

    def update_detector(
        self,
        tenant_id: str,
        detector_id: str,
        *,
        enabled: bool | None = None,
        min_confidence: float | None = None,
    ) -> sqlite3.Row | None:
        current = self.get_detector(tenant_id, detector_id)
        if current is None:
            return None
        self._connection.execute(
            "UPDATE detectors SET enabled = ?, min_confidence = ? WHERE tenant_id = ? AND id = ?",
            (
                int(current["enabled"] if enabled is None else enabled),
                current["min_confidence"] if min_confidence is None else min_confidence,
                tenant_id,
                detector_id,
            ),
        )
        self._connection.commit()
        return self.get_detector(tenant_id, detector_id)

    # -- dictionaries ----------------------------------------------------------
    def create_dictionary(
        self,
        tenant_id: str,
        name: str,
        match_mode: str,
        action: str,
        replacement: str | None,
        term_count: int,
    ) -> str:
        dictionary_id = uuid.uuid4().hex
        self._connection.execute(
            """
            INSERT INTO dictionaries(id, tenant_id, name, match_mode, action, replacement,
                                     term_count, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dictionary_id,
                tenant_id,
                name,
                match_mode,
                action,
                replacement,
                term_count,
                datetime.now(UTC).isoformat(),
            ),
        )
        self._connection.commit()
        return dictionary_id

    def list_dictionaries(self, tenant_id: str) -> list[sqlite3.Row]:
        return self._connection.execute(
            "SELECT * FROM dictionaries WHERE tenant_id = ? ORDER BY name, id", (tenant_id,)
        ).fetchall()

    # -- suggestions -----------------------------------------------------------
    def create_suggestion(
        self, tenant_id: str, kind: str, evidence: dict[str, Any], proposed_rule: dict[str, Any]
    ) -> str:
        suggestion_id = uuid.uuid4().hex
        self._connection.execute(
            """
            INSERT INTO suggestions(id, tenant_id, kind, evidence_json, proposed_rule_json,
                                    status, created_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?)
            """,
            (
                suggestion_id,
                tenant_id,
                kind,
                json.dumps(evidence, separators=(",", ":")),
                json.dumps(proposed_rule, separators=(",", ":")),
                datetime.now(UTC).isoformat(),
            ),
        )
        self._connection.commit()
        return suggestion_id

    def list_suggestions(self, tenant_id: str) -> list[sqlite3.Row]:
        return self._connection.execute(
            "SELECT * FROM suggestions WHERE tenant_id = ? ORDER BY created_at DESC, id DESC",
            (tenant_id,),
        ).fetchall()

    def resolve_suggestion(self, tenant_id: str, suggestion_id: str, status: str) -> bool:
        cursor = self._connection.execute(
            "UPDATE suggestions SET status = ?, resolved_at = ? WHERE tenant_id = ? AND id = ?",
            (status, datetime.now(UTC).isoformat(), tenant_id, suggestion_id),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    # -- settings --------------------------------------------------------------
    def get_settings(self, tenant_id: str) -> sqlite3.Row:
        row = self._connection.execute(
            "SELECT * FROM settings WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()
        if row is None:
            self._connection.execute("INSERT INTO settings(tenant_id) VALUES (?)", (tenant_id,))
            self._connection.commit()
            row = self._connection.execute(
                "SELECT * FROM settings WHERE tenant_id = ?", (tenant_id,)
            ).fetchone()
        return row

    def update_settings(
        self,
        tenant_id: str,
        *,
        audit_retention_days: int | None = None,
        capture_retention_days: int | None = None,
        content_capture_enabled: bool | None = None,
        sso_enabled: bool | None = None,
        sso_provider: str | None = None,
        sso_client_id: str | None = None,
    ) -> sqlite3.Row:
        current = self.get_settings(tenant_id)
        self._connection.execute(
            """
            UPDATE settings SET audit_retention_days = ?, capture_retention_days = ?,
                                content_capture_enabled = ?, sso_enabled = ?,
                                sso_provider = ?, sso_client_id = ?
            WHERE tenant_id = ?
            """,
            (
                current["audit_retention_days"]
                if audit_retention_days is None
                else audit_retention_days,
                current["capture_retention_days"]
                if capture_retention_days is None
                else capture_retention_days,
                int(
                    current["content_capture_enabled"]
                    if content_capture_enabled is None
                    else content_capture_enabled
                ),
                int(current["sso_enabled"] if sso_enabled is None else sso_enabled),
                current["sso_provider"] if sso_provider is None else sso_provider,
                current["sso_client_id"] if sso_client_id is None else sso_client_id,
                tenant_id,
            ),
        )
        self._connection.commit()
        return self.get_settings(tenant_id)

    def rotate_vault_key(self, tenant_id: str, when: datetime | None = None) -> sqlite3.Row:
        """Record a vault-key rotation timestamp (status surfaced in Settings)."""
        self.get_settings(tenant_id)
        self._connection.execute(
            "UPDATE settings SET vault_key_rotated_at = ? WHERE tenant_id = ?",
            ((when or datetime.now(UTC)).isoformat(), tenant_id),
        )
        self._connection.commit()
        return self.get_settings(tenant_id)

    # -- provider credentials (write-only) ------------------------------------
    def set_provider_credential(self, tenant_id: str, provider: str, secret: str) -> None:
        """Store a vendor key write-only: keep only its last 4 chars and a hash.

        The secret itself is never persisted and never rendered back to the
        browser (H.6.2 page 8, Part M).
        """
        self._connection.execute(
            """
            INSERT OR REPLACE INTO provider_credentials(
                tenant_id, provider, key_last4, key_hash, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                provider,
                secret[-4:],
                sha256(secret.encode()).hexdigest(),
                datetime.now(UTC).isoformat(),
            ),
        )
        self._connection.commit()

    def list_provider_credentials(self, tenant_id: str) -> list[sqlite3.Row]:
        """List configured provider credentials without exposing any secret."""
        return self._connection.execute(
            "SELECT provider, key_last4, updated_at FROM provider_credentials "
            "WHERE tenant_id = ? ORDER BY provider",
            (tenant_id,),
        ).fetchall()

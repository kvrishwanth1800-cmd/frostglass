"""Persistence for RE2-backed custom recognizer configuration."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from frostglass.admin.custom_recognizers import validate_pattern


@dataclass(frozen=True, slots=True)
class Recognizer:
    id: str
    tenant_id: str
    name: str
    pattern: str
    entity_type: str
    action: str
    min_confidence: float
    enabled: bool


class RecognizerStore:
    """Stores only validated RE2 patterns and operator-selected metadata."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS m7_custom_recognizers (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                pattern TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                action TEXT NOT NULL,
                min_confidence REAL NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                UNIQUE(tenant_id, name)
            );
            """
        )
        self._connection.commit()

    def create(
        self,
        tenant_id: str,
        name: str,
        pattern: str,
        entity_type: str,
        action: str,
        min_confidence: float,
    ) -> Recognizer:
        validate_pattern(pattern)
        if action not in {"allow", "tag", "pseudonymize", "redact", "block"}:
            raise ValueError("Unsupported recognizer action")
        if not 0 <= min_confidence <= 1:
            raise ValueError("Recognizer confidence must be between 0 and 1")
        recognizer_id = uuid.uuid4().hex
        self._connection.execute(
            "INSERT INTO m7_custom_recognizers VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (recognizer_id, tenant_id, name.strip(), pattern, entity_type.strip(), action, min_confidence, datetime.now(UTC).isoformat()),
        )
        self._connection.commit()
        return self.get(tenant_id, recognizer_id)

    def get(self, tenant_id: str, recognizer_id: str) -> Recognizer:
        row = self._connection.execute(
            "SELECT id, tenant_id, name, pattern, entity_type, action, min_confidence, enabled FROM m7_custom_recognizers WHERE tenant_id = ? AND id = ?",
            (tenant_id, recognizer_id),
        ).fetchone()
        if row is None:
            raise KeyError("Custom recognizer not found")
        data = dict(row)
        data["enabled"] = bool(data["enabled"])
        return Recognizer(**data)

    def list(self, tenant_id: str) -> list[Recognizer]:
        rows = self._connection.execute(
            "SELECT id, tenant_id, name, pattern, entity_type, action, min_confidence, enabled FROM m7_custom_recognizers WHERE tenant_id = ? ORDER BY name, id",
            (tenant_id,),
        ).fetchall()
        return [Recognizer(**(dict(row) | {"enabled": bool(row["enabled"])})) for row in rows]

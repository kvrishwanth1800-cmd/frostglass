"""Tenant-scoped dictionary persistence for M7.

This module is deliberately independent from the legacy AdminStore. It can be
wired into the Admin API without changing its data model. Terms are stored as
operator configuration, never copied into audit records.
"""

from __future__ import annotations

import csv
import io
import sqlite3
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

_VALID_MODES = frozenset({"exact", "word-boundary", "fuzzy"})
_VALID_ACTIONS = frozenset({"allow", "tag", "pseudonymize", "redact", "block"})


@dataclass(frozen=True, slots=True)
class DictionaryTerm:
    id: str
    dictionary_id: str
    term: str
    replacement: str | None


class DictionaryStore:
    """SQLite persistence and deterministic matching for custom term lists."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS m7_dictionaries (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                match_mode TEXT NOT NULL,
                action TEXT NOT NULL,
                replacement TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS m7_dictionary_terms (
                id TEXT PRIMARY KEY,
                dictionary_id TEXT NOT NULL REFERENCES m7_dictionaries(id) ON DELETE CASCADE,
                term TEXT NOT NULL,
                replacement TEXT,
                UNIQUE(dictionary_id, term)
            );
            CREATE INDEX IF NOT EXISTS m7_dictionary_terms_dictionary
                ON m7_dictionary_terms(dictionary_id, term);
            """
        )
        self._connection.commit()

    @staticmethod
    def _validate(mode: str, action: str) -> None:
        if mode not in _VALID_MODES:
            raise ValueError(f"Unsupported match mode: {mode}")
        if action not in _VALID_ACTIONS:
            raise ValueError(f"Unsupported dictionary action: {action}")

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def create(self, tenant_id: str, name: str, match_mode: str, action: str, replacement: str | None = None) -> str:
        self._validate(match_mode, action)
        dictionary_id = uuid.uuid4().hex
        self._connection.execute(
            "INSERT INTO m7_dictionaries VALUES (?, ?, ?, ?, ?, ?, ?)",
            (dictionary_id, tenant_id, name.strip(), match_mode, action, replacement, self._now()),
        )
        self._connection.commit()
        return dictionary_id

    def list(self, tenant_id: str) -> list[dict[str, object]]:
        rows = self._connection.execute(
            """
            SELECT d.*, COUNT(t.id) AS term_count
            FROM m7_dictionaries d LEFT JOIN m7_dictionary_terms t ON t.dictionary_id = d.id
            WHERE d.tenant_id = ? GROUP BY d.id ORDER BY d.name, d.id
            """,
            (tenant_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def add_terms(self, tenant_id: str, dictionary_id: str, terms: Iterable[str], replacement: str | None = None) -> int:
        self._owned(tenant_id, dictionary_id)
        cleaned = sorted({term.strip() for term in terms if term.strip()})
        self._connection.executemany(
            "INSERT OR IGNORE INTO m7_dictionary_terms(id, dictionary_id, term, replacement) VALUES (?, ?, ?, ?)",
            [(uuid.uuid4().hex, dictionary_id, term, replacement) for term in cleaned],
        )
        self._touch(dictionary_id)
        self._connection.commit()
        return len(cleaned)

    def import_csv(self, tenant_id: str, dictionary_id: str, source: str) -> int:
        reader = csv.reader(io.StringIO(source))
        terms = [row[0] for row in reader if row and row[0].strip() and row[0].strip().lower() != "term"]
        return self.add_terms(tenant_id, dictionary_id, terms)

    def terms(self, tenant_id: str, dictionary_id: str) -> list[DictionaryTerm]:
        self._owned(tenant_id, dictionary_id)
        rows = self._connection.execute(
            "SELECT id, dictionary_id, term, replacement FROM m7_dictionary_terms WHERE dictionary_id = ? ORDER BY term, id",
            (dictionary_id,),
        ).fetchall()
        return [DictionaryTerm(**dict(row)) for row in rows]

    def update_term(self, tenant_id: str, dictionary_id: str, term_id: str, term: str, replacement: str | None) -> DictionaryTerm:
        self._owned(tenant_id, dictionary_id)
        cursor = self._connection.execute(
            "UPDATE m7_dictionary_terms SET term = ?, replacement = ? WHERE id = ? AND dictionary_id = ?",
            (term.strip(), replacement, term_id, dictionary_id),
        )
        if cursor.rowcount != 1:
            raise KeyError("Dictionary term not found")
        self._touch(dictionary_id)
        self._connection.commit()
        return next(item for item in self.terms(tenant_id, dictionary_id) if item.id == term_id)

    def remove_term(self, tenant_id: str, dictionary_id: str, term_id: str) -> None:
        self._owned(tenant_id, dictionary_id)
        cursor = self._connection.execute(
            "DELETE FROM m7_dictionary_terms WHERE id = ? AND dictionary_id = ?", (term_id, dictionary_id)
        )
        if cursor.rowcount != 1:
            raise KeyError("Dictionary term not found")
        self._touch(dictionary_id)
        self._connection.commit()

    def match(self, tenant_id: str, text: str) -> list[DictionaryTerm]:
        """Return terms that match a request immediately after configuration changes."""
        matches: list[DictionaryTerm] = []
        for dictionary in self.list(tenant_id):
            for item in self.terms(tenant_id, str(dictionary["id"])):
                if self._matches(text, item.term, str(dictionary["match_mode"])):
                    matches.append(item)
        return matches

    @staticmethod
    def _matches(text: str, term: str, mode: str) -> bool:
        lowered, needle = text.casefold(), term.casefold()
        if mode == "exact":
            return lowered == needle
        if mode == "word-boundary":
            index = lowered.find(needle)
            while index >= 0:
                before = lowered[index - 1] if index else " "
                end = index + len(needle)
                after = lowered[end] if end < len(lowered) else " "
                if not before.isalnum() and not after.isalnum():
                    return True
                index = lowered.find(needle, index + 1)
            return False
        return needle in lowered

    def _owned(self, tenant_id: str, dictionary_id: str) -> None:
        row = self._connection.execute(
            "SELECT 1 FROM m7_dictionaries WHERE tenant_id = ? AND id = ?", (tenant_id, dictionary_id)
        ).fetchone()
        if row is None:
            raise KeyError("Dictionary not found")

    def _touch(self, dictionary_id: str) -> None:
        self._connection.execute("UPDATE m7_dictionaries SET updated_at = ? WHERE id = ?", (self._now(), dictionary_id))

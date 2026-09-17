"""AC-M5-03: with capture disabled, no seeded raw value reaches any DB column.

The test seeds known synthetic sensitive values (never real personal data)
across multiple entity types through the full gateway pipeline, then opens the
real audit database file and scans every column of every table, asserting that
none of the raw values (with or without separators) appear anywhere.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from frostglass.main import create_app

_KEY = {"Authorization": "Bearer fg-live-test-key"}

# Synthetic values only. Spanning secrets, financial, contact, and NER types.
_SEEDS = (
    "AKIA1234567890ABCDEF",
    "ghp_0123456789abcdefghijklmnopqrstuvwxyzA",
    "avery.stone@example.com",
    "4111 1111 1111 1111",
    "Avery Stone",
    "+1 415 555 0132",
)


@pytest.fixture(scope="module")
def audit_db_path(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    path = str(tmp_path_factory.mktemp("audit") / "audit.sqlite3")
    previous = {
        "FG_AUDIT_DATABASE_PATH": os.environ.get("FG_AUDIT_DATABASE_PATH"),
        "FG_CONTENT_CAPTURE": os.environ.get("FG_CONTENT_CAPTURE"),
    }
    os.environ["FG_AUDIT_DATABASE_PATH"] = path
    os.environ["FG_CONTENT_CAPTURE"] = "false"
    try:
        client = TestClient(create_app())
        for value in _SEEDS:
            client.post(
                "/v1/chat/completions",
                headers=_KEY,
                json={
                    "model": "mock-model",
                    "messages": [{"role": "user", "content": f"Please handle {value} now."}],
                },
            )
        yield path
    finally:
        for name, original in previous.items():
            if original is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = original


def test_ac_m5_03_no_raw_values_in_any_db_column(audit_db_path: str) -> None:
    connection = sqlite3.connect(audit_db_path)
    connection.row_factory = sqlite3.Row
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        ]
        assert "requests" in tables
        assert "findings" in tables

        cells: list[str] = []
        request_rows = 0
        for table in tables:
            for row in connection.execute(f"SELECT * FROM {table}").fetchall():
                if table == "requests":
                    request_rows += 1
                cells.extend(str(row[column]) for column in row.keys())
        haystack = "\n".join(cells)

        assert request_rows > 0
        for value in _SEEDS:
            assert value not in haystack
            assert value.replace(" ", "") not in haystack
    finally:
        connection.close()

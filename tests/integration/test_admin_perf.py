"""AC-M5-01: list endpoints stay under a 300 ms p95 over 10k requests."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from time import perf_counter

import pytest
from fastapi.testclient import TestClient

from frostglass.audit.models import RequestRecord
from frostglass.audit.store import AuditStore
from frostglass.main import create_app

_TOTAL = 10_000
_BASE = datetime(2026, 1, 1, tzinfo=UTC)
OWNER = {"Authorization": "Bearer fg-admin-owner-token"}


@pytest.fixture(scope="module")
def seeded_client() -> Iterator[TestClient]:
    app = create_app()
    store: AuditStore = app.state.audit_store
    for index in range(_TOTAL):
        store.record_request(
            RequestRecord(
                id=f"req-{index:06d}",
                tenant_id="default",
                team="test-team",
                user="seed-user",
                ts=_BASE + timedelta(seconds=index),
                model="mock-model",
                provider="openai",
                action="masked",
                policy_version=1,
                shadow=False,
            )
        )
    yield TestClient(app)


def _p95(durations_ms: list[float]) -> float:
    ordered = sorted(durations_ms)
    return ordered[int(len(ordered) * 0.95) - 1]


def test_ac_m5_01_requests_list_p95_under_300ms(seeded_client: TestClient) -> None:
    durations: list[float] = []
    for _ in range(40):
        start = perf_counter()
        response = seeded_client.get("/admin/requests?limit=100", headers=OWNER)
        durations.append((perf_counter() - start) * 1000)
        assert response.status_code == 200
        assert len(response.json()["items"]) == 100
    assert _p95(durations) < 300.0


def test_ac_m5_01_stats_overview_p95_under_300ms(seeded_client: TestClient) -> None:
    durations: list[float] = []
    for _ in range(40):
        start = perf_counter()
        response = seeded_client.get("/admin/stats/overview", headers=OWNER)
        durations.append((perf_counter() - start) * 1000)
        assert response.status_code == 200
    assert _p95(durations) < 300.0


def test_ac_m5_01_pagination_walks_all_rows(seeded_client: TestClient) -> None:
    seen = 0
    cursor: str | None = None
    pages = 0
    while True:
        url = "/admin/requests?limit=100"
        if cursor is not None:
            url += f"&cursor={cursor}"
        payload = seeded_client.get(url, headers=OWNER).json()
        seen += len(payload["items"])
        pages += 1
        cursor = payload["next_cursor"]
        if cursor is None:
            break
        assert pages <= 150
    assert seen == _TOTAL

"""AC-M5-05: no IDOR - a caller cannot reach another team's request by id."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from frostglass.main import create_app

GATEWAY_KEY = {"Authorization": "Bearer fg-live-test-key"}  # team: test-team
OWNER = {"Authorization": "Bearer fg-admin-owner-token"}  # tenant-wide
VIEWER = {"Authorization": "Bearer fg-admin-viewer-token"}  # team: other-team


@pytest.fixture(scope="module")
def seeded() -> Iterator[tuple[TestClient, str]]:
    client = TestClient(create_app())
    # Seed a request owned by test-team through the real gateway pipeline.
    client.post(
        "/v1/chat/completions",
        headers=GATEWAY_KEY,
        json={"model": "mock-model", "messages": [{"role": "user", "content": "hello"}]},
    )
    listing = client.get("/admin/requests", headers=OWNER).json()
    assert listing["items"], "owner should see the seeded test-team request"
    yield client, listing["items"][0]["id"]


def test_ac_m5_05_other_team_cannot_fetch_request(seeded: tuple[TestClient, str]) -> None:
    client, request_id = seeded
    assert client.get(f"/admin/requests/{request_id}", headers=VIEWER).status_code == 404


def test_ac_m5_05_other_team_cannot_fetch_trace(seeded: tuple[TestClient, str]) -> None:
    client, request_id = seeded
    assert client.get(f"/admin/requests/{request_id}/trace", headers=VIEWER).status_code == 404


def test_ac_m5_05_tenant_wide_owner_can_fetch_request(seeded: tuple[TestClient, str]) -> None:
    client, request_id = seeded
    assert client.get(f"/admin/requests/{request_id}", headers=OWNER).status_code == 200


def test_ac_m5_05_other_team_sees_empty_request_list(seeded: tuple[TestClient, str]) -> None:
    client, _ = seeded
    # The viewer's team (other-team) has no requests, so the list is empty even
    # though the tenant has one.
    assert client.get("/admin/requests", headers=VIEWER).json()["items"] == []

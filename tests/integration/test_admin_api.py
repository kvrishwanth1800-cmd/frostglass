"""Admin API happy-path smoke tests across the H.7 endpoint surface."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from frostglass.main import create_app

GATEWAY_KEY = {"Authorization": "Bearer fg-live-test-key"}
OWNER = {"Authorization": "Bearer fg-admin-owner-token"}


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    yield TestClient(create_app())


def test_request_and_trace_round_trip(client: TestClient) -> None:
    client.post(
        "/v1/chat/completions",
        headers=GATEWAY_KEY,
        json={
            "model": "mock-model",
            "messages": [{"role": "user", "content": "email me at avery@example.com"}],
        },
    )
    listing = client.get("/admin/requests", headers=OWNER).json()
    assert listing["items"]
    request_id = listing["items"][0]["id"]
    detail = client.get(f"/admin/requests/{request_id}", headers=OWNER)
    assert detail.status_code == 200
    trace = client.get(f"/admin/requests/{request_id}/trace", headers=OWNER)
    assert trace.status_code == 200
    assert "trace" in trace.json()


def test_policy_read_add_and_activate(client: TestClient) -> None:
    active = client.get("/admin/policies", headers=OWNER)
    assert active.status_code == 200
    versions = client.get("/admin/policies/versions", headers=OWNER).json()
    assert versions["active_version"] >= 1
    created = client.post(
        "/admin/policies",
        headers=OWNER,
        json={"yaml": "version: 2\ndefault_action: pseudonymize\nrules: []\n"},
    )
    assert created.status_code == 200
    assert created.json()["version"] == 2
    activated = client.post("/admin/policies/2/activate", headers=OWNER)
    assert activated.status_code == 200
    assert client.get("/admin/policies", headers=OWNER).json()["version"] == 2


def test_policy_test_sandbox_runs_without_provider(client: TestClient) -> None:
    response = client.post(
        "/admin/policies/test",
        headers=OWNER,
        json={"text": "reach me at avery@example.com"},
    )
    assert response.status_code == 200
    assert "findings" in response.json()


def test_detectors_list_and_patch(client: TestClient) -> None:
    detectors = client.get("/admin/detectors", headers=OWNER).json()["items"]
    assert detectors
    detector_id = detectors[0]["id"]
    patched = client.patch(
        f"/admin/detectors/{detector_id}",
        headers=OWNER,
        json={"enabled": False, "min_confidence": 0.9},
    )
    assert patched.status_code == 200
    assert patched.json()["enabled"] == 0


def test_dictionaries_teams_keys_and_settings(client: TestClient) -> None:
    dictionary = client.post(
        "/admin/dictionaries",
        headers=OWNER,
        json={"name": "project-names", "terms": ["aurora", "borealis"]},
    )
    assert dictionary.status_code == 200
    assert dictionary.json()["term_count"] == 2
    assert client.get("/admin/dictionaries", headers=OWNER).status_code == 200

    team = client.post("/admin/teams", headers=OWNER, json={"name": "payments"})
    assert team.status_code == 200
    key = client.post(
        "/admin/keys", headers=OWNER, json={"team": "payments", "name": "ci-key"}
    )
    assert key.status_code == 200
    assert key.json()["key"].startswith("fg-live-")

    settings = client.patch(
        "/admin/settings", headers=OWNER, json={"audit_retention_days": 45}
    )
    assert settings.status_code == 200
    assert settings.json()["audit_retention_days"] == 45


def test_admin_events_are_recorded(client: TestClient) -> None:
    client.post("/admin/teams", headers=OWNER, json={"name": "events-check"})
    events = client.get("/admin/events", headers=OWNER).json()["items"]
    assert any(event["action"] == "team.create" for event in events)


def test_admin_docs_published(client: TestClient) -> None:
    docs = client.get("/admin/docs")
    assert docs.status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/admin/requests" in schema["paths"]
    assert "/admin/policies" in schema["paths"]

"""AC-M5-02: RBAC is enforced server-side on every Admin API endpoint."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from frostglass.main import create_app

OWNER = {"Authorization": "Bearer fg-admin-owner-token"}
AUDITOR = {"Authorization": "Bearer fg-admin-auditor-token"}
VIEWER = {"Authorization": "Bearer fg-admin-viewer-token"}


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    yield TestClient(create_app())


# (method, path, json) for write/privileged endpoints.
_WRITES = [
    ("post", "/admin/teams", {"name": "t"}),
    ("post", "/admin/users", {"email": "a@b.co", "name": "A", "role": "viewer"}),
    ("post", "/admin/keys", {"team": "test-team", "name": "k"}),
    ("post", "/admin/policies", {"yaml": "version: 2\nrules: []\n"}),
    ("post", "/admin/policies/1/activate", None),
    ("patch", "/admin/settings", {"audit_retention_days": 30}),
]


@pytest.mark.parametrize(("method", "path", "body"), _WRITES)
def test_ac_m5_02_viewer_rejected_on_writes(
    client: TestClient, method: str, path: str, body: dict | None
) -> None:
    response = client.request(method, path, headers=VIEWER, json=body)
    assert response.status_code == 403


@pytest.mark.parametrize(("method", "path", "body"), _WRITES)
def test_ac_m5_02_missing_session_rejected(
    client: TestClient, method: str, path: str, body: dict | None
) -> None:
    response = client.request(method, path, json=body)
    assert response.status_code == 401


def test_ac_m5_02_invalid_session_rejected(client: TestClient) -> None:
    response = client.get("/admin/stats/overview", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_ac_m5_02_auditor_cannot_write_policy(client: TestClient) -> None:
    response = client.post(
        "/admin/policies", headers=AUDITOR, json={"yaml": "version: 2\nrules: []\n"}
    )
    assert response.status_code == 403


def test_ac_m5_02_auditor_cannot_manage_access(client: TestClient) -> None:
    response = client.post("/admin/teams", headers=AUDITOR, json={"name": "t"})
    assert response.status_code == 403


def test_ac_m5_02_viewer_cannot_read_trace_but_owner_can(client: TestClient) -> None:
    # Viewer lacks READ_TRACE entirely: rejected before any row lookup.
    missing = client.get("/admin/requests/does-not-exist/trace", headers=VIEWER)
    assert missing.status_code == 403
    # Owner holds READ_TRACE; the same unknown id is a 404, not a 403.
    owner = client.get("/admin/requests/does-not-exist/trace", headers=OWNER)
    assert owner.status_code == 404


def test_ac_m5_02_viewer_can_read_stats(client: TestClient) -> None:
    assert client.get("/admin/stats/overview", headers=VIEWER).status_code == 200

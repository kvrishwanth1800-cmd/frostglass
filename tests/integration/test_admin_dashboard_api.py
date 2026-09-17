"""M6 Admin API expansion: dashboard aggregates, team update, and settings.

These endpoints back the M6 dashboard pages (H.6.2) with real server-side
aggregates. RBAC stays server-side on every new endpoint (H.7); the negative
checks here mirror the M5 AC-M5-02 discipline for the new writes.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from frostglass.audit.models import DecisionTraceEntry, RequestRecord
from frostglass.audit.store import AuditStore
from frostglass.main import create_app

OWNER = {"Authorization": "Bearer fg-admin-owner-token"}
VIEWER = {"Authorization": "Bearer fg-admin-viewer-token"}
_NOW = datetime.now(UTC)


def _finding(entity_type: str, confidence: float, reported: bool = False) -> DecisionTraceEntry:
    return DecisionTraceEntry(
        entity_type=entity_type,
        detector="test",
        confidence=confidence,
        span=(0, 4),
        matched_rule_id="rule-1",
        action="pseudonymize",
        was_shadow=False,
        reason="seeded",
        value_hash="hash",
    )


def _seed(
    store: AuditStore,
    *,
    request_id: str,
    team: str,
    user: str,
    action: str,
    provider: str = "openai",
    model: str = "mock-model",
    cost_cents: int = 10,
    days_ago: int = 0,
    findings: tuple[DecisionTraceEntry, ...] = (),
) -> None:
    store.record_request(
        RequestRecord(
            id=request_id,
            tenant_id="default",
            team=team,
            user=user,
            ts=_NOW - timedelta(days=days_ago),
            model=model,
            provider=provider,
            action=action,
            policy_version=1,
            shadow=False,
            cost_cents=cost_cents,
            trace=findings,
        )
    )


@pytest.fixture()
def seeded_client() -> Iterator[TestClient]:
    app = create_app()
    store: AuditStore = app.state.audit_store
    # test-team: alice sends 3 flagged (PERSON) + 1 allowed; bob sends 1 flagged.
    _seed(
        store,
        request_id="t1",
        team="test-team",
        user="alice",
        action="masked",
        findings=(_finding("PERSON", 0.95),),
    )
    _seed(
        store,
        request_id="t2",
        team="test-team",
        user="alice",
        action="masked",
        findings=(_finding("PERSON", 0.65),),
    )
    _seed(
        store,
        request_id="t3",
        team="test-team",
        user="alice",
        action="blocked",
        findings=(_finding("AWS_ACCESS_KEY", 0.99, reported=True),),
    )
    _seed(store, request_id="t4", team="test-team", user="alice", action="allowed")
    _seed(
        store,
        request_id="t5",
        team="test-team",
        user="bob",
        action="masked",
        provider="anthropic",
        model="claude",
        cost_cents=25,
        findings=(_finding("EMAIL", 0.9),),
    )
    # other-team traffic must never appear for a team-scoped viewer.
    _seed(
        store,
        request_id="o1",
        team="other-team",
        user="mallory",
        action="blocked",
        findings=(_finding("PERSON", 0.99),),
    )
    # mark one finding reported so the false-positive widget has a numerator.
    trace = store.request_trace("default", "t3", None)
    store.report_false_positive("default", trace[0]["id"], None)
    yield TestClient(app)


def test_stats_overview_returns_full_aggregate_payload(seeded_client: TestClient) -> None:
    body = seeded_client.get("/admin/stats/overview?range=30d", headers=OWNER).json()
    # backward-compatible M5 keys still present
    assert body["range"] == "30d"
    assert "by_action" in body and "sampled" in body
    # new aggregate keys
    assert body["totals"]["last_30d"] == 6
    assert body["by_action"]["masked"] == 3
    assert body["by_action"]["blocked"] == 2
    assert body["sensitive_requests"] == 5
    top_entities = {row["entity_type"]: row["count"] for row in body["top_entity_types"]}
    assert top_entities["PERSON"] == 3
    providers = {row["provider"]: row["cost_cents"] for row in body["spend_by_provider"]}
    assert providers["anthropic"] == 25


def test_ac_m6_01_top_users_orders_most_flagged_first(seeded_client: TestClient) -> None:
    body = seeded_client.get("/admin/stats/top-users?range=7d", headers=OWNER).json()
    assert body["items"][0]["user"] == "alice"
    assert body["items"][0]["flagged"] == 3


def test_detections_confidence_buckets(seeded_client: TestClient) -> None:
    body = seeded_client.get("/admin/stats/detections?range=30d", headers=OWNER).json()
    person = body["by_entity_type"]["PERSON"]
    assert person["total"] == 3
    # two PERSON findings at >= 0.9 (0.95 and 0.99), all three at >= 0.6
    assert person["at_confidence"]["0.9"] == 2
    assert person["at_confidence"]["0.6"] == 3


def test_false_positive_rate(seeded_client: TestClient) -> None:
    body = seeded_client.get("/admin/stats/false-positives?range=30d", headers=OWNER).json()
    assert body["reported"] == 1
    assert body["total"] == 5
    assert 0.0 < body["rate"] < 1.0


def test_viewer_aggregates_are_team_scoped(seeded_client: TestClient) -> None:
    # viewer belongs to other-team; must see only other-team's single request.
    body = seeded_client.get("/admin/stats/overview?range=30d", headers=VIEWER).json()
    assert body["totals"]["last_30d"] == 1
    users = seeded_client.get("/admin/stats/top-users", headers=VIEWER).json()["items"]
    assert {row["user"] for row in users} == {"mallory"}


def test_request_view_exposes_cost_and_tokens(seeded_client: TestClient) -> None:
    items = seeded_client.get("/admin/requests?limit=100", headers=OWNER).json()["items"]
    sample = next(item for item in items if item["id"] == "t5")
    assert sample["cost_cents"] == 25
    assert "prompt_tokens" in sample and "provider_latency_ms" in sample


def test_team_update_round_trip(seeded_client: TestClient) -> None:
    teams = seeded_client.get("/admin/teams", headers=OWNER).json()["items"]
    team_id = next(team["id"] for team in teams if team["name"] == "test-team")
    updated = seeded_client.patch(
        f"/admin/teams/{team_id}",
        headers=OWNER,
        json={"shadow_mode": False, "allowed_models": ["gpt-4o", "claude"]},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["shadow_mode"] is False
    assert body["allowed_models"] == ["gpt-4o", "claude"]


def test_settings_sso_provider_and_vault(seeded_client: TestClient) -> None:
    patched = seeded_client.patch(
        "/admin/settings",
        headers=OWNER,
        json={"sso_enabled": True, "sso_provider": "okta", "sso_client_id": "abc123"},
    ).json()
    assert patched["sso_enabled"] is True
    assert patched["sso_provider"] == "okta"

    stored = seeded_client.post(
        "/admin/settings/providers",
        headers=OWNER,
        json={"provider": "openai", "secret": "supersecret1234"},
    )
    assert stored.status_code == 200
    assert stored.json()["key_last4"] == "1234"
    settings = seeded_client.get("/admin/settings", headers=OWNER).json()
    creds = {item["provider"]: item for item in settings["provider_credentials"]}
    assert creds["openai"]["key_last4"] == "1234"
    # the raw secret must never be echoed back anywhere in the settings payload
    assert "supersecret" not in str(settings)

    rotated = seeded_client.post("/admin/settings/vault/rotate", headers=OWNER).json()
    assert rotated["vault_key_rotated_at"] is not None


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("patch", "/admin/teams/any-id", {"shadow_mode": True}),
        ("post", "/admin/settings/providers", {"provider": "openai", "secret": "supersecret1234"}),
        ("post", "/admin/settings/vault/rotate", None),
    ],
)
def test_viewer_cannot_perform_new_writes(
    seeded_client: TestClient, method: str, path: str, payload: dict | None
) -> None:
    response = seeded_client.request(method.upper(), path, headers=VIEWER, json=payload)
    assert response.status_code == 403


@pytest.mark.parametrize(
    "path",
    ["/admin/stats/top-users", "/admin/stats/detections", "/admin/stats/false-positives"],
)
def test_new_reads_require_a_session(seeded_client: TestClient, path: str) -> None:
    assert seeded_client.get(path).status_code == 401

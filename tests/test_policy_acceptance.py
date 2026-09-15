"""M4 gateway and dry-run acceptance coverage."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from frostglass.main import create_app

_KEY = {"Authorization": "Bearer fg-live-test-key"}


def test_ac_m4_03_gateway_records_active_policy_version() -> None:
    response = TestClient(create_app()).post(
        "/v1/chat/completions",
        headers=_KEY,
        json={"model": "mock-model", "messages": [{"role": "user", "content": "Hello"}]},
    )
    assert response.status_code == 200
    assert response.headers["x-frostglass-policy-version"] == "1"


def test_ac_m4_04_dry_run_returns_findings_decisions_rules_and_masked_text() -> None:
    response = TestClient(create_app()).post(
        "/admin/policy/test",
        json={"text": "Contact Avery Stone with AKIA1234567890ABCDEF."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["policy_version"] == 1
    assert body["masked_text"] is None
    assert {item["entity_type"] for item in body["findings"]} >= {
        "AWS_ACCESS_KEY",
        "CUSTOMER_NAME",
    }
    secret = next(item for item in body["findings"] if item["entity_type"] == "AWS_ACCESS_KEY")
    assert secret["action"] == "block"
    assert secret["rule_id"] == "block-secrets"
    assert "AKIA1234567890ABCDEF" not in str(body)


def test_ac_m4_02_shadow_mode_forwards_original_payload_and_logs_counterfactual() -> None:
    from frostglass.detection.engine import DetectionEngine
    from frostglass.detection.models import CandidateSpan, DetectionContext
    from frostglass.gateway.pipeline import ProviderRegistry
    from frostglass.masking.consistency import ConsistencyManager
    from frostglass.masking.engine import MaskingEngine
    from frostglass.masking.models import MaskingContext
    from frostglass.masking.vault import EncryptedVault
    from frostglass.policy.defaults import build_policy_engine

    @dataclass(frozen=True)
    class Detector:
        def detect(self, text: str, context: DetectionContext) -> tuple[CandidateSpan, ...]:
            start = text.index("Avery Stone")
            return (CandidateSpan("PERSON", start, start + 11, 0.99, "test"),)

    vault = EncryptedVault("YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
    registry = ProviderRegistry(
        DetectionEngine((Detector(),)),
        MaskingEngine(ConsistencyManager(vault), "x" * 32),
        vault,
        build_policy_engine(),
    )
    payload = {"model": "mock-model", "messages": [{"role": "user", "content": "Avery Stone"}]}
    context = registry.detect(
        payload,
        DetectionContext("team", "x" * 32),
        MaskingContext("team", "request", "session"),
        "user",
        "team",
        True,
    )
    assert context.shadow is True
    assert context.decisions[0].decision.action.value == "pseudonymize"
    assert registry.mask(payload, context) == payload

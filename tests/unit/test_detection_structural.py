"""Tests for structural and secret detection layers."""

from __future__ import annotations

from frostglass.detection.models import DetectionContext
from frostglass.detection.secrets import SecretDetector
from frostglass.detection.structural import StructuralDetector

CONTEXT = DetectionContext("test-team", "tenant-salt-for-tests-must-be-long-enough")


def test_structural_detector_validates_cards_and_ibans() -> None:
    text = "Card 4111 1111 1111 1111 and IBAN GB82 WEST 1234 5698 7654 32"
    findings = StructuralDetector().detect(text, CONTEXT)
    assert {finding.entity_type for finding in findings} == {"CREDIT_CARD", "IBAN"}
    assert all(finding.confidence == 0.95 for finding in findings)


def test_structural_detector_preserves_spaced_and_dashed_card_spans() -> None:
    text = "Spaced 4111 1111 1111 1111, dashed 4111-1111-1111-1111."
    findings = [
        finding
        for finding in StructuralDetector().detect(text, CONTEXT)
        if finding.entity_type == "CREDIT_CARD"
    ]
    assert [text[finding.start : finding.end] for finding in findings] == [
        "4111 1111 1111 1111",
        "4111-1111-1111-1111",
    ]


def test_structural_detector_rejects_invalid_ip_and_card() -> None:
    text = "Bad 4111 1111 1111 1112 with 999.999.999.999"
    assert StructuralDetector().detect(text, CONTEXT) == []


def test_secret_detector_finds_known_formats_and_suppresses_hashes() -> None:
    key = "AKIAIOSFODNN7EXAMPLE"
    digest = "a" * 64
    findings = SecretDetector().detect(f"key={key} digest={digest}", CONTEXT)
    assert [finding.entity_type for finding in findings] == ["AWS_ACCESS_KEY"]


def test_entropy_detection_finds_random_token() -> None:
    token = "c29tZS1sb25nLXJhbmRvbS10b2tlbi13aXRoLWVudHJvcHk"
    findings = SecretDetector().detect(f"token={token}", CONTEXT)
    assert "HIGH_ENTROPY_TOKEN" in {finding.entity_type for finding in findings}

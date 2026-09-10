"""Tests for the Presidio and spaCy NER layer."""

from __future__ import annotations

from frostglass.detection.models import DetectionContext
from frostglass.detection.ner import NerDetector

CONTEXT = DetectionContext("test-team", "tenant-salt-for-tests-must-be-long-enough")
_PERSON_CORPUS_NAMES = (
    "Maria Garcia",
    "James Chen",
    "Robert Nakamura",
    "Fatima Ali",
    "Priya Patel",
    "Kwame Mensah",
    "Sofia Ivanova",
)


def test_ner_detects_person_location_and_organization() -> None:
    findings = NerDetector().detect("John Smith works at Acme in London.", CONTEXT)
    entity_types = {finding.entity_type for finding in findings}
    assert {"PERSON", "LOCATION", "ORGANIZATION"}.issubset(entity_types)


def test_ner_recognizes_unambiguous_person_corpus_names() -> None:
    detector = NerDetector()
    for name in _PERSON_CORPUS_NAMES:
        findings = detector.detect(f"{name} submitted the report.", CONTEXT)
        assert "PERSON" in {finding.entity_type for finding in findings}, name

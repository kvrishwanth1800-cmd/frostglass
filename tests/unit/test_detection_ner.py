"""Tests for the Presidio and spaCy NER layer."""

from __future__ import annotations

from frostglass.detection.models import DetectionContext
from frostglass.detection.ner import NerDetector

CONTEXT = DetectionContext("test-team", "tenant-salt-for-tests-must-be-long-enough")


def test_ner_detects_person_location_and_organization() -> None:
    findings = NerDetector().detect("Avery Stone works at Acme in London.", CONTEXT)
    entity_types = {finding.entity_type for finding in findings}
    assert {"PERSON", "LOCATION", "ORGANIZATION"}.issubset(entity_types)

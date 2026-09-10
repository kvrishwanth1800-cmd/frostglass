"""Tests for the Presidio and spaCy NER layer."""

from __future__ import annotations

from frostglass.detection.models import DetectionContext
from frostglass.detection.ner import NerDetector

CONTEXT = DetectionContext("test-team", "tenant-salt-for-tests-must-be-long-enough")
_TEXT = "Avery Stone works at Acme in London."


def test_ner_detects_person_location_and_organization() -> None:
    findings = NerDetector().detect(_TEXT, CONTEXT)
    entity_types = {finding.entity_type for finding in findings}
    assert {"PERSON", "LOCATION", "ORGANIZATION"}.issubset(entity_types)


def test_person_diagnostic_distinguishes_nlp_threshold_and_mapping() -> None:
    detector = NerDetector()
    raw_results = detector._analyzer.analyze(text=_TEXT, language="en", score_threshold=0.0)
    raw_persons = [result for result in raw_results if result.entity_type == "PERSON"]
    assert raw_persons, f"NLP did not return PERSON at score_threshold=0.0: {raw_results!r}"

    above_floor = [result for result in raw_persons if result.score >= CONTEXT.ner_confidence_floor]
    assert above_floor, (
        "NLP returned PERSON below the configured confidence floor "
        f"{CONTEXT.ner_confidence_floor}: {raw_persons!r}"
    )

    mapped_persons = [
        finding for finding in detector.detect(_TEXT, CONTEXT) if finding.entity_type == "PERSON"
    ]
    assert mapped_persons, f"PERSON was lost in CandidateSpan mapping: {above_floor!r}"

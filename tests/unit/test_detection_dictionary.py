"""Tests for the Aho-Corasick dictionary layer."""

from __future__ import annotations

from time import perf_counter

from frostglass.detection.dictionary import DictionaryDetector, DictionaryTerm
from frostglass.detection.models import DetectionContext

CONTEXT = DetectionContext("test-team", "tenant-salt-for-tests-must-be-long-enough")


def test_dictionary_matches_case_insensitively_with_original_offsets() -> None:
    detector = DictionaryDetector(
        (DictionaryTerm("Frost Project", "PROJECT_CODENAME", "dictionary.projects"),)
    )
    text = "The FROST PROJECT is confidential."
    finding = detector.detect(text, CONTEXT)[0]
    assert text[finding.start : finding.end] == "FROST PROJECT"
    assert finding.entity_type == "PROJECT_CODENAME"


def test_dictionary_word_boundary_rejects_substrings() -> None:
    detector = DictionaryDetector(
        (DictionaryTerm("acme", "CUSTOMER_NAME", "dictionary.customers", "word_boundary"),)
    )
    assert len(detector.detect("acme is a customer", CONTEXT)) == 1
    assert detector.detect("macmecorp", CONTEXT) == ()


def test_dictionary_5000_terms_matches_without_regex_scan() -> None:
    terms = tuple(
        DictionaryTerm(f"customer-{index:04d}", "CUSTOMER_NAME", "dictionary.customers")
        for index in range(5000)
    )
    detector = DictionaryDetector(terms)
    text = "prefix customer-4999 suffix " * 50
    started = perf_counter()
    findings = detector.detect(text, CONTEXT)
    elapsed = perf_counter() - started
    assert len(findings) == 50
    assert elapsed < 0.25

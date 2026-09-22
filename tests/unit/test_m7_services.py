from __future__ import annotations

import sqlite3

import pytest

from frostglass.admin.custom_recognizers import UnsafePatternError, test_pattern, validate_pattern
from frostglass.admin.dictionary_store import DictionaryStore
from frostglass.admin.suggestions_engine import generate_suggestions


def test_dictionary_crud_csv_paste_and_immediate_match() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    store = DictionaryStore(connection)
    dictionary_id = store.create("tenant-a", "Company secrets", "word-boundary", "pseudonymize")
    assert store.add_terms("tenant-a", dictionary_id, ["Aurora", "Borealis"]) == 2
    assert store.import_csv("tenant-a", dictionary_id, "term\nCascade\nDelta\n") == 2
    term = store.terms("tenant-a", dictionary_id)[0]
    updated = store.update_term("tenant-a", dictionary_id, term.id, "Aurora-Prime", "PROJECT")
    assert updated.replacement == "PROJECT"
    assert [item.term for item in store.match("tenant-a", "send Aurora-Prime to Cascade")] == [
        "Aurora-Prime",
        "Cascade",
    ]
    store.remove_term("tenant-a", dictionary_id, term.id)
    assert "Aurora-Prime" not in [item.term for item in store.terms("tenant-a", dictionary_id)]


@pytest.mark.parametrize("pattern", ["(", "(a+)+$", "(a|aa)+$", ".*secret", "(?=secret)secret", "(foo)\\1"])
def test_regex_rejects_invalid_or_redos_prone_patterns(pattern: str) -> None:
    with pytest.raises(UnsafePatternError):
        validate_pattern(pattern)


def test_re2_bounded_match_for_backtracking_adversarial_shapes() -> None:
    sample = "a" * 50_000 + "!"
    for pattern in (r"(a+)+$", r"(a|aa)+$", r"a*a*a*a*a*!$"):
        result = test_pattern(pattern, sample)
        assert result.matched is False
        assert result.elapsed_ms < 1_000


def test_regex_safe_test_returns_match_spans() -> None:
    result = test_pattern(r"AKIA[0-9A-Z]{16}", "key AKIA1234567890ABCDEF")
    assert result.matched is True
    assert result.spans == [(4, 24)]
    assert result.elapsed_ms < 1_000


def test_suggestions_generate_all_four_m7_kinds() -> None:
    cards = generate_suggestions(
        {"PERSON": 3400, "ACCOUNT": 400},
        {"PERSON": "allow", "ACCOUNT": "block"},
        {"[A-Z]{12}": 210},
        {"block-secrets": 0.24},
    )
    assert {card.kind for card in cards} == {
        "unpoliced_detection",
        "recurring_unknown_pattern",
        "overblocking_warning",
        "context_loss_warning",
    }

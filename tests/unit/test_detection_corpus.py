"""Golden corpus expectations and raw-value safety checks."""

from __future__ import annotations

from tests.corpus.score import evaluate


def test_corpus_scores_meet_m2_accuracy_targets() -> None:
    scores = evaluate()
    assert scores["CREDIT_CARD"].recall >= 0.98
    assert scores["IBAN"].recall >= 0.98
    assert scores["AWS_ACCESS_KEY"].recall >= 0.98
    assert scores["CUSTOMER_NAME"].recall >= 0.99
    assert scores["PERSON"].recall >= 0.85
    assert scores["LOCATION"].recall >= 0.85
    assert scores["ORGANIZATION"].recall >= 0.85
    total_true_positive = sum(score.true_positive for score in scores.values())
    total_false_positive = sum(score.false_positive for score in scores.values())
    assert total_true_positive / (total_true_positive + total_false_positive) >= 0.90


def test_clean_control_has_at_most_two_percent_false_positives() -> None:
    scores = evaluate()
    total_false_positive = sum(score.false_positive for score in scores.values())
    assert total_false_positive <= 1

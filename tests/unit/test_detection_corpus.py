"""Golden corpus expectations and raw-value safety checks."""

from __future__ import annotations

from tests.corpus.score import evaluate


def test_corpus_scores_meet_m2_accuracy_targets() -> None:
    evaluation = evaluate()
    scores = evaluation.scores
    assert scores["CREDIT_CARD"].recall >= 0.98
    assert scores["IBAN"].recall >= 0.98
    assert scores["AWS_ACCESS_KEY"].recall >= 0.98
    assert scores["CUSTOMER_NAME"].recall >= 0.99
    assert scores["PERSON"].recall >= 0.85
    assert scores["LOCATION"].recall >= 0.85
    assert scores["ORGANIZATION"].recall >= 0.85
    assert evaluation.overall_precision >= 0.90


def test_clean_control_has_at_most_two_percent_false_positives() -> None:
    evaluation = evaluate()
    assert evaluation.clean_false_positive_rate <= 0.02

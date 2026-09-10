"""Score the synthetic M2 golden corpus without printing raw values."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from frostglass.detection.defaults import build_detection_engine
from frostglass.detection.models import DetectionContext

_ROOT = Path(__file__).parent
_CONTEXT = DetectionContext("corpus", "synthetic-corpus-tenant-salt-which-is-long-enough")
_PRECISION_TARGET = 0.90
_FALSE_POSITIVE_RATE_TARGET = 0.02
_STRUCTURED_TARGET = 0.98
_DICTIONARY_TARGET = 0.99
_NER_TARGET = 0.85
_TARGETS = {
    "AWS_ACCESS_KEY": _STRUCTURED_TARGET,
    "CREDIT_CARD": _STRUCTURED_TARGET,
    "CUSTOMER_NAME": _DICTIONARY_TARGET,
    "IBAN": _STRUCTURED_TARGET,
    "LOCATION": _NER_TARGET,
    "ORGANIZATION": _NER_TARGET,
    "PERSON": _NER_TARGET,
    "PROJECT_CODENAME": _DICTIONARY_TARGET,
}


@dataclass(frozen=True)
class Score:
    """Aggregate counts for one entity group."""

    true_positive: int
    false_positive: int
    false_negative: int

    @property
    def precision(self) -> float:
        total = self.true_positive + self.false_positive
        return self.true_positive / total if total else 1.0

    @property
    def recall(self) -> float:
        total = self.true_positive + self.false_negative
        return self.true_positive / total if total else 1.0


@dataclass(frozen=True)
class Evaluation:
    """Corpus scores, including clean-control false-positive evidence."""

    scores: dict[str, Score]
    clean_false_positives: int
    clean_examples: int

    @property
    def overall_precision(self) -> float:
        true_positives = sum(score.true_positive for score in self.scores.values())
        false_positives = sum(score.false_positive for score in self.scores.values())
        total = true_positives + false_positives
        return true_positives / total if total else 1.0

    @property
    def clean_false_positive_rate(self) -> float:
        return self.clean_false_positives / self.clean_examples if self.clean_examples else 0.0


def _documents(directory: str | None = None) -> list[dict[str, object]]:
    documents: list[dict[str, object]] = []
    if directory:
        paths = [_ROOT / directory / "documents.json"]
    else:
        paths = sorted(_ROOT.glob("*/documents.json"))
    for path in paths:
        documents.extend(json.loads(path.read_text(encoding="utf-8")))
    return documents


def _actual(engine: object, text: str) -> set[tuple[str, str]]:
    return {
        (finding.entity_type, text[finding.start : finding.end])
        for finding in engine.detect(text, _CONTEXT)  # type: ignore[attr-defined]
    }


def evaluate() -> Evaluation:
    """Return per-entity scores and clean-control false-positive evidence."""
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    engine = build_detection_engine()
    clean_documents = _documents("clean_control")
    clean_false_positives = 0

    for document in _documents():
        text = document["text"]
        expected = document["expected"]
        if not isinstance(text, str) or not isinstance(expected, list):
            raise ValueError("Invalid corpus document")
        labels = {(item["entity_type"], item["value"]) for item in expected}
        actual = _actual(engine, text)
        for entity_type, _ in actual & labels:
            counts[entity_type][0] += 1
        for entity_type, _ in actual - labels:
            counts[entity_type][1] += 1
        for entity_type, _ in labels - actual:
            counts[entity_type][2] += 1

        if document in clean_documents:
            clean_false_positives += len(actual)

    return Evaluation(
        scores={entity_type: Score(*values) for entity_type, values in sorted(counts.items())},
        clean_false_positives=clean_false_positives,
        clean_examples=len(clean_documents),
    )


def main() -> None:
    """Print the complete M2 acceptance table without raw detection values."""
    evaluation = evaluate()
    print("| Entity type | Recall | Target | Result |")
    print("|---|---:|---:|---|")
    for entity_type, score in evaluation.scores.items():
        target = _TARGETS.get(entity_type)
        if target is None:
            continue
        result = "PASS" if score.recall >= target else "FAIL"
        print(f"| {entity_type} | {score.recall:.2%} | >= {target:.0%} | {result} |")
    precision_result = "PASS" if evaluation.overall_precision >= _PRECISION_TARGET else "FAIL"
    false_positive_result = (
        "PASS"
        if evaluation.clean_false_positive_rate <= _FALSE_POSITIVE_RATE_TARGET
        else "FAIL"
    )
    print()
    print(
        "Overall precision: "
        f"{evaluation.overall_precision:.2%} (target >= {_PRECISION_TARGET:.0%}) "
        f"{precision_result}"
    )
    print(
        "Clean-control false-positive rate: "
        f"{evaluation.clean_false_positive_rate:.2%} "
        f"({evaluation.clean_false_positives}/{evaluation.clean_examples} examples, "
        f"target <= {_FALSE_POSITIVE_RATE_TARGET:.0%}) {false_positive_result}"
    )


if __name__ == "__main__":
    main()

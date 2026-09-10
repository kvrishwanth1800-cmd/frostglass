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


def _documents() -> list[dict[str, object]]:
    documents: list[dict[str, object]] = []
    for path in sorted(_ROOT.glob("*/documents.json")):
        documents.extend(json.loads(path.read_text(encoding="utf-8")))
    return documents


def evaluate() -> dict[str, Score]:
    """Return per-entity precision and recall for corpus labels."""
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    engine = build_detection_engine()
    for document in _documents():
        text = document["text"]
        expected = document["expected"]
        if not isinstance(text, str) or not isinstance(expected, list):
            raise ValueError("Invalid corpus document")
        labels = {(item["entity_type"], item["value"]) for item in expected}
        actual = {
            (finding.entity_type, text[finding.start : finding.end])
            for finding in engine.detect(text, _CONTEXT)
        }
        for entity_type, _ in actual & labels:
            counts[entity_type][0] += 1
        for entity_type, _ in actual - labels:
            counts[entity_type][1] += 1
        for entity_type, _ in labels - actual:
            counts[entity_type][2] += 1
    return {entity_type: Score(*values) for entity_type, values in sorted(counts.items())}


def main() -> None:
    """Print a CI-friendly precision and recall table."""
    scores = evaluate()
    print("| Entity type | Precision | Recall |")
    print("|---|---:|---:|")
    for entity_type, score in scores.items():
        print(f"| {entity_type} | {score.precision:.2%} | {score.recall:.2%} |")


if __name__ == "__main__":
    main()

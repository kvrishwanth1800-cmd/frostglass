"""Deterministic merging for detector spans."""

from __future__ import annotations

from collections.abc import Iterable

from frostglass.detection.models import CandidateSpan


def _rank(span: CandidateSpan) -> tuple[float, int, int, str]:
    return (span.confidence, span.specificity, span.end - span.start, span.detector)


def merge_spans(candidates: Iterable[CandidateSpan]) -> tuple[CandidateSpan, ...]:
    """Keep the highest-ranked non-overlapping spans, ordered by text offset."""
    ranked = sorted(candidates, key=lambda span: (-span.start, span.end))
    selected: list[CandidateSpan] = []
    for candidate in sorted(ranked, key=_rank, reverse=True):
        if all(candidate.end <= span.start or candidate.start >= span.end for span in selected):
            selected.append(candidate)
    return tuple(sorted(selected, key=lambda span: (span.start, span.end)))

"""Composition root for the four detection layers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

from frostglass.detection.hashing import value_hash
from frostglass.detection.merge import merge_spans
from frostglass.detection.models import CandidateSpan, DetectionContext, Finding


class Detector(Protocol):
    """A layer that returns offsets only, never persisted raw values."""

    def detect(self, text: str, context: DetectionContext) -> Sequence[CandidateSpan]:
        """Return candidate spans for one text value."""


class DetectionEngine:
    """Run all detector layers and convert spans to safe findings."""

    def __init__(self, detectors: Iterable[Detector]) -> None:
        self._detectors = tuple(detectors)

    def detect(self, text: str, context: DetectionContext) -> tuple[Finding, ...]:
        candidates: list[CandidateSpan] = []
        for detector in self._detectors:
            candidates.extend(detector.detect(text, context))
        valid = (
            span
            for span in candidates
            if 0 <= span.start < span.end <= len(text) and 0.0 <= span.confidence <= 1.0
        )
        return tuple(
            Finding(
                entity_type=span.entity_type,
                start=span.start,
                end=span.end,
                confidence=span.confidence,
                detector=span.detector,
                value_hash=value_hash(text[span.start : span.end], context.tenant_salt),
            )
            for span in merge_spans(valid)
        )

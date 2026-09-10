"""Tenant dictionary matching using Aho-Corasick."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import ahocorasick

from frostglass.detection.models import CandidateSpan, DetectionContext

MatchMode = Literal["exact", "word_boundary"]


@dataclass(frozen=True, slots=True)
class DictionaryTerm:
    """One configured term. Terms never enter a finding."""

    value: str
    entity_type: str
    detector: str
    mode: MatchMode = "exact"
    confidence: float = 0.9


class DictionaryDetector:
    """Case-insensitive O(n) matching for immutable dictionary terms."""

    def __init__(self, terms: tuple[DictionaryTerm, ...]) -> None:
        self._automaton: ahocorasick.Automaton = ahocorasick.Automaton()
        for term in terms:
            normalized = term.value.casefold()
            if normalized:
                existing = self._automaton.get(normalized, [])
                existing.append(term)
                self._automaton.add_word(normalized, existing)
        self._automaton.make_automaton()

    @staticmethod
    def _has_word_boundary(text: str, start: int, end: int) -> bool:
        before = text[start - 1] if start else ""
        after = text[end] if end < len(text) else ""
        return (not before or not before.isalnum()) and (not after or not after.isalnum())

    def detect(self, text: str, _: DetectionContext) -> tuple[CandidateSpan, ...]:
        normalized = text.casefold()
        findings: list[CandidateSpan] = []
        for end, terms in self._automaton.iter(normalized):
            for term in terms:
                start = end - len(term.value) + 1
                stop = end + 1
                if term.mode == "word_boundary" and not self._has_word_boundary(text, start, stop):
                    continue
                findings.append(
                    CandidateSpan(
                        entity_type=term.entity_type,
                        start=start,
                        end=stop,
                        confidence=term.confidence,
                        detector=term.detector,
                        specificity=4,
                    )
                )
        return tuple(findings)

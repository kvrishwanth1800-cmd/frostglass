"""Raw-value-safe types used by the detection engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CandidateSpan:
    """A detector result before the engine hashes its matched text."""

    entity_type: str
    start: int
    end: int
    confidence: float
    detector: str
    specificity: int = 0


@dataclass(frozen=True, slots=True)
class Finding:
    """A safe detection record. Matched text is intentionally not retained."""

    entity_type: str
    start: int
    end: int
    confidence: float
    detector: str
    value_hash: str


@dataclass(frozen=True, slots=True)
class DetectionContext:
    """Request-scoped detector configuration without request content."""

    tenant_id: str
    tenant_salt: str
    ner_confidence_floor: float = 0.6

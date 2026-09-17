"""Presidio and spaCy backed named-entity recognition."""

from __future__ import annotations

from collections.abc import Sequence
from functools import cache

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngine, NlpEngineProvider

from frostglass.detection.models import CandidateSpan, DetectionContext

_ENTITY_MAP = {
    "PERSON": "PERSON",
    "LOCATION": "LOCATION",
    "ORGANIZATION": "ORGANIZATION",
    "NRP": "NRP",
    "MEDICAL_LICENSE": "MEDICAL",
    "MEDICAL": "MEDICAL",
}


@cache
def _shared_nlp_engine(model_name: str) -> NlpEngine:
    """Build the spaCy NLP engine once per model and share it process-wide.

    The spaCy model weights are large (~650MB) and read-only at inference
    time, so every AnalyzerEngine can safely reuse a single loaded copy.
    Without this, each create_app() loaded its own copy and the copies
    stacked until the process was killed.
    """
    provider = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": model_name}],
        }
    )
    return provider.create_engine()


class NerDetector:
    """Long-lived Presidio analyzer using the configured spaCy model."""

    def __init__(self, model_name: str = "en_core_web_lg") -> None:
        self._analyzer = AnalyzerEngine(
            nlp_engine=_shared_nlp_engine(model_name), supported_languages=["en"]
        )

    def detect(self, text: str, context: DetectionContext) -> Sequence[CandidateSpan]:
        results = self._analyzer.analyze(
            text=text, language="en", score_threshold=context.ner_confidence_floor
        )
        return tuple(
            CandidateSpan(
                entity_type=_ENTITY_MAP[result.entity_type],
                start=result.start,
                end=result.end,
                confidence=result.score,
                detector="ner.presidio_spacy",
                specificity=1,
            )
            for result in results
            if result.entity_type in _ENTITY_MAP
        )

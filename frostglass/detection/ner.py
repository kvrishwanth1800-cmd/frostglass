"""Presidio and spaCy backed named-entity recognition."""

from __future__ import annotations

from collections.abc import Sequence

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from frostglass.detection.models import CandidateSpan, DetectionContext

_ENTITY_MAP = {
    "PERSON": "PERSON",
    "LOCATION": "LOCATION",
    "ORGANIZATION": "ORGANIZATION",
    "NRP": "NRP",
    "MEDICAL_LICENSE": "MEDICAL",
    "MEDICAL": "MEDICAL",
}


class NerDetector:
    """Long-lived Presidio analyzer using the configured spaCy model."""

    def __init__(self, model_name: str = "en_core_web_lg") -> None:
        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": model_name}],
            }
        )
        self._analyzer = AnalyzerEngine(
            nlp_engine=provider.create_engine(), supported_languages=["en"]
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

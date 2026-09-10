"""Default detector composition for runtime and corpus evaluation."""

from __future__ import annotations

from frostglass.detection.dictionary import DictionaryDetector, DictionaryTerm
from frostglass.detection.engine import DetectionEngine
from frostglass.detection.ner import NerDetector
from frostglass.detection.secrets import SecretDetector
from frostglass.detection.structural import StructuralDetector

_DEFAULT_TERMS = (
    DictionaryTerm("Orion Initiative", "PROJECT_CODENAME", "dictionary.default"),
    DictionaryTerm("Avery Stone", "CUSTOMER_NAME", "dictionary.default"),
)


def build_detection_engine() -> DetectionEngine:
    """Build the complete M2 detection engine with immutable default terms."""
    return DetectionEngine(
        (StructuralDetector(), SecretDetector(), DictionaryDetector(_DEFAULT_TERMS), NerDetector())
    )

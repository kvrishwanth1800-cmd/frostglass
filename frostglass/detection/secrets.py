"""Credential and high-entropy secret recognition."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence

from frostglass.detection.models import CandidateSpan, DetectionContext

_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("AWS_ACCESS_KEY", "secrets.aws", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "GITHUB_TOKEN",
        "secrets.github",
        re.compile(r"\bghp_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    ),
    ("SLACK_TOKEN", "secrets.slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("STRIPE_KEY", "secrets.stripe", re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("OPENAI_KEY", "secrets.openai", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("ANTHROPIC_KEY", "secrets.anthropic", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("JWT", "secrets.jwt", re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")),
    ("PRIVATE_KEY", "secrets.private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)
_TOKEN = re.compile(r"\b[A-Za-z0-9+/=_-]{24,}\b")
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE
)
_HEX_HASH = re.compile(r"^[0-9a-f]{32}|[0-9a-f]{40}|[0-9a-f]{64}$", re.IGNORECASE)


def shannon_entropy(token: str) -> float:
    """Calculate entropy for a token without retaining it outside this call."""
    length = len(token)
    return -sum((count / length) * math.log2(count / length) for count in Counter(token).values())


class SecretDetector:
    """Recognize known credentials and conservative high-entropy tokens."""

    def detect(self, text: str, _: DetectionContext) -> Sequence[CandidateSpan]:
        findings: list[CandidateSpan] = []
        covered: list[tuple[int, int]] = []
        for entity_type, detector, pattern in _PATTERNS:
            for match in pattern.finditer(text):
                findings.append(
                    CandidateSpan(entity_type, match.start(), match.end(), 0.98, detector, 10)
                )
                covered.append((match.start(), match.end()))
        for match in _TOKEN.finditer(text):
            token = match.group()
            if any(match.start() >= start and match.end() <= end for start, end in covered):
                continue
            if _UUID.fullmatch(token) or _HEX_HASH.fullmatch(token):
                continue
            if shannon_entropy(token) >= 4.0 and len(set(token)) >= 10:
                findings.append(
                    CandidateSpan(
                        "HIGH_ENTROPY_TOKEN", match.start(), match.end(), 0.7, "secrets.entropy", 3
                    )
                )
        return findings

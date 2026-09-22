"""Custom regular-expression recognizers backed by Google RE2.

Only the M7 custom-recognizer path uses RE2. Existing standard-library regular
expressions elsewhere remain unchanged. RE2 guarantees linear-time matching
and does not implement backtracking-only features such as lookarounds and
backreferences. A conservative syntax filter remains as defence in depth.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

import re2

_MAX_PATTERN_LENGTH = 256
_FORBIDDEN = (
    (r"\\[1-9]", "backreferences are not allowed"),
    (r"\(\?([=!<])", "lookarounds are not allowed"),
    (r"\([^)]*[+*][^)]*\)[+*{]", "nested quantifiers are not allowed"),
    (r"\([^)]*\|[^)]*\)[+*{]", "quantified alternation is not allowed"),
    (r"\.\*|\.\+", "unbounded wildcard repetition is not allowed"),
    (r"\{\d+,\}", "unbounded repetition is not allowed"),
)


class UnsafePatternError(ValueError):
    """Raised when a custom recognizer is invalid or outside the M7 grammar."""


@dataclass(frozen=True, slots=True)
class RegexTestResult:
    matched: bool
    spans: list[tuple[int, int]]
    elapsed_ms: float


def validate_pattern(pattern: str) -> Any:
    """Validate the M7 allowlist and compile with RE2, never Python ``re``."""
    if not pattern or len(pattern) > _MAX_PATTERN_LENGTH:
        raise UnsafePatternError("Pattern must be between 1 and 256 characters")
    for expression, reason in _FORBIDDEN:
        if re.search(expression, pattern):
            raise UnsafePatternError(reason)
    try:
        return re2.compile(pattern)
    except Exception as error:
        raise UnsafePatternError(f"Invalid RE2 regular expression: {error}") from error


def test_pattern(pattern: str, sample: str) -> RegexTestResult:
    compiled = validate_pattern(pattern)
    started = time.perf_counter()
    spans = [(match.start(), match.end()) for match in compiled.finditer(sample)]
    elapsed_ms = (time.perf_counter() - started) * 1000
    return RegexTestResult(bool(spans), spans, elapsed_ms)

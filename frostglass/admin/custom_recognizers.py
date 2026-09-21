"""Safe custom regular-expression recognizers for M7.

Python's standard ``re`` engine has no execution timeout. This module uses a
conservative grammar: nested quantifiers, quantified alternation, lookarounds,
backreferences, and unbounded wildcard repetition are rejected before compile.
The allowlist intentionally favours predictable literal/token recognizers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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
    """Raised when a custom recognizer is invalid or unsafe for inline matching."""


@dataclass(frozen=True, slots=True)
class RegexTestResult:
    matched: bool
    spans: list[tuple[int, int]]


def validate_pattern(pattern: str) -> re.Pattern[str]:
    if not pattern or len(pattern) > _MAX_PATTERN_LENGTH:
        raise UnsafePatternError("Pattern must be between 1 and 256 characters")
    for expression, reason in _FORBIDDEN:
        if re.search(expression, pattern):
            raise UnsafePatternError(reason)
    try:
        return re.compile(pattern)
    except re.error as error:
        raise UnsafePatternError(f"Invalid regular expression: {error}") from error


def test_pattern(pattern: str, sample: str) -> RegexTestResult:
    compiled = validate_pattern(pattern)
    spans = [(match.start(), match.end()) for match in compiled.finditer(sample)]
    return RegexTestResult(bool(spans), spans)

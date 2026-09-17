"""Apply M3 masking modes to sorted, disjoint detection findings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256

from frostglass.detection.models import Finding
from frostglass.masking.consistency import ConsistencyManager
from frostglass.masking.models import MaskingContext, MaskingMode


class BlockedContentError(ValueError):
    """Raised when policy selects the block masking mode."""


@dataclass(frozen=True, slots=True)
class MaskingResult:
    """Masked content and the spans that must remain immune in this request."""

    text: str
    immune_spans: tuple[tuple[int, int], ...]


class MaskingEngine:
    """Transform findings without retaining raw values outside the vault."""

    def __init__(self, consistency: ConsistencyManager, tenant_salt: str) -> None:
        self._consistency = consistency
        self._tenant_salt = tenant_salt

    def mask(
        self,
        text: str,
        findings: tuple[Finding, ...],
        context: MaskingContext,
        modes: Mapping[tuple[int, int], MaskingMode],
    ) -> MaskingResult:
        """Mask sorted disjoint findings according to their per-finding modes.

        ``modes`` is keyed by each finding's ``(start, end)`` span so that two
        findings sharing an entity type but assigned different policy decisions
        never overwrite one another.
        """
        output: list[str] = []
        immune_spans: list[tuple[int, int]] = []
        cursor = 0
        tag_counts: dict[str, int] = {}
        for finding in findings:
            if finding.start < cursor or finding.end > len(text):
                raise ValueError("findings must be sorted, disjoint, and in range")
            output.append(text[cursor : finding.start])
            original = text[finding.start : finding.end]
            mode = modes.get((finding.start, finding.end), MaskingMode.PSEUDONYMIZE)
            replacement = self._replacement(
                mode,
                finding,
                original,
                context,
                tag_counts,
            )
            start = sum(len(part) for part in output)
            output.append(replacement)
            if mode in {MaskingMode.PSEUDONYMIZE, MaskingMode.TAG}:
                immune_spans.append((start, start + len(replacement)))
            cursor = finding.end
        output.append(text[cursor:])
        return MaskingResult("".join(output), tuple(immune_spans))

    def _replacement(
        self,
        mode: MaskingMode,
        finding: Finding,
        original: str,
        context: MaskingContext,
        tag_counts: dict[str, int],
    ) -> str:
        if mode is MaskingMode.ALLOW:
            return original
        if mode is MaskingMode.BLOCK:
            raise BlockedContentError(f"blocked {finding.entity_type}")
        if mode is MaskingMode.HASH:
            return "sha256:" + sha256(f"{self._tenant_salt}:{original}".encode()).hexdigest()[:16]
        if mode is MaskingMode.TAG:
            number = tag_counts.get(finding.entity_type, 0) + 1
            tag_counts[finding.entity_type] = number
            tag = finding.entity_type.removesuffix("_ADDRESS").replace("CREDIT_", "")
            return f"<{tag}_{number}>"
        return self._consistency.surrogate_for(
            context,
            finding.entity_type,
            original,
            finding.value_hash,
        )

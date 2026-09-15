"""Gateway provider routing, detection, masking, and fallback lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from frostglass.detection.engine import DetectionEngine
from frostglass.detection.models import DetectionContext, Finding
from frostglass.gateway.extract import TextLocation, extract_text, replace_text
from frostglass.gateway.providers.mock import MockProvider
from frostglass.masking.engine import MaskingEngine
from frostglass.masking.models import MaskingContext
from frostglass.masking.restore import restore_text
from frostglass.masking.vault import EncryptedVault


@dataclass(frozen=True)
class ProviderResult:
    payload: dict[str, Any]
    fallback_used: bool


@dataclass(frozen=True)
class LocatedFinding:
    """A safe finding associated with the payload location that was scanned."""

    location: TextLocation
    finding: Finding


@dataclass(frozen=True)
class GatewayRequestContext:
    """Request-scoped detection and reversible-masking state."""

    findings: tuple[LocatedFinding, ...]
    masking_context: MaskingContext


class ProviderRegistry:
    """Route models and apply the default M3 pseudonymization lifecycle."""

    def __init__(
        self,
        detection_engine: DetectionEngine,
        masking_engine: MaskingEngine,
        vault: EncryptedVault,
    ) -> None:
        self._detection_engine = detection_engine
        self._masking_engine = masking_engine
        self._vault = vault
        self.primary = MockProvider()
        self.fallback = MockProvider()
        self.failing_primary = MockProvider(fail=True)

    def _chain(self, model: str) -> list[MockProvider]:
        if model.startswith("fallback/"):
            return [self.failing_primary, self.fallback]
        return [self.primary, self.fallback]

    def detect(
        self,
        payload: dict[str, Any],
        detection_context: DetectionContext,
        masking_context: MaskingContext,
    ) -> GatewayRequestContext:
        """Scan every extracted request text value before provider routing."""
        findings = tuple(
            LocatedFinding(location, finding)
            for location in extract_text(payload)
            for finding in self._detection_engine.detect(location.text, detection_context)
        )
        return GatewayRequestContext(findings, masking_context)

    def mask(
        self, payload: dict[str, Any], request_context: GatewayRequestContext
    ) -> dict[str, Any]:
        """Mask each scanned text value without re-scanning generated surrogates."""
        by_text: dict[str, tuple[Finding, ...]] = {}
        for located in request_context.findings:
            found = by_text.get(located.location.text, ())
            by_text[located.location.text] = (*found, located.finding)

        def transform(text: str) -> str:
            findings = by_text.get(text, ())
            if not findings:
                return text
            result = self._masking_engine.mask(
                text,
                tuple(sorted(findings, key=lambda finding: finding.start)),
                request_context.masking_context,
                {},
            )
            return result.text

        return replace_text(payload, transform)

    def restore(
        self, payload: dict[str, Any], request_context: GatewayRequestContext
    ) -> dict[str, Any]:
        """Restore response values only from the request scope's encrypted vault."""
        reverse_map = self._vault.reverse_map(request_context.masking_context.scope_id)
        return replace_text(payload, lambda text: restore_text(text, reverse_map))

    async def complete(
        self,
        protocol: str,
        payload: dict[str, Any],
        request_context: GatewayRequestContext,
    ) -> ProviderResult:
        for index, provider in enumerate(self._chain(payload["model"])):
            try:
                response = await provider.complete(protocol, payload)
                return ProviderResult(self.restore(response, request_context), index > 0)
            except (TimeoutError, OSError):
                continue
        raise TimeoutError("all providers failed")

    async def stream(
        self, protocol: str, payload: dict[str, Any]
    ) -> tuple[AsyncIterator[str], bool]:
        for index, provider in enumerate(self._chain(payload["model"])):
            try:
                iterator = provider.stream(protocol, payload)
                first = await anext(iterator)

                async def with_first() -> AsyncIterator[str]:
                    yield first
                    async for event in iterator:
                        yield event

                return with_first(), index > 0
            except (TimeoutError, OSError):
                continue
        raise TimeoutError("all providers failed")

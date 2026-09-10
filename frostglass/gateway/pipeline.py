"""Gateway provider routing, detection, and fallback lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from frostglass.detection.engine import DetectionEngine
from frostglass.detection.models import DetectionContext, Finding
from frostglass.gateway.extract import TextLocation, extract_text
from frostglass.gateway.providers.mock import MockProvider


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
    """Request-scoped state shared by gateway lifecycle stages."""

    findings: tuple[LocatedFinding, ...]


class ProviderRegistry:
    """Routes model aliases through a deterministic provider fallback chain."""

    def __init__(self, detection_engine: DetectionEngine) -> None:
        self._detection_engine = detection_engine
        self.primary = MockProvider()
        self.fallback = MockProvider()
        self.failing_primary = MockProvider(fail=True)

    def _chain(self, model: str) -> list[MockProvider]:
        if model.startswith("fallback/"):
            return [self.failing_primary, self.fallback]
        return [self.primary, self.fallback]

    def detect(
        self, payload: dict[str, Any], detection_context: DetectionContext
    ) -> GatewayRequestContext:
        """Scan every extracted request text value before provider routing."""
        findings = tuple(
            LocatedFinding(location, finding)
            for location in extract_text(payload)
            for finding in self._detection_engine.detect(location.text, detection_context)
        )
        return GatewayRequestContext(findings=findings)

    async def complete(self, protocol: str, payload: dict[str, Any]) -> ProviderResult:
        for index, provider in enumerate(self._chain(payload["model"])):
            try:
                response = await provider.complete(protocol, payload)
                return ProviderResult(response, index > 0)
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

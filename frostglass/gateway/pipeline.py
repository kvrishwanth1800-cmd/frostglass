"""M1 provider routing and fallback lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from frostglass.gateway.providers.mock import MockProvider


@dataclass(frozen=True)
class ProviderResult:
    payload: dict[str, Any]
    fallback_used: bool


class ProviderRegistry:
    """Routes model aliases through a deterministic provider fallback chain."""

    def __init__(self) -> None:
        self.primary = MockProvider()
        self.fallback = MockProvider()
        self.failing_primary = MockProvider(fail=True)

    def _chain(self, model: str) -> list[MockProvider]:
        return [self.failing_primary, self.fallback] if model.startswith("fallback/") else [self.primary, self.fallback]

    async def complete(self, protocol: str, payload: dict[str, Any]) -> ProviderResult:
        for index, provider in enumerate(self._chain(payload["model"])):
            try:
                return ProviderResult(await provider.complete(protocol, payload), index > 0)
            except (TimeoutError, OSError):
                continue
        raise TimeoutError("all providers failed")

    async def stream(self, protocol: str, payload: dict[str, Any]) -> tuple[AsyncIterator[str], bool]:
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

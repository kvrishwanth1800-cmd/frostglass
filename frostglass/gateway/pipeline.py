"""Gateway provider routing, detection, policy, masking, and fallback lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from frostglass.detection.engine import DetectionEngine
from frostglass.detection.models import DetectionContext, Finding
from frostglass.gateway.extract import TextLocation, extract_text, replace_text
from frostglass.gateway.providers.mock import MockProvider
from frostglass.masking.engine import BlockedContentError, MaskingEngine
from frostglass.masking.models import MaskingContext, MaskingMode
from frostglass.masking.restore import restore_text
from frostglass.masking.vault import EncryptedVault
from frostglass.policy.engine import FindingDecision, PolicyEngine
from frostglass.policy.models import Action


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
    """Request-scoped detection, versioned decision, and masking state."""

    findings: tuple[LocatedFinding, ...]
    masking_context: MaskingContext
    decisions: tuple[FindingDecision, ...]
    policy_version: int
    shadow: bool

    @property
    def action(self) -> str:
        if self.shadow:
            return "shadow"
        if any(item.decision.action is Action.BLOCK for item in self.decisions):
            return "blocked"
        if any(item.decision.action is not Action.ALLOW for item in self.decisions):
            return "masked"
        return "allowed"


class ProviderRegistry:
    """Route models through detection, policy, and masking before providers."""

    def __init__(
        self,
        detection_engine: DetectionEngine,
        masking_engine: MaskingEngine,
        vault: EncryptedVault,
        policy_engine: PolicyEngine,
    ) -> None:
        self._detection_engine = detection_engine
        self._masking_engine = masking_engine
        self._vault = vault
        self._policy_engine = policy_engine
        self.primary = MockProvider()
        self.fallback = MockProvider()
        self.failing_primary = MockProvider(fail=True)

    def _chain(self, model: str) -> list[MockProvider]:
        if model.startswith("fallback/"):
            return [self.failing_primary, self.fallback]
        return [self.primary, self.fallback]

    def shadow_for_team(self, team: str) -> bool:
        """Read the durable per-team shadow setting for this request."""
        return self._policy_engine.shadow_for_team(team)

    def detect(
        self,
        payload: dict[str, Any],
        detection_context: DetectionContext,
        masking_context: MaskingContext,
        user: str,
        team: str,
        shadow: bool,
    ) -> GatewayRequestContext:
        """Scan and decide every extracted request text value before routing."""
        located = tuple(
            LocatedFinding(location, finding)
            for location in extract_text(payload)
            for finding in self._detection_engine.detect(location.text, detection_context)
        )
        decisions = self._policy_engine.evaluate(
            tuple(item.finding for item in located), user, team, payload["model"]
        )
        return GatewayRequestContext(
            located, masking_context, decisions, self._policy_engine.version, shadow
        )

    def mask(
        self, payload: dict[str, Any], request_context: GatewayRequestContext
    ) -> dict[str, Any]:
        """Apply decisions by payload location, never by duplicate text value."""
        if request_context.shadow:
            return payload
        if any(item.decision.action is Action.BLOCK for item in request_context.decisions):
            raise BlockedContentError("blocked by policy")
        by_path: dict[tuple[str | int, ...], list[tuple[Finding, MaskingMode]]] = {}
        for located, evaluated in zip(
            request_context.findings, request_context.decisions, strict=True
        ):
            by_path.setdefault(located.location.path, []).append(
                (located.finding, MaskingMode(evaluated.decision.action))
            )

        def walk(value: Any, path: tuple[str | int, ...]) -> Any:
            if isinstance(value, str):
                entries = by_path.get(path, [])
                if not entries:
                    return value
                findings = tuple(
                    item[0] for item in sorted(entries, key=lambda item: item[0].start)
                )
                modes = {(item[0].start, item[0].end): item[1] for item in entries}
                return self._masking_engine.mask(
                    value, findings, request_context.masking_context, modes
                ).text
            if isinstance(value, list):
                return [walk(child, path + (index,)) for index, child in enumerate(value)]
            if isinstance(value, dict):
                return {key: walk(child, path + (key,)) for key, child in value.items()}
            return value

        result = walk(payload, ())
        if not isinstance(result, dict):
            raise TypeError("gateway payload must remain an object")
        return result

    def restore(
        self, payload: dict[str, Any], request_context: GatewayRequestContext
    ) -> dict[str, Any]:
        """Restore response values only from the request scope's encrypted vault."""
        reverse_map = self._vault.reverse_map(request_context.masking_context.scope_id)
        return replace_text(payload, lambda text: restore_text(text, reverse_map))

    async def complete(
        self, protocol: str, payload: dict[str, Any], request_context: GatewayRequestContext
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

"""Fix 4 regression: same-type findings receive independent decisions end to end.

Asserts on the final masked payload that would be sent to the provider, not on
intermediate decision objects, so it proves the whole pipeline and masking path.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

from frostglass.detection.engine import DetectionEngine
from frostglass.detection.models import CandidateSpan, DetectionContext
from frostglass.gateway.pipeline import ProviderRegistry
from frostglass.masking.consistency import ConsistencyManager
from frostglass.masking.engine import MaskingEngine
from frostglass.masking.models import MaskingContext
from frostglass.masking.vault import EncryptedVault
from frostglass.policy.engine import PolicyEngine
from frostglass.policy.loader import PolicyStore
from frostglass.policy.models import Action, Rule, RuleSet


@dataclass(frozen=True)
class TwoPersonDetector:
    """Emit two PERSON spans at different confidences in one text value."""

    def detect(self, text: str, context: DetectionContext) -> tuple[CandidateSpan, ...]:
        spans: list[CandidateSpan] = []
        if "Alice" in text:
            start = text.index("Alice")
            spans.append(CandidateSpan("PERSON", start, start + 5, 0.99, "test"))
        if "Bob" in text:
            start = text.index("Bob")
            spans.append(CandidateSpan("PERSON", start, start + 3, 0.50, "test"))
        return tuple(spans)


def test_same_type_findings_get_independent_decisions() -> None:
    key = base64.b64encode(b"a" * 32).decode()
    vault = EncryptedVault(key)
    # A confidence-gated rule tags only the high-confidence PERSON; the
    # low-confidence PERSON falls through to the pseudonymize default.
    ruleset = RuleSet(
        version=1,
        default_action=Action.PSEUDONYMIZE,
        rules=(
            Rule(
                id="tag-confident-person",
                entity_types=frozenset({"PERSON"}),
                action=Action.TAG,
                min_confidence=0.9,
            ),
        ),
    )
    store = PolicyStore(":memory:", ruleset)
    store.set_shadow_for_team("team", False)
    registry = ProviderRegistry(
        DetectionEngine((TwoPersonDetector(),)),
        MaskingEngine(ConsistencyManager(vault), "x" * 32),
        vault,
        PolicyEngine(store),
    )
    payload = {
        "model": "mock-model",
        "messages": [{"role": "user", "content": "Alice and Bob"}],
    }
    context = registry.detect(
        payload,
        DetectionContext("team", "x" * 32),
        MaskingContext("team", "request", "session"),
        "user",
        "team",
        registry.shadow_for_team("team"),
    )
    masked = registry.mask(payload, context)
    content = masked["messages"][0]["content"]

    # High-confidence PERSON is tagged; low-confidence PERSON is pseudonymized,
    # not tagged. Collapsing by entity type would give both the same treatment.
    assert content.startswith("<PERSON_1> and ")
    assert "<PERSON_2>" not in content
    assert "Alice" not in content
    assert "Bob" not in content

"""Fix 3: every detected secret type defaults to block, not mask (H.2)."""

from __future__ import annotations

from frostglass.detection.models import Finding
from frostglass.detection.secrets import _PATTERNS
from frostglass.policy.defaults import build_policy_engine
from frostglass.policy.models import Action

# The full set of entity types the secret detector can emit.
SECRET_TYPES = {entity_type for entity_type, _, _ in _PATTERNS} | {"HIGH_ENTROPY_TOKEN"}


def test_every_detected_secret_type_blocks_by_default() -> None:
    engine = build_policy_engine()
    for entity_type in sorted(SECRET_TYPES):
        finding = Finding(entity_type, 0, 10, 0.98, "test", "hash")
        (evaluated,) = engine.evaluate((finding,), "user", "team", "model")
        assert evaluated.decision.action is Action.BLOCK, entity_type

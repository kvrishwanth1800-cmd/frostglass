"""Runtime default policy for Frostglass."""

from __future__ import annotations

from frostglass.policy.engine import PolicyEngine
from frostglass.policy.models import Action, Rule, RuleSet

_SECRET_TYPES = frozenset(
    {
        "AWS_ACCESS_KEY",
        "GITHUB_TOKEN",
        "PRIVATE_KEY",
        "JWT",
        "PASSWORD",
    }
)


def build_policy_engine() -> PolicyEngine:
    """Build the version-one safe default policy."""
    return PolicyEngine(
        RuleSet(
            version=1,
            default_action=Action.PSEUDONYMIZE,
            rules=(
                Rule(
                    id="block-secrets",
                    entity_types=_SECRET_TYPES,
                    action=Action.BLOCK,
                    min_confidence=0.7,
                    reason="Credentials must never leave the network.",
                ),
            ),
        )
    )

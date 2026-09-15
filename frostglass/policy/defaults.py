"""Runtime default policy for Frostglass."""

from __future__ import annotations

from frostglass.policy.engine import PolicyEngine
from frostglass.policy.loader import PolicyStore
from frostglass.policy.models import Action, Rule, RuleSet

_SECRET_TYPES = frozenset({"AWS_ACCESS_KEY", "GITHUB_TOKEN", "PRIVATE_KEY", "JWT", "PASSWORD"})


def default_ruleset() -> RuleSet:
    """Return the version-one safe default policy snapshot."""
    return RuleSet(
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


def build_policy_engine(database_path: str = ":memory:") -> PolicyEngine:
    """Build a policy engine backed by the configured durable policy database."""
    return PolicyEngine(PolicyStore(database_path, default_ruleset()))

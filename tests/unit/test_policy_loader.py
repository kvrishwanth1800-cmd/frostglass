"""YAML policy-loader tests for M4."""

from __future__ import annotations

from frostglass.policy.loader import load_yaml
from frostglass.policy.models import Action


def test_yaml_loader_creates_ruleset() -> None:
    ruleset = load_yaml(
        """
version: 2
default_action: allow
shadow_mode: false
rules:
  - id: team-person
    entity_types: [PERSON]
    action: pseudonymize
    min_confidence: 0.6
    scope: {teams: [support]}
    reason: Protect support conversations.
"""
    )
    assert ruleset.version == 2
    assert ruleset.default_action is Action.ALLOW
    assert ruleset.rules[0].scope.teams == frozenset({"support"})

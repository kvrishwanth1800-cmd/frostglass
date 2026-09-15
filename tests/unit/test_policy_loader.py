"""YAML and version-store tests for M4."""

from __future__ import annotations

import pytest

from frostglass.policy.loader import PolicyStore, load_yaml
from frostglass.policy.models import Action, RuleSet


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


def test_policy_versions_are_append_only_and_activatable() -> None:
    initial = RuleSet(1, Action.ALLOW, ())
    store = PolicyStore(initial)
    next_version = RuleSet(2, Action.PSEUDONYMIZE, ())
    store.write(next_version)
    store.activate(2)
    assert store.active is next_version
    with pytest.raises(ValueError):
        store.write(RuleSet(2, Action.BLOCK, ()))


def test_new_teams_default_to_shadow_mode() -> None:
    store = PolicyStore(RuleSet(1, Action.ALLOW, ()))
    assert store.shadow_for_team("new-team") is True

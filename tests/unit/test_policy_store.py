"""M4 durable policy-store coverage."""

from __future__ import annotations

import pytest

from frostglass.policy.defaults import default_ruleset
from frostglass.policy.loader import PolicyStore
from frostglass.policy.models import Action, RuleSet


def test_policy_versions_survive_store_reopen_and_are_immutable(tmp_path: object) -> None:
    database = str(tmp_path / "policies.sqlite3")  # type: ignore[operator]
    initial = default_ruleset()
    store = PolicyStore(database, initial)
    version_two = RuleSet(2, Action.ALLOW, ())
    store.write(version_two)
    store.activate(2)

    reopened = PolicyStore(database, initial)
    assert [item.version for item in reopened.versions()] == [1, 2]
    assert reopened.active.version == 2
    with pytest.raises(ValueError):
        reopened.write(RuleSet(2, Action.BLOCK, ()))


def test_new_teams_default_to_shadow_and_persist_explicit_setting(tmp_path: object) -> None:
    store = PolicyStore(str(tmp_path / "policies.sqlite3"), default_ruleset())  # type: ignore[operator]
    assert store.shadow_for_team("new-team") is True
    store.set_shadow_for_team("new-team", False)

    reopened = PolicyStore(str(tmp_path / "policies.sqlite3"), default_ruleset())  # type: ignore[operator]
    assert reopened.shadow_for_team("new-team") is False

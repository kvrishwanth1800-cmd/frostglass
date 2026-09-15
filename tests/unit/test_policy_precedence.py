"""AC-M4-01 exhaustive precedence tests."""

from __future__ import annotations

from itertools import product

import pytest

from frostglass.policy.models import Action, Rule, RuleSet, Scope, ScopeKind
from frostglass.policy.precedence import decide

_ACTIONS = tuple(Action)
_SCOPES = (
    Scope(),
    Scope(models=frozenset({"model"})),
    Scope(teams=frozenset({"team"})),
    Scope(users=frozenset({"user"})),
)


def _rule(rule_id: str, action: Action, scope: Scope) -> Rule:
    return Rule(rule_id, frozenset({"PERSON"}), action, scope=scope)


@pytest.mark.parametrize("first_action,second_action,first_scope,second_scope", product(_ACTIONS, _ACTIONS, _SCOPES, _SCOPES))
def test_ac_m4_01_precedence_covers_every_ordering_pair(
    first_action: Action, second_action: Action, first_scope: Scope, second_scope: Scope
) -> None:
    """Cover every 5x5 action pair and every 4x4 scope pair in both insertion orders."""
    first = _rule("first", first_action, first_scope)
    second = _rule("second", second_action, second_scope)
    ruleset = RuleSet(1, Action.ALLOW, (first, second))
    actual = decide(ruleset, "PERSON", 1.0, "user", "team", "model")
    matched = (first, second)
    blocks = tuple(rule for rule in matched if rule.action is Action.BLOCK)
    candidates = blocks or matched
    expected = max(
        candidates,
        key=lambda rule: (
            int(rule.scope.specificity),
            {
                Action.ALLOW: 0,
                Action.PSEUDONYMIZE: 1,
                Action.HASH: 2,
                Action.TAG: 3,
                Action.BLOCK: 4,
            }[rule.action],
        ),
    )
    assert actual.rule_id == expected.id
    assert actual.action is expected.action


def test_block_beats_more_specific_allow() -> None:
    decision = decide(
        RuleSet(
            4,
            Action.ALLOW,
            (
                _rule("global-block", Action.BLOCK, Scope()),
                _rule("user-allow", Action.ALLOW, Scope(users=frozenset({"user"}))),
            ),
        ),
        "PERSON",
        1.0,
        "user",
        "team",
        "model",
    )
    assert decision.rule_id == "global-block"
    assert decision.action is Action.BLOCK


def test_no_match_uses_default_action() -> None:
    decision = decide(RuleSet(3, Action.HASH, ()), "PERSON", 1.0, "user", "team", "model")
    assert decision.rule_id is None
    assert decision.action is Action.HASH


def test_scope_specificity_contract_is_ordered() -> None:
    assert tuple(ScopeKind) == (ScopeKind.GLOBAL, ScopeKind.MODEL, ScopeKind.TEAM, ScopeKind.USER)

"""Single source of truth for policy precedence."""

from __future__ import annotations

from frostglass.policy.models import Action, Decision, Rule, RuleSet, action_restrictiveness


def decide(
    ruleset: RuleSet, entity_type: str, confidence: float, user: str, team: str, model: str
) -> Decision:
    """Choose block first, then scope specificity, then restrictive action."""
    matched = [
        rule
        for rule in ruleset.rules
        if rule.matches(entity_type, confidence, user, team, model)
    ]
    if not matched:
        return Decision(
            ruleset.default_action,
            None,
            "No matching policy rule; applied default action.",
            ruleset.version,
        )
    block_rules = [rule for rule in matched if rule.action is Action.BLOCK]
    candidates = block_rules or matched
    candidates.sort(
        key=lambda rule: (int(rule.scope.specificity), action_restrictiveness(rule.action)),
        reverse=True,
    )
    winner = candidates[0]
    return Decision(winner.action, winner.id, winner.reason, ruleset.version)

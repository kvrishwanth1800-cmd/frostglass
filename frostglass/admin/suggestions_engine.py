"""Deterministic M7 suggestion generation from aggregate audit and policy facts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Suggestion:
    kind: str
    evidence: dict[str, Any]
    proposed_rule: dict[str, Any]


def generate_suggestions(
    entity_counts: dict[str, int],
    policy_actions: dict[str, str],
    unknown_patterns: dict[str, int],
    false_positive_rates: dict[str, float],
    *,
    minimum_frequency: int = 100,
    overblocking_rate: float = 0.1,
) -> list[Suggestion]:
    """Generate the four H.6.2 M7 card kinds from aggregate-only inputs."""
    cards: list[Suggestion] = []
    for entity_type, count in sorted(entity_counts.items()):
        action = policy_actions.get(entity_type, "allow")
        if count >= minimum_frequency and action == "allow":
            cards.append(Suggestion("unpoliced_detection", {"entity_type": entity_type, "count": count}, {"entity_type": entity_type, "action": "pseudonymize"}))
        if count >= minimum_frequency and action in {"tag", "block"}:
            cards.append(Suggestion("context_loss_warning", {"entity_type": entity_type, "count": count, "current_action": action}, {"entity_type": entity_type, "action": "pseudonymize"}))
    for pattern, count in sorted(unknown_patterns.items()):
        if count >= minimum_frequency:
            cards.append(Suggestion("recurring_unknown_pattern", {"pattern": pattern, "count": count}, {"recognizer_pattern": pattern, "action": "pseudonymize"}))
    for rule_id, rate in sorted(false_positive_rates.items()):
        if rate >= overblocking_rate:
            cards.append(Suggestion("overblocking_warning", {"rule_id": rule_id, "false_positive_rate": rate}, {"rule_id": rule_id, "change": "raise_min_confidence"}))
    return cards

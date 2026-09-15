"""YAML policy parsing and immutable version storage."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import yaml

from frostglass.policy.models import Action, Rule, RuleSet, Scope


def load_yaml(source: str) -> RuleSet:
    """Parse one policy YAML document into a validated immutable rule set."""
    document = yaml.safe_load(source)
    if not isinstance(document, Mapping):
        raise ValueError("policy YAML must be a mapping")
    version = document.get("version")
    if not isinstance(version, int) or version < 1:
        raise ValueError("policy version must be a positive integer")
    default_action = _action(document.get("default_action", "pseudonymize"))
    rules_value = document.get("rules", [])
    if not isinstance(rules_value, list):
        raise ValueError("policy rules must be a list")
    rules = tuple(_rule(raw) for raw in rules_value)
    if len({rule.id for rule in rules}) != len(rules):
        raise ValueError("policy rule IDs must be unique")
    shadow_mode = document.get("shadow_mode", False)
    if not isinstance(shadow_mode, bool):
        raise ValueError("shadow_mode must be boolean")
    return RuleSet(version, default_action, rules, shadow_mode)


def _action(value: object) -> Action:
    if not isinstance(value, str):
        raise ValueError("policy action must be a string")
    try:
        return Action(value)
    except ValueError as error:
        raise ValueError(f"unsupported policy action: {value}") from error


def _names(value: object, name: str) -> frozenset[str]:
    if value is None:
        return frozenset()
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"scope.{name} must be a list of non-empty strings")
    return frozenset(value)


def _rule(raw: object) -> Rule:
    if not isinstance(raw, Mapping):
        raise ValueError("each policy rule must be a mapping")
    rule_id = raw.get("id")
    entity_types = raw.get("entity_types")
    if not isinstance(rule_id, str) or not rule_id:
        raise ValueError("rule id must be a non-empty string")
    if not isinstance(entity_types, list) or not all(
        isinstance(item, str) and item for item in entity_types
    ):
        raise ValueError("rule entity_types must be a non-empty string list")
    confidence = raw.get("min_confidence", 0.0)
    if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("min_confidence must be between zero and one")
    scope_raw: Any = raw.get("scope", {})
    if not isinstance(scope_raw, Mapping):
        raise ValueError("rule scope must be a mapping")
    reason = raw.get("reason", "Matched policy rule.")
    consistency = raw.get("consistency")
    if not isinstance(reason, str) or not reason:
        raise ValueError("rule reason must be a non-empty string")
    if consistency is not None and consistency not in {"request", "session", "tenant"}:
        raise ValueError("consistency must be request, session, or tenant")
    return Rule(
        rule_id,
        frozenset(entity_types),
        _action(raw.get("action", "pseudonymize")),
        float(confidence),
        Scope(
            _names(scope_raw.get("users"), "users"),
            _names(scope_raw.get("teams"), "teams"),
            _names(scope_raw.get("models"), "models"),
        ),
        reason,
        consistency,
    )


class PolicyStore:
    """Append-only in-memory policy version repository for the M4 runtime."""

    def __init__(self, initial: RuleSet) -> None:
        self._versions: dict[int, RuleSet] = {initial.version: initial}
        self._active_version = initial.version

    @property
    def active(self) -> RuleSet:
        return self._versions[self._active_version]

    def versions(self) -> tuple[RuleSet, ...]:
        return tuple(self._versions[version] for version in sorted(self._versions))

    def write(self, candidate: RuleSet) -> RuleSet:
        """Append a new snapshot. Existing snapshots can never be mutated."""
        if candidate.version in self._versions:
            raise ValueError("policy version already exists")
        if candidate.version <= max(self._versions):
            raise ValueError("policy versions must increase")
        self._versions[candidate.version] = candidate
        return candidate

    def activate(self, version: int) -> RuleSet:
        if version not in self._versions:
            raise KeyError(version)
        self._active_version = version
        return self.active

    def shadow_for_team(self, team: str) -> bool:
        """New teams are shadow by default. Explicit team rules can enforce."""
        matching = [rule for rule in self.active.rules if team in rule.scope.teams]
        return self.active.shadow_mode if matching else True

"""Immutable policy rule and decision types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class Action(StrEnum):
    """Actions the policy engine can select for a finding."""

    ALLOW = "allow"
    PSEUDONYMIZE = "pseudonymize"
    HASH = "hash"
    TAG = "tag"
    BLOCK = "block"


class ScopeKind(IntEnum):
    """Scope ordering is part of the published precedence contract."""

    GLOBAL = 0
    MODEL = 1
    TEAM = 2
    USER = 3


@dataclass(frozen=True, slots=True)
class Scope:
    """Optional selectors that define where a rule applies."""

    users: frozenset[str] = frozenset()
    teams: frozenset[str] = frozenset()
    models: frozenset[str] = frozenset()

    def matches(self, user: str, team: str, model: str) -> bool:
        return (
            (not self.users or user in self.users)
            and (not self.teams or team in self.teams)
            and (not self.models or model in self.models)
        )

    @property
    def specificity(self) -> ScopeKind:
        if self.users:
            return ScopeKind.USER
        if self.teams:
            return ScopeKind.TEAM
        if self.models:
            return ScopeKind.MODEL
        return ScopeKind.GLOBAL


@dataclass(frozen=True, slots=True)
class Rule:
    """One immutable policy rule."""

    id: str
    entity_types: frozenset[str]
    action: Action
    min_confidence: float = 0.0
    scope: Scope = Scope()
    reason: str = "Matched policy rule."
    consistency: str | None = None

    def matches(
        self, entity_type: str, confidence: float, user: str, team: str, model: str
    ) -> bool:
        return (
            entity_type in self.entity_types
            and confidence >= self.min_confidence
            and self.scope.matches(user, team, model)
        )


@dataclass(frozen=True, slots=True)
class RuleSet:
    """An immutable, numbered policy snapshot."""

    version: int
    default_action: Action
    rules: tuple[Rule, ...]
    shadow_mode: bool = False


@dataclass(frozen=True, slots=True)
class Decision:
    """Explainable action chosen for one finding."""

    action: Action
    rule_id: str | None
    reason: str
    policy_version: int


_ACTION_RESTRICTIVENESS = {
    Action.ALLOW: 0,
    Action.PSEUDONYMIZE: 1,
    Action.HASH: 2,
    Action.TAG: 3,
    Action.BLOCK: 4,
}


def action_restrictiveness(action: Action) -> int:
    """Return the published action ordering for an equal scope."""
    return _ACTION_RESTRICTIVENESS[action]

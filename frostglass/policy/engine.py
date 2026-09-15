"""Policy evaluation over safe detection findings."""

from __future__ import annotations

from dataclasses import dataclass

from frostglass.detection.models import Finding
from frostglass.policy.loader import PolicyStore
from frostglass.policy.models import Decision, RuleSet
from frostglass.policy.precedence import decide


@dataclass(frozen=True, slots=True)
class FindingDecision:
    """A finding paired with its explainable, versioned policy decision."""

    finding: Finding
    decision: Decision
    policy_version: int


class PolicyEngine:
    """Decide actions without retaining the finding's raw matched value."""

    def __init__(self, source: RuleSet | PolicyStore) -> None:
        self._source = source

    @property
    def ruleset(self) -> RuleSet:
        return self._source.active if isinstance(self._source, PolicyStore) else self._source

    @property
    def version(self) -> int:
        return self.ruleset.version

    def shadow_for_team(self, team: str) -> bool:
        return self._source.shadow_for_team(team) if isinstance(self._source, PolicyStore) else True

    def evaluate(
        self, findings: tuple[Finding, ...], user: str, team: str, model: str
    ) -> tuple[FindingDecision, ...]:
        ruleset = self.ruleset
        return tuple(
            FindingDecision(
                finding,
                decide(ruleset, finding.entity_type, finding.confidence, user, team, model),
                ruleset.version,
            )
            for finding in findings
        )

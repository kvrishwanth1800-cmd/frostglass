"""Policy evaluation over safe detection findings."""

from __future__ import annotations

from dataclasses import dataclass

from frostglass.detection.models import Finding
from frostglass.policy.models import Decision, RuleSet
from frostglass.policy.precedence import decide


@dataclass(frozen=True, slots=True)
class FindingDecision:
    """A finding paired with its explainable policy decision."""

    finding: Finding
    decision: Decision


class PolicyEngine:
    """Decide actions without retaining the finding's raw matched value."""

    def __init__(self, ruleset: RuleSet) -> None:
        self._ruleset = ruleset

    @property
    def version(self) -> int:
        return self._ruleset.version

    def evaluate(
        self, findings: tuple[Finding, ...], user: str, team: str, model: str
    ) -> tuple[FindingDecision, ...]:
        return tuple(
            FindingDecision(
                finding,
                decide(self._ruleset, finding.entity_type, finding.confidence, user, team, model),
            )
            for finding in findings
        )

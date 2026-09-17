"""Policy evaluation over safe detection findings."""

from __future__ import annotations

from dataclasses import dataclass

from frostglass.detection.models import Finding
from frostglass.policy.loader import PolicyStore, load_yaml
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

    def versions(self) -> tuple[RuleSet, ...]:
        """Return every stored policy version, or just the static ruleset."""
        if isinstance(self._source, PolicyStore):
            return self._source.versions()
        return (self._source,)

    def add_version(self, source: str) -> RuleSet:
        """Parse and persist a new immutable policy version from YAML."""
        if not isinstance(self._source, PolicyStore):
            raise RuntimeError("policy versions are read-only for a static ruleset")
        return self._source.write(load_yaml(source))

    def activate(self, version: int) -> RuleSet:
        """Activate a stored policy version by number."""
        if not isinstance(self._source, PolicyStore):
            raise RuntimeError("policy activation is unavailable for a static ruleset")
        return self._source.activate(version)

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

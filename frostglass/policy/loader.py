"""Policy parsing and SQLite-backed immutable policy storage."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from frostglass.policy.models import Action, Rule, RuleSet, Scope


def load_yaml(source: str) -> RuleSet:
    """Parse one policy YAML document into a validated immutable rule set."""
    document = yaml.safe_load(source)
    if not isinstance(document, Mapping):
        raise ValueError("policy YAML must be a mapping")
    return _ruleset_from_raw(document)


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
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, int | float)
        or not 0.0 <= float(confidence) <= 1.0
    ):
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


def _ruleset_from_raw(raw: Mapping[str, object]) -> RuleSet:
    version = raw.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError("policy version must be a positive integer")
    rules_value = raw.get("rules", [])
    if not isinstance(rules_value, list):
        raise ValueError("policy rules must be a list")
    rules = tuple(_rule(item) for item in rules_value)
    if len({rule.id for rule in rules}) != len(rules):
        raise ValueError("policy rule IDs must be unique")
    shadow_mode = raw.get("shadow_mode", False)
    if not isinstance(shadow_mode, bool):
        raise ValueError("shadow_mode must be boolean")
    return RuleSet(version, _action(raw.get("default_action", "pseudonymize")), rules, shadow_mode)


def _serialize(ruleset: RuleSet) -> str:
    return json.dumps(
        {
            "version": ruleset.version,
            "default_action": ruleset.default_action.value,
            "shadow_mode": ruleset.shadow_mode,
            "rules": [
                {
                    "id": rule.id,
                    "entity_types": sorted(rule.entity_types),
                    "action": rule.action.value,
                    "min_confidence": rule.min_confidence,
                    "scope": {
                        "users": sorted(rule.scope.users),
                        "teams": sorted(rule.scope.teams),
                        "models": sorted(rule.scope.models),
                    },
                    "reason": rule.reason,
                    "consistency": rule.consistency,
                }
                for rule in ruleset.rules
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _deserialize(payload: str) -> RuleSet:
    raw = json.loads(payload)
    if not isinstance(raw, dict):
        raise ValueError("stored policy payload must be an object")
    return _ruleset_from_raw(raw)


class PolicyStore:
    """SQLite repository for immutable policy snapshots and team shadow settings."""

    def __init__(self, database_path: str, initial: RuleSet) -> None:
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS policy_versions (
                version INTEGER PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS policy_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                active_version INTEGER NOT NULL REFERENCES policy_versions(version)
            );
            CREATE TABLE IF NOT EXISTS team_policy_settings (
                team TEXT PRIMARY KEY,
                shadow_mode INTEGER NOT NULL CHECK (shadow_mode IN (0, 1))
            );
            """
        )
        self._connection.execute(
            "INSERT OR IGNORE INTO policy_versions(version, payload) VALUES (?, ?)",
            (initial.version, _serialize(initial)),
        )
        self._connection.execute(
            "INSERT OR IGNORE INTO policy_state(id, active_version) VALUES (1, ?)",
            (initial.version,),
        )
        self._connection.commit()

    @property
    def active(self) -> RuleSet:
        row = self._connection.execute(
            """
            SELECT policy_versions.payload FROM policy_state
            JOIN policy_versions ON policy_versions.version = policy_state.active_version
            WHERE policy_state.id = 1
            """
        ).fetchone()
        if row is None:
            raise RuntimeError("policy store has no active policy")
        return _deserialize(row[0])

    def versions(self) -> tuple[RuleSet, ...]:
        rows = self._connection.execute(
            "SELECT payload FROM policy_versions ORDER BY version"
        ).fetchall()
        return tuple(_deserialize(row[0]) for row in rows)

    def write(self, candidate: RuleSet) -> RuleSet:
        active_versions = self._connection.execute(
            "SELECT MAX(version) FROM policy_versions"
        ).fetchone()
        latest = active_versions[0]
        if latest is not None and candidate.version <= latest:
            raise ValueError("policy versions must increase and cannot be overwritten")
        self._connection.execute(
            "INSERT INTO policy_versions(version, payload) VALUES (?, ?)",
            (candidate.version, _serialize(candidate)),
        )
        self._connection.commit()
        return candidate

    def activate(self, version: int) -> RuleSet:
        if (
            self._connection.execute(
                "SELECT 1 FROM policy_versions WHERE version = ?", (version,)
            ).fetchone()
            is None
        ):
            raise KeyError(version)
        self._connection.execute(
            "UPDATE policy_state SET active_version = ? WHERE id = 1", (version,)
        )
        self._connection.commit()
        return self.active

    def shadow_for_team(self, team: str) -> bool:
        row = self._connection.execute(
            "SELECT shadow_mode FROM team_policy_settings WHERE team = ?", (team,)
        ).fetchone()
        return True if row is None else bool(row[0])

    def set_shadow_for_team(self, team: str, enabled: bool) -> None:
        self._connection.execute(
            """
            INSERT INTO team_policy_settings(team, shadow_mode) VALUES (?, ?)
            ON CONFLICT(team) DO UPDATE SET shadow_mode = excluded.shadow_mode
            """,
            (team, enabled),
        )
        self._connection.commit()

"""Raw-value-safe audit records for the M5 durable audit layer.

Nothing in this module carries a raw matched value. Findings are recorded by
offset, entity type, salted value hash, and decision only, so the audit
database can never become a plaintext archive of company secrets (H.5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DecisionTraceEntry:
    """One finding's explainable, versioned decision. No raw value."""

    entity_type: str
    detector: str
    confidence: float
    span: tuple[int, int]
    matched_rule_id: str | None
    action: str
    was_shadow: bool
    reason: str
    value_hash: str


@dataclass(frozen=True, slots=True)
class RequestRecord:
    """A single audited request plus its decision trace."""

    id: str
    tenant_id: str
    team: str
    user: str
    ts: datetime
    model: str
    provider: str
    action: str
    policy_version: int
    shadow: bool
    blocked_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_cents: int | None = None
    latency_ms: int | None = None
    provider_latency_ms: int | None = None
    status_code: int | None = None
    fallback_used: bool | None = None
    trace: tuple[DecisionTraceEntry, ...] = field(default_factory=tuple)

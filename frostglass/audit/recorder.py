"""Derive raw-value-safe audit rows from the gateway decision context."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from frostglass.audit.capture import ContentCapture
from frostglass.audit.models import DecisionTraceEntry, RequestRecord
from frostglass.audit.store import AuditStore
from frostglass.gateway.pipeline import GatewayRequestContext


class AuditRecorder:
    """Record each gateway request as safe metadata plus a decision trace."""

    def __init__(
        self, store: AuditStore, tenant_id: str, capture: ContentCapture | None = None
    ) -> None:
        self._store = store
        self._tenant_id = tenant_id
        self._capture = capture

    def record(
        self,
        *,
        user: str,
        team: str,
        model: str,
        provider: str,
        request_context: GatewayRequestContext,
        status_code: int,
        blocked_reason: str | None = None,
        latency_ms: int | None = None,
        provider_latency_ms: int | None = None,
        fallback_used: bool | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        cost_cents: int | None = None,
        masked_payload: dict[str, Any] | None = None,
    ) -> str:
        """Persist one request. Returns the generated audit request id."""
        request_id = uuid.uuid4().hex
        trace = tuple(
            DecisionTraceEntry(
                entity_type=located.finding.entity_type,
                detector=located.finding.detector,
                confidence=located.finding.confidence,
                span=(located.finding.start, located.finding.end),
                matched_rule_id=evaluated.decision.rule_id,
                action=str(evaluated.decision.action),
                was_shadow=request_context.shadow,
                reason=evaluated.decision.reason,
                value_hash=located.finding.value_hash,
            )
            for located, evaluated in zip(
                request_context.findings, request_context.decisions, strict=True
            )
        )
        record = RequestRecord(
            id=request_id,
            tenant_id=self._tenant_id,
            team=team,
            user=user,
            ts=datetime.now(UTC),
            model=model,
            provider=provider,
            action=request_context.action,
            policy_version=request_context.policy_version,
            shadow=request_context.shadow,
            blocked_reason=blocked_reason,
            status_code=status_code,
            latency_ms=latency_ms,
            provider_latency_ms=provider_latency_ms,
            fallback_used=fallback_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_cents=cost_cents,
            trace=trace,
        )
        sealed_capture = None
        if self._capture is not None and masked_payload is not None and not request_context.shadow:
            sealed_capture = self._capture.seal(masked_payload)
        self._store.record_request(record, sealed_capture)
        return request_id

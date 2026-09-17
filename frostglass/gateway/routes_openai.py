"""OpenAI-compatible gateway routes."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse

from frostglass.audit.recorder import AuditRecorder
from frostglass.detection.models import DetectionContext
from frostglass.errors import gateway_error
from frostglass.gateway.auth import Principal, VirtualKeyStore
from frostglass.gateway.budget import Limits
from frostglass.gateway.pipeline import GatewayRequestContext, ProviderRegistry
from frostglass.masking.engine import BlockedContentError
from frostglass.masking.models import MaskingContext


def _headers(
    request_id: str, fallback_used: bool, request_context: GatewayRequestContext
) -> dict[str, str]:
    entity_types = sorted({located.finding.entity_type for located in request_context.findings})
    return {
        "X-Frostglass-Request-Id": request_id,
        "X-Frostglass-Action": request_context.action,
        "X-Frostglass-Entities": json.dumps(entity_types),
        "X-Frostglass-Policy-Version": str(request_context.policy_version),
        "X-Frostglass-Fallback-Used": str(fallback_used).lower(),
    }


def _validate_model(payload: dict[str, Any], allowed_models: frozenset[str]) -> None:
    model = payload.get("model")
    if not isinstance(model, str):
        raise gateway_error(400, "'model' is required", "invalid_request_error")
    if "*" not in allowed_models and model not in allowed_models:
        raise gateway_error(403, "Model is not allowed for this key", "permission_error")


def record_request(
    recorder: AuditRecorder | None,
    provider: str,
    principal: Principal,
    payload: dict[str, Any],
    request_context: GatewayRequestContext,
    started: float,
    *,
    status_code: int = 200,
    blocked_reason: str | None = None,
    fallback_used: bool | None = None,
    masked_payload: dict[str, Any] | None = None,
) -> str | None:
    """Record one request via the audit recorder. Returns the audit id."""
    if recorder is None:
        return None
    model = payload.get("model")
    return recorder.record(
        user=principal.user,
        team=principal.team,
        model=model if isinstance(model, str) else "unknown",
        provider=provider,
        request_context=request_context,
        status_code=status_code,
        blocked_reason=blocked_reason,
        fallback_used=fallback_used,
        latency_ms=int((perf_counter() - started) * 1000),
        masked_payload=masked_payload,
    )


def create_router(
    key_store: VirtualKeyStore,
    limits: Limits,
    providers: ProviderRegistry,
    tenant_salt: str,
    recorder: AuditRecorder | None = None,
) -> APIRouter:
    """Create OpenAI routes bound to one application instance."""
    router = APIRouter()

    async def handle(
        payload: dict[str, Any], authorization: str | None, request: Request
    ) -> JSONResponse | StreamingResponse:
        started = perf_counter()
        principal = key_store.resolve(authorization)
        _validate_model(payload, principal.allowed_models)
        limits.check(principal)
        request_id = request.headers.get("X-Request-Id", "fg-m5-request")
        request_context = providers.detect(
            payload,
            DetectionContext(tenant_id=principal.team, tenant_salt=tenant_salt),
            MaskingContext(principal.team, request_id, request_id),
            principal.user,
            principal.team,
            providers.shadow_for_team(principal.team),
        )
        try:
            masked_payload = providers.mask(payload, request_context)
        except BlockedContentError as error:
            record_request(
                recorder,
                "openai",
                principal,
                payload,
                request_context,
                started,
                status_code=403,
                blocked_reason=str(error),
            )
            raise gateway_error(403, str(error), "policy_blocked") from error
        if payload.get("stream") is True:
            stream, fallback_used = await providers.stream("openai", masked_payload)
            audit_id = record_request(
                recorder,
                "openai",
                principal,
                payload,
                request_context,
                started,
                fallback_used=fallback_used,
                masked_payload=masked_payload,
            )

            async def events() -> AsyncIterator[str]:
                async for event in stream:
                    yield event

            limits.record_spend(principal)
            return StreamingResponse(
                events(),
                media_type="text/event-stream",
                headers=_headers(audit_id or request_id, fallback_used, request_context),
            )
        result = await providers.complete("openai", masked_payload, request_context)
        limits.record_spend(principal)
        audit_id = record_request(
            recorder,
            "openai",
            principal,
            payload,
            request_context,
            started,
            fallback_used=result.fallback_used,
            masked_payload=masked_payload,
        )
        return JSONResponse(
            result.payload,
            headers=_headers(audit_id or request_id, result.fallback_used, request_context),
        )

    @router.post("/v1/chat/completions", response_model=None)
    async def chat_completions(
        request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse | StreamingResponse:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise gateway_error(400, "Request body must be an object", "invalid_request_error")
        return await handle(payload, authorization, request)

    @router.post("/v1/embeddings", response_model=None)
    async def embeddings(
        request: Request, authorization: str | None = Header(default=None)
    ) -> JSONResponse | StreamingResponse:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise gateway_error(400, "Request body must be an object", "invalid_request_error")
        return await handle(payload, authorization, request)

    return router

"""Anthropic-compatible gateway routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse

from frostglass.audit.recorder import AuditRecorder
from frostglass.detection.models import DetectionContext
from frostglass.errors import gateway_error
from frostglass.gateway.auth import VirtualKeyStore
from frostglass.gateway.budget import Limits
from frostglass.gateway.pipeline import ProviderRegistry
from frostglass.gateway.routes_openai import _headers, _validate_model, record_request
from frostglass.masking.engine import BlockedContentError
from frostglass.masking.models import MaskingContext


def create_router(
    key_store: VirtualKeyStore,
    limits: Limits,
    providers: ProviderRegistry,
    tenant_salt: str,
    recorder: AuditRecorder | None = None,
) -> APIRouter:
    """Create Anthropic routes bound to one application instance."""
    router = APIRouter()

    @router.post("/v1/messages", response_model=None)
    async def messages(
        request: Request,
        x_api_key: str | None = Header(default=None, alias="x-api-key"),
    ) -> JSONResponse | StreamingResponse:
        payload: Any = await request.json()
        if not isinstance(payload, dict):
            raise gateway_error(400, "Request body must be an object", "invalid_request_error")
        started = perf_counter()
        principal = key_store.resolve(f"Bearer {x_api_key}" if x_api_key else None)
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
                "anthropic",
                principal,
                payload,
                request_context,
                started,
                status_code=403,
                blocked_reason=str(error),
            )
            raise gateway_error(403, str(error), "policy_blocked") from error
        if payload.get("stream") is True:
            stream, fallback_used = await providers.stream("anthropic", masked_payload)
            audit_id = record_request(
                recorder,
                "anthropic",
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
        result = await providers.complete("anthropic", masked_payload, request_context)
        limits.record_spend(principal)
        audit_id = record_request(
            recorder,
            "anthropic",
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

    return router

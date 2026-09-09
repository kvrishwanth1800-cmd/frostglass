"""Anthropic-compatible gateway routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse

from frostglass.errors import gateway_error
from frostglass.gateway.auth import VirtualKeyStore
from frostglass.gateway.budget import Limits
from frostglass.gateway.pipeline import ProviderRegistry
from frostglass.gateway.routes_openai import _headers, _validate_model

router = APIRouter()


def configure(key_store: VirtualKeyStore, limits: Limits, providers: ProviderRegistry) -> None:
    @router.post("/v1/messages")
    async def messages(request: Request, x_api_key: str | None = Header(default=None, alias="x-api-key")) -> JSONResponse | StreamingResponse:
        payload: Any = await request.json()
        if not isinstance(payload, dict):
            raise gateway_error(400, "Request body must be an object", "invalid_request_error")
        principal = key_store.resolve(f"Bearer {x_api_key}" if x_api_key else None)
        _validate_model(payload, principal.allowed_models)
        limits.check(principal)
        request_id = request.headers.get("X-Request-Id", "fg-m1-request")
        if payload.get("stream") is True:
            stream, fallback_used = await providers.stream("anthropic", payload)

            async def events() -> AsyncIterator[str]:
                async for event in stream:
                    yield event

            limits.record_spend(principal)
            return StreamingResponse(events(), media_type="text/event-stream", headers=_headers(request_id, fallback_used, principal.shadow_mode))
        result = await providers.complete("anthropic", payload)
        limits.record_spend(principal)
        return JSONResponse(result.payload, headers=_headers(request_id, result.fallback_used, principal.shadow_mode))

"""OpenAI-compatible gateway routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse

from frostglass.errors import gateway_error
from frostglass.gateway.auth import VirtualKeyStore
from frostglass.gateway.budget import Limits
from frostglass.gateway.pipeline import ProviderRegistry

router = APIRouter()


def _headers(request_id: str, fallback_used: bool, shadow: bool) -> dict[str, str]:
    action = "shadow" if shadow else "allowed"
    return {"X-Frostglass-Request-Id": request_id, "X-Frostglass-Action": action, "X-Frostglass-Entities": "[]", "X-Frostglass-Policy-Version": "m1", "X-Frostglass-Fallback-Used": str(fallback_used).lower()}


def _validate_model(payload: dict[str, Any], allowed_models: frozenset[str]) -> None:
    model = payload.get("model")
    if not isinstance(model, str):
        raise gateway_error(400, "'model' is required", "invalid_request_error")
    if "*" not in allowed_models and model not in allowed_models:
        raise gateway_error(403, "Model is not allowed for this key", "permission_error")


def configure(key_store: VirtualKeyStore, limits: Limits, providers: ProviderRegistry) -> None:
    async def handle(payload: dict[str, Any], authorization: str | None, request: Request) -> JSONResponse | StreamingResponse:
        principal = key_store.resolve(authorization)
        _validate_model(payload, principal.allowed_models)
        limits.check(principal)
        request_id = request.headers.get("X-Request-Id", "fg-m1-request")
        if payload.get("stream") is True:
            stream, fallback_used = await providers.stream("openai", payload)

            async def events() -> AsyncIterator[str]:
                async for event in stream:
                    yield event

            limits.record_spend(principal)
            return StreamingResponse(events(), media_type="text/event-stream", headers=_headers(request_id, fallback_used, principal.shadow_mode))
        result = await providers.complete("openai", payload)
        limits.record_spend(principal)
        return JSONResponse(result.payload, headers=_headers(request_id, result.fallback_used, principal.shadow_mode))

    @router.post("/v1/chat/completions")
    async def chat_completions(request: Request, authorization: str | None = Header(default=None)) -> JSONResponse | StreamingResponse:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise gateway_error(400, "Request body must be an object", "invalid_request_error")
        return await handle(payload, authorization, request)

    @router.post("/v1/embeddings")
    async def embeddings(request: Request, authorization: str | None = Header(default=None)) -> JSONResponse | StreamingResponse:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise gateway_error(400, "Request body must be an object", "invalid_request_error")
        return await handle(payload, authorization, request)

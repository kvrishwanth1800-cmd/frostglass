"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from frostglass.config import Settings
from frostglass.errors import GatewayError
from frostglass.gateway.auth import default_key_store
from frostglass.gateway.budget import Limits
from frostglass.gateway.pipeline import ProviderRegistry
from frostglass.gateway.routes_anthropic import configure as configure_anthropic
from frostglass.gateway.routes_anthropic import router as anthropic_router
from frostglass.gateway.routes_openai import configure as configure_openai
from frostglass.gateway.routes_openai import router as openai_router
from frostglass.observability.metrics import router as metrics_router


def create_app() -> FastAPI:
    """Create the application after validating security-critical configuration."""
    settings = Settings()
    app = FastAPI(title="Frostglass", version=settings.version)
    key_store, limits, providers = default_key_store(), Limits(), ProviderRegistry()
    configure_openai(key_store, limits, providers)
    configure_anthropic(key_store, limits, providers)

    @app.exception_handler(GatewayError)
    async def gateway_exception(_: Request, error: GatewayError) -> JSONResponse:
        return JSONResponse(error.body, status_code=error.status_code, headers=error.headers)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": settings.version}

    app.include_router(openai_router)
    app.include_router(anthropic_router)
    app.include_router(metrics_router)
    return app


app = create_app()

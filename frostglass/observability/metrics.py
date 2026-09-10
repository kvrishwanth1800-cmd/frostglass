"""Minimal Prometheus exposition for gateway requests."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

_METRICS = (
    "# HELP frostglass_gateway_requests_total Gateway requests\n"
    "# TYPE frostglass_gateway_requests_total counter\n"
    "frostglass_gateway_requests_total 0\n"
)


@router.get("/metrics", include_in_schema=False)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(_METRICS)

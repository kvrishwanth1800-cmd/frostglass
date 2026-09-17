"""FastAPI application factory."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse

from frostglass.admin.rbac import Role
from frostglass.admin.routes_admin import create_router as create_admin_router
from frostglass.admin.routes_policies import PolicyTestRequest
from frostglass.admin.routes_policies import create_router as create_policy_router
from frostglass.admin.store import AdminStore
from frostglass.audit.capture import ContentCapture
from frostglass.audit.recorder import AuditRecorder
from frostglass.audit.store import AuditStore
from frostglass.config import Settings
from frostglass.detection.defaults import build_detection_engine
from frostglass.detection.models import DetectionContext
from frostglass.errors import GatewayError
from frostglass.gateway.auth import default_key_store
from frostglass.gateway.budget import Limits
from frostglass.gateway.pipeline import ProviderRegistry
from frostglass.gateway.routes_anthropic import create_router as create_anthropic_router
from frostglass.gateway.routes_openai import create_router as create_openai_router
from frostglass.masking.consistency import ConsistencyManager
from frostglass.masking.engine import BlockedContentError, MaskingEngine
from frostglass.masking.models import MaskingContext, MaskingMode
from frostglass.masking.vault import EncryptedVault
from frostglass.observability.metrics import router as metrics_router
from frostglass.policy.defaults import build_policy_engine

_DEFAULT_TENANT = "default"

# Local/dev + test session tokens, one per role. Production issues sessions via
# OIDC in M6; these seeds let the Admin API and its RBAC be exercised now.
_SESSION_TOKENS: dict[Role, str] = {
    Role.OWNER: "fg-admin-owner-token",
    Role.ADMIN: "fg-admin-admin-token",
    Role.AUDITOR: "fg-admin-auditor-token",
    Role.VIEWER: "fg-admin-viewer-token",
}


def _seed_admin(admin_store: AdminStore) -> None:
    """Seed a default tenant with one session per role and a few detectors."""
    admin_store.upsert_team(_DEFAULT_TENANT, "test-team", shadow_mode=True)
    admin_store.upsert_team(_DEFAULT_TENANT, "other-team", shadow_mode=True)
    for role, token in _SESSION_TOKENS.items():
        team = "other-team" if role is Role.VIEWER else "test-team"
        admin_store.create_session(token, f"{role}-user", _DEFAULT_TENANT, team, role)
    for name, kind in (("secret-scanner", "regex"), ("ner", "ml"), ("dictionary", "exact")):
        admin_store.seed_detector(_DEFAULT_TENANT, name, kind)


def create_app() -> FastAPI:
    """Create an application with request handlers isolated to this instance."""
    settings = Settings()
    app = FastAPI(title="Frostglass", version=settings.version)
    detection_engine = build_detection_engine()
    vault = EncryptedVault(settings.vault_encryption_key)
    masking_engine = MaskingEngine(ConsistencyManager(vault), settings.tenant_salt)
    policy_engine = build_policy_engine(settings.policy_database_path)
    key_store, limits = default_key_store(), Limits()
    providers = ProviderRegistry(detection_engine, masking_engine, vault, policy_engine)
    audit_store = AuditStore(settings.audit_database_path)
    admin_store = AdminStore(audit_store.connection)
    _seed_admin(admin_store)
    capture = (
        ContentCapture(
            settings.vault_encryption_key, timedelta(days=settings.capture_retention_days)
        )
        if settings.content_capture
        else None
    )
    recorder = AuditRecorder(audit_store, _DEFAULT_TENANT, capture)
    app.state.audit_store = audit_store
    app.state.admin_store = admin_store
    app.state.audit_recorder = recorder

    async def dry_run(body: Any) -> dict[str, Any]:
        """Run the detect/decide/mask sandbox with no provider call (H.7 test)."""
        request = body if isinstance(body, PolicyTestRequest) else PolicyTestRequest(**body)
        findings = detection_engine.detect(
            request.text,
            DetectionContext(tenant_id=request.team, tenant_salt=settings.tenant_salt),
        )
        evaluations = policy_engine.evaluate(
            findings, request.user, request.team, request.model
        )
        modes = {
            (item.finding.start, item.finding.end): MaskingMode(item.decision.action)
            for item in evaluations
        }
        context = MaskingContext(request.team, "policy-test", "policy-test")
        try:
            masked_text: str | None = masking_engine.mask(
                request.text, findings, context, modes
            ).text
        except BlockedContentError:
            masked_text = None
        return {
            "policy_version": policy_engine.version,
            "findings": [
                {
                    "entity_type": item.finding.entity_type,
                    "confidence": item.finding.confidence,
                    "detector": item.finding.detector,
                    "span": [item.finding.start, item.finding.end],
                    "action": str(item.decision.action),
                    "rule_id": item.decision.rule_id,
                    "reason": item.decision.reason,
                }
                for item in evaluations
            ],
            "masked_text": masked_text,
        }

    @app.exception_handler(GatewayError)
    async def gateway_exception(_: Request, error: GatewayError) -> JSONResponse:
        return JSONResponse(error.body, status_code=error.status_code, headers=error.headers)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": settings.version}

    @app.get("/admin/docs", include_in_schema=False)
    async def admin_docs() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url="/openapi.json", title="Frostglass Admin API"
        )

    app.include_router(
        create_openai_router(key_store, limits, providers, settings.tenant_salt, recorder)
    )
    app.include_router(
        create_anthropic_router(key_store, limits, providers, settings.tenant_salt, recorder)
    )
    app.include_router(
        create_policy_router(detection_engine, policy_engine, masking_engine, settings.tenant_salt)
    )
    app.include_router(create_admin_router(audit_store, admin_store, policy_engine, dry_run))
    app.include_router(metrics_router)
    return app


app = create_app()

"""Admin API routes. RBAC is enforced server-side on every endpoint (H.7)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Body, Header, Query
from pydantic import BaseModel, Field

from frostglass.admin.pagination import decode_cursor, encode_cursor
from frostglass.admin.rbac import AdminIdentity, Permission, Role
from frostglass.admin.store import AdminStore
from frostglass.audit.store import AuditStore
from frostglass.errors import gateway_error
from frostglass.policy.engine import PolicyEngine

_MAX_LIMIT = 100

DryRunHandler = Callable[[Any], Awaitable[dict[str, Any]]]


class TeamCreate(BaseModel):
    name: str = Field(min_length=1)
    shadow_mode: bool = True
    monthly_budget_cents: int = 0
    rate_limit_rpm: int = 60
    allowed_models: list[str] = Field(default_factory=list)


class TeamUpdate(BaseModel):
    shadow_mode: bool | None = None
    monthly_budget_cents: int | None = Field(default=None, ge=0)
    rate_limit_rpm: int | None = Field(default=None, ge=0)
    allowed_models: list[str] | None = None


class UserCreate(BaseModel):
    email: str = Field(min_length=3)
    name: str = Field(min_length=1)
    role: str = "viewer"


class KeyCreate(BaseModel):
    team: str = Field(min_length=1)
    name: str = Field(min_length=1)


class DetectorPatch(BaseModel):
    enabled: bool | None = None
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class DictionaryCreate(BaseModel):
    name: str = Field(min_length=1)
    match_mode: str = "word-boundary"
    action: str = "pseudonymize"
    replacement: str | None = None
    terms: list[str] = Field(default_factory=list)


class SettingsPatch(BaseModel):
    audit_retention_days: int | None = Field(default=None, ge=1)
    capture_retention_days: int | None = Field(default=None, ge=1)
    content_capture_enabled: bool | None = None
    sso_enabled: bool | None = None
    sso_provider: str | None = None
    sso_client_id: str | None = None


class ProviderCredentialSet(BaseModel):
    provider: str = Field(min_length=1)
    secret: str = Field(min_length=1)


class PolicyCreate(BaseModel):
    yaml: str = Field(min_length=1)


def _team_view(row: Any) -> dict[str, Any]:
    import json

    return {
        "id": row["id"],
        "name": row["name"],
        "shadow_mode": bool(row["shadow_mode"]),
        "monthly_budget_cents": row["monthly_budget_cents"],
        "rate_limit_rpm": row["rate_limit_rpm"],
        "allowed_models": json.loads(row["allowed_models"] or "[]"),
        "content_capture_enabled": bool(row["content_capture_enabled"]),
    }


def _settings_view(row: Any, providers: list[Any]) -> dict[str, Any]:
    return {
        "audit_retention_days": row["audit_retention_days"],
        "capture_retention_days": row["capture_retention_days"],
        "content_capture_enabled": bool(row["content_capture_enabled"]),
        "sso_enabled": bool(row["sso_enabled"]),
        "sso_provider": row["sso_provider"],
        "sso_client_id": row["sso_client_id"],
        "vault_key_rotated_at": row["vault_key_rotated_at"],
        "provider_credentials": [
            {
                "provider": item["provider"],
                "key_last4": item["key_last4"],
                "updated_at": item["updated_at"],
            }
            for item in providers
        ],
    }


def _ruleset_view(ruleset: Any) -> dict[str, Any]:
    return {
        "version": ruleset.version,
        "default_action": str(ruleset.default_action),
        "shadow_mode": ruleset.shadow_mode,
        "rules": [
            {
                "id": rule.id,
                "entity_types": sorted(rule.entity_types),
                "action": str(rule.action),
                "min_confidence": rule.min_confidence,
                "reason": rule.reason,
            }
            for rule in ruleset.rules
        ],
    }


def create_router(
    audit_store: AuditStore,
    admin_store: AdminStore,
    policy_engine: PolicyEngine,
    dry_run: DryRunHandler,
) -> APIRouter:
    """Create Admin API routes bound to one application instance."""
    router = APIRouter(prefix="/admin", tags=["admin"])

    def identify(authorization: str | None) -> AdminIdentity:
        if not authorization or not authorization.startswith("Bearer "):
            raise gateway_error(401, "Admin session required", "authentication_error")
        identity = admin_store.resolve_session(authorization.removeprefix("Bearer "))
        if identity is None:
            raise gateway_error(401, "Invalid admin session", "authentication_error")
        return identity

    def scope_team(identity: AdminIdentity) -> str | None:
        """Return the team filter to apply: None for tenant-wide roles."""
        return None if identity.tenant_wide else identity.team

    def paginate(cursor: str | None) -> tuple[str, str] | None:
        if cursor is None:
            return None
        position = decode_cursor(cursor)
        if "ts" not in position or "id" not in position:
            raise gateway_error(400, "Invalid cursor", "invalid_request_error")
        return position["ts"], position["id"]

    @router.get("/stats/overview")
    async def stats_overview(
        authorization: str | None = Header(default=None), range: str = "7d"
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_STATS)
        return audit_store.stats_overview(
            identity.tenant_id, team=scope_team(identity), range=range
        )

    @router.get("/stats/top-users")
    async def stats_top_users(
        authorization: str | None = Header(default=None),
        range: str = "7d",
        limit: int = Query(default=10, ge=1, le=_MAX_LIMIT),
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_STATS)
        return {
            "range": range,
            "items": audit_store.top_users(
                identity.tenant_id, team=scope_team(identity), range=range, limit=limit
            ),
        }

    @router.get("/stats/detections")
    async def stats_detections(
        authorization: str | None = Header(default=None), range: str = "7d"
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_STATS)
        return audit_store.detection_estimates(
            identity.tenant_id, team=scope_team(identity), range=range
        )

    @router.get("/stats/false-positives")
    async def stats_false_positives(
        authorization: str | None = Header(default=None), range: str = "7d"
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_STATS)
        return audit_store.false_positive_rate(
            identity.tenant_id, team=scope_team(identity), range=range
        )

    @router.get("/requests")
    async def list_requests(
        authorization: str | None = Header(default=None),
        action: str | None = None,
        cursor: str | None = None,
        limit: int = Query(default=50, ge=1, le=_MAX_LIMIT),
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_REQUESTS)
        rows, next_cursor = audit_store.list_requests(
            identity.tenant_id,
            team=scope_team(identity),
            action=action,
            limit=limit,
            cursor=paginate(cursor),
        )
        return {
            "items": [_request_view(row) for row in rows],
            "next_cursor": (
                encode_cursor({"ts": next_cursor[0], "id": next_cursor[1]})
                if next_cursor is not None
                else None
            ),
        }

    @router.get("/requests/{request_id}")
    async def get_request(
        request_id: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_REQUESTS)
        row = audit_store.get_request(identity.tenant_id, request_id, scope_team(identity))
        if row is None:
            raise gateway_error(404, "Request not found", "not_found")
        return _request_view(row)

    @router.get("/requests/{request_id}/trace")
    async def get_trace(
        request_id: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        row = audit_store.get_request(identity.tenant_id, request_id, scope_team(identity))
        if row is None:
            # A request that exists elsewhere in the tenant is hidden as a 404 before the
            # permission gate so a cross-team caller cannot distinguish "forbidden" from
            # "absent" (AC-M5-05 IDOR). A genuinely unknown id falls through to the
            # permission check, so a viewer without READ_TRACE still gets 403 (AC-M5-02).
            if audit_store.get_request(identity.tenant_id, request_id, None) is not None:
                raise gateway_error(404, "Request not found", "not_found")
            identity.require(Permission.READ_TRACE)
            raise gateway_error(404, "Request not found", "not_found")
        identity.require(Permission.READ_TRACE)
        trace = audit_store.request_trace(identity.tenant_id, request_id, scope_team(identity))
        return {"request_id": request_id, "trace": [_finding_view(row) for row in trace]}

    @router.post("/findings/{finding_id}/false-positive")
    async def report_false_positive(
        finding_id: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.REPORT_FALSE_POSITIVE)
        if not audit_store.report_false_positive(
            identity.tenant_id, finding_id, scope_team(identity)
        ):
            raise gateway_error(404, "Finding not found", "not_found")
        admin_store.record_event(identity, "finding.false_positive", finding_id)
        return {"finding_id": finding_id, "false_positive_reported": True}

    @router.get("/policies")
    async def get_policies(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_POLICY)
        return _ruleset_view(policy_engine.ruleset)

    @router.get("/policies/versions")
    async def list_policy_versions(
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_POLICY)
        return {
            "active_version": policy_engine.version,
            "versions": [_ruleset_view(ruleset) for ruleset in policy_engine.versions()],
        }

    @router.post("/policies")
    async def create_policy(
        body: PolicyCreate, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_POLICY)
        try:
            written = policy_engine.add_version(body.yaml)
        except ValueError as error:
            raise gateway_error(400, str(error), "invalid_request_error") from error
        admin_store.record_event(
            identity, "policy.create", str(written.version), after={"version": written.version}
        )
        return _ruleset_view(written)

    @router.post("/policies/{version}/activate")
    async def activate_policy(
        version: int, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_POLICY)
        try:
            activated = policy_engine.activate(version)
        except KeyError as error:
            raise gateway_error(404, "Policy version not found", "not_found") from error
        admin_store.record_event(identity, "policy.activate", str(version))
        return _ruleset_view(activated)

    @router.post("/policies/test")
    async def test_policy(
        body: dict[str, Any] = Body(...), authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_POLICY)
        return await dry_run(body)

    @router.get("/teams")
    async def list_teams(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_ACCESS)
        return {"items": [_team_view(row) for row in admin_store.list_teams(identity.tenant_id)]}

    @router.post("/teams")
    async def create_team(
        body: TeamCreate, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_ACCESS)
        team_id = admin_store.upsert_team(
            identity.tenant_id,
            body.name,
            shadow_mode=body.shadow_mode,
            monthly_budget_cents=body.monthly_budget_cents,
            rate_limit_rpm=body.rate_limit_rpm,
            allowed_models=body.allowed_models,
        )
        admin_store.record_event(identity, "team.create", team_id, after=body.model_dump())
        return {"id": team_id}

    @router.patch("/teams/{team_id}")
    async def update_team(
        team_id: str, body: TeamUpdate, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_ACCESS)
        before = admin_store.get_team(identity.tenant_id, team_id)
        if before is None:
            raise gateway_error(404, "Team not found", "not_found")
        updated = admin_store.update_team(
            identity.tenant_id,
            team_id,
            shadow_mode=body.shadow_mode,
            monthly_budget_cents=body.monthly_budget_cents,
            rate_limit_rpm=body.rate_limit_rpm,
            allowed_models=body.allowed_models,
        )
        admin_store.record_event(
            identity, "team.update", team_id, before=_team_view(before), after=_team_view(updated)
        )
        return _team_view(updated)

    @router.get("/users")
    async def list_users(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_ACCESS)
        return {"items": [dict(row) for row in admin_store.list_users(identity.tenant_id)]}

    @router.post("/users")
    async def create_user(
        body: UserCreate, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_ACCESS)
        try:
            role = Role(body.role)
        except ValueError as error:
            raise gateway_error(400, "Unknown role", "invalid_request_error") from error
        user_id = admin_store.create_user(identity.tenant_id, body.email, body.name, role)
        admin_store.record_event(
            identity, "user.create", user_id, after={"email": body.email, "role": body.role}
        )
        return {"id": user_id}

    @router.get("/keys")
    async def list_keys(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_ACCESS)
        return {"items": [dict(row) for row in admin_store.list_keys(identity.tenant_id)]}

    @router.post("/keys")
    async def create_key(
        body: KeyCreate, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_ACCESS)
        issued = admin_store.issue_key(identity.tenant_id, body.team, body.name)
        admin_store.record_event(
            identity, "key.issue", issued.id, after={"team": body.team, "prefix": issued.key_prefix}
        )
        return {"id": issued.id, "key": issued.full_key, "key_prefix": issued.key_prefix}

    @router.post("/keys/{key_id}/revoke")
    async def revoke_key(
        key_id: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_ACCESS)
        if not admin_store.revoke_key(identity.tenant_id, key_id):
            raise gateway_error(404, "Key not found", "not_found")
        admin_store.record_event(identity, "key.revoke", key_id)
        return {"id": key_id, "revoked": True}

    @router.get("/detectors")
    async def list_detectors(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_DETECTORS)
        return {"items": [dict(row) for row in admin_store.list_detectors(identity.tenant_id)]}

    @router.patch("/detectors/{detector_id}")
    async def patch_detector(
        detector_id: str,
        body: DetectorPatch,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_DETECTORS)
        before = admin_store.get_detector(identity.tenant_id, detector_id)
        if before is None:
            raise gateway_error(404, "Detector not found", "not_found")
        updated = admin_store.update_detector(
            identity.tenant_id,
            detector_id,
            enabled=body.enabled,
            min_confidence=body.min_confidence,
        )
        admin_store.record_event(
            identity, "detector.update", detector_id, before=dict(before), after=dict(updated)
        )
        return dict(updated)

    @router.get("/dictionaries")
    async def list_dictionaries(
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_DICTIONARIES)
        return {"items": [dict(row) for row in admin_store.list_dictionaries(identity.tenant_id)]}

    @router.post("/dictionaries")
    async def create_dictionary(
        body: DictionaryCreate, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_DICTIONARIES)
        dictionary_id = admin_store.create_dictionary(
            identity.tenant_id,
            body.name,
            body.match_mode,
            body.action,
            body.replacement,
            len(body.terms),
        )
        admin_store.record_event(
            identity, "dictionary.create", dictionary_id, after={"name": body.name}
        )
        return {"id": dictionary_id, "term_count": len(body.terms)}

    @router.get("/suggestions")
    async def list_suggestions(
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_SUGGESTIONS)
        return {"items": [dict(row) for row in admin_store.list_suggestions(identity.tenant_id)]}

    @router.post("/suggestions/{suggestion_id}/apply")
    async def apply_suggestion(
        suggestion_id: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_SUGGESTIONS)
        if not admin_store.resolve_suggestion(identity.tenant_id, suggestion_id, "applied"):
            raise gateway_error(404, "Suggestion not found", "not_found")
        admin_store.record_event(identity, "suggestion.apply", suggestion_id)
        return {"id": suggestion_id, "status": "applied"}

    @router.post("/suggestions/{suggestion_id}/dismiss")
    async def dismiss_suggestion(
        suggestion_id: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_SUGGESTIONS)
        if not admin_store.resolve_suggestion(identity.tenant_id, suggestion_id, "dismissed"):
            raise gateway_error(404, "Suggestion not found", "not_found")
        admin_store.record_event(identity, "suggestion.dismiss", suggestion_id)
        return {"id": suggestion_id, "status": "dismissed"}

    @router.get("/settings")
    async def get_settings(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_SETTINGS)
        return _settings_view(
            admin_store.get_settings(identity.tenant_id),
            admin_store.list_provider_credentials(identity.tenant_id),
        )

    @router.patch("/settings")
    async def patch_settings(
        body: SettingsPatch, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_SETTINGS)
        before = admin_store.get_settings(identity.tenant_id)
        updated = admin_store.update_settings(
            identity.tenant_id,
            audit_retention_days=body.audit_retention_days,
            capture_retention_days=body.capture_retention_days,
            content_capture_enabled=body.content_capture_enabled,
            sso_enabled=body.sso_enabled,
            sso_provider=body.sso_provider,
            sso_client_id=body.sso_client_id,
        )
        admin_store.record_event(
            identity,
            "settings.update",
            identity.tenant_id,
            before=dict(before),
            after=dict(updated),
        )
        return _settings_view(
            updated, admin_store.list_provider_credentials(identity.tenant_id)
        )

    @router.post("/settings/providers")
    async def set_provider_credential(
        body: ProviderCredentialSet, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_SETTINGS)
        admin_store.set_provider_credential(identity.tenant_id, body.provider, body.secret)
        # Never log the secret; only that a credential for this provider was set.
        admin_store.record_event(
            identity, "settings.provider_credential", body.provider, after={"provider": body.provider}
        )
        return {"provider": body.provider, "key_last4": body.secret[-4:], "stored": True}

    @router.post("/settings/vault/rotate")
    async def rotate_vault_key(
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_SETTINGS)
        updated = admin_store.rotate_vault_key(identity.tenant_id)
        admin_store.record_event(identity, "settings.vault_rotate", identity.tenant_id)
        return {"vault_key_rotated_at": updated["vault_key_rotated_at"]}

    @router.get("/events")
    async def list_events(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_ACCESS)
        return {"items": [dict(row) for row in admin_store.list_events(identity.tenant_id)]}

    return router


def _request_view(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "team": row["team"],
        "user": row["user_id"],
        "ts": row["ts"],
        "model": row["model"],
        "provider": row["provider"],
        "action": row["action"],
        "policy_version": row["policy_version"],
        "shadow": bool(row["shadow"]),
        "blocked_reason": row["blocked_reason"],
        "prompt_tokens": row["prompt_tokens"],
        "completion_tokens": row["completion_tokens"],
        "cost_cents": row["cost_cents"],
        "latency_ms": row["latency_ms"],
        "provider_latency_ms": row["provider_latency_ms"],
        "status_code": row["status_code"],
        "fallback_used": None if row["fallback_used"] is None else bool(row["fallback_used"]),
    }


def _finding_view(row: Any) -> dict[str, Any]:
    return {
        "entity_type": row["entity_type"],
        "detector": row["detector"],
        "confidence": row["confidence"],
        "span": [row["span_start"], row["span_end"]],
        "matched_rule_id": row["matched_rule_id"],
        "action": row["action_taken"],
        "was_shadow": bool(row["was_shadow"]),
        "reason": row["reason"],
        "false_positive_reported": bool(row["false_positive_reported"]),
    }

"""Admin API routes. RBAC is enforced server-side on every endpoint (H.7)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel, Field

from frostglass.admin.pagination import decode_cursor, encode_cursor
from frostglass.admin.rbac import AdminIdentity, Permission, Role
from frostglass.admin.store import AdminStore
from frostglass.audit.store import AuditStore
from frostglass.errors import gateway_error

_MAX_LIMIT = 100


class TeamCreate(BaseModel):
    name: str = Field(min_length=1)
    shadow_mode: bool = True
    monthly_budget_cents: int = 0
    rate_limit_rpm: int = 60


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


def create_router(audit_store: AuditStore, admin_store: AdminStore) -> APIRouter:
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
        rows, _ = audit_store.list_requests(
            identity.tenant_id, team=scope_team(identity), limit=_MAX_LIMIT
        )
        by_action: dict[str, int] = {}
        for row in rows:
            by_action[row["action"]] = by_action.get(row["action"], 0) + 1
        return {"range": range, "sampled": len(rows), "by_action": by_action}

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
        identity.require(Permission.READ_TRACE)
        if audit_store.get_request(identity.tenant_id, request_id, scope_team(identity)) is None:
            raise gateway_error(404, "Request not found", "not_found")
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

    @router.get("/teams")
    async def list_teams(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_ACCESS)
        return {"items": [dict(row) for row in admin_store.list_teams(identity.tenant_id)]}

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
        )
        admin_store.record_event(identity, "team.create", team_id, after=body.model_dump())
        return {"id": team_id}

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
        return dict(admin_store.get_settings(identity.tenant_id))

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
        )
        admin_store.record_event(
            identity,
            "settings.update",
            identity.tenant_id,
            before=dict(before),
            after=dict(updated),
        )
        return dict(updated)

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
        "latency_ms": row["latency_ms"],
        "status_code": row["status_code"],
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

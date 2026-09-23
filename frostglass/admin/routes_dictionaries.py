"""Tenant-scoped M7 dictionary and custom-recognizer Admin API routes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from frostglass.admin.custom_recognizers import UnsafePatternError, test_pattern
from frostglass.admin.dictionary_store import DictionaryStore
from frostglass.admin.rbac import AdminIdentity, Permission
from frostglass.admin.recognizer_store import RecognizerStore
from frostglass.admin.store import AdminStore
from frostglass.errors import gateway_error

Identify = Callable[[str | None], AdminIdentity]


class DictionaryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    match_mode: str = "word-boundary"
    action: str = "pseudonymize"
    replacement: str | None = Field(default=None, max_length=120)
    terms: list[str] = Field(default_factory=list, max_length=5_000)


class TermsImport(BaseModel):
    source: str = Field(min_length=1, max_length=1_000_000)
    format: str = "paste"


class TermCreate(BaseModel):
    term: str = Field(min_length=1, max_length=500)
    replacement: str | None = Field(default=None, max_length=120)


class TermUpdate(TermCreate):
    pass


class RecognizerTest(BaseModel):
    pattern: str = Field(min_length=1, max_length=256)
    sample: str = Field(default="", max_length=20_000)


class RecognizerCreate(RecognizerTest):
    name: str = Field(min_length=1, max_length=120)
    entity_type: str = Field(min_length=1, max_length=80)
    action: str = "pseudonymize"
    min_confidence: float = Field(default=0.8, ge=0, le=1)


def create_router(
    dictionary_store: DictionaryStore,
    recognizer_store: RecognizerStore,
    admin_store: AdminStore,
) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["dictionaries"])

    def identify(authorization: str | None) -> AdminIdentity:
        if not authorization or not authorization.startswith("Bearer "):
            raise gateway_error(401, "Admin session required", "authentication_error")
        identity = admin_store.resolve_session(authorization.removeprefix("Bearer "))
        if identity is None:
            raise gateway_error(401, "Invalid admin session", "authentication_error")
        return identity

    @router.get("/dictionaries")
    async def list_dictionaries(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_DICTIONARIES)
        return {"items": dictionary_store.list(identity.tenant_id)}

    @router.post("/dictionaries")
    async def create_dictionary(body: DictionaryCreate, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_DICTIONARIES)
        try:
            dictionary_id = dictionary_store.create(identity.tenant_id, body.name, body.match_mode, body.action, body.replacement)
            count = dictionary_store.add_terms(identity.tenant_id, dictionary_id, body.terms, body.replacement)
        except ValueError as error:
            raise gateway_error(422, str(error), "validation_error") from error
        admin_store.record_event(identity, "dictionary.create", dictionary_id, after={"name": body.name, "term_count": count})
        return {"id": dictionary_id, "term_count": count}

    @router.get("/dictionaries/{dictionary_id}/terms")
    async def list_terms(dictionary_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.READ_DICTIONARIES)
        try:
            return {"items": [item.__dict__ for item in dictionary_store.terms(identity.tenant_id, dictionary_id)]}
        except KeyError as error:
            raise gateway_error(404, "Dictionary not found", "not_found") from error

    @router.post("/dictionaries/{dictionary_id}/terms")
    async def add_term(dictionary_id: str, body: TermCreate, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_DICTIONARIES)
        try:
            dictionary_store.add_terms(identity.tenant_id, dictionary_id, [body.term], body.replacement)
        except KeyError as error:
            raise gateway_error(404, "Dictionary not found", "not_found") from error
        admin_store.record_event(identity, "dictionary.term.add", dictionary_id, after={"term_count_change": 1})
        return {"added": True}

    @router.patch("/dictionaries/{dictionary_id}/terms/{term_id}")
    async def update_term(dictionary_id: str, term_id: str, body: TermUpdate, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_DICTIONARIES)
        try:
            term = dictionary_store.update_term(identity.tenant_id, dictionary_id, term_id, body.term, body.replacement)
        except KeyError as error:
            raise gateway_error(404, "Dictionary term not found", "not_found") from error
        admin_store.record_event(identity, "dictionary.term.update", term_id)
        return {"id": term.id, "term": term.term, "replacement": term.replacement}

    @router.delete("/dictionaries/{dictionary_id}/terms/{term_id}")
    async def delete_term(dictionary_id: str, term_id: str, authorization: str | None = Header(default=None)) -> None:
        identity = identify(authorization)
        identity.require(Permission.WRITE_DICTIONARIES)
        try:
            dictionary_store.remove_term(identity.tenant_id, dictionary_id, term_id)
        except KeyError as error:
            raise gateway_error(404, "Dictionary term not found", "not_found") from error
        admin_store.record_event(identity, "dictionary.term.delete", term_id)

    @router.post("/dictionaries/{dictionary_id}/import")
    async def import_terms(dictionary_id: str, body: TermsImport, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_DICTIONARIES)
        try:
            if body.format == "csv":
                count = dictionary_store.import_csv(identity.tenant_id, dictionary_id, body.source)
            elif body.format == "paste":
                count = dictionary_store.add_terms(identity.tenant_id, dictionary_id, body.source.splitlines())
            else:
                raise ValueError("Import format must be csv or paste")
        except (KeyError, ValueError) as error:
            raise gateway_error(422, str(error), "validation_error") from error
        admin_store.record_event(identity, "dictionary.import", dictionary_id, after={"term_count_change": count})
        return {"imported": count}

    @router.post("/recognizers/test")
    async def test_recognizer(body: RecognizerTest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_DETECTORS)
        try:
            result = test_pattern(body.pattern, body.sample)
        except UnsafePatternError as error:
            raise gateway_error(422, str(error), "unsafe_pattern") from error
        return {"matched": result.matched, "spans": result.spans}

    @router.post("/recognizers")
    async def create_recognizer(body: RecognizerCreate, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        identity = identify(authorization)
        identity.require(Permission.WRITE_DETECTORS)
        try:
            recognizer = recognizer_store.create(identity.tenant_id, body.name, body.pattern, body.entity_type, body.action, body.min_confidence)
        except (UnsafePatternError, ValueError) as error:
            raise gateway_error(422, str(error), "unsafe_pattern") from error
        admin_store.record_event(identity, "recognizer.create", recognizer.id, after={"name": recognizer.name})
        return {"id": recognizer.id, "name": recognizer.name, "enabled": recognizer.enabled}

    return router

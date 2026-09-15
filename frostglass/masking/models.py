"""Types shared by masking, consistency, and restoration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MaskingMode(StrEnum):
    """Supported M3 masking decisions."""

    ALLOW = "allow"
    PSEUDONYMIZE = "pseudonymize"
    TAG = "tag"
    HASH = "hash"
    BLOCK = "block"


class ConsistencyScope(StrEnum):
    """Lifetime of a surrogate mapping."""

    REQUEST = "request"
    SESSION = "session"
    TENANT = "tenant"


@dataclass(frozen=True, slots=True)
class MaskingContext:
    """Identifiers used to derive the configured mapping scope."""

    tenant_id: str
    request_id: str
    session_id: str | None = None
    scope: ConsistencyScope = ConsistencyScope.SESSION

    @property
    def scope_id(self) -> str:
        """Return the vault key namespace for this request."""
        if self.scope is ConsistencyScope.REQUEST:
            return f"request:{self.request_id}"
        if self.scope is ConsistencyScope.TENANT:
            return f"tenant:{self.tenant_id}"
        if self.session_id is None:
            return f"request:{self.request_id}"
        return f"session:{self.tenant_id}:{self.session_id}"


@dataclass(frozen=True, slots=True)
class VaultMapping:
    """A reversible mapping held only in the encrypted vault."""

    value_hash: str
    original: str
    surrogate: str
    entity_type: str

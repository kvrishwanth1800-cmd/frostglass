"""Virtual-key authentication and principal resolution."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest

from frostglass.errors import gateway_error


@dataclass(frozen=True)
class Principal:
    user: str
    team: str
    allowed_models: frozenset[str]
    monthly_budget_cents: int
    rate_limit_rpm: int
    shadow_mode: bool = False


class VirtualKeyStore:
    """In-memory M1 key store. Stored values are hashes, never plaintext keys."""

    def __init__(self) -> None:
        self._keys: dict[str, tuple[str, Principal]] = {}

    def register(self, key: str, principal: Principal) -> None:
        if not key.startswith("fg-live-"):
            raise ValueError("virtual keys must use the fg-live- prefix")
        self._keys[key[:12]] = (sha256(key.encode()).hexdigest(), principal)

    def resolve(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise gateway_error(401, "Missing Frostglass virtual key", "authentication_error")
        key = authorization.removeprefix("Bearer ")
        entry = self._keys.get(key[:12])
        if entry is None or not compare_digest(entry[0], sha256(key.encode()).hexdigest()):
            raise gateway_error(401, "Invalid Frostglass virtual key", "authentication_error")
        return entry[1]


def default_key_store() -> VirtualKeyStore:
    store = VirtualKeyStore()
    store.register(
        "fg-live-test-key",
        Principal("test-user", "test-team", frozenset({"*"}), 100_000, 60),
    )
    store.register(
        "fg-live-budget-key",
        Principal("budget-user", "budget-team", frozenset({"*"}), 0, 60),
    )
    store.register(
        "fg-live-rate-key",
        Principal("rate-user", "rate-team", frozenset({"*"}), 100_000, 1),
    )
    return store

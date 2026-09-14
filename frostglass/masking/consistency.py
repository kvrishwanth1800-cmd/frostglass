"""Stable surrogate allocation for request, session, and tenant scopes."""

from __future__ import annotations

from frostglass.masking.models import MaskingContext, VaultMapping
from frostglass.masking.surrogates import SurrogateGenerator
from frostglass.masking.vault import EncryptedVault


class ConsistencyManager:
    """Reuse existing vault mappings before generating a surrogate."""

    def __init__(self, vault: EncryptedVault) -> None:
        self._vault = vault

    def surrogate_for(
        self, context: MaskingContext, entity_type: str, original: str, value_hash: str
    ) -> str:
        """Return a stable per-scope surrogate and store it encrypted if new."""
        existing = self._vault.get(context.scope_id, value_hash)
        if existing is not None:
            return existing.surrogate
        surrogate = SurrogateGenerator(context.scope_id).generate(entity_type, original, value_hash)
        self._vault.put(context.scope_id, VaultMapping(value_hash, original, surrogate, entity_type))
        return surrogate

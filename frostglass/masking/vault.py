"""AES-GCM encrypted in-memory vault used by M3 and local development."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from frostglass.masking.models import VaultMapping


@dataclass(frozen=True, slots=True)
class _StoredValue:
    ciphertext: bytes
    expires_at: datetime


class EncryptedVault:
    """Store forward and reverse mappings encrypted until their TTL expires."""

    def __init__(self, encryption_key: str, ttl: timedelta = timedelta(hours=1)) -> None:
        key = base64.b64decode(encryption_key, validate=True)
        self._cipher = AESGCM(key)
        self._ttl = ttl
        self._forward: dict[tuple[str, str], _StoredValue] = {}
        self._reverse: dict[tuple[str, str], _StoredValue] = {}

    def get(self, scope_id: str, value_hash: str) -> VaultMapping | None:
        """Return an unexpired mapping by salted value hash."""
        stored = self._forward.get((scope_id, value_hash))
        return self._decode(stored) if stored is not None else None

    def reverse_map(self, scope_id: str) -> dict[str, str]:
        """Return active surrogate-to-original mappings for restoration only."""
        self.purge_expired()
        mappings: dict[str, str] = {}
        for (stored_scope, surrogate), stored in self._reverse.items():
            if stored_scope == scope_id:
                mapping = self._decode(stored)
                if mapping is not None:
                    mappings[surrogate] = mapping.original
        return mappings

    def put(self, scope_id: str, mapping: VaultMapping) -> None:
        """Encrypt and store both directions of one reversible mapping."""
        stored = self._encode(mapping)
        self._forward[(scope_id, mapping.value_hash)] = stored
        self._reverse[(scope_id, mapping.surrogate)] = stored

    def purge_expired(self) -> None:
        """Remove mappings that have reached their configured TTL."""
        now = datetime.now(UTC)
        self._forward = {
            key: value for key, value in self._forward.items() if value.expires_at > now
        }
        self._reverse = {
            key: value for key, value in self._reverse.items() if value.expires_at > now
        }

    def _encode(self, mapping: VaultMapping) -> _StoredValue:
        nonce = os.urandom(12)
        payload = json.dumps(
            {
                "value_hash": mapping.value_hash,
                "original": mapping.original,
                "surrogate": mapping.surrogate,
                "entity_type": mapping.entity_type,
            },
            separators=(",", ":"),
        ).encode()
        ciphertext = self._cipher.encrypt(nonce, payload, None)
        return _StoredValue(nonce + ciphertext, datetime.now(UTC) + self._ttl)

    def _decode(self, stored: _StoredValue) -> VaultMapping | None:
        if stored.expires_at <= datetime.now(UTC):
            return None
        nonce, ciphertext = stored.ciphertext[:12], stored.ciphertext[12:]
        payload = json.loads(self._cipher.decrypt(nonce, ciphertext, None))
        return VaultMapping(**payload)

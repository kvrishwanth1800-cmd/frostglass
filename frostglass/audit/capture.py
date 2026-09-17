"""Optional, encrypted, short-TTL capture of masked payloads only.

Content capture is off by default (Part J). When enabled it stores the MASKED
payload only, encrypted with AES-GCM under the vault key, with a short TTL. The
unmasked original is never passed here and never stored (Part M).
"""

from __future__ import annotations

import base64
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class ContentCapture:
    """Seal and open masked payloads for opt-in, RBAC-gated capture."""

    def __init__(self, encryption_key: str, ttl: timedelta) -> None:
        self._cipher = AESGCM(base64.b64decode(encryption_key, validate=True))
        self._ttl = ttl

    def seal(self, masked_payload: dict[str, Any]) -> tuple[bytes, datetime]:
        """Encrypt a masked payload and return the blob and its expiry."""
        nonce = os.urandom(12)
        plaintext = json.dumps(masked_payload, separators=(",", ":")).encode()
        ciphertext = self._cipher.encrypt(nonce, plaintext, None)
        return nonce + ciphertext, datetime.now(UTC) + self._ttl

    def open(self, sealed: bytes) -> dict[str, Any]:
        """Decrypt a previously sealed masked payload."""
        nonce, ciphertext = sealed[:12], sealed[12:]
        payload = json.loads(self._cipher.decrypt(nonce, ciphertext, None))
        if not isinstance(payload, dict):
            raise ValueError("captured payload must be an object")
        return payload

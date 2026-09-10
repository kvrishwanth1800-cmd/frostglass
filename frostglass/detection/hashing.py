"""Hashing helpers for safe finding correlation."""

from __future__ import annotations

import hashlib


def value_hash(value: str, tenant_salt: str) -> str:
    """Return a tenant-scoped SHA-256 hash without retaining the raw value."""
    encoded_value = value.encode("utf-8")
    encoded_salt = tenant_salt.encode("utf-8")
    payload = len(encoded_salt).to_bytes(4, "big") + encoded_salt + encoded_value
    return hashlib.sha256(payload).hexdigest()

"""Opaque cursor helpers for deterministic keyset pagination."""

from __future__ import annotations

import base64
import json


def encode_cursor(payload: dict[str, str]) -> str:
    """Encode a keyset position as an opaque, URL-safe cursor."""
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str) -> dict[str, str]:
    """Decode an opaque cursor back into its keyset position."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        payload = json.loads(raw)
    except (ValueError, json.JSONDecodeError) as error:
        raise ValueError("invalid cursor") from error
    if not isinstance(payload, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in payload.items()
    ):
        raise ValueError("invalid cursor")
    return payload

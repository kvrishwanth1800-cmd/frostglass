"""Shared pytest configuration."""

from __future__ import annotations

import base64
import os

os.environ.setdefault("FG_VAULT_ENCRYPTION_KEY", base64.b64encode(b"a" * 32).decode())
os.environ.setdefault("FG_TENANT_SALT", "tenant-salt-for-tests-must-be-long-enough")

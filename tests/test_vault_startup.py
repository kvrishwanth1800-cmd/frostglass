"""Application startup must validate the key used by the M3 vault."""

from __future__ import annotations

import base64

import pytest
from pydantic import ValidationError


def test_app_refuses_missing_vault_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FG_VAULT_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("FG_TENANT_SALT", "tenant-salt-for-tests-must-be-long-enough")
    from frostglass.main import create_app

    with pytest.raises(ValidationError):
        create_app()


def test_app_creates_vault_from_configured_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FG_VAULT_ENCRYPTION_KEY", base64.b64encode(b"v" * 32).decode())
    monkeypatch.setenv("FG_TENANT_SALT", "tenant-salt-for-tests-must-be-long-enough")
    from frostglass.main import create_app

    assert create_app().title == "Frostglass"

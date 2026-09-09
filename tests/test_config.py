import base64

import pytest
from pydantic import ValidationError

from frostglass.config import Settings


def test_settings_rejects_missing_security_values(monkeypatch) -> None:
    monkeypatch.delenv("FG_VAULT_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("FG_TENANT_SALT", raising=False)

    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_placeholder_key(monkeypatch) -> None:
    monkeypatch.setenv("FG_VAULT_ENCRYPTION_KEY", "changeme")
    monkeypatch.setenv("FG_TENANT_SALT", "tenant-salt-for-tests-must-be-long-enough")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_accepts_valid_security_values(monkeypatch) -> None:
    monkeypatch.setenv("FG_VAULT_ENCRYPTION_KEY", base64.b64encode(b"a" * 32).decode())
    monkeypatch.setenv("FG_TENANT_SALT", "tenant-salt-for-tests-must-be-long-enough")

    assert Settings().tenant_salt == "tenant-salt-for-tests-must-be-long-enough"

"""Runtime configuration and security validation."""

from __future__ import annotations

import base64

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDERS = {
    "changeme",
    "change-me",
    "example",
    "placeholder",
    "your-key-here",
    "replace-me",
}


class Settings(BaseSettings):
    """Settings loaded only from the process environment."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    vault_encryption_key: str = Field(validation_alias="FG_VAULT_ENCRYPTION_KEY")
    tenant_salt: str = Field(validation_alias="FG_TENANT_SALT")
    version: str = "0.0.1"

    @field_validator("vault_encryption_key")
    @classmethod
    def validate_vault_key(cls, value: str) -> str:
        normalized = value.strip()
        if normalized.lower() in _PLACEHOLDERS:
            raise ValueError("FG_VAULT_ENCRYPTION_KEY must not use a placeholder")
        try:
            decoded = base64.b64decode(normalized, validate=True)
        except ValueError as error:
            raise ValueError("FG_VAULT_ENCRYPTION_KEY must be valid base64") from error
        if len(decoded) != 32:
            raise ValueError("FG_VAULT_ENCRYPTION_KEY must decode to exactly 32 bytes")
        return normalized

    @field_validator("tenant_salt")
    @classmethod
    def validate_tenant_salt(cls, value: str) -> str:
        normalized = value.strip()
        if normalized.lower() in _PLACEHOLDERS or len(normalized) < 32:
            raise ValueError(
                "FG_TENANT_SALT must be a non-placeholder value of at least 32 characters"
            )
        return normalized

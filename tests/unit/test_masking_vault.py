"""Unit tests for M3 consistency scopes and encrypted vault storage."""

from __future__ import annotations

import base64
from datetime import timedelta

import pytest
from cryptography.exceptions import InvalidTag

from frostglass.masking.consistency import ConsistencyManager
from frostglass.masking.models import ConsistencyScope, MaskingContext, VaultMapping
from frostglass.masking.vault import EncryptedVault

_KEY = base64.b64encode(b"k" * 32).decode()


def test_same_value_is_stable_within_session_scope() -> None:
    manager = ConsistencyManager(EncryptedVault(_KEY))
    context = MaskingContext("tenant", "request-one", "conversation", ConsistencyScope.SESSION)
    first = manager.surrogate_for(context, "PERSON", "Avery Stone", "value-hash")
    second = manager.surrogate_for(context, "PERSON", "Avery Stone", "value-hash")
    assert first == second


def test_scope_ids_distinguish_request_session_and_tenant() -> None:
    request = MaskingContext("tenant", "request-one", "conversation", ConsistencyScope.REQUEST)
    session = MaskingContext("tenant", "request-one", "conversation", ConsistencyScope.SESSION)
    tenant = MaskingContext("tenant", "request-one", "conversation", ConsistencyScope.TENANT)
    assert len({request.scope_id, session.scope_id, tenant.scope_id}) == 3


def test_vault_ciphertext_is_unreadable_without_key() -> None:
    vault = EncryptedVault(_KEY)
    mapping = VaultMapping("hash", "Avery Stone", "Marcus Feld", "PERSON")
    vault.put("session:tenant:conversation", mapping)
    stored = next(iter(vault._forward.values()))
    wrong = EncryptedVault(base64.b64encode(b"z" * 32).decode())
    with pytest.raises(InvalidTag):
        wrong._cipher.decrypt(stored.ciphertext[:12], stored.ciphertext[12:], None)


def test_vault_purges_expired_mappings() -> None:
    vault = EncryptedVault(_KEY, ttl=timedelta(seconds=-1))
    vault.put("scope", VaultMapping("hash", "Avery", "Marcus", "PERSON"))
    vault.purge_expired()
    assert vault.get("scope", "hash") is None

"""AC-M3 masking-engine tests."""

from __future__ import annotations

import base64

import pytest

from frostglass.detection.models import Finding
from frostglass.masking.consistency import ConsistencyManager
from frostglass.masking.engine import BlockedContentError, MaskingEngine
from frostglass.masking.models import MaskingContext, MaskingMode
from frostglass.masking.restore import restore_text
from frostglass.masking.vault import EncryptedVault

_KEY = base64.b64encode(b"m" * 32).decode()
_CONTEXT = MaskingContext("tenant", "request", "session")


def _finding(entity_type: str, start: int, end: int, value_hash: str) -> Finding:
    return Finding(entity_type, start, end, 1.0, "test", value_hash)


def _engine() -> MaskingEngine:
    vault = EncryptedVault(_KEY)
    return MaskingEngine(ConsistencyManager(vault), "tenant-salt")


def test_ac_m3_01_round_trip_restores_non_sensitive_text() -> None:
    text = "Email Avery Stone about the order."
    finding = _finding("PERSON", 6, 17, "person-hash")
    vault = EncryptedVault(_KEY)
    engine = MaskingEngine(ConsistencyManager(vault), "tenant-salt")
    masked = engine.mask(text, (finding,), _CONTEXT, {})
    assert masked.text.startswith("Email ")
    assert masked.text.endswith(" about the order.")
    assert restore_text(masked.text, vault.reverse_map(_CONTEXT.scope_id)) == text


def test_ac_m3_05_surrogate_spans_are_immune() -> None:
    text = "Avery Stone"
    finding = _finding("PERSON", 0, len(text), "person-hash")
    result = _engine().mask(text, (finding,), _CONTEXT, {})
    assert result.text != text
    assert result.immune_spans == ((0, len(result.text)),)


def test_allow_tag_hash_and_block_modes() -> None:
    text = "Avery Stone"
    finding = _finding("PERSON", 0, len(text), "person-hash")
    engine = _engine()
    assert engine.mask(text, (finding,), _CONTEXT, {"PERSON": MaskingMode.ALLOW}).text == text
    assert engine.mask(text, (finding,), _CONTEXT, {"PERSON": MaskingMode.TAG}).text == "<PERSON_1>"
    hashed = engine.mask(text, (finding,), _CONTEXT, {"PERSON": MaskingMode.HASH}).text
    assert hashed.startswith("sha256:")
    assert "Avery" not in hashed
    with pytest.raises(BlockedContentError):
        engine.mask(text, (finding,), _CONTEXT, {"PERSON": MaskingMode.BLOCK})


def test_ac_m3_02_session_identity_is_stable_for_five_turns() -> None:
    engine = _engine()
    finding = _finding("PERSON", 0, 11, "person-hash")
    outputs = [engine.mask("Avery Stone", (finding,), _CONTEXT, {}).text for _ in range(5)]
    assert len(set(outputs)) == 1

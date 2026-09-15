"""AC-M3-03 coverage for streaming restoration at surrogate boundaries."""

from __future__ import annotations

import pytest

from frostglass.masking.restore import restore_stream, restore_text

_SURROGATE = "Marcus Feld"
_ORIGINAL = "Avery Stone"
_RESPONSE = f"Hello {_SURROGATE}, your request is complete."
_EXPECTED = f"Hello {_ORIGINAL}, your request is complete."
_MAPPING = {_SURROGATE: _ORIGINAL}


def _restore(chunks: list[str]) -> str:
    return "".join(restore_stream(chunks, _MAPPING))


def test_restore_non_streaming_response() -> None:
    assert restore_text(_RESPONSE, _MAPPING) == _EXPECTED


def test_restore_split_mid_first_name() -> None:
    assert _restore(["Hello Mar", "cus Feld, your", " request is complete."]) == _EXPECTED


def test_restore_split_at_space() -> None:
    assert _restore(["Hello Marcus", " Feld, your", " request is complete."]) == _EXPECTED


def test_restore_split_mid_last_name() -> None:
    assert _restore(["Hello Marcus Fe", "ld, your", " request is complete."]) == _EXPECTED


def test_restore_character_by_character() -> None:
    assert _restore(list(_RESPONSE)) == _EXPECTED


def test_restore_single_chunk() -> None:
    assert _restore([_RESPONSE]) == _EXPECTED


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (first, second)
        for first in range(1, len(_RESPONSE) - 1)
        for second in range(first + 1, len(_RESPONSE))
    ],
)
def test_restore_every_three_chunk_boundary(first: int, second: int) -> None:
    chunks = [_RESPONSE[:first], _RESPONSE[first:second], _RESPONSE[second:]]
    assert _restore(chunks) == _EXPECTED

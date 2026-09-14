"""Unit tests for M3 format-preserving surrogate generation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from frostglass.masking.surrogates import SurrogateGenerator


def _luhn_valid(value: str) -> bool:
    digits = [int(character) for character in value if character.isdigit()]
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def test_dates_use_one_constant_session_offset() -> None:
    generator = SurrogateGenerator("session-1")
    first = date.fromisoformat(generator.generate("DATE", "2026-03-01", "one"))
    second = date.fromisoformat(generator.generate("DATE", "2026-03-11", "two"))
    assert (second - first).days == 10


def test_credit_card_uses_documented_test_range_and_luhn() -> None:
    surrogate = SurrogateGenerator("session-1").generate(
        "CREDIT_CARD", "4111 1111 1111 1111", "card"
    )
    assert surrogate.startswith("411111")
    assert len([character for character in surrogate if character.isdigit()]) == 16
    assert _luhn_valid(surrogate)


def test_person_preserves_token_count_and_capitalization() -> None:
    generator = SurrogateGenerator("session-1")
    assert len(generator.generate("PERSON", "Avery", "single").split()) == 1
    assert len(generator.generate("PERSON", "AVERY STONE", "upper").split()) == 2
    assert generator.generate("PERSON", "AVERY STONE", "upper").isupper()


def test_money_preserves_bucket_and_precision() -> None:
    surrogate = SurrogateGenerator("session-1").generate("MONEY", "$1,240.50", "money")
    value = Decimal(surrogate.removeprefix("$").replace(",", ""))
    assert Decimal("1000") <= value < Decimal("10000")
    assert surrogate.split(".")[1] == "50" or len(surrogate.split(".")[1]) == 2


def test_number_at_bucket_boundary_stays_in_bucket() -> None:
    surrogate = SurrogateGenerator("session-1").generate("NUMBER", "100", "boundary")
    assert 100 <= int(surrogate) < 1000

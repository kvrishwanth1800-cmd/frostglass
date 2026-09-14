"""Format-preserving, non-original surrogates for M3 masking."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256

_NAME_PAIRS = (("Marcus", "Feld"), ("Sofia", "Ivanova"), ("Priya", "Patel"))
_CITIES = ("Denver", "Madison", "Portland")
_COMPANIES = ("Northstar", "Bluehaven", "Cedarpoint")
_CARD_PREFIXES = (("3", "378282"), ("4", "411111"), ("5", "555555"))


def _stable_index(seed: str, size: int) -> int:
    return int.from_bytes(sha256(seed.encode()).digest()[:4], "big") % size


def _apply_case(value: str, template: str) -> str:
    if template.isupper():
        return value.upper()
    if template.islower():
        return value.lower()
    return value


def _luhn_check_digit(prefix: str) -> str:
    total = 0
    for index, character in enumerate(reversed(prefix + "0")):
        digit = int(character)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return str((-total) % 10)


def _date_offset(session_id: str) -> int:
    return _stable_index(f"date:{session_id}", 181) - 90


class SurrogateGenerator:
    """Generate deterministic, valid replacements from a request seed."""

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._date_shift = timedelta(days=_date_offset(session_id))

    def generate(self, entity_type: str, original: str, value_hash: str) -> str:
        """Return a same-shape surrogate and never return the original value."""
        seed = f"{entity_type}:{value_hash}"
        if entity_type in {"PERSON", "CUSTOMER_NAME"}:
            return self._person(original, seed)
        if entity_type == "EMAIL_ADDRESS":
            return self._email(original, seed)
        if entity_type == "PHONE_NUMBER":
            return self._phone(original, seed)
        if entity_type == "CREDIT_CARD":
            return self._card(original, seed)
        if entity_type in {"DATE", "DATE_TIME"}:
            return self._date(original)
        if entity_type in {"MONEY", "NUMBER"}:
            return self._number(original, seed)
        if entity_type == "LOCATION":
            return _CITIES[_stable_index(seed, len(_CITIES))]
        if entity_type == "ORGANIZATION":
            return self._organization(original, seed)
        if entity_type in {"ACCOUNT", "ID"}:
            return self._identifier(original, seed)
        return f"TOKEN-{value_hash[:10].upper()}"

    def _person(self, original: str, seed: str) -> str:
        words = original.split()
        first, last = _NAME_PAIRS[_stable_index(seed, len(_NAME_PAIRS))]
        generated = first if len(words) == 1 else f"{first} {last}"
        return _apply_case(generated, original)

    def _email(self, original: str, seed: str) -> str:
        local, _, _domain = original.partition("@")
        first, last = _NAME_PAIRS[_stable_index(seed, len(_NAME_PAIRS))]
        generated_local = f"{first}.{last}" if "." in local else first
        return f"{generated_local.lower()}@example-corp.com"

    def _phone(self, original: str, seed: str) -> str:
        digits = [character for character in original if character.isdigit()]
        if len(digits) < 7:
            return self._identifier(original, seed)
        suffix = f"{100 + _stable_index(seed, 900):03d}"
        replacement = "55501" + suffix
        replacement = replacement[-len(digits) :].zfill(len(digits))
        iterator = iter(replacement)
        return "".join(next(iterator) if character.isdigit() else character for character in original)

    def _card(self, original: str, seed: str) -> str:
        digits = "".join(character for character in original if character.isdigit())
        prefix = next((test_prefix for marker, test_prefix in _CARD_PREFIXES if digits.startswith(marker)), "411111")
        body_length = max(len(digits) - len(prefix) - 1, 1)
        body = "".join(str(_stable_index(f"{seed}:{index}", 10)) for index in range(body_length))
        replacement = prefix + body
        replacement += _luhn_check_digit(replacement)
        replacement = replacement[: len(digits)]
        iterator = iter(replacement)
        return "".join(next(iterator) if character.isdigit() else character for character in original)

    def _date(self, original: str) -> str:
        for parser, formatter in (("%Y-%m-%d", "%Y-%m-%d"), ("%Y/%m/%d", "%Y/%m/%d")):
            try:
                return (datetime.strptime(original, parser).date() + self._date_shift).strftime(formatter)
            except ValueError:
                continue
        try:
            parsed = datetime.fromisoformat(original.replace("Z", "+00:00"))
        except ValueError:
            return original
        return (parsed + self._date_shift).isoformat().replace("+00:00", "Z")

    def _number(self, original: str, seed: str) -> str:
        match = re.fullmatch(r"(?P<prefix>[^0-9-]*)(?P<number>-?[0-9,]+(?:\.[0-9]+)?)(?P<suffix>.*)", original)
        if match is None:
            return original
        compact = match.group("number").replace(",", "")
        try:
            value = Decimal(compact)
        except InvalidOperation:
            return original
        precision = max(-value.as_tuple().exponent, 0)
        delta = Decimal(_stable_index(seed, 19) - 9) / Decimal("100")
        replacement = value * (Decimal("1") + delta)
        if value != 0:
            bucket = Decimal(10) ** max(value.copy_abs().adjusted(), 0)
            lower = bucket if value > 0 else -bucket * Decimal(10)
            upper = bucket * Decimal(10) if value > 0 else -bucket
            epsilon = Decimal(1).scaleb(-precision)
            replacement = min(max(replacement, lower + epsilon), upper - epsilon)
        formatted = f"{replacement:,.{precision}f}"
        return f"{match.group('prefix')}{formatted}{match.group('suffix')}"

    def _organization(self, original: str, seed: str) -> str:
        suffix = next((item for item in ("Ltd", "Inc", "LLC", "Corp") if original.endswith(item)), "")
        name = _COMPANIES[_stable_index(seed, len(_COMPANIES))]
        return f"{name} {suffix}".strip()

    def _identifier(self, original: str, seed: str) -> str:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if original.isupper() else "abcdefghijklmnopqrstuvwxyz"
        generated: list[str] = []
        for index, character in enumerate(original):
            if character.isdigit():
                generated.append(str(_stable_index(f"{seed}:{index}", 10)))
            elif character.isalpha():
                generated.append(alphabet[_stable_index(f"{seed}:{index}", len(alphabet))])
            else:
                generated.append(character)
        return "".join(generated)

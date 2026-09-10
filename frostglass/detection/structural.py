"""High-precision structural recognizers with local validation."""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Sequence

import phonenumbers

from frostglass.detection.models import CandidateSpan, DetectionContext

_CARD = re.compile(r"(?:\d[ -]?){13,19}")
_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}", re.IGNORECASE)
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b", re.IGNORECASE)
_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_MAC = re.compile(r"\b(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}\b", re.IGNORECASE)
_MONEY = re.compile(r"(?:[$€£]\s?\d[\d,]*(?:\.\d{2})?|\b\d[\d,]*(?:\.\d{2})?\s?(?:USD|EUR|GBP)\b)")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d(). -]{7,}\d)(?!\w)")
_SSN = re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b")


def _luhn(value: str) -> bool:
    digits = [int(char) for char in value if char.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2:
            digit *= 2
            digit -= 9 if digit > 9 else 0
        total += digit
    return total % 10 == 0


def _iban_valid(value: str) -> bool:
    compact = value.replace(" ", "").upper()
    if not 15 <= len(compact) <= 34 or not compact.isalnum():
        return False
    rearranged = compact[4:] + compact[:4]
    digits = "".join(str(ord(char) - 55) if char.isalpha() else char for char in rearranged)
    return int(digits) % 97 == 1


def _valid_ssn(value: str) -> bool:
    digits = value.replace("-", "")
    return digits[:3] not in {"000", "666"} and not digits.startswith("9") and digits[3:5] != "00"


class StructuralDetector:
    """Detect common structured values without retaining their text."""

    def detect(self, text: str, _: DetectionContext) -> Sequence[CandidateSpan]:
        findings: list[CandidateSpan] = []
        for match in _CARD.finditer(text):
            if _luhn(match.group()):
                findings.append(
                    CandidateSpan(
                        "CREDIT_CARD", match.start(), match.end(), 0.95, "structural.luhn", 9
                    )
                )
        for match in _IBAN.finditer(text):
            if _iban_valid(match.group()):
                findings.append(
                    CandidateSpan("IBAN", match.start(), match.end(), 0.95, "structural.iban", 8)
                )
        for match in _EMAIL.finditer(text):
            findings.append(
                CandidateSpan(
                    "EMAIL_ADDRESS", match.start(), match.end(), 0.95, "structural.email", 7
                )
            )
        for match in _SSN.finditer(text):
            confidence = 0.95 if _valid_ssn(match.group()) else 0.6
            findings.append(
                CandidateSpan("US_SSN", match.start(), match.end(), confidence, "structural.ssn", 8)
            )
        for match in _IP.finditer(text):
            try:
                ipaddress.ip_address(match.group())
            except ValueError:
                continue
            findings.append(
                CandidateSpan("IP_ADDRESS", match.start(), match.end(), 0.95, "structural.ip", 5)
            )
        for match in _MAC.finditer(text):
            findings.append(
                CandidateSpan("MAC_ADDRESS", match.start(), match.end(), 0.95, "structural.mac", 5)
            )
        for match in _PHONE.finditer(text):
            try:
                parsed = phonenumbers.parse(match.group(), "US")
            except phonenumbers.NumberParseException:
                continue
            confidence = 0.95 if phonenumbers.is_valid_number(parsed) else 0.6
            if phonenumbers.is_possible_number(parsed):
                findings.append(
                    CandidateSpan(
                        "PHONE_NUMBER",
                        match.start(),
                        match.end(),
                        confidence,
                        "structural.phone",
                        6,
                    )
                )
        for match in _MONEY.finditer(text):
            findings.append(
                CandidateSpan("MONEY", match.start(), match.end(), 0.6, "structural.money", 2)
            )
        return findings

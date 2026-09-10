"""Walk and replace text in all gateway payload locations."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TextLocation:
    path: tuple[str | int, ...]
    text: str


def extract_text(payload: Any) -> list[TextLocation]:
    """Return every text value, including system, messages, tools, calls, and results."""
    found: list[TextLocation] = []

    def walk(value: Any, path: tuple[str | int, ...]) -> None:
        if isinstance(value, str):
            found.append(TextLocation(path, value))
        elif isinstance(value, dict):
            for key, child in value.items():
                walk(child, path + (key,))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, path + (index,))

    walk(payload, ())
    return found


def replace_text(payload: Any, transform: Callable[[str], str]) -> Any:
    """Copy a payload and replace every extracted text value without changing its shape."""
    value = deepcopy(payload)

    def walk(item: Any) -> Any:
        if isinstance(item, str):
            return transform(item)
        if isinstance(item, list):
            return [walk(child) for child in item]
        if isinstance(item, dict):
            return {key: walk(child) for key, child in item.items()}
        return item

    return walk(value)

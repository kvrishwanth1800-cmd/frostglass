"""Provider protocol."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol


class Provider(Protocol):
    async def complete(self, protocol: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    async def stream(self, protocol: str, payload: dict[str, Any]) -> AsyncIterator[str]: ...

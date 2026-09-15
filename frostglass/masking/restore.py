"""Restore vault-backed surrogates in complete and streamed provider responses."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping


class StreamRestorer:
    """Restore surrogates without emitting a possible partial surrogate."""

    def __init__(self, reverse_map: Mapping[str, str], latency_cap: int = 256) -> None:
        self._reverse_map = dict(reverse_map)
        self._tail_length = min(
            max((len(surrogate) for surrogate in self._reverse_map), default=0),
            latency_cap,
        )
        self._buffer = ""

    def feed(self, chunk: str) -> str:
        """Buffer a chunk and emit only text that cannot start a surrogate."""
        self._buffer += chunk
        if self._tail_length == 0:
            emitted, self._buffer = self._buffer, ""
            return emitted
        if len(self._buffer) <= self._tail_length:
            return ""
        emitted = self._buffer[: -self._tail_length]
        self._buffer = self._buffer[-self._tail_length :]
        return restore_text(emitted, self._reverse_map)

    def finish(self) -> str:
        """Restore and flush the remaining tail when the stream ends."""
        remaining, self._buffer = self._buffer, ""
        return restore_text(remaining, self._reverse_map)


def restore_text(text: str, reverse_map: Mapping[str, str]) -> str:
    """Restore all surrogates from a scope-specific reverse mapping."""
    restored = text
    for surrogate in sorted(reverse_map, key=len, reverse=True):
        restored = restored.replace(surrogate, reverse_map[surrogate])
    return restored


def restore_stream(chunks: Iterable[str], reverse_map: Mapping[str, str]) -> Iterator[str]:
    """Yield restored provider chunks while holding a safe rolling tail."""
    restorer = StreamRestorer(reverse_map)
    for chunk in chunks:
        emitted = restorer.feed(chunk)
        if emitted:
            yield emitted
    final = restorer.finish()
    if final:
        yield final

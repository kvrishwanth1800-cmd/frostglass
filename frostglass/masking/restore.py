"""Restore vault-backed surrogates in complete and streamed provider responses."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping


class StreamRestorer:
    """Restore surrogates without emitting any partial surrogate."""

    def __init__(self, reverse_map: Mapping[str, str], latency_cap: int = 256) -> None:
        self._reverse_map = dict(reverse_map)
        self._tail_length = min(
            max((len(surrogate) for surrogate in self._reverse_map), default=0),
            latency_cap,
        )
        self._buffer = ""

    def feed(self, chunk: str) -> str:
        """Buffer a chunk and emit text that cannot be part of a pending match."""
        self._buffer += chunk
        if self._tail_length == 0:
            emitted, self._buffer = self._buffer, ""
            return emitted
        cut = len(self._buffer) - self._tail_length
        if cut <= 0:
            return ""
        for surrogate in self._reverse_map:
            start = self._buffer.find(surrogate)
            while start >= 0:
                end = start + len(surrogate)
                if start < cut < end:
                    cut = start
                start = self._buffer.find(surrogate, start + 1)
        if cut <= 0:
            return ""
        emitted = restore_text(self._buffer[:cut], self._reverse_map)
        self._buffer = self._buffer[cut:]
        return emitted

    def finish(self) -> str:
        """Restore and flush the remaining raw tail when the stream ends."""
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

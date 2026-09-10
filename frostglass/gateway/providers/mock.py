"""Network-free provider used by all M1 tests."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any


class MockProvider:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    async def complete(self, protocol: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.fail:
            raise TimeoutError("mock provider failed")
        if protocol == "anthropic":
            return {
                "id": "msg_mock",
                "type": "message",
                "role": "assistant",
                "model": payload["model"],
                "content": [{"type": "text", "text": "mock response"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 1, "output_tokens": 2},
            }
        return {
            "id": "chatcmpl_mock",
            "object": "chat.completion",
            "created": 0,
            "model": payload["model"],
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "mock response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        }

    async def stream(self, protocol: str, payload: dict[str, Any]) -> AsyncIterator[str]:
        result = await self.complete(protocol, payload)
        if protocol == "anthropic":
            event = {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "mock response"},
            }
            yield "event: content_block_delta\ndata: " + json.dumps(event) + "\n\n"
            yield 'event: message_stop\ndata: {"type": "message_stop"}\n\n'
        else:
            chunk = {
                "id": result["id"],
                "object": "chat.completion.chunk",
                "model": result["model"],
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": "mock response"},
                        "finish_reason": "stop",
                    }
                ],
            }
            yield "data: " + json.dumps(chunk) + "\n\n"
            yield "data: [DONE]\n\n"

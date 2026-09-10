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
            content = [{"type": "text", "text": "mock response"}]
            if payload.get("tools"):
                tool = payload["tools"][0]
                content = [
                    {
                        "type": "tool_use",
                        "id": "toolu_mock",
                        "name": tool["name"],
                        "input": {"query": "mock"},
                    }
                ]
            return {
                "id": "msg_mock",
                "type": "message",
                "role": "assistant",
                "model": payload["model"],
                "content": content,
                "stop_reason": "tool_use" if payload.get("tools") else "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 2},
            }
        message: dict[str, Any] = {"role": "assistant", "content": "mock response"}
        if payload.get("tools"):
            tool = payload["tools"][0]["function"]
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock",
                        "type": "function",
                        "function": {"name": tool["name"], "arguments": '{"query":"mock"}'},
                    }
                ],
            }
        return {
            "id": "chatcmpl_mock",
            "object": "chat.completion",
            "created": 0,
            "model": payload["model"],
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "tool_calls" if payload.get("tools") else "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        }

    async def stream(self, protocol: str, payload: dict[str, Any]) -> AsyncIterator[str]:
        result = await self.complete(protocol, payload)
        if protocol == "anthropic":
            start = {
                "type": "message_start",
                "message": {
                    "id": result["id"],
                    "type": "message",
                    "role": "assistant",
                    "content": [],
                    "model": result["model"],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 1, "output_tokens": 0},
                },
            }
            yield "event: message_start\ndata: " + json.dumps(start) + "\n\n"
            yield (
                "event: content_block_start\ndata: "
                '{"type":"content_block_start","index":0,'
                '"content_block":{"type":"text","text":""}}\n\n'
            )
            event = {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "mock response"},
            }
            yield "event: content_block_delta\ndata: " + json.dumps(event) + "\n\n"
            yield "event: content_block_stop\ndata: {\"type\":\"content_block_stop\",\"index\":0}\n\n"
            yield (
                "event: message_delta\ndata: "
                '{"type":"message_delta","delta":{"stop_reason":"end_turn",'
                '"stop_sequence":null},"usage":{"output_tokens":2}}\n\n'
            )
            yield "event: message_stop\ndata: {\"type\":\"message_stop\"}\n\n"
            return
        first = {
            "id": result["id"],
            "object": "chat.completion.chunk",
            "created": 0,
            "model": result["model"],
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
        yield "data: " + json.dumps(first) + "\n\n"
        chunk = {
            "id": result["id"],
            "object": "chat.completion.chunk",
            "created": 0,
            "model": result["model"],
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "mock response"},
                    "finish_reason": None,
                }
            ],
        }
        yield "data: " + json.dumps(chunk) + "\n\n"
        terminal = {
            "id": result["id"],
            "object": "chat.completion.chunk",
            "created": 0,
            "model": result["model"],
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield "data: " + json.dumps(terminal) + "\n\n"
        yield "data: [DONE]\n\n"

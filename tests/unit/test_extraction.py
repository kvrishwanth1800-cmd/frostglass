"""Security regression tests for gateway payload text extraction (Fixes 1, 2)."""

from __future__ import annotations

from typing import Any

from frostglass.gateway.extract import extract_text, replace_text

SECRET = "AKIA1234567890ABCDEF"


def _texts(payload: dict[str, Any]) -> set[str]:
    return {location.text for location in extract_text(payload)}


def test_openai_embeddings_input_string_is_extracted() -> None:
    assert SECRET in _texts({"model": "m", "input": SECRET})


def test_openai_embeddings_input_list_is_extracted() -> None:
    assert SECRET in _texts({"model": "m", "input": ["safe", SECRET]})


def test_anthropic_tool_use_input_is_extracted() -> None:
    payload = {
        "model": "m",
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "t1",
                        "name": "lookup",
                        "input": {"credential": SECRET},
                    }
                ],
            }
        ],
    }
    assert SECRET in _texts(payload)


def test_anthropic_tool_result_content_string_is_extracted() -> None:
    payload = {
        "model": "m",
        "messages": [
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "t1", "content": SECRET}],
            }
        ],
    }
    assert SECRET in _texts(payload)


def test_anthropic_tool_result_content_blocks_are_extracted() -> None:
    payload = {
        "model": "m",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t1",
                        "content": [{"type": "text", "text": SECRET}],
                    }
                ],
            }
        ],
    }
    assert SECRET in _texts(payload)


def test_tool_schema_default_enum_and_description_are_extracted() -> None:
    payload = {
        "model": "m",
        "messages": [{"role": "user", "content": "run"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "lookup",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "credential": {
                                "type": "string",
                                "default": SECRET,
                                "description": "a token",
                            },
                            "region": {"type": "string", "enum": ["us", "eu"]},
                        },
                    },
                },
            }
        ],
    }
    texts = _texts(payload)
    assert SECRET in texts
    assert "a token" in texts
    assert "us" in texts
    # JSON-schema keywords must never be scanned as prompt text.
    assert "object" not in texts
    assert "string" not in texts


def test_anthropic_input_schema_is_extracted() -> None:
    payload = {
        "model": "m",
        "messages": [{"role": "user", "content": "run"}],
        "tools": [
            {
                "name": "lookup",
                "description": "desc",
                "input_schema": {
                    "type": "object",
                    "properties": {"credential": {"type": "string", "default": SECRET}},
                },
            }
        ],
    }
    assert SECRET in _texts(payload)


def test_replace_text_round_trips_new_locations() -> None:
    payload = {
        "model": "m",
        "input": SECRET,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "tool_use", "input": {"credential": SECRET}},
                    {"type": "tool_result", "content": SECRET},
                ],
            }
        ],
    }
    replaced = replace_text(payload, lambda text: "X")
    assert SECRET not in str(replaced)
    assert replaced["input"] == "X"
    block = replaced["messages"][0]["content"]
    assert block[0]["input"]["credential"] == "X"
    assert block[1]["content"] == "X"

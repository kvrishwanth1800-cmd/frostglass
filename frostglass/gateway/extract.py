"""Extract and replace only prompt-bearing gateway payload text."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

_SCHEMA_TEXT_KEYS = frozenset({"description", "default", "const", "title"})
_SCHEMA_LIST_KEYS = frozenset({"enum", "examples"})


@dataclass(frozen=True)
class TextLocation:
    """One prompt-bearing string and its precise payload path."""

    path: tuple[str | int, ...]
    text: str


def extract_text(payload: Any) -> list[TextLocation]:
    """Return prompt content, never routing or protocol metadata.

    Supported locations span the OpenAI and Anthropic request shapes: system
    prompt content, message content (string or content-block arrays), tool-call
    arguments, Anthropic ``tool_use`` inputs and ``tool_result`` content, tool
    and function definitions including their JSON-schema text, and the
    embeddings ``input`` field. Model identifiers and message role labels are
    deliberately excluded.
    """
    found: list[TextLocation] = []

    def collect_json(value: Any, path: tuple[str | int, ...]) -> None:
        """Collect every string leaf of arbitrary JSON, e.g. tool arguments."""
        if isinstance(value, str):
            found.append(TextLocation(path, value))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                collect_json(item, path + (index,))
        elif isinstance(value, dict):
            for key, item in value.items():
                collect_json(item, path + (key,))

    def collect_schema(value: Any, path: tuple[str | int, ...]) -> None:
        """Collect prompt-bearing text in a JSON schema without its keywords."""
        if isinstance(value, dict):
            for key, item in value.items():
                child = path + (key,)
                if key in _SCHEMA_TEXT_KEYS and isinstance(item, str):
                    found.append(TextLocation(child, item))
                elif key in _SCHEMA_LIST_KEYS and isinstance(item, list):
                    for index, element in enumerate(item):
                        if isinstance(element, str):
                            found.append(TextLocation(child + (index,), element))
                else:
                    collect_schema(item, child)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                collect_schema(item, path + (index,))

    def collect_block(block: Any, path: tuple[str | int, ...]) -> None:
        """Collect text from one message content block, either provider's shape."""
        if not isinstance(block, dict):
            return
        if isinstance(block.get("text"), str):
            found.append(TextLocation(path + ("text",), block["text"]))
        if isinstance(block.get("input"), (dict, list)):
            collect_json(block["input"], path + ("input",))
        if "content" in block:
            collect_content(block["content"], path + ("content",))

    def collect_content(value: Any, path: tuple[str | int, ...]) -> None:
        """Collect message content: a string or a list of content blocks."""
        if isinstance(value, str):
            found.append(TextLocation(path, value))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                collect_block(item, path + (index,))

    def collect_tool_calls(value: Any, path: tuple[str | int, ...]) -> None:
        if not isinstance(value, list):
            return
        for index, call in enumerate(value):
            if not isinstance(call, dict):
                continue
            function = call.get("function")
            if isinstance(function, dict) and isinstance(function.get("arguments"), str):
                found.append(
                    TextLocation(path + (index, "function", "arguments"), function["arguments"])
                )
            if isinstance(call.get("input"), (dict, list)):
                collect_json(call["input"], path + (index, "input"))

    if not isinstance(payload, dict):
        return found

    collect_content(payload.get("system"), ("system",))
    messages = payload.get("messages")
    if isinstance(messages, list):
        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                continue
            base = ("messages", index)
            collect_content(message.get("content"), base + ("content",))
            collect_tool_calls(message.get("tool_calls"), base + ("tool_calls",))
            if isinstance(message.get("tool_result"), str):
                found.append(TextLocation(base + ("tool_result",), message["tool_result"]))
    tools = payload.get("tools")
    if isinstance(tools, list):
        for index, tool in enumerate(tools):
            if not isinstance(tool, dict):
                continue
            base = ("tools", index)
            if isinstance(tool.get("description"), str):
                found.append(TextLocation(base + ("description",), tool["description"]))
            if isinstance(tool.get("input_schema"), (dict, list)):
                collect_schema(tool["input_schema"], base + ("input_schema",))
            function = tool.get("function")
            if isinstance(function, dict):
                if isinstance(function.get("description"), str):
                    found.append(
                        TextLocation(base + ("function", "description"), function["description"])
                    )
                if isinstance(function.get("parameters"), (dict, list)):
                    collect_schema(function["parameters"], base + ("function", "parameters"))
    input_value = payload.get("input")
    if isinstance(input_value, str):
        found.append(TextLocation(("input",), input_value))
    elif isinstance(input_value, list):
        for index, item in enumerate(input_value):
            if isinstance(item, str):
                found.append(TextLocation(("input", index), item))
    return found


def replace_text(payload: Any, transform: Callable[[str], str]) -> Any:
    """Copy and replace exactly the locations returned by ``extract_text``."""
    value = deepcopy(payload)
    if not isinstance(value, dict):
        return value
    locations = extract_text(value)
    for location in locations:
        target: Any = value
        for segment in location.path[:-1]:
            target = target[segment]
        target[location.path[-1]] = transform(location.text)
    return value

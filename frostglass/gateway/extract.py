"""Extract and replace only prompt-bearing gateway payload text."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TextLocation:
    """One prompt-bearing string and its precise payload path."""

    path: tuple[str | int, ...]
    text: str


def extract_text(payload: Any) -> list[TextLocation]:
    """Return prompt content, never routing or protocol metadata.

    The supported locations are system prompt content, message content, tool
    definitions, tool-call arguments, and tool results. Model identifiers and
    message role labels are deliberately excluded.
    """
    found: list[TextLocation] = []

    def collect_content(value: Any, path: tuple[str | int, ...]) -> None:
        if isinstance(value, str):
            found.append(TextLocation(path, value))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    found.append(TextLocation(path + (index, "text"), item["text"]))

    def collect_tool_calls(value: Any, path: tuple[str | int, ...]) -> None:
        if not isinstance(value, list):
            return
        for index, call in enumerate(value):
            if not isinstance(call, dict):
                continue
            function = call.get("function")
            if isinstance(function, dict) and isinstance(function.get("arguments"), str):
                found.append(TextLocation(path + (index, "function", "arguments"), function["arguments"]))
            if isinstance(call.get("input"), str):
                found.append(TextLocation(path + (index, "input"), call["input"]))

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
            function = tool.get("function")
            if isinstance(function, dict) and isinstance(function.get("description"), str):
                found.append(TextLocation(base + ("function", "description"), function["description"]))
            if isinstance(tool.get("description"), str):
                found.append(TextLocation(base + ("description",), tool["description"]))
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

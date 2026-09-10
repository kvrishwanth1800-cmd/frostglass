"""M1 SDK compatibility acceptance tests over an HTTP server and mock provider."""

from __future__ import annotations

import socket
import threading
from collections.abc import Generator
from time import sleep

import anthropic
import openai
import pytest
import uvicorn

from frostglass.main import create_app


@pytest.fixture
def gateway_url() -> Generator[str, None, None]:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(),
            host="127.0.0.1",
            port=port,
            log_level="warning",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        sleep(0.01)
    else:
        raise RuntimeError("gateway test server did not start")
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_ac_m1_01_openai_sdk_non_streaming_streaming_and_tools(gateway_url: str) -> None:
    client = openai.OpenAI(api_key="fg-live-test-key", base_url=f"{gateway_url}/v1")
    response = client.chat.completions.create(
        model="mock-model",
        messages=[{"role": "user", "content": "Hello"}],
    )
    assert response.choices[0].message.content == "mock response"

    stream = client.chat.completions.create(
        model="mock-model",
        messages=[{"role": "user", "content": "Hello"}],
        stream=True,
    )
    content = "".join(chunk.choices[0].delta.content or "" for chunk in stream)
    assert content == "mock response"

    tools = [{"type": "function", "function": {"name": "lookup", "parameters": {}}}]
    tool_response = client.chat.completions.create(
        model="mock-model",
        messages=[{"role": "user", "content": "Look this up"}],
        tools=tools,
    )
    assert tool_response.choices[0].message.tool_calls[0].function.name == "lookup"


def test_ac_m1_02_anthropic_sdk_non_streaming_streaming_and_tools(gateway_url: str) -> None:
    client = anthropic.Anthropic(api_key="fg-live-test-key", base_url=gateway_url)
    response = client.messages.create(
        model="mock-model",
        max_tokens=16,
        messages=[{"role": "user", "content": "Hello"}],
    )
    assert response.content[0].text == "mock response"

    with client.messages.stream(
        model="mock-model",
        max_tokens=16,
        messages=[{"role": "user", "content": "Hello"}],
    ) as stream:
        assert stream.get_final_text() == "mock response"

    tool_response = client.messages.create(
        model="mock-model",
        max_tokens=16,
        messages=[{"role": "user", "content": "Look this up"}],
        tools=[
            {
                "name": "lookup",
                "input_schema": {"type": "object", "properties": {}},
            }
        ],
    )
    assert tool_response.content[0].name == "lookup"

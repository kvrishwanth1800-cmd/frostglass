"""M1 acceptance tests. These use only Frostglass's network-free mock provider."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from frostglass.gateway.extract import extract_text, replace_text
from frostglass.main import create_app

KEY = {"Authorization": "Bearer fg-live-test-key"}
ANTHROPIC_KEY = {
    "x-api-key": "fg-live-test-key",
    "anthropic-version": "2023-06-01",
}


def client() -> TestClient:
    return TestClient(create_app())


def chat_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": "mock-model",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    payload.update(overrides)
    return payload


def test_ac_m1_01_openai_compatible_non_streaming() -> None:
    response = client().post("/v1/chat/completions", headers=KEY, json=chat_payload())
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "mock response"
    assert response.headers["x-frostglass-action"] == "allowed"


def test_ac_m1_02_anthropic_compatible_non_streaming() -> None:
    payload = {
        "model": "mock-model",
        "max_tokens": 16,
        "messages": [{"role": "user", "content": "Hello"}],
    }
    response = client().post("/v1/messages", headers=ANTHROPIC_KEY, json=payload)
    assert response.status_code == 200
    assert response.json()["content"][0]["text"] == "mock response"


def test_ac_m1_03_streaming_matches_non_streaming() -> None:
    test_client = client()
    non_streamed = test_client.post(
        "/v1/chat/completions", headers=KEY, json=chat_payload()
    ).json()
    streamed = test_client.post(
        "/v1/chat/completions", headers=KEY, json=chat_payload(stream=True)
    )
    assert streamed.status_code == 200
    assert "mock response" in streamed.text
    assert "[DONE]" in streamed.text
    assert non_streamed["choices"][0]["message"]["content"] in streamed.text


def test_ac_m1_04_tool_call_payloads_round_trip_and_extract() -> None:
    payload = chat_payload(
        messages=[
            {"role": "system", "content": "System text"},
            {"role": "user", "content": [{"type": "text", "text": "Multipart text"}]},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "name": "lookup",
                            "arguments": '{"query": "tool args"}',
                        }
                    }
                ],
            },
            {"role": "tool", "content": "tool result"},
        ],
        tools=[
            {
                "type": "function",
                "function": {"name": "lookup", "description": "tool definition"},
            }
        ],
    )
    texts = {location.text for location in extract_text(payload)}
    assert {"System text", "Multipart text", "tool definition", "tool result"}.issubset(texts)
    assert any("tool args" in text for text in texts)
    replaced = replace_text(payload, lambda text: f"masked:{text}")
    assert "masked:tool result" in {location.text for location in extract_text(replaced)}
    response = client().post("/v1/chat/completions", headers=KEY, json=payload)
    assert response.status_code == 200


def test_ac_m1_05_budget_and_rate_limit_errors() -> None:
    test_client = client()
    budget = test_client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer fg-live-budget-key"},
        json=chat_payload(),
    )
    assert budget.status_code == 402
    rate_headers = {"Authorization": "Bearer fg-live-rate-key"}
    assert test_client.post(
        "/v1/chat/completions", headers=rate_headers, json=chat_payload()
    ).status_code == 200
    limited = test_client.post(
        "/v1/chat/completions", headers=rate_headers, json=chat_payload()
    )
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"


def test_ac_m1_06_provider_failure_uses_fallback() -> None:
    response = client().post(
        "/v1/chat/completions",
        headers=KEY,
        json=chat_payload(model="fallback/mock-model"),
    )
    assert response.status_code == 200
    assert response.headers["x-frostglass-fallback-used"] == "true"


def test_anthropic_streaming_is_sse() -> None:
    payload = {
        "model": "mock-model",
        "max_tokens": 16,
        "stream": True,
        "messages": [{"role": "user", "content": "Hello"}],
    }
    response = client().post("/v1/messages", headers=ANTHROPIC_KEY, json=payload)
    assert response.status_code == 200
    assert "event: content_block_delta" in response.text


def test_metrics_endpoint() -> None:
    response = client().get("/metrics")
    assert response.status_code == 200
    assert "frostglass_gateway_requests_total" in response.text

"""M2 detection lifecycle integration tests using the network-free mock provider."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from frostglass.main import create_app

_KEY = {"Authorization": "Bearer fg-live-test-key"}


def test_detection_finds_message_and_tool_call_content_before_mock_provider() -> None:
    """The gateway scans all extracted values and exposes only safe entity metadata."""
    payload = {
        "model": "mock-model",
        "messages": [
            {
                "role": "system",
                "content": "Follow the policy for 4111 1111 1111 1111.",
            },
            {"role": "user", "content": "Please run the customer lookup."},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "name": "lookup_customer",
                            "arguments": '{"access_key": "AKIA1234567890ABCDEF"}',
                        }
                    }
                ],
            },
        ],
    }

    response = TestClient(create_app()).post(
        "/v1/chat/completions", headers=_KEY, json=payload
    )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "mock response"
    assert set(json.loads(response.headers["x-frostglass-entities"])) >= {
        "AWS_ACCESS_KEY",
        "CREDIT_CARD",
    }
    assert "AKIA1234567890ABCDEF" not in response.headers["x-frostglass-entities"]
    assert "4111 1111 1111 1111" not in response.headers["x-frostglass-entities"]

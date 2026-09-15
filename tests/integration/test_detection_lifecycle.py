"""M2 detection lifecycle integration tests using the network-free mock provider."""

from __future__ import annotations

from fastapi.testclient import TestClient

from frostglass.main import create_app

_KEY = {"Authorization": "Bearer fg-live-test-key"}


def test_detection_finds_prompt_content_before_policy_blocks_secret() -> None:
    """A tool-call secret is detected and blocked before provider forwarding."""
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
        "/v1/chat/completions",
        headers=_KEY,
        json=payload,
    )

    assert response.status_code == 403
    assert response.json()["error"]["type"] == "policy_block"
    assert "AKIA1234567890ABCDEF" not in response.text

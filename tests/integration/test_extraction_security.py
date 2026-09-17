"""Integration regression: secrets in every prompt-bearing field are blocked.

These cover the gateway extraction gaps found by the M4 adversarial gate:
embeddings input, Anthropic tool_use.input and tool_result.content, and tool
schema text. Each posts a real AWS key pattern and asserts a policy block with
no secret echoed back.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from frostglass.main import create_app
from frostglass.policy.defaults import default_ruleset
from frostglass.policy.loader import PolicyStore

_KEY = {"Authorization": "Bearer fg-live-test-key"}
_ANTHROPIC_KEY = {"x-api-key": "fg-live-test-key", "anthropic-version": "2023-06-01"}
SECRET = "AKIA1234567890ABCDEF"


def _enforcing_client(monkeypatch: object, tmp_path: Path) -> TestClient:
    database = str(tmp_path / "policies.sqlite3")
    PolicyStore(database, default_ruleset()).set_shadow_for_team("test-team", False)
    monkeypatch.setenv("FG_POLICY_DATABASE_PATH", database)  # type: ignore[union-attr]
    return TestClient(create_app())


def test_embeddings_input_secret_is_blocked(monkeypatch: object, tmp_path: Path) -> None:
    client = _enforcing_client(monkeypatch, tmp_path)
    response = client.post(
        "/v1/embeddings", headers=_KEY, json={"model": "mock-model", "input": SECRET}
    )
    assert response.status_code == 403
    assert response.json()["error"]["type"] == "policy_blocked"
    assert SECRET not in response.text


def test_anthropic_tool_use_input_secret_is_blocked(monkeypatch: object, tmp_path: Path) -> None:
    client = _enforcing_client(monkeypatch, tmp_path)
    payload = {
        "model": "mock-model",
        "max_tokens": 16,
        "messages": [
            {
                "role": "user",
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
    response = client.post("/v1/messages", headers=_ANTHROPIC_KEY, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["type"] == "policy_blocked"
    assert SECRET not in response.text


def test_anthropic_tool_result_content_secret_is_blocked(
    monkeypatch: object, tmp_path: Path
) -> None:
    client = _enforcing_client(monkeypatch, tmp_path)
    payload = {
        "model": "mock-model",
        "max_tokens": 16,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "t1", "content": SECRET}],
            }
        ],
    }
    response = client.post("/v1/messages", headers=_ANTHROPIC_KEY, json=payload)
    assert response.status_code == 403
    assert SECRET not in response.text


def test_tool_schema_default_secret_is_blocked(monkeypatch: object, tmp_path: Path) -> None:
    client = _enforcing_client(monkeypatch, tmp_path)
    payload = {
        "model": "mock-model",
        "messages": [{"role": "user", "content": "run it"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "lookup",
                    "parameters": {
                        "type": "object",
                        "properties": {"credential": {"type": "string", "default": SECRET}},
                    },
                },
            }
        ],
    }
    response = client.post("/v1/chat/completions", headers=_KEY, json=payload)
    assert response.status_code == 403
    assert SECRET not in response.text

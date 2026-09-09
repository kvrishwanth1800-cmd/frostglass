import base64

from fastapi.testclient import TestClient


def test_health_reports_status_and_version(monkeypatch) -> None:
    monkeypatch.setenv("FG_VAULT_ENCRYPTION_KEY", base64.b64encode(b"a" * 32).decode())
    monkeypatch.setenv("FG_TENANT_SALT", "tenant-salt-for-tests-must-be-long-enough")

    from frostglass.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.0.1"}

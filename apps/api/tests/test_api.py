from fastapi.testclient import TestClient

from scrapling_cloud.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_missing_api_key_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/usage")
    assert response.status_code == 401


def test_demo_login_returns_dashboard_api_key() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/auth/login",
            json={"email": "demo@scrapling.cloud", "password": "demo12345"},
        )
        assert response.status_code == 200
        api_key = response.json()["api_key"]
        usage = client.get("/v1/usage", headers={"Authorization": f"Bearer {api_key}"})
    assert usage.status_code == 200
    assert usage.json()["plan"] == "growth"

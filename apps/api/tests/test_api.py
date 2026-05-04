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

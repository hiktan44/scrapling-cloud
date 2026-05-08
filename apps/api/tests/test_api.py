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


def test_admin_can_issue_keys_and_add_credits() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/v1/auth/login",
            json={"email": "admin@scrapling.cloud", "password": "admin12345"},
        )
        assert login.status_code == 200
        admin_key = login.json()["api_key"]
        headers = {"Authorization": f"Bearer {admin_key}"}

        orgs = client.get("/v1/admin/organizations", headers=headers)
        assert orgs.status_code == 200
        target = next(org for org in orgs.json() if org["owner_email"] == "demo@scrapling.cloud")

        credit = client.post(
            f"/v1/admin/organizations/{target['id']}/credits",
            headers=headers,
            json={"operation": "add", "credits": 1234, "plan": "growth", "concurrency_limit": 9},
        )
        assert credit.status_code == 200
        assert credit.json()["monthly_credits"] >= target["monthly_credits"] + 1234
        assert credit.json()["concurrency_limit"] == 9

        issued = client.post(
            f"/v1/admin/organizations/{target['id']}/api-keys",
            headers=headers,
            json={"name": "Test issued key"},
        )
        assert issued.status_code == 200
        raw_key = issued.json()["key"]
        usage = client.get("/v1/usage", headers={"Authorization": f"Bearer {raw_key}"})
        assert usage.status_code == 200
        assert usage.json()["plan"] == "growth"

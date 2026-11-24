from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from scrapling_cloud import main
from scrapling_cloud.db import SessionLocal
from scrapling_cloud.main import app
from scrapling_cloud.models import LoginEvent, User

PASSWORD = "journal-pass-123"


def _signup(client: TestClient) -> str:
    email = f"journal-{uuid4().hex[:12]}@example.com"
    response = client.post(
        "/v1/auth/signup",
        json={"email": email, "password": PASSWORD, "organization_name": "Journal Test"},
    )
    assert response.status_code == 200
    return email


def _events(email: str) -> list[tuple[str, object]]:
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
        rows = db.execute(
            select(LoginEvent.method, LoginEvent.created_at).where(LoginEvent.user_id == user_id).order_by(LoginEvent.created_at)
        ).all()
    return [(method, created_at) for method, created_at in rows]


def _total_events() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(LoginEvent))


def test_signup_and_successful_login_write_one_row_each() -> None:
    with TestClient(app) as client:
        email = _signup(client)
        assert [method for method, _ in _events(email)] == ["register"]

        login = client.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert login.status_code == 200

    events = _events(email)
    assert [method for method, _ in events] == ["register", "password"]
    assert all(created_at is not None and created_at.tzinfo is None for _, created_at in events)


def test_failed_login_writes_no_row() -> None:
    with TestClient(app) as client:
        email = _signup(client)
        before = _total_events()

        wrong_password = client.post("/v1/auth/login", json={"email": email, "password": "not-the-password"})
        unknown_user = client.post("/v1/auth/login", json={"email": f"nobody-{uuid4().hex}@example.com", "password": PASSWORD})

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert _total_events() == before
    assert [method for method, _ in _events(email)] == ["register"]


def test_journal_failure_does_not_break_login(monkeypatch) -> None:
    with TestClient(app) as client:
        email = _signup(client)
        # Force a DB-level failure (NOT NULL violation) on the journal insert only.
        monkeypatch.setattr(main, "LoginEvent", lambda **kwargs: LoginEvent(**{**kwargs, "method": None}))

        login = client.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert login.status_code == 200
        api_key = login.json()["api_key"]
        usage = client.get("/v1/usage", headers={"Authorization": f"Bearer {api_key}"})

    assert usage.status_code == 200
    assert [method for method, _ in _events(email)] == ["register"]

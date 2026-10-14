"""Every test gets a throwaway data dir, its own SQLite file, the console
email backend and no external keys, so nothing touches the network or the
real paper portfolio."""

import asyncio
import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TOKEN_RE = re.compile(r"token=([\w.-]+)")


@pytest.fixture
def settings_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("DOCS_DIR", str(tmp_path / "docs"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}")
    monkeypatch.setenv("EMAIL_BACKEND", "console")
    monkeypatch.setenv("FRONTEND_URL", "http://test")
    monkeypatch.setenv("ADMIN_EMAILS", '["admin@test.com"]')
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("WEB3_RPC_URL", "")
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-at-least-thirty-two-bytes")  # HS256 wants >= 32
    monkeypatch.setenv("NEWS_AUTO_REFRESH", "false")
    os.environ.pop("PAPER_TRADING", None)
    os.environ.pop("REQUIRE_EMAIL_VERIFICATION", None)

    from app.api import deps
    from app.config import get_settings
    from app.db.database import dispose_db

    get_settings.cache_clear()
    deps.reset_singletons()
    asyncio.run(dispose_db())
    yield get_settings()
    asyncio.run(dispose_db())
    get_settings.cache_clear()
    deps.reset_singletons()


@pytest.fixture
def client(settings_env):
    from main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


def register_and_verify(client: TestClient, email: str = "user@test.com", password: str = "secret123",
                        name: str = "User") -> str:
    """Register, pull the verification link out of the console outbox, verify.
    Returns the access token."""
    from app.api import deps

    response = client.post("/api/auth/register", json={"email": email, "password": password, "name": name})
    assert response.status_code == 201, response.text
    data = response.json()
    if data["access_token"]:
        return data["access_token"]
    outbox = deps._email.outbox
    assert outbox and outbox[-1]["to"] == email
    token = TOKEN_RE.search(outbox[-1]["text"]).group(1)
    verified = client.post("/api/auth/verify", json={"token": token})
    assert verified.status_code == 200, verified.text
    return verified.json()["access_token"]


@pytest.fixture
def auth_headers(client):
    return {"Authorization": f"Bearer {register_and_verify(client)}"}


@pytest.fixture
def admin_headers(client):
    return {"Authorization": f"Bearer {register_and_verify(client, email='admin@test.com', name='Admin')}"}

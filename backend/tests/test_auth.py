"""Registration with email verification, login, password reset and the
admin endpoints, all against the console email backend."""

import os

from fastapi.testclient import TestClient

from tests.conftest import TOKEN_RE, register_and_verify


def _outbox():
    from app.api import deps

    return deps._email.outbox


def test_register_requires_verification_then_logs_in(client):
    response = client.post("/api/auth/register", json={"email": "ana@test.com", "password": "secret123", "name": "Ana"})
    assert response.status_code == 201
    data = response.json()
    assert data["access_token"] is None and data["verification_required"] is True
    assert data["user"]["is_verified"] is False and data["user"]["role"] == "user"
    assert data["verify_url"].startswith("http://test/verify?token=")  # console backend + DEBUG

    mail = _outbox()[-1]
    assert mail["to"] == "ana@test.com" and "Confirma" in mail["subject"]
    assert "http://test/verify?token=" in mail["text"]

    blocked = client.post("/api/auth/login", json={"email": "ana@test.com", "password": "secret123"})
    assert blocked.status_code == 403 and blocked.json()["detail"]["code"] == "unverified"

    token = TOKEN_RE.search(mail["text"]).group(1)
    verified = client.post("/api/auth/verify", json={"token": token}).json()
    assert verified["access_token"] and verified["user"]["is_verified"] is True

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {verified['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == "ana@test.com"

    again = client.post("/api/auth/login", json={"email": "ana@test.com", "password": "secret123"})
    assert again.status_code == 200 and again.json()["user"]["last_login_at"]


def test_verify_rejects_garbage_and_access_tokens(client):
    token = register_and_verify(client)
    assert client.post("/api/auth/verify", json={"token": "not-a-token-at-all"}).status_code == 400
    assert client.post("/api/auth/verify", json={"token": token}).status_code == 400  # wrong purpose


def test_duplicate_email_and_bad_password(client):
    register_and_verify(client, email="dup@test.com")
    dup = client.post("/api/auth/register", json={"email": "dup@test.com", "password": "secret123"})
    assert dup.status_code == 409 and dup.json()["detail"]["code"] == "email_taken"
    bad = client.post("/api/auth/login", json={"email": "dup@test.com", "password": "wrong-one"})
    assert bad.status_code == 401 and bad.json()["detail"]["code"] == "bad_credentials"


def test_resend_verification_is_generic(client):
    client.post("/api/auth/register", json={"email": "slow@test.com", "password": "secret123"})
    before = len(_outbox())
    assert client.post("/api/auth/resend-verification", json={"email": "slow@test.com"}).status_code == 200
    assert client.post("/api/auth/resend-verification", json={"email": "nobody@test.com"}).status_code == 200
    assert len(_outbox()) == before + 1  # only the real pending account got a mail


def test_password_reset_flow(client):
    register_and_verify(client, email="ana@test.com", password="secret123")
    assert client.post("/api/auth/forgot-password", json={"email": "ana@test.com"}).status_code == 200
    mail = _outbox()[-1]
    assert "http://test/reset?token=" in mail["text"]
    token = TOKEN_RE.search(mail["text"]).group(1)

    weak = client.post("/api/auth/reset-password", json={"token": token, "password": "short"})
    assert weak.status_code == 422
    done = client.post("/api/auth/reset-password", json={"token": token, "password": "newsecret456"})
    assert done.status_code == 200 and done.json()["access_token"]
    assert client.post("/api/auth/login", json={"email": "ana@test.com", "password": "secret123"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "ana@test.com", "password": "newsecret456"}).status_code == 200


def test_admin_endpoints(client, admin_headers, auth_headers):
    assert client.get("/api/admin/users", headers=auth_headers).status_code == 403

    listing = client.get("/api/admin/users", headers=admin_headers).json()
    assert listing["total"] == 2 and {u["email"] for u in listing["items"]} == {"admin@test.com", "user@test.com"}
    admin_user = next(u for u in listing["items"] if u["email"] == "admin@test.com")
    plain_user = next(u for u in listing["items"] if u["email"] == "user@test.com")
    assert admin_user["role"] == "admin"  # ADMIN_EMAILS promoted it on registration

    found = client.get("/api/admin/users", params={"q": "user@"}, headers=admin_headers).json()
    assert found["total"] == 1

    stats = client.get("/api/admin/stats", headers=admin_headers).json()
    assert stats == {"total": 2, "verified": 2, "active": 2, "admins": 1, "new_7d": 2}

    promoted = client.patch(f"/api/admin/users/{plain_user['id']}", json={"role": "admin"}, headers=admin_headers)
    assert promoted.status_code == 200 and promoted.json()["role"] == "admin"

    self_lock = client.patch(f"/api/admin/users/{admin_user['id']}", json={"is_active": False}, headers=admin_headers)
    assert self_lock.status_code == 400

    off = client.patch(f"/api/admin/users/{plain_user['id']}", json={"is_active": False}, headers=admin_headers)
    assert off.json()["is_active"] is False
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 401  # deactivated users are out

    assert client.delete(f"/api/admin/users/{plain_user['id']}", headers=admin_headers).status_code == 204
    assert client.get("/api/admin/stats", headers=admin_headers).json()["total"] == 1


def test_registration_without_verification(settings_env, monkeypatch):
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "false")
    from app.api import deps
    from app.config import get_settings
    from main import create_app

    get_settings.cache_clear()
    deps.reset_singletons()
    with TestClient(create_app()) as client:
        data = client.post("/api/auth/register", json={"email": "fast@test.com", "password": "secret123"}).json()
        assert data["access_token"] and data["verification_required"] is False and data["user"]["is_verified"]
    os.environ.pop("REQUIRE_EMAIL_VERIFICATION", None)

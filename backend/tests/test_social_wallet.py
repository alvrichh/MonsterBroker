"""Sign-In with Ethereum end to end (a real key signs the message), the
providers endpoint, and wallet linking."""

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient

from tests.conftest import register_and_verify

KEY = Account.create()
NONCE, VERIFY, LINK = "/api/auth/wallet/nonce", "/api/auth/wallet/verify", "/api/auth/wallet/link"


def _signed(message: str, key=KEY) -> dict:
    signature = Account.sign_message(encode_defunct(text=message), private_key=key.key).signature.hex()
    return {"message": message, "signature": signature if signature.startswith("0x") else f"0x{signature}"}


def _challenge(client) -> str:
    return client.post(NONCE, json={"address": KEY.address}).json()["message"]


def test_providers_empty_without_credentials(client):
    data = client.get("/api/auth/oauth/providers").json()
    assert data["providers"] == [] and data["wallet"] is True and data["chain_id"] == 84532
    assert client.get("/api/auth/oauth/google/start").status_code == 404


def test_providers_listed_when_configured(settings_env, monkeypatch):
    # GitHub: static endpoints, so the redirect builds offline (Google would
    # fetch its discovery document first).
    monkeypatch.setenv("GITHUB_CLIENT_ID", "id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret")
    monkeypatch.setenv("PUBLIC_API_URL", "https://api.example.org")
    from app.api import deps
    from app.config import get_settings
    from main import create_app

    get_settings.cache_clear()
    deps.reset_singletons()
    with TestClient(create_app()) as client:
        data = client.get("/api/auth/oauth/providers").json()
        assert [p["id"] for p in data["providers"]] == ["github"]
        assert data["providers"][0]["start_url"] == "https://api.example.org/api/auth/oauth/github/start"
        start = client.get("/api/auth/oauth/github/start", follow_redirects=False)
        assert start.status_code in (302, 307)
        location = start.headers["location"]
        assert location.startswith("https://github.com/login/oauth/authorize?")
        assert "redirect_uri=https%3A%2F%2Fapi.example.org%2Fapi%2Fauth%2Foauth%2Fgithub%2Fcallback" in location
        assert "state=" in location and "set-cookie" in start.headers  # CSRF state lives in the session cookie
        assert client.get("/api/auth/oauth/google/start").status_code == 404


def test_wallet_sign_in_creates_an_account(client):
    message = _challenge(client)
    assert message.startswith("test wants you to sign in with your Ethereum account:")
    assert KEY.address in message and "Chain ID: 84532" in message

    done = client.post(VERIFY, json=_signed(message))
    assert done.status_code == 200, done.text
    user = done.json()["user"]
    assert user["provider"] == "wallet" and user["wallet_address"] == KEY.address and user["is_verified"]
    assert user["email"].endswith("@wallet.monsterbroker")

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {done.json()['access_token']}"})
    assert me.status_code == 200 and me.json()["wallet_address"] == KEY.address

    # The nonce is single-use.
    replay = client.post(VERIFY, json=_signed(message))
    assert replay.status_code == 400 and replay.json()["detail"]["code"] == "siwe"


def test_wallet_rejects_wrong_signer_and_tampering(client):
    message = _challenge(client)
    assert client.post(VERIFY, json=_signed(message, Account.create())).status_code == 400
    tampered = message.replace("Nonce: ", "Nonce: x")
    assert client.post(VERIFY, json=_signed(tampered)).status_code == 400
    assert client.post(NONCE, json={"address": "0x1234"}).status_code == 422


def test_link_wallet_to_password_account(client):
    token = register_and_verify(client)
    headers = {"Authorization": f"Bearer {token}"}
    linked = client.post(LINK, json=_signed(_challenge(client)), headers=headers)
    assert linked.status_code == 200 and linked.json()["wallet_address"] == KEY.address

    # Signing in with that wallet now lands on the same account, not a new one.
    again = client.post(VERIFY, json=_signed(_challenge(client))).json()
    assert again["user"]["email"] == "user@test.com" and again["user"]["provider"] == "password"

    # A second account cannot claim the same wallet.
    other = register_and_verify(client, email="second@test.com")
    taken = client.post(LINK, json=_signed(_challenge(client)), headers={"Authorization": f"Bearer {other}"})
    assert taken.status_code == 409 and taken.json()["detail"]["code"] == "wallet_taken"

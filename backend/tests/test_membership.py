"""Free vs Pro: admins grant it, finishing every quest earns a month, and
an open-ended plan is never shortened."""

from datetime import timedelta

from app.db.models import PLAN_PRO, User
from app.services.membership import grant_pro, is_pro, revoke_pro
from app.utils.helpers import utc_now
from tests.conftest import register_and_verify, wallet_sign_in


def _user(**fields) -> User:
    base = {"id": "u", "email": "u@test.com", "name": "U", "password_hash": "x", "role": "user", "plan": "free"}
    return User(**{**base, **fields})


def test_is_pro_rules():
    assert not is_pro(_user())
    assert is_pro(_user(role="admin"))
    assert is_pro(_user(plan=PLAN_PRO))  # no expiry
    assert is_pro(_user(plan=PLAN_PRO, plan_until=utc_now() + timedelta(days=1)))
    assert not is_pro(_user(plan=PLAN_PRO, plan_until=utc_now() - timedelta(minutes=1)))
    assert is_pro(_user(plan=PLAN_PRO, plan_until=(utc_now() + timedelta(days=1)).replace(tzinfo=None)))  # SQLite


def test_grants_extend_but_never_shorten():
    user = _user()
    grant_pro(user, 30, "quests")
    first = user.plan_until
    grant_pro(user, 30, "quests")  # a second month stacks on the first
    assert user.plan_until - first == timedelta(days=30)

    expired = _user(plan=PLAN_PRO, plan_until=utc_now() - timedelta(days=5))
    grant_pro(expired, 10, "admin")  # an expired plan restarts from now
    assert timedelta(days=9) < expired.plan_until - utc_now() <= timedelta(days=10)

    forever = _user(plan=PLAN_PRO, plan_until=None)
    grant_pro(forever, 30, "quests")
    assert forever.plan_until is None  # still open-ended

    revoke_pro(forever)
    assert not is_pro(forever) and forever.plan_source is None


def test_admin_grants_and_revokes_pro(client, admin_headers):
    token = register_and_verify(client, email="member@test.com")
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["plan"] == "free" and me["is_pro"] is False

    granted = client.patch(f"/api/admin/users/{me['id']}", json={"plan": "pro", "plan_days": 7}, headers=admin_headers)
    assert granted.status_code == 200 and granted.json()["is_pro"] is True and granted.json()["plan_until"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["is_pro"] is True and me["plan"] == "pro"

    revoked = client.patch(f"/api/admin/users/{me['id']}", json={"plan": "free"}, headers=admin_headers)
    assert revoked.json()["is_pro"] is False and revoked.json()["plan_until"] is None

    assert client.patch(f"/api/admin/users/{me['id']}", json={"plan": "gold"}, headers=admin_headers).status_code == 422


def test_finishing_every_quest_earns_a_month_of_pro(client):
    from tests.test_token import _record

    token, _ = wallet_sign_in(client)
    headers = {"Authorization": f"Bearer {token}"}
    user_id = client.get("/api/auth/me", headers=headers).json()["id"]
    _record(user_id, "bot_tick")
    client.post("/api/token/events", json={"event": "glossary_read"}, headers=headers)

    first = client.post("/api/token/claim", json={"quest": "welcome"}, headers=headers).json()
    assert first["pro_days_granted"] is None
    client.post("/api/token/claim", json={"quest": "first_tick"}, headers=headers)
    assert client.get("/api/auth/me", headers=headers).json()["is_pro"] is False

    last = client.post("/api/token/claim", json={"quest": "glossary"}, headers=headers).json()
    assert last["pro_days_granted"] == 30
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["is_pro"] is True and me["plan"] == "pro" and me["plan_until"]

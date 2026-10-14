"""Levels add up from what the account did; certificates carry the level
and can be upgraded, never downgraded."""

from app.services.levels import LEVELS, level_for, next_level, outranks
from tests.conftest import register_and_verify, wallet_sign_in
from tests.test_token import _record


def test_ladder_rules():
    assert [lv.id for lv in LEVELS] == ["bronze", "silver", "gold", "platinum"]
    assert level_for(0).id == "bronze" and level_for(29).id == "bronze" and level_for(30).id == "silver"
    assert level_for(80).id == "gold" and level_for(999).id == "platinum"
    assert next_level(level_for(0)).id == "silver" and next_level(level_for(140)) is None
    assert outranks("gold", "silver") and not outranks("silver", "silver") and not outranks("bronze", "gold")


def test_public_ladder(client):
    data = client.get("/api/levels").json()
    assert [lv["id"] for lv in data["levels"]] == ["bronze", "silver", "gold", "platinum"]
    assert data["points"]["certificate"] == 25
    assert data["events"] == ["bot_tick", "glossary_read", "bot_config", "perp_mode", "wallet_lookup"]


def test_bot_settings_earn_events(client, auth_headers):
    client.put("/api/bot/config", json={"strategy": "rsi_reversion"}, headers=auth_headers)
    me = client.get("/api/levels/me", headers=auth_headers).json()
    assert me["events_done"] == ["bot_config"] and me["points"] == 10

    client.put("/api/bot/config", json={"market": "perp", "leverage": 3}, headers=auth_headers)
    me = client.get("/api/levels/me", headers=auth_headers).json()
    assert me["events_done"] == ["bot_config", "perp_mode"] and me["points"] == 20  # bot_config counts once

    courses = client.get("/api/certificates/courses", headers=auth_headers).json()
    perps = next(c for c in courses if c["id"] == "perps-101")
    assert perps["done"] == ["perp_mode"] and perps["completed"] is False  # still needs a tick


def test_points_climb_with_activity(client, admin_headers):
    token, _ = wallet_sign_in(client)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/levels/me").status_code == 401

    me = client.get("/api/levels/me", headers=headers).json()
    assert me["points"] == 10 and me["level"] == "bronze" and me["next_level"] == "silver"  # the wallet
    assert me["breakdown"]["wallet"] == 10 and me["progress"] == round(10 / 30, 3)

    client.post("/api/token/events", json={"event": "glossary_read"}, headers=headers)  # +10
    client.post("/api/token/claim", json={"quest": "welcome"}, headers=headers)  # +15
    me = client.get("/api/levels/me", headers=headers).json()
    assert me["points"] == 35 and me["level"] == "silver" and me["next_at"] == 80

    client.post("/api/certificates/futures-101/issue", json={}, headers=headers)  # +25
    client.post("/api/token/claim", json={"quest": "glossary"}, headers=headers)  # +15
    opinion = {"rating": 5, "text": "Nivel Oro conseguido, qué gusto."}
    review = client.post("/api/reviews", json=opinion, headers=headers)
    me = client.get("/api/levels/me", headers=headers).json()
    assert me["points"] == 75 and me["level"] == "silver"  # the review counts once approved
    client.patch(f"/api/admin/reviews/{review.json()['id']}", json={"status": "approved"}, headers=admin_headers)
    me = client.get("/api/levels/me", headers=headers).json()
    assert me["points"] == 95 and me["level"] == "gold" and me["counts"]["review"] == 1


def test_certificate_carries_and_upgrades_the_level(client):
    token = register_and_verify(client, name="Grace Hopper")
    headers = {"Authorization": f"Bearer {token}"}
    user_id = client.get("/api/auth/me", headers=headers).json()["id"]
    _record(user_id, "bot_tick")

    first = client.post("/api/certificates/monster-starter/issue", json={}, headers=headers).json()
    assert first["tier"] == "bronze"  # 10 points: one event
    svg = client.get(f"/api/certificates/{first['code']}.svg").text
    assert "NIVEL BRONCE" in svg and "#e09a5a" in svg

    client.post("/api/token/events", json={"event": "glossary_read"}, headers=headers)
    client.post("/api/certificates/futures-101/issue", json={}, headers=headers)  # 10+10+25+25 = 70 → silver
    again = client.post("/api/certificates/monster-starter/issue", json={"name": "Other"}, headers=headers).json()
    assert again["code"] == first["code"] and again["holder"] == "Grace Hopper" and again["tier"] == "silver"
    assert "NIVEL PLATA" in client.get(f"/api/certificates/{first['code']}.svg").text
    assert "SILVER LEVEL" in client.get(f"/api/certificates/{first['code']}.svg?lang=en").text

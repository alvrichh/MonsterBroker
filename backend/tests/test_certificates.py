"""Courses track progress through events; a finished course issues one
certificate with a public code, an SVG and a watermark unless the holder
is Pro."""

from tests.conftest import register_and_verify
from tests.test_token import _record

COURSES = "/api/certificates/courses"


def _auth(client, email="learner@test.com"):
    token = register_and_verify(client, email=email, name="Ada Lovelace")
    headers = {"Authorization": f"Bearer {token}"}
    user_id = client.get("/api/auth/me", headers=headers).json()["id"]
    return headers, user_id


def test_catalogue_is_public_and_progress_needs_a_session(client):
    public = client.get(COURSES).json()
    assert [c["id"] for c in public] == ["monster-starter", "futures-101", "perps-101"]
    assert public[0]["requires"] == ["bot_tick"] and public[0]["done"] == [] and public[0]["completed"] is False

    headers, user_id = _auth(client)
    _record(user_id, "bot_tick")
    mine = client.get(COURSES, headers=headers).json()
    starter, futures, _perps = mine
    assert starter["completed"] is True and starter["done"] == ["bot_tick"] and starter["certificate"] is None
    assert futures["completed"] is False


def test_issue_requires_completion_and_happens_once(client):
    headers, user_id = _auth(client)
    denied = client.post("/api/certificates/futures-101/issue", json={}, headers=headers)
    assert denied.status_code == 400 and denied.json()["detail"]["code"] == "not_completed"
    assert client.post("/api/certificates/nope/issue", json={}, headers=headers).status_code == 404
    assert client.post("/api/certificates/futures-101/issue", json={}).status_code == 401

    client.post("/api/token/events", json={"event": "glossary_read"}, headers=headers)
    issued = client.post("/api/certificates/futures-101/issue", json={"name": "  Ada L.  "}, headers=headers)
    assert issued.status_code == 201, issued.text
    cert = issued.json()
    assert cert["holder"] == "Ada L." and cert["course_title"] == "Futuros 101"
    assert cert["code"].startswith("MB-") and len(cert["code"]) == 11
    assert cert["verify_url"] == f"http://test/certificates/verify/{cert['code']}"
    assert cert["svg_url"] == f"http://127.0.0.1:8000/api/certificates/{cert['code']}.svg"

    again = client.post("/api/certificates/futures-101/issue", json={"name": "Someone Else"}, headers=headers)
    assert again.status_code == 201 and again.json()["code"] == cert["code"]  # the same one, name untouched
    assert again.json()["holder"] == "Ada L."

    mine = client.get("/api/certificates/mine", headers=headers).json()
    assert [c["code"] for c in mine] == [cert["code"]]
    course = next(c for c in client.get(COURSES, headers=headers).json() if c["id"] == "futures-101")
    assert course["certificate"]["code"] == cert["code"]


def test_verify_and_render(client, admin_headers):
    headers, user_id = _auth(client)
    _record(user_id, "bot_tick")
    cert = client.post("/api/certificates/monster-starter/issue", json={}, headers=headers).json()
    code = cert["code"]

    verified = client.get(f"/api/certificates/{code.lower()}").json()
    assert verified["valid"] is True and verified["certificate"]["holder"] == "Ada Lovelace"
    assert client.get("/api/certificates/MB-NOPE1234").json() == {"valid": False, "certificate": None}
    assert client.get("/api/certificates/MB-NOPE1234.svg").status_code == 404

    svg = client.get(f"/api/certificates/{code}.svg")
    assert svg.status_code == 200 and svg.headers["content-type"].startswith("image/svg+xml")
    body = svg.text
    assert "Ada Lovelace" in body and code in body and "Trading en papel con el Monstruo" in body
    assert "CERTIFICADO DE APRENDIZAJE" in body and "VERSIÓN GRATUITA" in body  # free: watermarked
    assert "CERTIFICATE OF LEARNING" in client.get(f"/api/certificates/{code}.svg?lang=en").text

    client.patch(f"/api/admin/users/{user_id}", json={"plan": "pro"}, headers=admin_headers)
    clean = client.get(f"/api/certificates/{code}.svg").text
    assert "VERSIÓN GRATUITA" not in clean and 'opacity="0.07"' not in clean


def test_holder_name_is_escaped(client):
    headers, user_id = _auth(client)
    _record(user_id, "bot_tick")
    cert = client.post("/api/certificates/monster-starter/issue", json={"name": "<b>Eve & co</b>"}, headers=headers)
    body = client.get(f"/api/certificates/{cert.json()['code']}.svg").text
    assert "&lt;b&gt;Eve &amp; co&lt;/b&gt;" in body and "<b>Eve" not in body

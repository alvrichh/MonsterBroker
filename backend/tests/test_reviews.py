"""Reviews are real: one per member, moderated, with honest usage numbers
next to them."""

from tests.conftest import register_and_verify

REVIEW = {"rating": 5, "text": "El Monstruo me ha enseñado más que tres cursos de YouTube."}
ADMIN_REVIEWS = "/api/admin/reviews"


def _moderate(client, review_id: str, status: str, headers: dict):
    return client.patch(f"{ADMIN_REVIEWS}/{review_id}", json={"status": status}, headers=headers)


def test_public_list_starts_empty_with_real_numbers(client):
    data = client.get("/api/reviews").json()
    assert data["count"] == 0 and data["average"] is None and data["items"] == []
    assert data["stats"] == {"accounts": 0, "certificates": 0, "claims": 0, "ticks": 0}


def test_submit_needs_a_session_and_valid_input(client, auth_headers):
    assert client.post("/api/reviews", json=REVIEW).status_code == 401
    too_high = client.post("/api/reviews", json={"rating": 6, "text": REVIEW["text"]}, headers=auth_headers)
    too_short = client.post("/api/reviews", json={"rating": 5, "text": "corto"}, headers=auth_headers)
    assert too_high.status_code == 422 and too_short.status_code == 422


def test_moderation_flow(client, auth_headers, admin_headers):
    created = client.post("/api/reviews", json=REVIEW, headers=auth_headers)
    assert created.status_code == 201 and created.json()["status"] == "pending"
    assert created.json()["name"] == "User"
    review_id = created.json()["id"]
    assert client.get("/api/reviews").json()["items"] == []  # not public yet
    assert client.get("/api/reviews/mine", headers=auth_headers).json()["status"] == "pending"

    pending = client.get(f"{ADMIN_REVIEWS}?status=pending", headers=admin_headers).json()
    assert [r["id"] for r in pending] == [review_id]
    assert client.get(ADMIN_REVIEWS, headers=auth_headers).status_code == 403

    approved = _moderate(client, review_id, "approved", admin_headers)
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    public = client.get("/api/reviews").json()
    assert public["count"] == 1 and public["average"] == 5.0 and public["items"][0]["text"] == REVIEW["text"]
    assert public["stats"]["accounts"] == 2

    # Editing keeps a single review and sends it back to moderation.
    edit = {"rating": 4, "text": "Sigue siendo muy bueno, pero quiero alertas."}
    edited = client.post("/api/reviews", json=edit, headers=auth_headers)
    assert edited.json()["id"] == review_id and edited.json()["status"] == "pending"
    assert client.get("/api/reviews").json()["count"] == 0

    assert _moderate(client, review_id, "hidden", admin_headers).json()["status"] == "hidden"
    assert _moderate(client, "nope", "approved", admin_headers).status_code == 404


def test_admin_reviews_are_approved_at_once(client, admin_headers):
    posted = client.post("/api/reviews", json=REVIEW, headers=admin_headers).json()
    assert posted["status"] == "approved" and posted["is_pro"] is True
    assert client.get("/api/reviews").json()["count"] == 1


def test_second_member_has_their_own_review(client, auth_headers):
    other = {"Authorization": f"Bearer {register_and_verify(client, email='other@test.com', name='Otra')}"}
    client.post("/api/reviews", json=REVIEW, headers=auth_headers)
    client.post("/api/reviews", json={"rating": 3, "text": "Está bien pero quiero más cursos."}, headers=other)
    assert client.get("/api/reviews/mine", headers=other).json()["rating"] == 3
    assert client.get("/api/reviews/mine", headers=auth_headers).json()["rating"] == 5

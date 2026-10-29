from tests.helpers import make_question, make_subject, register


def test_question_needs_exactly_one_correct_option(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    r = client.post(
        "/questions",
        json={
            "subject_id": subject["id"],
            "text": "Q",
            "options": [{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}],
        },
    )
    assert r.status_code == 422

    r = client.post(
        "/questions",
        json={
            "subject_id": subject["id"],
            "text": "Q",
            "options": [{"text": "a", "is_correct": False}, {"text": "b", "is_correct": False}],
        },
    )
    assert r.status_code == 422


def test_option_with_only_an_image_is_allowed(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    r = client.post(
        "/questions",
        json={
            "subject_id": subject["id"],
            "text": "Q",
            "options": [
                {"text": "", "image_url": "/uploads/a.png", "is_correct": True},
                {"text": "b", "is_correct": False},
            ],
        },
    )
    assert r.status_code == 201, r.text


def test_option_with_neither_text_nor_image_is_rejected(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    r = client.post(
        "/questions",
        json={
            "subject_id": subject["id"],
            "text": "Q",
            "options": [{"text": "", "is_correct": True}, {"text": "b", "is_correct": False}],
        },
    )
    assert r.status_code == 422


def test_question_rejects_non_http_image_links(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    r = client.post(
        "/questions",
        json={
            "subject_id": subject["id"],
            "text": "Q",
            "image_url": "javascript:alert(1)",
            "options": [{"text": "a", "is_correct": True}, {"text": "b"}],
        },
    )
    assert r.status_code == 422


def test_question_requires_a_real_subject(client):
    register(client, "A", "a@x.com")
    r = client.post(
        "/questions",
        json={
            "subject_id": "not-a-real-subject",
            "text": "Q",
            "options": [{"text": "a", "is_correct": True}, {"text": "b"}],
        },
    )
    assert r.status_code == 404


def test_any_user_can_add_to_any_subject(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"], "Physics")

    register(client, "B", "b@x.com")
    q = make_question(client, subject["id"], "Added by B")
    assert q["text"] == "Added by B"


def test_only_creator_can_delete_their_question(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    q = make_question(client, subject["id"])

    register(client, "B", "b@x.com")
    assert client.delete(f"/questions/{q['id']}").status_code == 404

    client.post("/auth/login", json={"email": "a@x.com", "password": "password123"})
    assert client.delete(f"/questions/{q['id']}").status_code == 200


def test_attempted_question_cannot_be_deleted(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    q = make_question(client, subject["id"])

    practice = client.get(f"/questions/{q['id']}/practice").json()
    option_id = practice["options"][0]["id"]
    client.post(f"/questions/{q['id']}/answer", json={"selected_option_id": option_id})

    r = client.delete(f"/questions/{q['id']}")
    assert r.status_code == 400

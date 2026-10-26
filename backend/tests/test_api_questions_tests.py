from tests.test_api_roles import inline_question, make_question, make_test, register


def test_question_needs_exactly_one_correct_option(client):
    register(client, "T1", "t1@x.com", "teacher")
    r = client.post(
        "/questions",
        json={"text": "Q", "options": [{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}]},
    )
    assert r.status_code == 422

    r = client.post(
        "/questions",
        json={"text": "Q", "options": [{"text": "a", "is_correct": False}, {"text": "b", "is_correct": False}]},
    )
    assert r.status_code == 422


def test_option_with_only_an_image_is_allowed(client):
    register(client, "T1", "t1@x.com", "teacher")
    r = client.post(
        "/questions",
        json={
            "text": "Q",
            "options": [
                {"text": "", "image_url": "/uploads/a.png", "is_correct": True},
                {"text": "b", "is_correct": False},
            ],
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["options"][0]["text"] == ""


def test_option_with_neither_text_nor_image_is_rejected(client):
    register(client, "T1", "t1@x.com", "teacher")
    r = client.post(
        "/questions",
        json={"text": "Q", "options": [{"text": "", "is_correct": True}, {"text": "b", "is_correct": False}]},
    )
    assert r.status_code == 422


def test_question_rejects_non_http_image_links(client):
    register(client, "T1", "t1@x.com", "teacher")
    r = client.post(
        "/questions",
        json={
            "text": "Q",
            "image_url": "javascript:alert(1)",
            "options": [{"text": "a", "is_correct": True}, {"text": "b"}],
        },
    )
    assert r.status_code == 422


def test_question_at_most_six_options(client):
    register(client, "T1", "t1@x.com", "teacher")
    opts = [{"text": str(i), "is_correct": i == 0} for i in range(7)]
    r = client.post("/questions", json={"text": "Q", "options": opts})
    assert r.status_code == 422


def test_question_bank_only_shows_own_questions(client):
    register(client, "T1", "t1@x.com", "teacher")
    make_question(client, "T1 question")
    register(client, "T2", "t2@x.com", "teacher")
    make_question(client, "T2 question")

    r = client.get("/questions")
    assert [q["text"] for q in r.json()] == ["T2 question"]


def test_test_requires_sane_marking_scheme(client):
    register(client, "T1", "t1@x.com", "teacher")
    r = client.post(
        "/tests/with-questions",
        json={
            "title": "Bad",
            "marks_correct": -1,  # must be >= 0
            "marks_wrong": -1,
            "marks_skipped": 0,
            "sections": [{"title": "S1", "duration_mins": 10, "questions": [inline_question()]}],
        },
    )
    assert r.status_code == 422


def test_publish_toggle_and_teacher_only_results(client):
    register(client, "T1", "t1@x.com", "teacher")
    test = make_test(client, published=False)
    assert test["published"] is False

    updated = client.patch(f"/tests/{test['id']}", json={"published": True}).json()
    assert updated["published"] is True

    results = client.get(f"/tests/{test['id']}/results").json()
    assert results["attempt_count"] == 0

    register(client, "T2", "t2@x.com", "teacher")
    assert client.get(f"/tests/{test['id']}/results").status_code == 404
    assert client.patch(f"/tests/{test['id']}", json={"published": False}).status_code == 404

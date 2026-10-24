def register(client, name, email, role, invite_code=None):
    body = {"name": name, "email": email, "password": "password123", "role": role}
    if invite_code:
        body["invite_code"] = invite_code
    r = client.post("/auth/register", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def make_question(client, text="Q1"):
    r = client.post(
        "/questions",
        json={
            "text": text,
            "teacher_rating": "easy",
            "options": [
                {"text": "right", "is_correct": True},
                {"text": "wrong", "is_correct": False},
            ],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def inline_question(text="Q1"):
    return {
        "text": text,
        "teacher_rating": "easy",
        "options": [
            {"text": "right", "is_correct": True},
            {"text": "wrong", "is_correct": False},
        ],
    }


def make_test(client, question_texts=("Q1",), **overrides):
    """Build a one-section test via the Google-Forms-style builder."""
    body = {
        "title": "T",
        "marks_correct": 4,
        "marks_wrong": -1,
        "marks_skipped": 0,
        "published": True,
        "sections": [
            {
                "title": "Section 1",
                "duration_mins": 10,
                "questions": [inline_question(t) for t in question_texts],
            }
        ],
    }
    body.update(overrides)
    r = client.post("/tests/with-questions", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def make_test_with_question(client, text="Q1", **overrides):
    """Build a one-section, one-question test and return (test, question-with-options)."""
    test = make_test(client, question_texts=(text,), **overrides)
    bank = client.get("/questions").json()
    question = next(q for q in bank if q["text"] == text)
    return test, question


def join_test(client, test):
    """A student looks up a test by its room key, unlocking it for them."""
    r = client.post("/student/tests/join", json={"room_key": test["room_key"]})
    assert r.status_code == 200, r.text
    return r.json()


def test_student_cannot_create_question(client):
    register(client, "Stu", "stu@x.com", "student")
    r = client.post(
        "/questions",
        json={"text": "Q", "options": [{"text": "a", "is_correct": True}, {"text": "b"}]},
    )
    assert r.status_code == 403


def test_teacher_cannot_delete_another_teachers_question(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    q = make_question(client)

    register(client, "T2", "t2@x.com", "teacher", "teacher123")
    r = client.delete(f"/questions/{q['id']}")
    assert r.status_code == 404


def test_question_used_in_a_section_cannot_be_deleted(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    make_test(client, question_texts=("Used question",))
    bank = client.get("/questions").json()
    qid = next(q["id"] for q in bank if q["text"] == "Used question")

    r = client.delete(f"/questions/{qid}")
    assert r.status_code == 400


def test_student_cannot_see_unpublished_test(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    make_test(client, published=False)

    register(client, "Stu", "stu@x.com", "student")
    r = client.get("/student/tests")
    assert r.status_code == 200
    assert r.json() == []


def test_student_cannot_read_another_students_attempt(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    test = make_test(client)

    register(client, "S1", "s1@x.com", "student")
    join_test(client, test)
    attempt = client.post("/student/attempts/start", json={"test_id": test["id"]}).json()
    attempt_id = attempt["attempt_id"]
    # Options are never sent with the correct flag while a test is running.
    assert "is_correct" not in attempt["sections"][0]["questions"][0]["options"][0]

    register(client, "S2", "s2@x.com", "student")
    r = client.get(f"/student/attempts/{attempt_id}")
    assert r.status_code == 404


def test_teacher_cannot_see_students_profile_endpoint(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    r = client.get("/profile")
    assert r.status_code == 403

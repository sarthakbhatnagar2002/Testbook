from tests.test_api_roles import register


def test_create_test_with_sections_and_inline_questions(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    r = client.post(
        "/tests/with-questions",
        json={
            "title": "Form-built test",
            "marks_correct": 4,
            "marks_wrong": -1,
            "marks_skipped": 0,
            "published": True,
            "sections": [
                {
                    "title": "Math",
                    "duration_mins": 15,
                    "questions": [
                        {
                            "text": "2 + 2 = ?",
                            "options": [
                                {"text": "3", "is_correct": False},
                                {"text": "4", "is_correct": True},
                            ],
                        }
                    ],
                },
                {
                    "title": "Geography",
                    "duration_mins": 10,
                    "questions": [
                        {
                            "text": "Capital of France?",
                            "options": [
                                {"text": "Paris", "is_correct": True},
                                {"text": "Rome", "is_correct": False},
                            ],
                        }
                    ],
                },
            ],
        },
    )
    assert r.status_code == 201, r.text
    test = r.json()
    assert test["published"] is True
    assert test["total_duration_mins"] == 25
    assert len(test["sections"]) == 2
    assert [s["title"] for s in test["sections"]] == ["Math", "Geography"]
    assert [s["question_count"] for s in test["sections"]] == [1, 1]

    bank = client.get("/questions").json()
    assert {q["text"] for q in bank} == {"2 + 2 = ?", "Capital of France?"}


def test_with_questions_rejects_empty_section_list(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    r = client.post(
        "/tests/with-questions",
        json={
            "title": "Empty",
            "marks_correct": 4,
            "marks_wrong": -1,
            "marks_skipped": 0,
            "sections": [],
        },
    )
    assert r.status_code == 422


def test_with_questions_rejects_section_with_no_questions(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    r = client.post(
        "/tests/with-questions",
        json={
            "title": "T",
            "marks_correct": 4,
            "marks_wrong": -1,
            "marks_skipped": 0,
            "sections": [{"title": "S1", "duration_mins": 10, "questions": []}],
        },
    )
    assert r.status_code == 422


def test_with_questions_rejects_bad_option_shape(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    r = client.post(
        "/tests/with-questions",
        json={
            "title": "Bad",
            "marks_correct": 4,
            "marks_wrong": -1,
            "marks_skipped": 0,
            "sections": [
                {
                    "title": "S1",
                    "duration_mins": 10,
                    "questions": [
                        {
                            "text": "Q",
                            "options": [{"text": "a", "is_correct": False}, {"text": "b", "is_correct": False}],
                        }
                    ],
                }
            ],
        },
    )
    assert r.status_code == 422


def test_each_teacher_only_sees_their_own_questions_via_builder(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    client.post(
        "/tests/with-questions",
        json={
            "title": "T1 test",
            "marks_correct": 4,
            "marks_wrong": -1,
            "marks_skipped": 0,
            "sections": [
                {
                    "title": "S1",
                    "duration_mins": 10,
                    "questions": [
                        {
                            "text": "Q1",
                            "options": [{"text": "a", "is_correct": True}, {"text": "b", "is_correct": False}],
                        }
                    ],
                }
            ],
        },
    )
    register(client, "T2", "t2@x.com", "teacher", "teacher123")
    assert client.get("/questions").json() == []

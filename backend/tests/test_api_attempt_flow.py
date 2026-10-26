from datetime import datetime, timedelta, timezone

from tests.test_api_roles import inline_question, join_test, make_test, make_test_with_question, register


def test_full_attempt_lifecycle(client):
    register(client, "T1", "t1@x.com", "teacher")
    client.post(
        "/tests/with-questions",
        json={
            "title": "T",
            "marks_correct": 4,
            "marks_wrong": -1,
            "marks_skipped": 0,
            "published": True,
            "sections": [
                {
                    "title": "Section 1",
                    "duration_mins": 10,
                    "questions": [inline_question("Q1"), inline_question("Q2")],
                }
            ],
        },
    )
    test = client.get("/tests").json()[0]
    bank = {q["text"]: q for q in client.get("/questions").json()}
    q1, q2 = bank["Q1"], bank["Q2"]

    register(client, "Stu", "stu@x.com", "student")
    join_test(client, test)
    state = client.post("/student/attempts/start", json={"test_id": test["id"]}).json()
    attempt_id = state["attempt_id"]
    assert state["status"] == "in_progress"
    assert len(state["sections"]) == 1
    assert len(state["sections"][0]["questions"]) == 2
    correct_option_q1 = next(o["id"] for o in q1["options"] if o["is_correct"])

    # Starting again while in progress resumes the same attempt.
    again = client.post("/student/attempts/start", json={"test_id": test["id"]}).json()
    assert again["attempt_id"] == attempt_id

    autosave_body = {
        "current_question_id": q1["id"],
        "questions": {
            q1["id"]: {
                "selected_option_id": correct_option_q1,
                "visited": True,
                "marked_for_review": False,
                "time_spent_seconds": 12,
            }
        },
        "sections": {
            state["sections"][0]["id"]: {"started_at": "2026-01-01T00:00:00Z", "locked": False},
        },
    }
    r = client.patch(f"/student/attempts/{attempt_id}/autosave", json=autosave_body)
    assert r.json() == {"ok": True}

    # Resuming shows the restored draft.
    resumed = client.get(f"/student/attempts/{attempt_id}").json()
    assert resumed["draft"]["questions"][q1["id"]]["selected_option_id"] == correct_option_q1
    assert resumed["draft"]["sections"][state["sections"][0]["id"]]["locked"] is False

    result = client.post(f"/student/attempts/{attempt_id}/submit", json=autosave_body).json()
    assert result["correct_count"] == 1
    assert result["skipped_count"] == 1
    assert result["score"] == 4
    # The review shows the correct answer now that the test is submitted.
    q1_review = next(a for a in result["answers"] if a["question"]["id"] == q1["id"])
    assert any(o["is_correct"] for o in q1_review["question"]["options"])

    # Idempotent: submitting again returns the same result, no double count.
    again_result = client.post(f"/student/attempts/{attempt_id}/submit", json=autosave_body).json()
    assert again_result["score"] == 4

    # GET result works post-submit.
    fetched = client.get(f"/student/attempts/{attempt_id}/result").json()
    assert fetched["score"] == 4

    # Shows up in history.
    history = client.get("/student/tests/history").json()
    assert len(history) == 1
    assert history[0]["score"] == 4

    # Profile reflects it.
    profile = client.get("/profile").json()
    assert profile["tests_taken"] == 1
    assert profile["average_score"] == 4


def test_cannot_submit_before_grading_wrong_question_ids(client):
    register(client, "T1", "t1@x.com", "teacher")
    test, q1 = make_test_with_question(client, "Q1")

    register(client, "Stu", "stu@x.com", "student")
    join_test(client, test)
    attempt_id = client.post("/student/attempts/start", json={"test_id": test["id"]}).json()["attempt_id"]
    result = client.post(
        f"/student/attempts/{attempt_id}/submit",
        json={"questions": {q1["id"]: {"selected_option_id": "not-a-real-option"}}},
    ).json()
    assert result["skipped_count"] == 1


def test_upcoming_test_is_not_startable_yet(client):
    register(client, "T1", "t1@x.com", "teacher")
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    test, _ = make_test_with_question(client, "Q1", start_time=future)

    register(client, "Stu", "stu@x.com", "student")
    join_test(client, test)
    tests_list = client.get("/student/tests").json()
    assert tests_list[0]["availability"] == "upcoming"

    r = client.post("/student/attempts/start", json={"test_id": test["id"]})
    assert r.status_code == 400


def test_closed_test_cannot_be_started(client):
    register(client, "T1", "t1@x.com", "teacher")
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    test, _ = make_test_with_question(client, "Q1", end_time=past)

    register(client, "Stu", "stu@x.com", "student")
    join_test(client, test)
    assert client.get("/student/tests").json() == []
    r = client.post("/student/attempts/start", json={"test_id": test["id"]})
    assert r.status_code == 400


def test_total_duration_is_sum_of_sections(client):
    register(client, "T1", "t1@x.com", "teacher")
    client.post(
        "/tests/with-questions",
        json={
            "title": "Multi-section",
            "marks_correct": 4,
            "marks_wrong": -1,
            "marks_skipped": 0,
            "published": True,
            "sections": [
                {"title": "A", "duration_mins": 20, "questions": [inline_question("A1")]},
                {"title": "B", "duration_mins": 30, "questions": [inline_question("B1")]},
            ],
        },
    )
    test = client.get("/tests").json()[0]
    assert test["total_duration_mins"] == 50

    register(client, "Stu", "stu@x.com", "student")
    join_test(client, test)
    student_test = client.get("/student/tests").json()[0]
    assert student_test["total_duration_mins"] == 50


def test_report_question(client):
    register(client, "T1", "t1@x.com", "teacher")
    test, q1 = make_test_with_question(client, "Q1")

    register(client, "Stu", "stu@x.com", "student")
    join_test(client, test)
    attempt_id = client.post("/student/attempts/start", json={"test_id": test["id"]}).json()["attempt_id"]
    r = client.post(
        "/student/reports",
        json={"question_id": q1["id"], "test_attempt_id": attempt_id, "message": "Option B is also correct"},
    )
    assert r.status_code == 201


def test_cannot_start_without_joining_first(client):
    register(client, "T1", "t1@x.com", "teacher")
    test, _ = make_test_with_question(client, "Q1")

    register(client, "Stu", "stu@x.com", "student")
    r = client.post("/student/attempts/start", json={"test_id": test["id"]})
    assert r.status_code == 403


def test_join_with_wrong_key_fails(client):
    register(client, "T1", "t1@x.com", "teacher")
    make_test_with_question(client, "Q1")

    register(client, "Stu", "stu@x.com", "student")
    r = client.post("/student/tests/join", json={"room_key": "NOPE99"})
    assert r.status_code == 404


def test_join_is_case_insensitive(client):
    register(client, "T1", "t1@x.com", "teacher")
    test, _ = make_test_with_question(client, "Q1")

    register(client, "Stu", "stu@x.com", "student")
    r = client.post("/student/tests/join", json={"room_key": test["room_key"].lower()})
    assert r.status_code == 200


def test_cannot_join_or_start_an_archived_test(client):
    register(client, "T1", "t1@x.com", "teacher")
    test, _ = make_test_with_question(client, "Q1")
    client.patch(f"/tests/{test['id']}", json={"archived": True})

    register(client, "Stu", "stu@x.com", "student")
    r = client.post("/student/tests/join", json={"room_key": test["room_key"]})
    assert r.status_code == 404


def test_archiving_after_joining_blocks_a_new_start(client):
    register(client, "T1", "t1@x.com", "teacher")
    test, _ = make_test_with_question(client, "Q1")

    register(client, "Stu", "stu@x.com", "student")
    join_test(client, test)

    client.post("/auth/login", json={"email": "t1@x.com", "password": "password123"})
    client.patch(f"/tests/{test['id']}", json={"archived": True})

    client.post("/auth/login", json={"email": "stu@x.com", "password": "password123"})
    r = client.post("/student/attempts/start", json={"test_id": test["id"]})
    assert r.status_code == 400

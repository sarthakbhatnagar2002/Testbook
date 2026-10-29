from tests.helpers import make_question, make_subject, register


def answer(client, question_id, want_correct):
    practice = client.get(f"/questions/{question_id}/practice").json()
    text = "right" if want_correct else "wrong"
    option_id = next(o["id"] for o in practice["options"] if o["text"] == text)
    client.post(f"/questions/{question_id}/answer", json={"selected_option_id": option_id})


def test_empty_profile(client):
    register(client, "A", "a@x.com")
    profile = client.get("/profile").json()
    assert profile["total_questions_solved"] == 0
    assert profile["total_questions_attempted"] == 0
    assert profile["overall_accuracy"] == 0.0
    assert profile["currently_solving"] is None
    assert profile["subjects"] == []
    assert profile["recent_attempts"] == []


def test_profile_tracks_progress_across_subjects(client, db_session):
    a = register(client, "A", "a@x.com")
    physics = make_subject(db_session, a["id"], "Physics")
    chemistry = make_subject(db_session, a["id"], "Chemistry")
    p1 = make_question(client, physics["id"], "P1")
    p2 = make_question(client, physics["id"], "P2")
    c1 = make_question(client, chemistry["id"], "C1")

    answer(client, p1["id"], want_correct=True)
    answer(client, p2["id"], want_correct=False)
    answer(client, c1["id"], want_correct=True)

    profile = client.get("/profile").json()
    assert profile["total_questions_attempted"] == 3
    assert profile["total_questions_solved"] == 2
    assert round(profile["overall_accuracy"]) == 67

    by_name = {s["subject_name"]: s for s in profile["subjects"]}
    assert by_name["Physics"]["solved_count"] == 1
    assert by_name["Physics"]["total_questions"] == 2
    assert by_name["Chemistry"]["solved_count"] == 1

    # Most recently practiced subject (Chemistry, answered last) is "currently solving".
    assert profile["currently_solving"]["subject_name"] == "Chemistry"

    assert len(profile["recent_attempts"]) == 3
    assert profile["recent_attempts"][0]["question_text"] == "C1"


def test_profile_isolated_per_user(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"], "Physics")
    q = make_question(client, subject["id"])
    answer(client, q["id"], want_correct=True)

    register(client, "B", "b@x.com")
    profile = client.get("/profile").json()
    assert profile["total_questions_attempted"] == 0

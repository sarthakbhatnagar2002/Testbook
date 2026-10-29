from tests.helpers import make_question, make_subject, register


def answer_correctly(client, question_id):
    """Looks up the option labelled 'right' and submits it."""
    practice = client.get(f"/questions/{question_id}/practice").json()
    option_id = next(o["id"] for o in practice["options"] if o["text"] == "right")
    r = client.post(f"/questions/{question_id}/answer", json={"selected_option_id": option_id})
    assert r.status_code == 200, r.text
    return r.json()


def test_subjects_have_no_create_endpoint(client, db_session):
    """Subjects are a fixed, pre-seeded set -- nobody can create one via the API."""
    a = register(client, "A", "a@x.com")
    make_subject(db_session, a["id"], "Physics")

    r = client.post("/subjects", json={"name": "Biology"})
    assert r.status_code == 405


def test_pre_seeded_subjects_are_visible_to_any_user(client, db_session):
    a = register(client, "A", "a@x.com")
    make_subject(db_session, a["id"], "Physics")
    make_subject(db_session, a["id"], "Chemistry")

    register(client, "B", "b@x.com")
    names = {s["name"] for s in client.get("/subjects").json()}
    assert names == {"Physics", "Chemistry"}


def test_subject_counts_questions_and_progress(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"], "Physics")
    q1 = make_question(client, subject["id"], "Q1")
    make_question(client, subject["id"], "Q2")

    before = client.get("/subjects").json()[0]
    assert before["question_count"] == 2
    assert before["solved_count"] == 0
    assert before["accuracy"] == 0.0

    answer_correctly(client, q1["id"])

    after = client.get("/subjects").json()[0]
    assert after["solved_count"] == 1
    assert after["accuracy"] == 100.0

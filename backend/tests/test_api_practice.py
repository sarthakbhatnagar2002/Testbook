from tests.helpers import make_question, make_subject, register


def test_practice_never_reveals_correct_option(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    q = make_question(client, subject["id"])

    practice = client.get(f"/questions/{q['id']}/practice").json()
    assert "is_correct" not in practice["options"][0]
    assert practice["status"] == "not_attempted"


def test_answering_reveals_correct_option_and_explanation(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    q = make_question(client, subject["id"], "Q1", explanation="Because of X.")

    practice = client.get(f"/questions/{q['id']}/practice").json()
    right_id = next(o["id"] for o in practice["options"] if o["text"] == "right")
    wrong_id = next(o["id"] for o in practice["options"] if o["text"] == "wrong")

    wrong_result = client.post(f"/questions/{q['id']}/answer", json={"selected_option_id": wrong_id}).json()
    assert wrong_result["is_correct"] is False
    assert wrong_result["correct_option_id"] == right_id
    assert wrong_result["explanation"] == "Because of X."

    right_result = client.post(f"/questions/{q['id']}/answer", json={"selected_option_id": right_id}).json()
    assert right_result["is_correct"] is True


def test_status_updates_after_answering(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    q = make_question(client, subject["id"])

    practice = client.get(f"/questions/{q['id']}/practice").json()
    right_id = next(o["id"] for o in practice["options"] if o["text"] == "right")
    client.post(f"/questions/{q['id']}/answer", json={"selected_option_id": right_id})

    updated = client.get(f"/questions/{q['id']}/practice").json()
    assert updated["status"] == "correct"

    listing = client.get(f"/subjects/{subject['id']}/questions").json()
    assert listing[0]["status"] == "correct"


def test_retrying_updates_status_to_latest_outcome(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    q = make_question(client, subject["id"])
    practice = client.get(f"/questions/{q['id']}/practice").json()
    right_id = next(o["id"] for o in practice["options"] if o["text"] == "right")
    wrong_id = next(o["id"] for o in practice["options"] if o["text"] == "wrong")

    client.post(f"/questions/{q['id']}/answer", json={"selected_option_id": right_id})
    client.post(f"/questions/{q['id']}/answer", json={"selected_option_id": wrong_id})

    updated = client.get(f"/questions/{q['id']}/practice").json()
    assert updated["status"] == "incorrect"


def test_option_from_another_question_is_rejected(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    q1 = make_question(client, subject["id"], "Q1")
    q2 = make_question(client, subject["id"], "Q2")

    q2_practice = client.get(f"/questions/{q2['id']}/practice").json()
    foreign_option_id = q2_practice["options"][0]["id"]

    r = client.post(f"/questions/{q1['id']}/answer", json={"selected_option_id": foreign_option_id})
    assert r.status_code == 400


def test_next_prev_question_navigation(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    q1 = make_question(client, subject["id"], "Q1")
    q2 = make_question(client, subject["id"], "Q2")
    q3 = make_question(client, subject["id"], "Q3")

    middle = client.get(f"/questions/{q2['id']}/practice").json()
    assert middle["prev_question_id"] == q1["id"]
    assert middle["next_question_id"] == q3["id"]

    first = client.get(f"/questions/{q1['id']}/practice").json()
    assert first["prev_question_id"] is None

    last = client.get(f"/questions/{q3['id']}/practice").json()
    assert last["next_question_id"] is None


def test_answer_requires_a_selected_option(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    q = make_question(client, subject["id"])

    r = client.post(f"/questions/{q['id']}/answer", json={})
    assert r.status_code == 422

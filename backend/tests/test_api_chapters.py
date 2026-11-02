from tests.helpers import make_chapter, make_question, make_subject, register


def test_chapters_have_no_create_endpoint(client, db_session):
    """Chapters are a fixed, pre-seeded set -- nobody can create one via the API."""
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])

    r = client.post(f"/subjects/{subject['id']}/chapters", json={"name": "Kinematics"})
    assert r.status_code == 405


def test_lists_chapters_in_position_order(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    make_chapter(db_session, subject["id"], "Second", position=1)
    make_chapter(db_session, subject["id"], "First", position=0)

    names = [c["name"] for c in client.get(f"/subjects/{subject['id']}/chapters").json()]
    assert names == ["First", "Second"]


def test_chapter_counts_questions_and_progress(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    chapter = make_chapter(db_session, subject["id"], "Kinematics")
    q1 = make_question(db_session, subject["id"], a["id"], "Q1", chapter_id=chapter["id"])
    make_question(db_session, subject["id"], a["id"], "Q2", chapter_id=chapter["id"])

    before = client.get(f"/subjects/{subject['id']}/chapters").json()[0]
    assert before["question_count"] == 2
    assert before["solved_count"] == 0

    practice = client.get(f"/questions/{q1['id']}/practice").json()
    right_id = next(o["id"] for o in practice["options"] if o["text"] == "right")
    client.post(f"/questions/{q1['id']}/answer", json={"selected_option_id": right_id})

    after = client.get(f"/subjects/{subject['id']}/chapters").json()[0]
    assert after["solved_count"] == 1
    assert after["accuracy"] == 100.0


def test_unknown_subject_404s(client):
    register(client, "A", "a@x.com")
    r = client.get("/subjects/not-a-real-subject/chapters")
    assert r.status_code == 404

from datetime import timedelta

from app import models
from app.time_utils import utcnow
from tests.helpers import make_question, make_subject, register


def test_empty_activity(client):
    register(client, "A", "a@x.com")
    r = client.get("/profile/activity")
    assert r.status_code == 200
    assert r.json() == {}


def test_activity_only_counts_correct_attempts(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    q = make_question(client, subject["id"])

    practice = client.get(f"/questions/{q['id']}/practice").json()
    wrong_id = next(o["id"] for o in practice["options"] if o["text"] == "wrong")
    client.post(f"/questions/{q['id']}/answer", json={"selected_option_id": wrong_id})

    assert client.get("/profile/activity").json() == {}


def test_activity_groups_by_day_across_multiple_days(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    q1 = make_question(client, subject["id"], "Q1")
    q2 = make_question(client, subject["id"], "Q2")

    # Today: one correct attempt via the real API.
    practice = client.get(f"/questions/{q1['id']}/practice").json()
    right_id = next(o["id"] for o in practice["options"] if o["text"] == "right")
    client.post(f"/questions/{q1['id']}/answer", json={"selected_option_id": right_id})

    # Backdate two more correct attempts to yesterday, directly in the DB.
    yesterday = utcnow() - timedelta(days=1)
    db_session.add_all(
        [
            models.Attempt(
                user_id=a["id"], question_id=q1["id"], selected_option_id=right_id,
                is_correct=True, created_at=yesterday,
            ),
            models.Attempt(
                user_id=a["id"], question_id=q2["id"], selected_option_id=right_id,
                is_correct=True, created_at=yesterday,
            ),
        ]
    )
    db_session.commit()

    activity = client.get("/profile/activity").json()
    assert len(activity) == 2
    today_key = utcnow().strftime("%Y-%m-%d")
    yesterday_key = yesterday.strftime("%Y-%m-%d")
    assert activity[today_key] == 1
    assert activity[yesterday_key] == 2


def test_activity_isolated_per_user(client, db_session):
    a = register(client, "A", "a@x.com")
    subject = make_subject(db_session, a["id"])
    q = make_question(client, subject["id"])
    practice = client.get(f"/questions/{q['id']}/practice").json()
    right_id = next(o["id"] for o in practice["options"] if o["text"] == "right")
    client.post(f"/questions/{q['id']}/answer", json={"selected_option_id": right_id})

    register(client, "B", "b@x.com")
    assert client.get("/profile/activity").json() == {}

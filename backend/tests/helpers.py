from app import models


def register(client, name, email):
    r = client.post("/auth/register", json={"name": name, "email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    return r.json()


def make_subject(db_session, creator_id, name="Physics"):
    """Subjects have no create API (they're a fixed, pre-seeded set) -- insert directly."""
    subject = models.Subject(name=name, created_by=creator_id)
    db_session.add(subject)
    db_session.commit()
    db_session.refresh(subject)
    return {"id": subject.id, "name": subject.name}


def inline_question(text="Q1", correct_index=0):
    return {
        "text": text,
        "options": [
            {"text": "right", "is_correct": correct_index == 0},
            {"text": "wrong", "is_correct": correct_index == 1},
        ],
    }


def make_question(client, subject_id, text="Q1", explanation=None):
    body = inline_question(text)
    body["subject_id"] = subject_id
    if explanation:
        body["explanation"] = explanation
    r = client.post("/questions", json=body)
    assert r.status_code == 201, r.text
    return r.json()

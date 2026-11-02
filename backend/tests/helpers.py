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


def make_chapter(db_session, subject_id, name="Chapter 1", position=0):
    """Chapters have no create API (they're a fixed, pre-seeded set) -- insert directly."""
    chapter = models.Chapter(subject_id=subject_id, name=name, position=position)
    db_session.add(chapter)
    db_session.commit()
    db_session.refresh(chapter)
    return {"id": chapter.id, "name": chapter.name, "subject_id": chapter.subject_id}


def make_question(db_session, subject_id, creator_id, text="Q1", explanation=None, correct_index=0, chapter_id=None):
    """Questions have no create API anymore (fixed, pre-seeded content) -- insert directly."""
    if chapter_id is None:
        chapter_id = make_chapter(db_session, subject_id)["id"]

    question = models.Question(
        subject_id=subject_id, chapter_id=chapter_id, created_by=creator_id, text=text, explanation=explanation
    )
    question.options = [
        models.Option(text="right", position=0, is_correct=correct_index == 0),
        models.Option(text="wrong", position=1, is_correct=correct_index == 1),
    ]
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    return {"id": question.id, "text": question.text, "chapter_id": question.chapter_id}

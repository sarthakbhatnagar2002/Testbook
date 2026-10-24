import json
from datetime import datetime, timedelta, timezone

import pytest

from app import models
from app.attempts_logic import finalize_attempt, finalize_if_expired


def mk_user(db, name, role):
    user = models.User(name=name, email=f"{name}@x.com", password_hash="x", role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def world(db_session):
    """Teacher, two students, a 3-question test (mirrors the Next.js integration test)."""
    db = db_session
    teacher = mk_user(db, "t", "teacher")
    student = mk_user(db, "s1", "student")
    student2 = mk_user(db, "s2", "student")

    questions = []
    for i in range(3):
        q = models.Question(teacher_id=teacher.id, text=f"Q{i}")
        db.add(q)
        db.commit()
        db.refresh(q)
        correct = models.Option(question_id=q.id, text="right", is_correct=True, position=0)
        wrong = models.Option(question_id=q.id, text="wrong", is_correct=False, position=1)
        db.add_all([correct, wrong])
        db.commit()
        db.refresh(correct)
        db.refresh(wrong)
        questions.append({"id": q.id, "correct": correct.id, "wrong": wrong.id})

    test = models.Test(teacher_id=teacher.id, title="T", room_key="ABC123", published=True)
    db.add(test)
    db.commit()
    db.refresh(test)
    section = models.TestSection(test_id=test.id, title="Section 1", position=0, duration_mins=10)
    db.add(section)
    db.commit()
    db.refresh(section)
    for position, q in enumerate(questions):
        db.add(models.TestQuestion(section_id=section.id, question_id=q["id"], position=position))
    db.commit()

    return {
        "db": db,
        "teacher": teacher,
        "student": student,
        "student2": student2,
        "q": questions,
        "test_id": test.id,
    }


def counters(db, question_id):
    q = db.get(models.Question, question_id)
    return {"attempts": q.attempts_count, "correct": q.correct_count}


def new_test_attempt(db, user_id, test_id, scheme=None):
    scheme = scheme or {"correct": 4, "wrong": -1, "skipped": 0}
    attempt = models.TestAttempt(user_id=user_id, test_id=test_id, scheme_snapshot=json.dumps(scheme))
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt.id


class TestFirstAttemptCounting:
    def test_only_first_answered_attempt_counts_toward_difficulty(self, world):
        db, q = world["db"], world["q"]
        # A retake (not practice mode, since that's been removed) answering the
        # same question again must not change the counters a second time.
        first = new_test_attempt(db, world["student"].id, world["test_id"])
        finalize_attempt(db, first, {q[0]["id"]: q[0]["wrong"]})
        assert counters(db, q[0]["id"]) == {"attempts": 1, "correct": 0}

        second = new_test_attempt(db, world["student"].id, world["test_id"])
        finalize_attempt(db, second, {q[0]["id"]: q[0]["correct"]})
        assert counters(db, q[0]["id"]) == {"attempts": 1, "correct": 0}

        # A different student's first attempt does count.
        third = new_test_attempt(db, world["student2"].id, world["test_id"])
        finalize_attempt(db, third, {q[0]["id"]: q[0]["correct"]})
        assert counters(db, q[0]["id"]) == {"attempts": 2, "correct": 1}


class TestTimedTest:
    def test_scores_with_snapshot_scheme_and_updates_counters_once(self, world):
        db, q = world["db"], world["q"]
        attempt_id = new_test_attempt(db, world["student"].id, world["test_id"])
        # Q0 correct, Q1 wrong, Q2 skipped. A forged option id for Q2 must be ignored.
        result = finalize_attempt(
            db,
            attempt_id,
            {q[0]["id"]: q[0]["correct"], q[1]["id"]: q[1]["wrong"], q[2]["id"]: "not-a-real-option"},
        )
        assert (result.score, result.correct_count, result.wrong_count, result.skipped_count) == (3, 1, 1, 1)
        assert counters(db, q[0]["id"]) == {"attempts": 1, "correct": 1}
        assert counters(db, q[1]["id"]) == {"attempts": 1, "correct": 0}
        assert counters(db, q[2]["id"]) == {"attempts": 0, "correct": 0}

    def test_idempotent_submit_does_not_double_count(self, world):
        db, q = world["db"], world["q"]
        attempt_id = new_test_attempt(db, world["student2"].id, world["test_id"])
        finalize_attempt(db, attempt_id, {q[2]["id"]: q[2]["correct"]})
        before = counters(db, q[2]["id"])
        finalize_attempt(db, attempt_id, {q[2]["id"]: q[2]["wrong"]})
        assert counters(db, q[2]["id"]) == before
        attempt = db.get(models.TestAttempt, attempt_id)
        assert attempt.status == "submitted"
        assert attempt.correct_count == 1

    def test_zero_negative_marking_from_snapshot(self, world):
        db, q = world["db"], world["q"]
        attempt_id = new_test_attempt(
            db, world["student"].id, world["test_id"], {"correct": 1, "wrong": 0, "skipped": 0}
        )
        result = finalize_attempt(db, attempt_id, {q[0]["id"]: q[0]["wrong"], q[1]["id"]: q[1]["wrong"]})
        assert result.score == 0

    def test_expired_attempt_grades_from_autosaved_answers(self, world):
        db, q = world["db"], world["q"]
        attempt_id = new_test_attempt(db, world["student2"].id, world["test_id"])
        attempt = db.get(models.TestAttempt, attempt_id)
        attempt.started_at = datetime.now(timezone.utc) - timedelta(hours=1)  # test is 10 min
        attempt.draft_state = json.dumps(
            {"questions": {q[1]["id"]: {"selected_option_id": q[1]["correct"]}}}
        )
        db.commit()
        finalize_if_expired(db, attempt_id)
        db.refresh(attempt)
        assert attempt.status == "submitted"
        assert attempt.score == 4
        assert attempt.skipped_count == 2

    def test_option_from_another_question_is_ignored(self, world):
        db, q = world["db"], world["q"]
        attempt_id = new_test_attempt(db, world["student"].id, world["test_id"])
        result = finalize_attempt(db, attempt_id, {q[1]["id"]: q[2]["correct"]})
        assert result.skipped_count == 3
        assert counters(db, q[1]["id"]) == {"attempts": 0, "correct": 0}

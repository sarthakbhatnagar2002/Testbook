"""Grading + difficulty counters, transactional. Ported from lib/attempts.ts."""

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .scoring import MarkingScheme, Outcome, grade_answer, score_test
from .time_utils import utcnow

# Seconds of grace after the timer ends, for slow networks at the last moment.
SUBMIT_GRACE_SECS = 30


def parse_draft(raw: str) -> dict:
    """Autosaved in-progress state: { currentQuestionId, questions: {qid: {...}} }."""
    try:
        v = json.loads(raw)
        if isinstance(v, dict):
            return v
    except (TypeError, ValueError):
        pass
    return {}


def _already_answered(db: Session, user_id: str, question_ids: list[str]) -> set[str]:
    """
    Which of these questions has this user already answered (not skipped)?
    Only a user's first answered attempt counts toward difficulty.
    """
    if not question_ids:
        return set()
    rows = db.execute(
        select(models.Attempt.question_id)
        .where(
            models.Attempt.user_id == user_id,
            models.Attempt.question_id.in_(question_ids),
            models.Attempt.selected_option_id.is_not(None),
        )
        .distinct()
    ).scalars()
    return set(rows)


def _bump_counters(db: Session, question_id: str, correct: bool) -> None:
    question = db.get(models.Question, question_id)
    if question is None:
        return
    question.attempts_count += 1
    if correct:
        question.correct_count += 1


def total_duration_mins(db: Session, test_id: str) -> int:
    """A test's duration is the sum of its sections' durations."""
    return (
        db.execute(
            select(func.coalesce(func.sum(models.TestSection.duration_mins), 0)).where(
                models.TestSection.test_id == test_id
            )
        ).scalar_one()
    )


def ordered_question_ids(db: Session, test_id: str) -> list[str]:
    """All question ids in a test, in section-then-position order."""
    return list(
        db.execute(
            select(models.TestQuestion.question_id)
            .join(models.TestSection, models.TestSection.id == models.TestQuestion.section_id)
            .where(models.TestSection.test_id == test_id)
            .order_by(models.TestSection.position, models.TestQuestion.position)
        ).scalars()
    )


def finalize_attempt(db: Session, attempt_id: str, answers: dict[str, str]) -> models.TestAttempt | None:
    """
    Grade and close a test attempt. Safe to call twice: a submitted attempt is
    returned unchanged. `answers` maps questionId -> optionId.
    """
    attempt = db.get(models.TestAttempt, attempt_id)
    if attempt is None or attempt.status == "submitted":
        return attempt

    scheme: MarkingScheme = json.loads(attempt.scheme_snapshot)
    question_ids = ordered_question_ids(db, attempt.test_id)

    options_by_question: dict[str, list[models.Option]] = {qid: [] for qid in question_ids}
    if question_ids:
        for opt in db.execute(
            select(models.Option).where(models.Option.question_id.in_(question_ids))
        ).scalars():
            options_by_question[opt.question_id].append(opt)

    seen = _already_answered(db, attempt.user_id, question_ids)

    outcomes: list[Outcome] = []
    for qid in question_ids:
        q_opts = options_by_question[qid]
        correct_opt = next((o for o in q_opts if o.is_correct), None)
        picked_raw = answers.get(qid)
        # Ignore option ids that do not belong to this question.
        picked = picked_raw if any(o.id == picked_raw for o in q_opts) else None
        outcome: Outcome = grade_answer(picked, correct_opt.id) if correct_opt else "skipped"
        outcomes.append(outcome)

        answered = picked is not None
        is_first = answered and qid not in seen
        db.add(
            models.Attempt(
                user_id=attempt.user_id,
                question_id=qid,
                test_attempt_id=attempt.id,
                selected_option_id=picked,
                is_correct=outcome == "correct",
                is_first_attempt=is_first,
            )
        )
        if is_first:
            _bump_counters(db, qid, outcome == "correct")

    result = score_test(outcomes, scheme)
    attempt.score = result.score
    attempt.correct_count = result.correct_count
    attempt.wrong_count = result.wrong_count
    attempt.skipped_count = result.skipped_count
    attempt.status = "submitted"
    attempt.submitted_at = utcnow()
    db.commit()
    db.refresh(attempt)
    return attempt


def finalize_if_expired(db: Session, attempt_id: str) -> None:
    """
    Lazy expiry: if an in-progress attempt is past its time (plus grace), grade
    it from the last autosaved answers. No background job needed.
    """
    attempt = db.get(models.TestAttempt, attempt_id)
    if attempt is None or attempt.status == "submitted":
        return
    duration_mins = total_duration_mins(db, attempt.test_id)
    end = attempt.started_at.timestamp() + duration_mins * 60
    if utcnow().timestamp() > end + SUBMIT_GRACE_SECS:
        draft = parse_draft(attempt.draft_state)
        answers = {
            qid: state.get("selected_option_id")
            for qid, state in draft.get("questions", {}).items()
            if state.get("selected_option_id")
        }
        finalize_attempt(db, attempt_id, answers)

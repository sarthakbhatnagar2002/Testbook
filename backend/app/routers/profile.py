from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_user

router = APIRouter(tags=["profile"])

RECENT_ATTEMPTS_LIMIT = 15


def _subject_progress(db: Session, user_id: str, subject: models.Subject) -> schemas.SubjectProgressOut:
    total_questions = len(subject.questions)
    attempts = db.execute(
        select(models.Attempt.question_id, models.Attempt.is_correct, models.Attempt.created_at)
        .join(models.Question, models.Question.id == models.Attempt.question_id)
        .where(models.Attempt.user_id == user_id, models.Question.subject_id == subject.id)
        .order_by(models.Attempt.created_at)
    ).all()
    solved_count = len({qid for qid, correct, _ in attempts if correct})
    accuracy = round(sum(1 for _, c, _ in attempts if c) / len(attempts) * 100, 1) if attempts else 0.0
    last_practiced_at = attempts[-1][2] if attempts else None

    return schemas.SubjectProgressOut(
        subject_id=subject.id,
        subject_name=subject.name,
        total_questions=total_questions,
        solved_count=solved_count,
        accuracy=accuracy,
        last_practiced_at=last_practiced_at,
    )


@router.get("/profile", response_model=schemas.ProfileOut)
def get_profile(user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    subjects = db.execute(select(models.Subject)).scalars().all()
    progress = [_subject_progress(db, user.id, s) for s in subjects]
    practiced = [p for p in progress if p.last_practiced_at is not None]
    practiced.sort(key=lambda p: p.last_practiced_at, reverse=True)
    currently_solving = practiced[0] if practiced else None

    all_attempts = db.execute(
        select(models.Attempt).where(models.Attempt.user_id == user.id)
    ).scalars().all()
    total_attempted = len({a.question_id for a in all_attempts})
    total_solved = len({a.question_id for a in all_attempts if a.is_correct})
    overall_accuracy = (
        round(sum(1 for a in all_attempts if a.is_correct) / len(all_attempts) * 100, 1)
        if all_attempts
        else 0.0
    )

    recent_rows = db.execute(
        select(models.Attempt, models.Question, models.Subject)
        .join(models.Question, models.Question.id == models.Attempt.question_id)
        .join(models.Subject, models.Subject.id == models.Question.subject_id)
        .where(models.Attempt.user_id == user.id)
        .order_by(models.Attempt.created_at.desc())
        .limit(RECENT_ATTEMPTS_LIMIT)
    ).all()
    recent_attempts = [
        schemas.RecentAttemptOut(
            question_id=question.id,
            question_text=question.text,
            subject_name=subject.name,
            is_correct=attempt.is_correct,
            created_at=attempt.created_at,
        )
        for attempt, question, subject in recent_rows
    ]

    return schemas.ProfileOut(
        name=user.name,
        email=user.email,
        total_questions_solved=total_solved,
        total_questions_attempted=total_attempted,
        overall_accuracy=overall_accuracy,
        currently_solving=currently_solving,
        subjects=sorted(progress, key=lambda p: p.subject_name),
        recent_attempts=recent_attempts,
    )


@router.get("/profile/activity", response_model=dict[str, int])
def get_activity(user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    """
    Questions solved correctly per day, for a GitHub-style contribution graph.
    Keyed by UTC date (YYYY-MM-DD); days with no activity are simply absent --
    the frontend fills gaps with 0 when it builds the grid.
    """
    rows = db.execute(
        select(func.date(models.Attempt.created_at), func.count())
        .where(models.Attempt.user_id == user.id, models.Attempt.is_correct.is_(True))
        .group_by(func.date(models.Attempt.created_at))
    ).all()
    return {day: count for day, count in rows}

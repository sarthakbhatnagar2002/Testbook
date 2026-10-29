from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_user

router = APIRouter(prefix="/subjects", tags=["subjects"])


def _to_out(db: Session, subject: models.Subject, user_id: str) -> schemas.SubjectOut:
    question_count = db.execute(
        select(func.count()).select_from(models.Question).where(models.Question.subject_id == subject.id)
    ).scalar_one()

    attempts = db.execute(
        select(models.Attempt.question_id, models.Attempt.is_correct)
        .join(models.Question, models.Question.id == models.Attempt.question_id)
        .where(models.Attempt.user_id == user_id, models.Question.subject_id == subject.id)
    ).all()
    solved_count = len({qid for qid, correct in attempts if correct})
    accuracy = round(sum(1 for _, c in attempts if c) / len(attempts) * 100, 1) if attempts else 0.0

    return schemas.SubjectOut(
        id=subject.id,
        name=subject.name,
        question_count=question_count,
        solved_count=solved_count,
        accuracy=accuracy,
    )


@router.get("", response_model=list[schemas.SubjectOut])
def list_subjects(user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    """Subjects are a fixed, pre-seeded set — there is no create endpoint."""
    subjects = db.execute(select(models.Subject).order_by(models.Subject.name)).scalars()
    return [_to_out(db, s, user.id) for s in subjects]

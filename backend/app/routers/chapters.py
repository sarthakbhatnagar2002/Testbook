from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_user

router = APIRouter(prefix="/subjects/{subject_id}/chapters", tags=["chapters"])


def _to_out(db: Session, chapter: models.Chapter, user_id: str) -> schemas.ChapterOut:
    question_count = db.execute(
        select(func.count()).select_from(models.Question).where(models.Question.chapter_id == chapter.id)
    ).scalar_one()

    attempts = db.execute(
        select(models.Attempt.question_id, models.Attempt.is_correct)
        .join(models.Question, models.Question.id == models.Attempt.question_id)
        .where(models.Attempt.user_id == user_id, models.Question.chapter_id == chapter.id)
    ).all()
    solved_count = len({qid for qid, correct in attempts if correct})
    accuracy = round(sum(1 for _, c in attempts if c) / len(attempts) * 100, 1) if attempts else 0.0

    return schemas.ChapterOut(
        id=chapter.id,
        subject_id=chapter.subject_id,
        name=chapter.name,
        position=chapter.position,
        question_count=question_count,
        solved_count=solved_count,
        accuracy=accuracy,
    )


@router.get("", response_model=list[schemas.ChapterOut])
def list_chapters(
    subject_id: str,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Chapters are a fixed, pre-seeded set -- there is no create endpoint."""
    subject = db.get(models.Subject, subject_id)
    if not subject:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found")

    chapters = db.execute(
        select(models.Chapter).where(models.Chapter.subject_id == subject_id).order_by(models.Chapter.position)
    ).scalars()
    return [_to_out(db, c, user.id) for c in chapters]

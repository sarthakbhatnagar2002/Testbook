from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_teacher
from ..difficulty import difficulty_tier

router = APIRouter(prefix="/questions", tags=["questions"])


def _to_out(q: models.Question) -> schemas.QuestionOut:
    tier = difficulty_tier(q.attempts_count, q.correct_count, q.teacher_rating)
    return schemas.QuestionOut(
        id=q.id,
        text=q.text,
        image_url=q.image_url,
        explanation=q.explanation,
        teacher_rating=q.teacher_rating,
        attempts_count=q.attempts_count,
        correct_count=q.correct_count,
        tier=tier["tier"],
        tier_source=tier["source"],
        options=[schemas.OptionOutWithAnswer.model_validate(o) for o in q.options],
        created_at=q.created_at,
    )


@router.get("", response_model=list[schemas.QuestionOut])
def list_questions(teacher: models.User = Depends(require_teacher), db: Session = Depends(get_db)):
    rows = db.execute(
        select(models.Question)
        .where(models.Question.teacher_id == teacher.id)
        .order_by(models.Question.created_at.desc())
    ).scalars()
    return [_to_out(q) for q in rows]


@router.post("", response_model=schemas.QuestionOut, status_code=status.HTTP_201_CREATED)
def create_question(
    body: schemas.QuestionCreateIn,
    teacher: models.User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    question = models.Question(
        teacher_id=teacher.id,
        text=body.text,
        image_url=body.image_url,
        explanation=body.explanation,
        teacher_rating=body.teacher_rating,
    )
    question.options = [
        models.Option(text=o.text, image_url=o.image_url, is_correct=o.is_correct, position=i)
        for i, o in enumerate(body.options)
    ]
    db.add(question)
    db.commit()
    db.refresh(question)
    return _to_out(question)


@router.delete("/{question_id}")
def delete_question(
    question_id: str,
    teacher: models.User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    # Questions used in a test are kept, so old results stay intact.
    used = db.execute(
        select(models.TestQuestion.question_id).where(models.TestQuestion.question_id == question_id)
    ).first()
    if used:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "That question is used in a test and cannot be deleted"
        )
    question = db.get(models.Question, question_id)
    if not question or question.teacher_id != teacher.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    db.query(models.Attempt).filter(models.Attempt.question_id == question_id).delete()
    db.delete(question)
    db.commit()
    return {"ok": True}

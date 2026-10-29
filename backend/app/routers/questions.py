from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_user

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("", response_model=schemas.QuestionListItemOut, status_code=status.HTTP_201_CREATED)
def create_question(
    body: schemas.QuestionCreateIn,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    subject = db.get(models.Subject, body.subject_id)
    if not subject:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found")

    question = models.Question(
        subject_id=body.subject_id,
        created_by=user.id,
        text=body.text,
        image_url=body.image_url,
        explanation=body.explanation,
    )
    question.options = [
        models.Option(text=o.text, image_url=o.image_url, is_correct=o.is_correct, position=i)
        for i, o in enumerate(body.options)
    ]
    db.add(question)
    db.commit()
    db.refresh(question)
    return schemas.QuestionListItemOut(
        id=question.id, text=question.text, image_url=question.image_url, status="not_attempted"
    )


@router.delete("/{question_id}")
def delete_question(
    question_id: str,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    question = db.get(models.Question, question_id)
    if not question or question.created_by != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")

    # Keep questions anyone (including other users) has already attempted,
    # so their practice history stays intact.
    attempted = db.execute(
        select(models.Attempt.id).where(models.Attempt.question_id == question_id)
    ).first()
    if attempted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This question has already been attempted and can't be deleted")

    db.delete(question)
    db.commit()
    return {"ok": True}

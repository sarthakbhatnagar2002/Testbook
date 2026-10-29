from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_user

router = APIRouter(tags=["practice"])


def _status_for(outcomes: dict[str, bool], question_id: str) -> schemas.QuestionStatus:
    if question_id not in outcomes:
        return "not_attempted"
    return "correct" if outcomes[question_id] else "incorrect"


def _user_outcomes(db: Session, user_id: str, question_ids: list[str]) -> dict[str, bool]:
    """Latest-attempt outcome per question id (None entries filtered: unattempted)."""
    if not question_ids:
        return {}
    rows = db.execute(
        select(models.Attempt.question_id, models.Attempt.is_correct, models.Attempt.created_at)
        .where(models.Attempt.user_id == user_id, models.Attempt.question_id.in_(question_ids))
        .order_by(models.Attempt.created_at)
    ).all()
    outcomes: dict[str, bool] = {}
    for qid, correct, _created in rows:
        outcomes[qid] = correct  # last write wins: rows are ordered oldest -> newest
    return outcomes


@router.get("/subjects/{subject_id}/questions", response_model=list[schemas.QuestionListItemOut])
def list_subject_questions(
    subject_id: str,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    subject = db.get(models.Subject, subject_id)
    if not subject:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found")

    questions = db.execute(
        select(models.Question)
        .where(models.Question.subject_id == subject_id)
        .order_by(models.Question.created_at)
    ).scalars().all()
    outcomes = _user_outcomes(db, user.id, [q.id for q in questions])

    return [
        schemas.QuestionListItemOut(
            id=q.id, text=q.text, image_url=q.image_url, status=_status_for(outcomes, q.id)
        )
        for q in questions
    ]


def _ordered_question_ids(db: Session, subject_id: str) -> list[str]:
    return list(
        db.execute(
            select(models.Question.id)
            .where(models.Question.subject_id == subject_id)
            .order_by(models.Question.created_at)
        ).scalars()
    )


@router.get("/questions/{question_id}/practice", response_model=schemas.QuestionPracticeOut)
def get_question_for_practice(
    question_id: str,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    question = db.get(models.Question, question_id)
    if not question:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    subject = db.get(models.Subject, question.subject_id)

    ordered_ids = _ordered_question_ids(db, question.subject_id)
    idx = ordered_ids.index(question.id)
    prev_id = ordered_ids[idx - 1] if idx > 0 else None
    next_id = ordered_ids[idx + 1] if idx < len(ordered_ids) - 1 else None

    outcomes = _user_outcomes(db, user.id, [question.id])

    return schemas.QuestionPracticeOut(
        id=question.id,
        subject_id=question.subject_id,
        subject_name=subject.name,
        text=question.text,
        image_url=question.image_url,
        options=[schemas.OptionOut.model_validate(o) for o in question.options],
        status=_status_for(outcomes, question.id),
        next_question_id=next_id,
        prev_question_id=prev_id,
    )


@router.post("/questions/{question_id}/answer", response_model=schemas.AnswerResultOut)
def answer_question(
    question_id: str,
    body: schemas.AnswerIn,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    question = db.get(models.Question, question_id)
    if not question:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")

    options = question.options
    correct_option = next((o for o in options if o.is_correct), None)
    if correct_option is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Question has no correct option")
    if not any(o.id == body.selected_option_id for o in options):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That option does not belong to this question")

    is_correct = body.selected_option_id == correct_option.id

    db.add(
        models.Attempt(
            user_id=user.id,
            question_id=question.id,
            selected_option_id=body.selected_option_id,
            is_correct=is_correct,
        )
    )
    db.commit()

    return schemas.AnswerResultOut(
        is_correct=is_correct,
        correct_option_id=correct_option.id,
        selected_option_id=body.selected_option_id,
        explanation=question.explanation,
    )

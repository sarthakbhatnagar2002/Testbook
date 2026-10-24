from statistics import mean

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_student

router = APIRouter(tags=["profile"])

RECENT_SCORES_LIMIT = 10


@router.get("/profile", response_model=schemas.ProfileOut)
def get_profile(student: models.User = Depends(require_student), db: Session = Depends(get_db)):
    submitted = db.execute(
        select(models.TestAttempt)
        .where(models.TestAttempt.user_id == student.id, models.TestAttempt.status == "submitted")
        .order_by(models.TestAttempt.submitted_at.desc())
    ).scalars().all()

    answered = db.execute(
        select(models.Attempt).where(
            models.Attempt.user_id == student.id, models.Attempt.selected_option_id.is_not(None)
        )
    ).scalars().all()
    total_answered = len(answered)
    total_correct = sum(1 for a in answered if a.is_correct)

    scores = [a.score for a in submitted]
    recent_scores = [
        schemas.RecentScoreOut(
            test_title=(db.get(models.Test, a.test_id).title if db.get(models.Test, a.test_id) else "(deleted test)"),
            score=a.score,
            submitted_at=a.submitted_at,
        )
        for a in submitted[:RECENT_SCORES_LIMIT]
    ]

    return schemas.ProfileOut(
        name=student.name,
        email=student.email,
        role=student.role,
        tests_taken=len(submitted),
        average_score=round(mean(scores), 2) if scores else 0.0,
        overall_accuracy=round(total_correct / total_answered * 100, 1) if total_answered else 0.0,
        recent_scores=recent_scores,
    )

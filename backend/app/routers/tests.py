import secrets
import string
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_teacher
from ..time_utils import to_naive_utc

router = APIRouter(prefix="/tests", tags=["tests"])

ROOM_KEY_ALPHABET = string.ascii_uppercase + string.digits
ROOM_KEY_LENGTH = 6


def _generate_room_key(db: Session) -> str:
    while True:
        key = "".join(secrets.choice(ROOM_KEY_ALPHABET) for _ in range(ROOM_KEY_LENGTH))
        exists = db.execute(select(models.Test.id).where(models.Test.room_key == key)).first()
        if not exists:
            return key


def _question_count(db: Session, section_id: str) -> int:
    return db.execute(
        select(func.count()).select_from(models.TestQuestion).where(models.TestQuestion.section_id == section_id)
    ).scalar_one()


def _to_out(db: Session, t: models.Test) -> schemas.TestOut:
    sections = sorted(t.sections, key=lambda s: s.position)
    section_outs = [
        schemas.TestSectionOut(
            id=s.id,
            title=s.title,
            position=s.position,
            duration_mins=s.duration_mins,
            question_count=_question_count(db, s.id),
        )
        for s in sections
    ]
    return schemas.TestOut(
        id=t.id,
        title=t.title,
        room_key=t.room_key,
        total_duration_mins=sum(s.duration_mins for s in sections),
        marks_correct=t.marks_correct,
        marks_wrong=t.marks_wrong,
        marks_skipped=t.marks_skipped,
        published=t.published,
        archived=t.archived,
        start_time=t.start_time,
        end_time=t.end_time,
        sections=section_outs,
        created_at=t.created_at,
    )


@router.get("", response_model=list[schemas.TestOut])
def list_tests(teacher: models.User = Depends(require_teacher), db: Session = Depends(get_db)):
    rows = db.execute(
        select(models.Test)
        .where(models.Test.teacher_id == teacher.id)
        .order_by(models.Test.created_at.desc())
    ).scalars()
    return [_to_out(db, t) for t in rows]


@router.post("/with-questions", response_model=schemas.TestOut, status_code=status.HTTP_201_CREATED)
def create_test_with_questions(
    body: schemas.TestWithQuestionsIn,
    teacher: models.User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Google-Forms-style builder: create the test, its sections and all questions in one go."""
    start_time = to_naive_utc(body.start_time)
    end_time = to_naive_utc(body.end_time)
    if end_time and start_time and end_time <= start_time:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "End time must be after the start time")

    test = models.Test(
        teacher_id=teacher.id,
        title=body.title,
        room_key=_generate_room_key(db),
        marks_correct=body.marks_correct,
        marks_wrong=body.marks_wrong,
        marks_skipped=body.marks_skipped,
        published=body.published,
        start_time=start_time,
        end_time=end_time,
    )
    db.add(test)
    db.flush()

    for section_position, section_in in enumerate(body.sections):
        section = models.TestSection(
            test_id=test.id,
            title=section_in.title,
            position=section_position,
            duration_mins=section_in.duration_mins,
        )
        db.add(section)
        db.flush()

        for q_position, q in enumerate(section_in.questions):
            question = models.Question(
                teacher_id=teacher.id,
                text=q.text,
                image_url=q.image_url,
                explanation=q.explanation,
                teacher_rating=q.teacher_rating,
            )
            question.options = [
                models.Option(text=o.text, image_url=o.image_url, is_correct=o.is_correct, position=i)
                for i, o in enumerate(q.options)
            ]
            db.add(question)
            db.flush()
            db.add(models.TestQuestion(section_id=section.id, question_id=question.id, position=q_position))

    db.commit()
    db.refresh(test)
    return _to_out(db, test)


@router.patch("/{test_id}", response_model=schemas.TestOut)
def update_test(
    test_id: str,
    body: schemas.TestUpdateIn,
    teacher: models.User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    test = db.get(models.Test, test_id)
    if not test or test.teacher_id != teacher.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test not found")
    if body.published is not None:
        test.published = body.published
    if body.archived is not None:
        test.archived = body.archived
    if body.start_time is not None:
        test.start_time = to_naive_utc(body.start_time)
    if body.end_time is not None:
        test.end_time = to_naive_utc(body.end_time)
    db.commit()
    db.refresh(test)
    return _to_out(db, test)


@router.get("/{test_id}/results", response_model=schemas.TeacherTestResultsOut)
def test_results(
    test_id: str,
    teacher: models.User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    test = db.get(models.Test, test_id)
    if not test or test.teacher_id != teacher.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test not found")

    attempts = db.execute(
        select(models.TestAttempt)
        .where(models.TestAttempt.test_id == test_id, models.TestAttempt.status == "submitted")
        .order_by(models.TestAttempt.submitted_at.desc())
    ).scalars().all()

    rows = []
    for a in attempts:
        student = db.get(models.User, a.user_id)
        rows.append(
            schemas.TeacherAttemptRow(
                user_name=student.name if student else "(deleted)",
                user_email=student.email if student else "",
                score=a.score,
                correct_count=a.correct_count,
                wrong_count=a.wrong_count,
                skipped_count=a.skipped_count,
                submitted_at=a.submitted_at,
            )
        )

    scores = [a.score for a in attempts]
    return schemas.TeacherTestResultsOut(
        test_id=test.id,
        title=test.title,
        attempt_count=len(attempts),
        average_score=round(mean(scores), 2) if scores else 0.0,
        highest_score=max(scores) if scores else 0,
        attempts=rows,
    )

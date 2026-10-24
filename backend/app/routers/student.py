import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..attempts_logic import (
    SUBMIT_GRACE_SECS,
    finalize_attempt,
    finalize_if_expired,
    ordered_question_ids,
    parse_draft,
    total_duration_mins,
)
from ..database import get_db
from ..deps import require_student
from ..time_utils import utcnow

router = APIRouter(tags=["student"])


def _availability(test: models.Test, now: datetime) -> str:
    if test.start_time and now < test.start_time:
        return "upcoming"
    if test.end_time and now > test.end_time:
        return "closed"
    return "open"


def _own_attempt(db: Session, user_id: str, attempt_id: str) -> tuple[models.TestAttempt, models.Test] | None:
    attempt = db.get(models.TestAttempt, attempt_id)
    if not attempt or attempt.user_id != user_id:
        return None
    test = db.get(models.Test, attempt.test_id)
    return (attempt, test) if test else None


def _sections_for(db: Session, test_id: str) -> list[models.TestSection]:
    rows = db.execute(
        select(models.TestSection).where(models.TestSection.test_id == test_id).order_by(models.TestSection.position)
    ).scalars()
    return list(rows)


def _questions_by_id(db: Session, question_ids: list[str]) -> dict[str, models.Question]:
    if not question_ids:
        return {}
    rows = db.execute(select(models.Question).where(models.Question.id.in_(question_ids))).scalars()
    return {q.id: q for q in rows}


def _build_state(db: Session, attempt: models.TestAttempt, test: models.Test) -> schemas.AttemptStateOut:
    sections = _sections_for(db, test.id)
    all_question_ids = [tq.question_id for s in sections for tq in s.test_questions]
    questions_by_id = _questions_by_id(db, all_question_ids)
    draft_raw = parse_draft(attempt.draft_state)

    section_outs = [
        schemas.AttemptSectionOut(
            id=s.id,
            title=s.title,
            position=s.position,
            duration_mins=s.duration_mins,
            questions=[
                schemas.QuestionPublicOut(
                    id=questions_by_id[tq.question_id].id,
                    text=questions_by_id[tq.question_id].text,
                    image_url=questions_by_id[tq.question_id].image_url,
                    options=[schemas.OptionOut.model_validate(o) for o in questions_by_id[tq.question_id].options],
                )
                for tq in s.test_questions
            ],
        )
        for s in sections
    ]

    return schemas.AttemptStateOut(
        attempt_id=attempt.id,
        test_id=test.id,
        test_title=test.title,
        marks_correct=test.marks_correct,
        marks_wrong=test.marks_wrong,
        marks_skipped=test.marks_skipped,
        started_at=attempt.started_at,
        total_seconds_remaining=(
            0
            if attempt.status == "submitted"
            else max(
                0,
                int(
                    attempt.started_at.timestamp()
                    + total_duration_mins(db, test.id) * 60
                    - utcnow().timestamp()
                ),
            )
        ),
        status=attempt.status,
        sections=section_outs,
        draft=schemas.DraftStateIn(**draft_raw) if draft_raw else schemas.DraftStateIn(),
    )


def _build_result(db: Session, attempt: models.TestAttempt, test: models.Test) -> schemas.AttemptResultOut:
    question_ids = ordered_question_ids(db, test.id)
    questions_by_id = _questions_by_id(db, question_ids)
    answers_by_question = {
        a.question_id: a
        for a in db.execute(
            select(models.Attempt).where(models.Attempt.test_attempt_id == attempt.id)
        ).scalars()
    }
    answers = []
    for qid in question_ids:
        q = questions_by_id[qid]
        a = answers_by_question.get(qid)
        answers.append(
            schemas.ReviewAnswerOut(
                question=schemas.ReviewQuestionOut(
                    id=q.id,
                    text=q.text,
                    image_url=q.image_url,
                    explanation=q.explanation,
                    options=[schemas.OptionOutWithAnswer.model_validate(o) for o in q.options],
                ),
                selected_option_id=a.selected_option_id if a else None,
                is_correct=a.is_correct if a else False,
            )
        )
    return schemas.AttemptResultOut(
        attempt_id=attempt.id,
        test_title=test.title,
        score=attempt.score,
        correct_count=attempt.correct_count,
        wrong_count=attempt.wrong_count,
        skipped_count=attempt.skipped_count,
        marks_correct=test.marks_correct,
        marks_wrong=test.marks_wrong,
        marks_skipped=test.marks_skipped,
        submitted_at=attempt.submitted_at,
        answers=answers,
    )


def _has_access(db: Session, student_id: str, test_id: str) -> bool:
    return (
        db.execute(
            select(models.TestAccess).where(
                models.TestAccess.user_id == student_id, models.TestAccess.test_id == test_id
            )
        ).scalar_one_or_none()
        is not None
    )


def _to_student_test_out(db: Session, student_id: str, test: models.Test, now: datetime) -> schemas.StudentTestOut:
    availability = _availability(test, now)
    attempt = db.execute(
        select(models.TestAttempt)
        .where(models.TestAttempt.user_id == student_id, models.TestAttempt.test_id == test.id)
        .order_by(models.TestAttempt.started_at.desc())
    ).scalars().first()
    in_progress = attempt if attempt and attempt.status == "in_progress" else None
    return schemas.StudentTestOut(
        id=test.id,
        title=test.title,
        total_duration_mins=total_duration_mins(db, test.id),
        marks_correct=test.marks_correct,
        marks_wrong=test.marks_wrong,
        marks_skipped=test.marks_skipped,
        start_time=test.start_time,
        end_time=test.end_time,
        availability="open" if in_progress else availability,
        attempt_status="in_progress" if in_progress else "none",
        attempt_id=in_progress.id if in_progress else None,
    )


@router.get("/student/tests", response_model=list[schemas.StudentTestOut])
def list_student_tests(student: models.User = Depends(require_student), db: Session = Depends(get_db)):
    """Only tests this student has joined with a room key (see /student/tests/join)."""
    now = utcnow()
    joined_test_ids = db.execute(
        select(models.TestAccess.test_id).where(models.TestAccess.user_id == student.id)
    ).scalars().all()
    if not joined_test_ids:
        return []
    tests = db.execute(
        select(models.Test).where(
            models.Test.id.in_(joined_test_ids),
            models.Test.published.is_(True),
            models.Test.archived.is_(False),
        )
    ).scalars().all()
    out = []
    for test in tests:
        out_row = _to_student_test_out(db, student.id, test, now)
        if _availability(test, now) == "closed" and out_row.attempt_status == "none":
            continue
        out.append(out_row)
    return out


@router.post("/student/tests/join", response_model=schemas.StudentTestOut)
def join_test(
    body: schemas.JoinTestIn,
    student: models.User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """Look a test up by its room key and unlock it for this student."""
    key = body.room_key.strip().upper()
    test = db.execute(select(models.Test).where(models.Test.room_key == key)).scalar_one_or_none()
    if not test or not test.published or test.archived:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No test found for that key")
    if not _has_access(db, student.id, test.id):
        db.add(models.TestAccess(user_id=student.id, test_id=test.id))
        db.commit()
    return _to_student_test_out(db, student.id, test, utcnow())


@router.get("/student/tests/history", response_model=list[schemas.PreviousAttemptOut])
def list_history(student: models.User = Depends(require_student), db: Session = Depends(get_db)):
    attempts = db.execute(
        select(models.TestAttempt)
        .where(models.TestAttempt.user_id == student.id, models.TestAttempt.status == "submitted")
        .order_by(models.TestAttempt.submitted_at.desc())
    ).scalars()
    out = []
    for a in attempts:
        test = db.get(models.Test, a.test_id)
        out.append(
            schemas.PreviousAttemptOut(
                attempt_id=a.id,
                test_id=a.test_id,
                test_title=test.title if test else "(deleted test)",
                score=a.score,
                correct_count=a.correct_count,
                wrong_count=a.wrong_count,
                skipped_count=a.skipped_count,
                submitted_at=a.submitted_at,
            )
        )
    return out


@router.post("/student/attempts/start", response_model=schemas.AttemptStateOut)
def start_attempt(
    body: schemas.StartTestIn,
    student: models.User = Depends(require_student),
    db: Session = Depends(get_db),
):
    test = db.get(models.Test, body.test_id)
    if not test or not test.published:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test not found")

    # Resume an unfinished attempt if one exists (grading it first if it ran out of time).
    open_attempts = db.execute(
        select(models.TestAttempt).where(
            models.TestAttempt.user_id == student.id,
            models.TestAttempt.test_id == test.id,
            models.TestAttempt.status == "in_progress",
        )
    ).scalars().all()
    for a in open_attempts:
        finalize_if_expired(db, a.id)

    still_open = db.execute(
        select(models.TestAttempt).where(
            models.TestAttempt.user_id == student.id,
            models.TestAttempt.test_id == test.id,
            models.TestAttempt.status == "in_progress",
        )
    ).scalars().first()
    if still_open:
        return _build_state(db, still_open, test)

    if test.archived:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This test has been archived")
    if not _has_access(db, student.id, test.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Join this test with its room key first")

    availability = _availability(test, utcnow())
    if availability != "open":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This test is not open right now")

    attempt = models.TestAttempt(
        user_id=student.id,
        test_id=test.id,
        # Frozen copy of the marking scheme: later edits never change this score.
        scheme_snapshot=json.dumps(
            {"correct": test.marks_correct, "wrong": test.marks_wrong, "skipped": test.marks_skipped}
        ),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return _build_state(db, attempt, test)


@router.get("/student/attempts/{attempt_id}", response_model=schemas.AttemptStateOut)
def get_attempt(
    attempt_id: str,
    student: models.User = Depends(require_student),
    db: Session = Depends(get_db),
):
    owned = _own_attempt(db, student.id, attempt_id)
    if not owned:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    finalize_if_expired(db, attempt_id)
    db.expire_all()
    attempt, test = _own_attempt(db, student.id, attempt_id)
    return _build_state(db, attempt, test)


@router.patch("/student/attempts/{attempt_id}/autosave")
def autosave(
    attempt_id: str,
    body: schemas.SubmitTestIn,
    student: models.User = Depends(require_student),
    db: Session = Depends(get_db),
):
    owned = _own_attempt(db, student.id, attempt_id)
    if not owned:
        return {"ok": False}
    attempt, test = owned
    if attempt.status != "in_progress":
        return {"ok": False}
    end = attempt.started_at.timestamp() + total_duration_mins(db, test.id) * 60
    if utcnow().timestamp() > end + SUBMIT_GRACE_SECS:
        return {"ok": False}
    attempt.draft_state = body.model_dump_json()
    db.commit()
    return {"ok": True}


@router.post("/student/attempts/{attempt_id}/submit", response_model=schemas.AttemptResultOut)
def submit_attempt(
    attempt_id: str,
    body: schemas.SubmitTestIn,
    student: models.User = Depends(require_student),
    db: Session = Depends(get_db),
):
    owned = _own_attempt(db, student.id, attempt_id)
    if not owned:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    attempt, test = owned
    if attempt.status == "in_progress":
        end = attempt.started_at.timestamp() + total_duration_mins(db, test.id) * 60
        late = utcnow().timestamp() > end + SUBMIT_GRACE_SECS
        if late:
            # Too late: ignore what the browser sent and grade the last autosave instead.
            answers = {
                qid: s.selected_option_id
                for qid, s in parse_draft(attempt.draft_state).get("questions", {}).items()
                if isinstance(s, dict) and s.get("selected_option_id")
            }
        else:
            attempt.draft_state = body.model_dump_json()
            db.commit()
            answers = {qid: s.selected_option_id for qid, s in body.questions.items() if s.selected_option_id}
        finalize_attempt(db, attempt_id, answers)
    db.expire_all()
    attempt, test = _own_attempt(db, student.id, attempt_id)
    return _build_result(db, attempt, test)


@router.get("/student/attempts/{attempt_id}/result", response_model=schemas.AttemptResultOut)
def get_result(
    attempt_id: str,
    student: models.User = Depends(require_student),
    db: Session = Depends(get_db),
):
    owned = _own_attempt(db, student.id, attempt_id)
    if not owned:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    attempt, test = owned
    if attempt.status != "submitted":
        finalize_if_expired(db, attempt_id)
        db.expire_all()
        attempt, test = _own_attempt(db, student.id, attempt_id)
    if attempt.status != "submitted":
        raise HTTPException(status.HTTP_409_CONFLICT, "Test not submitted yet")
    return _build_result(db, attempt, test)


@router.post("/student/reports", status_code=status.HTTP_201_CREATED)
def report_question(
    body: schemas.ReportIn,
    student: models.User = Depends(require_student),
    db: Session = Depends(get_db),
):
    question = db.get(models.Question, body.question_id)
    if not question:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    db.add(
        models.QuestionReport(
            question_id=body.question_id,
            user_id=student.id,
            test_attempt_id=body.test_attempt_id,
            message=body.message,
        )
    )
    db.commit()
    return {"ok": True}

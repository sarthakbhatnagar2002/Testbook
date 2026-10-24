import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .time_utils import utcnow


def gen_id() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    teacher_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_rating: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    attempts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    options: Mapped[list["Option"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="Option.position"
    )


class Option(Base):
    __tablename__ = "options"
    __table_args__ = (Index("options_question_idx", "question_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    question_id: Mapped[str] = mapped_column(
        String, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    question: Mapped[Question] = relationship(back_populates="options")


class Test(Base):
    """A test's total duration is the sum of its sections' durations."""

    __tablename__ = "tests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    teacher_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    # Auto-generated when the test is created. Students must know this to join.
    room_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    marks_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    marks_wrong: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    marks_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Availability window, stored in UTC. Null start = open immediately, null end = no deadline.
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    sections: Mapped[list["TestSection"]] = relationship(
        back_populates="test", cascade="all, delete-orphan", order_by="TestSection.position"
    )


class TestSection(Base):
    """
    A timed block of questions within a test. Each section gets its own
    countdown, started the moment a student first opens it; when that runs
    out the section locks and the next one starts (see attempts_logic.py).
    """

    __tablename__ = "test_sections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    test_id: Mapped[str] = mapped_column(String, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_mins: Mapped[int] = mapped_column(Integer, nullable=False)

    test: Mapped[Test] = relationship(back_populates="sections")
    test_questions: Mapped[list["TestQuestion"]] = relationship(
        back_populates="section", cascade="all, delete-orphan", order_by="TestQuestion.position"
    )


class TestQuestion(Base):
    __tablename__ = "test_questions"

    section_id: Mapped[str] = mapped_column(
        String, ForeignKey("test_sections.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[str] = mapped_column(String, ForeignKey("questions.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    section: Mapped[TestSection] = relationship(back_populates="test_questions")


class TestAccess(Base):
    """A student has joined a test with its room key and may now start it."""

    __tablename__ = "test_access"

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), primary_key=True)
    test_id: Mapped[str] = mapped_column(String, ForeignKey("tests.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TestAttempt(Base):
    __tablename__ = "test_attempts"
    __table_args__ = (
        Index("test_attempts_user_idx", "user_id"),
        Index("test_attempts_test_idx", "test_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    test_id: Mapped[str] = mapped_column(String, ForeignKey("tests.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="in_progress")
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # JSON copy of the marking scheme used, so later edits never change old scores.
    scheme_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    # Autosaved in-progress state: JSON { currentQuestionId, questions: { [questionId]: {
    #   selectedOptionId, visited, markedForReview, timeSpentSeconds } } }
    draft_state: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class Attempt(Base):
    """One row per answered question: a graded test question (practice mode removed)."""

    __tablename__ = "attempts"
    __table_args__ = (
        Index("attempts_user_question_idx", "user_id", "question_id"),
        Index("attempts_question_idx", "question_id"),
        Index("attempts_test_attempt_idx", "test_attempt_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    question_id: Mapped[str] = mapped_column(String, ForeignKey("questions.id"), nullable=False)
    test_attempt_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=True
    )
    selected_option_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_first_attempt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class QuestionReport(Base):
    """A student flagging a problem with a question, from the exam screen's Report modal."""

    __tablename__ = "question_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    question_id: Mapped[str] = mapped_column(String, ForeignKey("questions.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    test_attempt_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("test_attempts.id"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

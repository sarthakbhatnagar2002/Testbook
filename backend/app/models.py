import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Subject(Base):
    """A question bank, e.g. Physics, Chemistry, Maths. Anyone can create one."""

    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    questions: Mapped[list["Question"]] = relationship(back_populates="subject")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (Index("questions_subject_idx", "subject_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    subject_id: Mapped[str] = mapped_column(String, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    subject: Mapped[Subject] = relationship(back_populates="questions")
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


class Attempt(Base):
    """One row per practice answer. Retries are allowed; every attempt is kept."""

    __tablename__ = "attempts"
    __table_args__ = (
        Index("attempts_user_question_idx", "user_id", "question_id"),
        Index("attempts_question_idx", "question_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    question_id: Mapped[str] = mapped_column(String, ForeignKey("questions.id"), nullable=False)
    selected_option_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

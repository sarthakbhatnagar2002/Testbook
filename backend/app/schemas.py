from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PlainSerializer, field_validator, model_validator

from .time_utils import to_utc_iso

# Datetimes are stored as naive UTC (see time_utils). Serialize them with an
# explicit UTC offset so the frontend can convert to the user's local time
# unambiguously, e.g. with `new Date(isoString)`.
UtcDateTime = Annotated[datetime, PlainSerializer(to_utc_iso, return_type=str, when_used="json")]


def _valid_image_url(v: str | None) -> str | None:
    """Accepts an absolute http(s) URL or a path returned by POST /uploads."""
    if not v:
        return None
    if not (v.startswith("http://") or v.startswith("https://") or v.startswith("/uploads/")):
        raise ValueError("Invalid image reference")
    return v


# ---------- auth ----------


class RegisterIn(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=8)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name is required")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_looks_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v:
            raise ValueError("Enter a valid email")
        return v


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str

    model_config = {"from_attributes": True}


# ---------- subjects ----------


class SubjectOut(BaseModel):
    id: str
    name: str
    question_count: int
    solved_count: int
    accuracy: float


# ---------- questions ----------


class OptionIn(BaseModel):
    text: str = ""
    image_url: str | None = None
    is_correct: bool = False

    _v = field_validator("image_url")(_valid_image_url)

    @model_validator(mode="after")
    def text_or_image_required(self) -> "OptionIn":
        if not self.text.strip() and not self.image_url:
            raise ValueError("Each option needs text or an image")
        return self


class OptionOut(BaseModel):
    id: str
    text: str
    image_url: str | None
    position: int

    model_config = {"from_attributes": True}


class OptionOutWithAnswer(OptionOut):
    is_correct: bool


class QuestionCreateIn(BaseModel):
    subject_id: str
    text: str
    image_url: str | None = None
    explanation: str | None = None
    options: list[OptionIn]

    _v = field_validator("image_url")(_valid_image_url)

    @field_validator("text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question text is required")
        return v

    @field_validator("options")
    @classmethod
    def options_valid(cls, v: list[OptionIn]) -> list[OptionIn]:
        if len(v) < 2:
            raise ValueError("Add at least two options")
        if len(v) > 6:
            raise ValueError("At most 6 options")
        if sum(1 for o in v if o.is_correct) != 1:
            raise ValueError("Pick exactly one correct option")
        return v


QuestionStatus = Literal["not_attempted", "correct", "incorrect"]


class QuestionListItemOut(BaseModel):
    """A question in a subject's list. No answer revealed."""

    id: str
    text: str
    image_url: str | None
    status: QuestionStatus


class QuestionPracticeOut(BaseModel):
    """A single question to answer. No answer revealed."""

    id: str
    subject_id: str
    subject_name: str
    text: str
    image_url: str | None
    options: list[OptionOut]
    status: QuestionStatus
    next_question_id: str | None
    prev_question_id: str | None


class AnswerIn(BaseModel):
    selected_option_id: str


class AnswerResultOut(BaseModel):
    is_correct: bool
    correct_option_id: str
    selected_option_id: str
    explanation: str | None


# ---------- profile ----------


class SubjectProgressOut(BaseModel):
    subject_id: str
    subject_name: str
    total_questions: int
    solved_count: int
    accuracy: float
    last_practiced_at: UtcDateTime | None


class RecentAttemptOut(BaseModel):
    question_id: str
    question_text: str
    subject_name: str
    is_correct: bool
    created_at: UtcDateTime


class ProfileOut(BaseModel):
    name: str
    email: str
    total_questions_solved: int
    total_questions_attempted: int
    overall_accuracy: float
    currently_solving: SubjectProgressOut | None
    subjects: list[SubjectProgressOut]
    recent_attempts: list[RecentAttemptOut]

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PlainSerializer, field_validator, model_validator

from .time_utils import to_utc_iso

Role = Literal["teacher", "student"]
Rating = Literal["easy", "medium", "hard"]

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
    role: Role = "student"
    invite_code: str | None = None

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
    role: Role

    model_config = {"from_attributes": True}


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
    text: str
    image_url: str | None = None
    explanation: str | None = None
    teacher_rating: Rating = "medium"
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


class QuestionOut(BaseModel):
    id: str
    text: str
    image_url: str | None
    explanation: str | None
    teacher_rating: Rating
    attempts_count: int
    correct_count: int
    tier: Rating
    tier_source: Literal["data", "teacher"]
    options: list[OptionOutWithAnswer]
    created_at: UtcDateTime


class QuestionPublicOut(BaseModel):
    """Sent while a test is running: never carries which option is correct."""

    id: str
    text: str
    image_url: str | None
    options: list[OptionOut]


# ---------- tests & sections ----------


class TestSectionIn(BaseModel):
    title: str
    duration_mins: int = Field(ge=1, le=600)
    questions: list[QuestionCreateIn]

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Give the section a title")
        return v

    @field_validator("questions")
    @classmethod
    def at_least_one_question(cls, v: list[QuestionCreateIn]) -> list[QuestionCreateIn]:
        if not v:
            raise ValueError("Add at least one question to the section")
        return v


class TestWithQuestionsIn(BaseModel):
    """Google-Forms-style test builder: the test and all of its sections in one go."""

    title: str
    marks_correct: int = Field(ge=0)
    marks_wrong: int = Field(le=0)
    marks_skipped: int = Field(le=0, default=0)
    published: bool = False
    start_time: datetime | None = None
    end_time: datetime | None = None
    sections: list[TestSectionIn]

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Give the test a title")
        return v

    @field_validator("sections")
    @classmethod
    def at_least_one_section(cls, v: list[TestSectionIn]) -> list[TestSectionIn]:
        if not v:
            raise ValueError("Add at least one section")
        return v


class TestUpdateIn(BaseModel):
    published: bool | None = None
    archived: bool | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class TestSectionOut(BaseModel):
    id: str
    title: str
    position: int
    duration_mins: int
    question_count: int


class TestOut(BaseModel):
    id: str
    title: str
    room_key: str
    total_duration_mins: int
    marks_correct: int
    marks_wrong: int
    marks_skipped: int
    published: bool
    archived: bool
    start_time: UtcDateTime | None
    end_time: UtcDateTime | None
    sections: list[TestSectionOut]
    created_at: UtcDateTime


class JoinTestIn(BaseModel):
    room_key: str = Field(min_length=1)


class StudentTestOut(BaseModel):
    id: str
    title: str
    total_duration_mins: int
    marks_correct: int
    marks_wrong: int
    marks_skipped: int
    start_time: UtcDateTime | None
    end_time: UtcDateTime | None
    availability: Literal["upcoming", "open", "closed"]
    attempt_status: Literal["none", "in_progress", "submitted"]
    attempt_id: str | None


class PreviousAttemptOut(BaseModel):
    attempt_id: str
    test_id: str
    test_title: str
    score: int
    correct_count: int
    wrong_count: int
    skipped_count: int
    submitted_at: UtcDateTime | None


# ---------- attempts ----------


class QuestionStateIn(BaseModel):
    selected_option_id: str | None = None
    visited: bool = False
    marked_for_review: bool = False
    time_spent_seconds: int = 0


class SectionStateIn(BaseModel):
    """Recorded the moment a student opens a section, so a resume shows the right countdown."""

    started_at: datetime | None = None
    locked: bool = False


class DraftStateIn(BaseModel):
    current_question_id: str | None = None
    questions: dict[str, QuestionStateIn] = Field(default_factory=dict)
    sections: dict[str, SectionStateIn] = Field(default_factory=dict)


class StartTestIn(BaseModel):
    test_id: str


class AttemptSectionOut(BaseModel):
    id: str
    title: str
    position: int
    duration_mins: int
    questions: list[QuestionPublicOut]


class AttemptStateOut(BaseModel):
    attempt_id: str
    test_id: str
    test_title: str
    marks_correct: int
    marks_wrong: int
    marks_skipped: int
    started_at: UtcDateTime
    total_seconds_remaining: int
    status: Literal["in_progress", "submitted"]
    sections: list[AttemptSectionOut]
    draft: DraftStateIn


class SubmitTestIn(BaseModel):
    current_question_id: str | None = None
    questions: dict[str, QuestionStateIn] = Field(default_factory=dict)
    sections: dict[str, SectionStateIn] = Field(default_factory=dict)


class ReviewQuestionOut(BaseModel):
    id: str
    text: str
    image_url: str | None
    explanation: str | None
    options: list[OptionOutWithAnswer]


class ReviewAnswerOut(BaseModel):
    question: ReviewQuestionOut
    selected_option_id: str | None
    is_correct: bool


class AttemptResultOut(BaseModel):
    attempt_id: str
    test_title: str
    score: int
    correct_count: int
    wrong_count: int
    skipped_count: int
    marks_correct: int
    marks_wrong: int
    marks_skipped: int
    submitted_at: UtcDateTime | None
    answers: list[ReviewAnswerOut]


class ReportIn(BaseModel):
    question_id: str
    test_attempt_id: str | None = None
    message: str = Field(min_length=1, max_length=2000)


# ---------- profile / results ----------


class RecentScoreOut(BaseModel):
    test_title: str
    score: int
    submitted_at: UtcDateTime | None


class ProfileOut(BaseModel):
    name: str
    email: str
    role: Role
    tests_taken: int
    average_score: float
    overall_accuracy: float
    recent_scores: list[RecentScoreOut]


class TeacherAttemptRow(BaseModel):
    user_name: str
    user_email: str
    score: int
    correct_count: int
    wrong_count: int
    skipped_count: int
    submitted_at: UtcDateTime | None


class TeacherTestResultsOut(BaseModel):
    test_id: str
    title: str
    attempt_count: int
    average_score: float
    highest_score: int
    attempts: list[TeacherAttemptRow]

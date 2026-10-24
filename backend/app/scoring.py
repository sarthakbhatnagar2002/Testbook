"""Scoring: the single source of truth. Every submit goes through scoreTest()."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypedDict

Outcome = Literal["correct", "wrong", "skipped"]


class MarkingScheme(TypedDict):
    correct: int  # e.g. 4
    wrong: int  # e.g. -1 (use 0 for no negative marking)
    skipped: int  # usually 0


def grade_answer(selected_option_id: str | None, correct_option_id: str) -> Outcome:
    """Decide the outcome of one answer. selected = None means skipped."""
    if not selected_option_id:
        return "skipped"
    return "correct" if selected_option_id == correct_option_id else "wrong"


def marks_for(outcome: Outcome, scheme: MarkingScheme) -> int:
    return scheme[outcome]


@dataclass
class TestResult:
    score: int = 0
    correct_count: int = 0
    wrong_count: int = 0
    skipped_count: int = 0


def score_test(outcomes: list[Outcome], scheme: MarkingScheme) -> TestResult:
    result = TestResult()
    for outcome in outcomes:
        result.score += marks_for(outcome, scheme)
        if outcome == "correct":
            result.correct_count += 1
        elif outcome == "wrong":
            result.wrong_count += 1
        else:
            result.skipped_count += 1
    return result


def seconds_remaining(started_at: datetime, duration_mins: int, now: datetime) -> int:
    """Seconds left for an attempt, computed from the server clock."""
    end = started_at.timestamp() + duration_mins * 60
    return max(0, int(end - now.timestamp()))

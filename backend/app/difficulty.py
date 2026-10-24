"""Difficulty tier, derived from real first-attempt data once there is enough of it."""

from typing import Literal, TypedDict

Tier = Literal["easy", "medium", "hard"]

# Below this many first attempts we trust the teacher's rating over the data.
MIN_ATTEMPTS_FOR_TIER = 10


class TierResult(TypedDict):
    tier: Tier
    source: Literal["data", "teacher"]


def failure_rate(attempts_count: int, correct_count: int) -> float | None:
    """Failure rate among first attempts. None until there is enough data."""
    if attempts_count < MIN_ATTEMPTS_FOR_TIER:
        return None
    return (attempts_count - correct_count) / attempts_count


def difficulty_tier(attempts_count: int, correct_count: int, teacher_rating: Tier) -> TierResult:
    """
    Simple fixed cut-offs for the MVP:
      fail rate < 30% -> easy, 30-60% -> medium, > 60% -> hard.
    """
    rate = failure_rate(attempts_count, correct_count)
    if rate is None:
        return {"tier": teacher_rating, "source": "teacher"}
    if rate < 0.3:
        return {"tier": "easy", "source": "data"}
    if rate <= 0.6:
        return {"tier": "medium", "source": "data"}
    return {"tier": "hard", "source": "data"}

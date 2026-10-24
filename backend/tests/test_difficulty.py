from app.difficulty import difficulty_tier


def test_uses_teacher_rating_until_enough_data():
    assert difficulty_tier(3, 0, "easy") == {"tier": "easy", "source": "teacher"}


def test_derives_tiers_from_failure_rate():
    assert difficulty_tier(20, 18, "hard") == {"tier": "easy", "source": "data"}
    assert difficulty_tier(20, 10, "easy") == {"tier": "medium", "source": "data"}
    assert difficulty_tier(20, 4, "easy") == {"tier": "hard", "source": "data"}

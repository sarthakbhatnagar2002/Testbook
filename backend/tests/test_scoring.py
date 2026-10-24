from datetime import datetime, timezone

from app.scoring import grade_answer, score_test, seconds_remaining

SCHEME = {"correct": 4, "wrong": -1, "skipped": 0}


def test_grade_answer_correct_wrong_skipped():
    assert grade_answer("a", "a") == "correct"
    assert grade_answer("b", "a") == "wrong"
    assert grade_answer(None, "a") == "skipped"
    assert grade_answer("", "a") == "skipped"


def test_score_test_applies_negative_marking():
    r = score_test(["correct", "correct", "wrong", "skipped"], SCHEME)
    assert (r.score, r.correct_count, r.wrong_count, r.skipped_count) == (7, 2, 1, 1)


def test_score_test_supports_zero_negative_marking():
    r = score_test(["wrong", "wrong"], {"correct": 1, "wrong": 0, "skipped": 0})
    assert r.score == 0


def test_score_test_can_go_below_zero():
    assert score_test(["wrong", "wrong"], SCHEME).score == -2


def test_score_test_handles_empty_test():
    assert score_test([], SCHEME).score == 0


def test_seconds_remaining_counts_down_from_server_clock():
    start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 1, 1, 10, 10, 0, tzinfo=timezone.utc)
    assert seconds_remaining(start, 30, now) == 1200


def test_seconds_remaining_never_goes_negative():
    start = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert seconds_remaining(start, 30, now) == 0

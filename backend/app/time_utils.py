"""
SQLite has no timezone-aware storage: datetimes round-trip as naive values.
Convention used everywhere in this app: all datetimes are stored and compared
as naive UTC. API responses serialize them with an explicit UTC offset so the
frontend can convert to the user's local timezone unambiguously.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

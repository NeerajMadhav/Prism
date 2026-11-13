"""Date helpers for billing periods and forecasts."""

from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from typing import Any


def utc_now() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(tz=UTC)


def to_utc_day(value: Any) -> datetime:
    """Normalize any date/datetime to UTC midnight (one row per calendar day)."""
    if isinstance(value, datetime):
        d = value.astimezone(UTC).date() if value.tzinfo else value.date()
        return datetime(d.year, d.month, d.day, tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    raise TypeError(f"Cannot convert {type(value)!r} to UTC day")


def iter_days(start: date, end_exclusive: date) -> list[date]:
    """Inclusive start, exclusive end calendar days."""
    days: list[date] = []
    cur = start
    while cur < end_exclusive:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def current_month_start(ref: date | None = None) -> date:
    """First day of the current (or given) month."""
    d = ref or utc_now().date()
    return date(d.year, d.month, 1)


def next_month_start(ref: date | None = None) -> date:
    """First day of the next month."""
    start = current_month_start(ref)
    if start.month == 12:
        return date(start.year + 1, 1, 1)
    return date(start.year, start.month + 1, 1)


def days_in_month(ref: date | None = None) -> int:
    """Number of days in the month of ref."""
    d = ref or utc_now().date()
    return monthrange(d.year, d.month)[1]


def days_remaining_in_month(ref: date | None = None) -> int:
    """Days left including today."""
    d = ref or utc_now().date()
    return days_in_month(d) - d.day + 1


def days_elapsed_in_month(ref: date | None = None) -> int:
    """Days elapsed including today."""
    d = ref or utc_now().date()
    return d.day

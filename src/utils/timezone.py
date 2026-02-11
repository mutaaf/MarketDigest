"""Timezone helpers for CT/ET/UTC conversions."""

from datetime import datetime, timedelta

import pytz

CT = pytz.timezone("US/Central")
ET = pytz.timezone("US/Eastern")
UTC = pytz.utc


def now_ct() -> datetime:
    return datetime.now(CT)


def now_utc() -> datetime:
    return datetime.now(UTC)


def to_ct(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = UTC.localize(dt)
    return dt.astimezone(CT)


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = CT.localize(dt)
    return dt.astimezone(UTC)


def today_ct() -> datetime:
    return now_ct().replace(hour=0, minute=0, second=0, microsecond=0)


def is_weekday() -> bool:
    return now_ct().weekday() < 5


def is_friday() -> bool:
    return now_ct().weekday() == 4


def format_time_ct(dt: datetime, fmt: str = "%I:%M %p CT") -> str:
    return to_ct(dt).strftime(fmt)


def format_date(dt: datetime, fmt: str = "%b %d, %Y") -> str:
    return dt.strftime(fmt)


def start_of_week_ct() -> datetime:
    """Return Monday 00:00 CT of the current week."""
    now = now_ct()
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def session_times_utc(session_name: str, reference_date: datetime | None = None) -> tuple[datetime, datetime]:
    """Get session open/close times in UTC for a given date.

    Sessions that span midnight (Sydney, Tokyo) have close on next day.
    """
    from config.settings import get_settings

    sessions = get_settings().instruments.get("sessions", {})
    session = sessions.get(session_name)
    if not session:
        raise ValueError(f"Unknown session: {session_name}")

    if reference_date is None:
        reference_date = today_ct()

    open_h, open_m = map(int, session["open_ct"].split(":"))
    close_h, close_m = map(int, session["close_ct"].split(":"))

    open_ct = reference_date.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
    close_ct = reference_date.replace(hour=close_h, minute=close_m, second=0, microsecond=0)

    # If close is before open, session spans midnight
    if close_ct <= open_ct:
        close_ct += timedelta(days=1)

    if open_ct.tzinfo is None:
        open_ct = CT.localize(open_ct)
    if close_ct.tzinfo is None:
        close_ct = CT.localize(close_ct)

    return open_ct.astimezone(UTC), close_ct.astimezone(UTC)

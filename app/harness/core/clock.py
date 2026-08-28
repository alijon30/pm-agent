"""Time, injectable, and how a moment is written down for a person.

Everything that reads the clock takes a Clock so tests can move time. The two human formatters
live here rather than with any one surface because Slack, the console and the graph must all
write the same date the same way."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def iso(dt: datetime) -> str:
    """UTC, second precision, fixed width — so Firestore string comparison equals time
    comparison and no document ever needs a Timestamp type."""
    return dt.astimezone(UTC).replace(microsecond=0).isoformat()


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def readable(value: str) -> datetime | None:
    """An ISO string as a datetime, or None. Tolerant on purpose: callers format what they can
    and leave out what they cannot, rather than raising over a field that was always optional."""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def human_date(value: str) -> str:
    """"Sep 1". Empty for anything unparseable, so a caller can leave the date out entirely."""
    when = readable(value)
    return f"{MONTHS[when.month - 1]} {when.day}" if when else ""


def human_due(value: str) -> str:
    """"Mon Sep 1" — the weekday is what tells someone whether a date is soon."""
    when = readable(value)
    return f"{when:%a} {human_date(value)}" if when else ""


def human_delta(value: str, now: datetime) -> str:
    """How far off something is, said the way someone waiting would say it.

    An absolute time answers "when"; a person looking at a queue is asking "how soon". Minutes
    while it is minutes, hours while it is today, "tomorrow 09:00" once the date turns — and a
    plain date beyond that, where the hour stops mattering."""
    when = readable(value)
    if when is None:
        return ""
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    seconds = (when - now).total_seconds()
    if seconds <= 0:
        return "due now"
    if seconds < 3600:
        return f"in {max(1, round(seconds / 60))} min"
    here, there = now.astimezone(UTC), when.astimezone(UTC)
    days = (there.date() - here.date()).days
    if days == 0:
        return f"in {round(seconds / 3600)} h"
    if days == 1:
        return f"tomorrow {there:%H:%M}"
    return human_due(value)

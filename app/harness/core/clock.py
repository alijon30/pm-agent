"""Time, injectable, and how a moment is written down for a person.

Everything that reads the clock takes a Clock so tests can move time. The two human formatters
live here rather than with any one surface because Slack, the console and the graph must all
write the same date the same way."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

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


def when_phrase(value: str, now: datetime) -> str:
    """A date as somebody would say it out loud: "today", "tomorrow", "Monday", "Sep 4".

    Different from human_delta, which answers "how soon" for a queue. This answers "when" for a
    sentence — "it was meant to be underway today" — and a weekday is what a person uses inside
    the week they are living in."""
    when = readable(value)
    if when is None:
        return ""
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    here, there = now.astimezone(UTC), when.astimezone(UTC)
    days = (there.date() - here.date()).days
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    if days == -1:
        return "yesterday"
    if 2 <= days <= 6:
        return f"{there:%A}"
    return human_date(value)



def stamp_local(value: str, tz: Any) -> str:
    """"Aug 29 09:00" in the team's own timezone — the same shape the graph draws.

    A standup posted at 9am in California read as "16:00" when the console wrote UTC, which
    makes the agent look like it ran at the wrong time."""
    moment = readable(value)
    if moment is None:
        return ""
    here = moment.astimezone(tz)
    return f"{MONTHS[here.month - 1]} {here.day} {here:%H:%M}"


def sprint_day(sprint: dict[str, Any], today: str) -> str:
    """"day 3 of Sprint 1", or nothing at all. A sprint is a shared sense of where in the week
    everyone is, and it is the one number that makes a standup feel situated.

    Lives here rather than beside the Slack blocks because the console says it too, and the
    console may not reach a connector."""
    start, name = str(sprint.get("start") or ""), str(sprint.get("name") or "")
    first, now = readable(start), readable(today)
    if not name or first is None or now is None:
        return ""
    day = (now.date() - first.date()).days + 1
    return f"day {day} of {name}" if day >= 1 else f"{name} starts {human_date(start)}"

"""How much the agent may do in a day, and when it may interrupt people.

Writes and pings are counted separately because they cost differently: a wrong ticket is noise
in a backlog, a wrong ping is noise in someone's evening. Exceeding a cap defers work to the
next window and records why — nothing is ever dropped silently."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any, Literal

CapKind = Literal["write", "ping"]
DEFAULT_QUIET = ("20:00", "08:00")


@dataclass(frozen=True)
class CapsVerdict:
    ok: bool
    defer_until: datetime | None = None
    reason: str = ""


def _parse_hhmm(value: str) -> time:
    hour, _, minute = value.partition(":")
    return time(int(hour), int(minute or 0))


def in_quiet_hours(now_local: datetime, quiet_hours: list[str] | tuple[str, ...]) -> bool:
    start, end = (quiet_hours or DEFAULT_QUIET)[0], (quiet_hours or DEFAULT_QUIET)[1]
    begins, ends = _parse_hhmm(start), _parse_hhmm(end)
    current = now_local.time()
    if begins <= ends:  # a window inside one day, e.g. 12:00–13:00
        return begins <= current < ends
    return current >= begins or current < ends  # wraps midnight, e.g. 20:00–08:00


def next_window(now_local: datetime, quiet_hours: list[str] | tuple[str, ...]) -> datetime:
    """The first moment quiet hours are over. Same day if the window ends later today,
    tomorrow if it wraps past midnight."""
    ends = _parse_hhmm((quiet_hours or DEFAULT_QUIET)[1])
    candidate = now_local.replace(hour=ends.hour, minute=ends.minute, second=0, microsecond=0)
    if candidate <= now_local:
        candidate += timedelta(days=1)
    return candidate


def _next_midnight(now_local: datetime) -> datetime:
    return (now_local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def check_caps(
    kind: CapKind,
    counts_today: dict[str, int],
    now_local: datetime,
    policy: dict[str, Any],
) -> CapsVerdict:
    """Whether one more write or ping is allowed right now."""
    if kind == "ping":
        quiet = policy.get("quiet_hours") or DEFAULT_QUIET
        if in_quiet_hours(now_local, quiet):
            until = next_window(now_local, quiet)
            return CapsVerdict(False, until, f"quiet hours until {until:%H:%M}")
        cap = int(policy.get("daily_ping_cap", 10))
        used = int(counts_today.get("ping", 0))
        if used >= cap:
            return CapsVerdict(
                False, _next_midnight(now_local), f"daily ping cap reached ({used}/{cap})"
            )
        return CapsVerdict(True)

    cap = int(policy.get("daily_write_cap", 40))
    used = int(counts_today.get("write", 0))
    if used >= cap:
        return CapsVerdict(
            False, _next_midnight(now_local), f"daily write cap reached ({used}/{cap})"
        )
    return CapsVerdict(True)

"""Time, injectable. Everything that reads the clock takes a Clock so tests can move time."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


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

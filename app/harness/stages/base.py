"""Shared stage types. A stage is a function (task, deps) -> StageResult; it never writes to the
queue itself — the runner does, atomically with marking the task done."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.harness.deps import Deps
from app.harness.store.db import Doc


@dataclass(frozen=True)
class StageResult:
    result: dict[str, Any]
    children: list[dict[str, Any]] = field(default_factory=list)
    # Open task ids this stage's work makes obsolete; the queue cancels them in the same
    # transaction that creates the children, so a re-plan is never briefly double-booked.
    supersedes: list[str] = field(default_factory=list)


StageHandler = Callable[[Doc, Deps], Awaitable[StageResult]]

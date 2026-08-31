"""Shared stage types: a stage is a function (task, deps) -> StageResult."""

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
    # Open task ids this stage's work makes obsolete; cancelled in the same transaction.
    supersedes: list[str] = field(default_factory=list)


StageHandler = Callable[[Doc, Deps], Awaitable[StageResult]]

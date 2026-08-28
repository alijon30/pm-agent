"""Everything a route or a stage needs, in one object, so wiring lives in main.py and tests
build it from fakes in one place (tests/conftest.py)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agents.base.protocols import (
    Extractor,
    Planner,
    Reconciler,
    Reporter,
    Reviewer,
    Triage,
)
from app.config import Settings
from app.harness.core.clock import Clock
from app.harness.store.actions import ActionStore
from app.harness.store.corrections import CorrectionStore
from app.harness.store.db import Db
from app.harness.store.decisions import DecisionStore
from app.harness.store.events import EventStore
from app.harness.store.lessons import LessonStore
from app.harness.store.projects import ProjectStore
from app.harness.store.tasks import TaskQueue
from app.harness.verify.ids import IdGate


@dataclass
class Deps:
    settings: Settings
    db: Db
    clock: Clock
    queue: TaskQueue
    events: EventStore
    projects: ProjectStore
    decisions: DecisionStore
    extractor: Extractor
    triage: Triage
    actions: ActionStore | None = None
    corrections: CorrectionStore | None = None
    lessons: LessonStore | None = None
    ids: IdGate | None = None
    reconciler: Reconciler | None = None
    planner: Planner | None = None
    # The steward answers a person; the planner answers an event. Same shape.
    steward: Planner | None = None
    reviewer: Reviewer | None = None
    reporter: Reporter | None = None
    linear: Any = None
    notion: Any = None
    code: Any = None
    slack: Any = None
    github: Any = None
    # True only for deps built by build_deps(): the app's startup hook finishes the wiring that
    # needs an async read (roster, project ids) — test deps wire themselves and skip this.
    wire_on_startup: bool = False

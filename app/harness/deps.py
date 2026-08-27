"""Everything a route or a stage needs, in one object, so wiring lives in main.py and tests
build it from fakes in one place (tests/conftest.py)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.protocols import Extractor, Triage
from app.config import Settings
from app.harness.core.clock import Clock
from app.harness.store.db import Db
from app.harness.store.decisions import DecisionStore
from app.harness.store.events import EventStore
from app.harness.store.projects import ProjectStore
from app.harness.store.tasks import TaskQueue


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

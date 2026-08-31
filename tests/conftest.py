from datetime import UTC, datetime

import pytest
from app.agents.triage import PassthroughTriage
from app.config import Settings
from app.harness.deps import Deps
from app.harness.store.decisions import DecisionStore
from app.harness.store.events import EventStore
from app.harness.store.projects import ProjectStore
from app.harness.store.tasks import TaskQueue
from app.main import create_app
from fastapi.testclient import TestClient

from tests.fakes.fake_agents import FakeExtractor
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_db import FakeDb

T0 = datetime(2026, 8, 27, 9, 0, tzinfo=UTC)

ACME = {
    "slug": "acme",
    "linear_team_id": "",
    "linear_project_id": "",
    "notion_root_page_id": "",
    "slack_channel_id": "",
    "code_repo": "tests/fixtures/acme-invoicing",
    "roster": [
        {"name": "Maya Chen", "aliases": ["Maya"], "linear_user_id": "", "slack_id": "", "role": "pm"},
        {"name": "Nodir Rahimov", "aliases": ["Nodir"], "linear_user_id": "", "slack_id": "",
         "role": "backend"},
        {"name": "Priya Nair", "aliases": ["Priya"], "linear_user_id": "", "slack_id": "",
         "role": "frontend"},
        {"name": "Tom Alvarez", "aliases": ["Tom"], "linear_user_id": "", "slack_id": "",
         "role": "support"},
    ],
    "policy": {"max_depth": 4, "max_children": 12, "max_plan_size": 12, "max_open_tasks": 50,
               "plan_horizon_days": 30},
}


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(T0)


@pytest.fixture
def db() -> FakeDb:
    return FakeDb()


@pytest.fixture
def settings() -> Settings:
    return Settings.for_tests(fathom_webhook_secret="", tick_token="tick-secret")


@pytest.fixture
def extractor() -> FakeExtractor:
    return FakeExtractor([])


@pytest.fixture
async def deps(db: FakeDb, clock: FakeClock, settings: Settings, extractor: FakeExtractor) -> Deps:
    projects = ProjectStore(db, default_slug=settings.default_project_slug)
    await projects.upsert("acme", ACME)
    return Deps(
        settings=settings,
        db=db,
        clock=clock,
        queue=TaskQueue(db, clock, lease_minutes=settings.lease_minutes),
        events=EventStore(db, clock),
        projects=projects,
        decisions=DecisionStore(db, clock),
        extractor=extractor,
        triage=PassthroughTriage(),
    )


@pytest.fixture
def client(deps: Deps) -> TestClient:
    return TestClient(create_app(deps))

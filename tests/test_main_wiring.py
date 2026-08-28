"""The startup hook finishes the wiring that needs the database — and stays away from deps that
wired themselves."""

from typing import Any

from app.config import Settings
from app.harness.deps import Deps
from app.main import finish_wiring

from tests.conftest import ACME
from tests.fakes.fake_agents import FakeExtractor
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_db import FakeDb


async def test_test_deps_are_left_exactly_as_the_test_built_them(deps: Deps) -> None:
    sentinel = object()
    deps.reconciler = sentinel  # type: ignore[assignment]
    await finish_wiring(deps)
    assert deps.reconciler is sentinel  # wire_on_startup=False → untouched


async def test_startup_wires_the_gate_and_agents_from_the_project_document(
    deps: Deps,
) -> None:
    deps.wire_on_startup = True
    await deps.projects.upsert("acme", {**ACME, "linear_team_id": "team-1"})
    await finish_wiring(deps)

    assert deps.ids is not None and deps.code is not None
    assert deps.reconciler is not None and deps.planner is not None
    assert deps.ids.person_exists("Maya Chen") is True
    assert deps.ids.person_exists("Sam") is False
    assert deps.code.exists("acme/config.py") is True


async def test_an_unseeded_project_boots_degraded_instead_of_crashing(
    settings: Settings, clock: FakeClock,
) -> None:
    from app.agents.triage import PassthroughTriage
    from app.harness.store.decisions import DecisionStore
    from app.harness.store.events import EventStore
    from app.harness.store.projects import ProjectStore
    from app.harness.store.tasks import TaskQueue

    db = FakeDb()
    empty: Any = Deps(
        settings=settings, db=db, clock=clock,
        queue=TaskQueue(db, clock), events=EventStore(db, clock),
        projects=ProjectStore(db, default_slug="acme"),
        decisions=DecisionStore(db, clock), extractor=FakeExtractor([]),
        triage=PassthroughTriage(), wire_on_startup=True,
    )
    await finish_wiring(empty)  # must not raise
    assert empty.reconciler is None and empty.ids is None


async def test_the_meeting_lookup_matches_recorded_fathom_events(deps: Deps) -> None:
    deps.wire_on_startup = True
    await deps.events.record(provider="fathom", provider_event_id="msg_1",
                             payload={"recording_id": 8841201}, project_id="acme")
    await finish_wiring(deps)
    assert deps.ids is not None
    assert await deps.ids.ref_exists("fathom:8841201@00:01:42") is True
    assert await deps.ids.ref_exists("fathom:999@00:00:01") is False

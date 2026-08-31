"""plan is where the agent decides what to watch. These tests are about the boundary: the model
proposes, the gate decides, the queue schedules — and none of those steps trusts the previous
one blindly."""

from datetime import UTC, datetime
from typing import Any

from app.harness.deps import Deps
from app.harness.stages.plan import default_followups, parse_offset, run
from app.harness.store.actions import ActionStore
from app.harness.store.db import Doc
from app.harness.verify.ids import IdGate

from tests.conftest import ACME
from tests.fakes.fake_agents import FakePlanner
from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_slack import FakeSlack

NOW = datetime(2026, 8, 27, 9, 0, tzinfo=UTC)
CONTEXT = {
    "created": [{"identifier": "INV-143", "title": "Move reminders", "owner": "Nodir Rahimov"}],
    "updated": [],
    "items": [{"identifier": "INV-143", "owner": "Nodir Rahimov", "due": "2026-09-04"}],
    "decision_ids": ["dec-1"],
    "meeting": {"title": "Q3 Billing planning"},
}

GOOD_PLAN = {
    "tasks": [
        {"key": "started", "kind": "check_issue_state",
         "params": {"issue": "INV-143", "expect": ["In Progress", "Done"]},
         "due": "2026-09-03T16:00:00Z", "reason": "should be underway the day before it is due",
         "depends_on": [], "on_unmet": "nudge_assignee", "on_dep_failed": "skip", "context": {}},
        {"key": "pr", "kind": "check_pr_exists", "params": {"issue": "INV-143"},
         "due": "2026-09-04T16:00:00Z", "reason": "a pull request should exist by Friday",
         "depends_on": ["started"], "on_unmet": "nudge_assignee", "on_dep_failed": "skip",
         "context": {}},
    ],
    "supersedes": [],
    "notes": "Nodir committed to Friday, so I will check Thursday and Friday.",
}
BAD_PLAN = {
    "tasks": [{"key": "ghost", "kind": "check_issue_state",
               "params": {"issue": "INV-999", "expect": ["Done"]},
               "due": "2026-09-03T16:00:00Z", "reason": "watch a phantom", "depends_on": [],
               "on_unmet": "none", "on_dep_failed": "skip", "context": {}}],
    "supersedes": [], "notes": "",
}


async def wire(deps: Deps, *, planner_results: list[dict[str, Any]],
               context: dict[str, Any] | None = None) -> Doc:
    await deps.projects.upsert("acme", {**ACME, "slack_channel_id": "C-product"})
    deps.actions = ActionStore(deps.db, deps.clock)
    deps.slack = FakeSlack()
    deps.planner = FakePlanner(planner_results)
    deps.ids = IdGate(
        linear=FakeLinear(issues=[
            {"id": "u-143", "identifier": "INV-143", "title": "Move reminders", "description": "",
             "state": "Todo", "priority": 3, "assignee": None, "due_date": None, "url": "",
             "updated_at": ""}]),
        roster=ACME["roster"],
    )
    tid = await deps.queue.enqueue(kind="plan", project_id="acme", payload={},
                                   reason="plan the follow-through", root_event_id="fathom:msg_1",
                                   context=context if context is not None else CONTEXT)
    assert tid is not None
    task = await deps.queue.claim(tid)
    assert task is not None
    return task


# --- the default chain ------------------------------------------------------------------------

def test_an_offset_moves_around_the_date_that_was_promised() -> None:
    anchor = datetime(2026, 9, 4, 16, 0, tzinfo=UTC)
    assert parse_offset("-1d", anchor) == datetime(2026, 9, 3, 16, 0, tzinfo=UTC)
    assert parse_offset("0d", anchor) == anchor
    assert parse_offset("+3d", anchor) == datetime(2026, 9, 7, 16, 0, tzinfo=UTC)


def test_the_default_chain_watches_start_then_pull_request_then_landing() -> None:
    chain = default_followups(CONTEXT, ACME["policy"], NOW).model_dump()
    assert [t["kind"] for t in chain["tasks"]] == [
        "check_issue_state", "check_pr_exists", "check_issue_state"]
    assert chain["tasks"][1]["depends_on"] == ["inv143_started"]
    assert chain["tasks"][2]["depends_on"] == ["inv143_pr"]
    assert chain["tasks"][0]["due"] == "2026-09-03T16:00:00+00:00"
    assert chain["tasks"][2]["on_unmet"] == "escalate_channel"


def test_the_default_chain_never_schedules_a_check_in_the_past() -> None:
    overdue = {"items": [{"identifier": "INV-143", "due": "2026-08-01"}]}
    chain = default_followups(overdue, ACME["policy"], NOW).model_dump()
    assert chain["tasks"][0]["due"] == "2026-08-27T10:00:00+00:00"


def test_nothing_filed_means_nothing_to_watch() -> None:
    assert default_followups({}, ACME["policy"], NOW).model_dump()["tasks"] == []


# --- the stage --------------------------------------------------------------------------------

async def test_a_valid_plan_becomes_scheduled_work_in_dependency_order(deps: Deps) -> None:
    task = await wire(deps, planner_results=[GOOD_PLAN])
    out = await run(task, deps)

    assert out.result["accepted"] == ["started", "pr"]
    assert out.result["rejected"] == [] and out.result["bounced"] is False
    assert "Nodir committed to Friday" in out.result["notes"]

    assert [c["kind"] for c in out.children] == ["check_issue_state", "check_pr_exists"]
    assert out.children[1]["depends_on"] == ["started"]
    assert out.children[0]["params"] == {"issue": "INV-143", "expect": ["In Progress", "Done"]}
    assert out.children[0]["on_unmet"] == "nudge_assignee"


async def test_the_planner_sees_the_catalog_what_is_already_scheduled_and_the_clock(
    deps: Deps,
) -> None:
    task = await wire(deps, planner_results=[GOOD_PLAN])
    await deps.queue.enqueue(kind="check_issue_state", project_id="acme", payload={},
                             reason="already watching", params={"issue": "INV-104",
                                                               "expect": ["Done"]})
    await run(task, deps)

    sent = deps.planner.calls[0]
    assert sent["now"] == "2026-08-27T09:00:00+00:00"
    assert sent["context"]["created"][0]["identifier"] == "INV-143"
    assert {c["kind"] for c in sent["catalog"]} >= {"check_issue_state", "nudge", "escalate"}
    assert sent["policy"]["plan_horizon_days"] == 30
    assert sent["feedback"] is None


async def test_an_invalid_plan_is_bounced_once_and_the_rejection_is_reported(
    deps: Deps,
) -> None:
    task = await wire(deps, planner_results=[BAD_PLAN, GOOD_PLAN])
    out = await run(task, deps)

    assert out.result["bounced"] is True
    assert out.result["accepted"] == ["started", "pr"]
    assert len(deps.planner.calls) == 2
    assert "INV-999" in (deps.planner.calls[1]["feedback"] or "")


async def test_a_plan_that_stays_invalid_falls_back_and_says_why(deps: Deps) -> None:
    """Seen live: the planner proposed three checks, all missing a required param, and the
    bounce did not fix them — and nothing got scheduled at all. A rejected plan is the same
    emergency as no plan: the default chain watches the real work either way, and the
    rejections are still reported."""
    task = await wire(deps, planner_results=[BAD_PLAN, BAD_PLAN])
    out = await run(task, deps)

    assert [c["kind"] for c in out.children] == [
        "check_issue_state", "check_pr_exists", "check_issue_state"]
    assert out.result["accepted"] == ["inv143_started", "inv143_pr", "inv143_done"]
    assert "INV-999" in out.result["rejected"][0]["reason"]
    assert "default follow-up chain" in out.result["notes"]


async def test_a_planner_that_breaks_its_own_json_still_yields_the_default_chain(
    deps: Deps,
) -> None:
    """Seen live on Vertex with thinking on: the model hand-writes its plan JSON and breaks
    it. The commitment still gets watched — by the deterministic chain, honestly labelled."""
    import json as jsonlib

    class BrokenPlanner:
        async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
            raise jsonlib.JSONDecodeError("Expecting ',' delimiter", '{"tasks": [', 10)

    task = await wire(deps, planner_results=[])
    deps.planner = BrokenPlanner()
    out = await run(task, deps)

    assert [c["kind"] for c in out.children] == [
        "check_issue_state", "check_pr_exists", "check_issue_state"]
    assert "was not usable" in out.result["notes"]
    assert "default follow-up chain" in out.result["notes"]


async def test_a_planner_with_nothing_to_say_falls_back_to_the_default_chain(
    deps: Deps,
) -> None:
    empty = {"tasks": [], "supersedes": [], "notes": ""}
    task = await wire(deps, planner_results=[empty])
    out = await run(task, deps)

    assert [c["kind"] for c in out.children] == [
        "check_issue_state", "check_pr_exists", "check_issue_state"]
    assert "default follow-up chain" in out.result["notes"]


async def test_a_plan_may_retire_work_that_reality_has_moved_past(deps: Deps) -> None:
    task = await wire(deps, planner_results=[GOOD_PLAN])
    stale = await deps.queue.enqueue(kind="check_issue_state", project_id="acme", payload={},
                                     reason="stale", params={"issue": "INV-143",
                                                             "expect": ["Done"]})
    assert stale is not None
    deps.planner.results = [{**GOOD_PLAN, "supersedes": [stale, "not-a-real-task"]}]
    out = await run(task, deps)

    assert out.supersedes == [stale]  # the id it made up is simply not there


async def test_the_team_is_told_what_will_be_checked(deps: Deps) -> None:
    task = await wire(deps, planner_results=[GOOD_PLAN])
    await run(task, deps)

    assert len(deps.slack.posts) == 1
    assert deps.slack.posts[0]["text"] == "Here's how I'll follow through:"
    rendered = str(deps.slack.posts[0]["blocks"])
    assert "Here's how I'll follow through:" in rendered
    assert "Sep 3 — check that INV-143 is underway" in rendered
    assert "if not, I'll check in with Nodir" in rendered
    assert "check_issue_state" not in rendered and "2026-09-03" not in rendered
    assert "(s)" not in rendered


async def test_a_slack_outage_never_unschedules_the_work(deps: Deps) -> None:
    from app.harness.core.errors import SourceUnavailable

    task = await wire(deps, planner_results=[GOOD_PLAN])

    async def down(*args: Any, **kwargs: Any) -> str:
        raise SourceUnavailable("slack", "ratelimited")

    deps.slack.post = down  # type: ignore[method-assign]
    out = await run(task, deps)
    assert len(out.children) == 2


async def test_with_no_planner_configured_the_default_chain_still_runs(deps: Deps) -> None:
    task = await wire(deps, planner_results=[])
    deps.planner = None
    out = await run(task, deps)
    assert [c["kind"] for c in out.children] == [
        "check_issue_state", "check_pr_exists", "check_issue_state"]


async def test_what_the_agent_learned_about_itself_reaches_the_planner(deps: Deps) -> None:
    from app.harness.store.lessons import LessonStore

    task = await wire(deps, planner_results=[GOOD_PLAN])
    deps.lessons = LessonStore(deps.db, deps.clock)
    await deps.lessons.add(project_id="acme", text="Wait a working day before asking for a PR.",
                           evidence=["task:t-1"])
    await deps.lessons.add(project_id="acme", text="Escalate rather than nudge nobody.",
                           evidence=["task:t-2"])
    await run(task, deps)

    assert deps.planner.calls[0]["lessons"] == [
        "Escalate rather than nudge nobody.", "Wait a working day before asking for a PR."]


async def test_a_project_that_has_learned_nothing_sends_the_planner_an_empty_list(
    deps: Deps,
) -> None:
    task = await wire(deps, planner_results=[GOOD_PLAN])
    await run(task, deps)

    assert deps.planner.calls[0]["lessons"] == []

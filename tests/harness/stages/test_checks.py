"""The checks the agent scheduled for itself. Most of these are about restraint: one message,
to one person, only when there is something real to say."""

from datetime import UTC, datetime
from typing import Any

from app.harness.deps import Deps
from app.harness.kinds.registry import KINDS
from app.harness.kinds.templates import TEMPLATES, render
from app.harness.stages.checks import CHECKS, run_check, run_nudge
from app.harness.stages.runner import STAGES
from app.harness.store.actions import ActionStore
from app.harness.store.db import Doc

from tests.conftest import ACME
from tests.fakes.fake_github import FakeGitHub
from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_slack import FakeSlack

ISSUE = {"id": "u-143", "identifier": "INV-143", "title": "Move reminders to 3 days",
         "description": "", "state": "Todo", "priority": 3,
         "assignee": {"id": "u-nodir", "name": "Nodir Rahimov"}, "due_date": "2026-09-04",
         "url": "https://linear.app/acme/issue/INV-143", "updated_at": ""}
PR = {"number": 7, "title": "Reminders (INV-143)", "state": "open", "merged": False,
      "url": "https://github.com/acme/x/pull/7", "branch": "inv-143", "reviews": 0,
      "updated_at": "2026-08-29T10:00:00Z", "mentions": ["INV-143"]}

PROJECT = {
    **ACME, "slack_channel_id": "C-product",
    "roster": [{**m, "slack_id": f"U-{m['name'].split()[0].lower()}"} for m in ACME["roster"]],
}


async def wire(
    deps: Deps, *, kind: str, params: dict[str, Any], on_unmet: str = "none",
    issues: list[dict[str, Any]] | None = None, prs: list[dict[str, Any]] | None = None,
    project: dict[str, Any] | None = None,
) -> Doc:
    await deps.projects.upsert("acme", project or PROJECT)
    deps.actions = ActionStore(deps.db, deps.clock)
    deps.slack = FakeSlack()
    deps.linear = FakeLinear(issues=issues if issues is not None else [ISSUE])
    deps.github = FakeGitHub(prs if prs is not None else [])
    tid = await deps.queue.enqueue(kind=kind, project_id="acme", payload={}, params=params,
                                   reason="scheduled check", on_unmet=on_unmet)
    assert tid is not None
    task = await deps.queue.claim(tid)
    assert task is not None
    return task


# --- the catalog is fully executable ----------------------------------------------------------

def test_every_kind_the_planner_may_schedule_has_something_that_runs_it() -> None:
    schedulable = set(KINDS) - {"daily_review", "reconcile_item", "escalate"}
    assert schedulable <= set(STAGES), f"unrunnable kinds: {schedulable - set(STAGES)}"


def test_every_check_kind_has_an_executor() -> None:
    assert {k for k in KINDS if k.startswith("check_")} == set(CHECKS)


# --- observing --------------------------------------------------------------------------------

async def test_an_issue_in_an_expected_state_is_met_and_nobody_is_disturbed(deps: Deps) -> None:
    task = await wire(deps, kind="check_issue_state", on_unmet="nudge_assignee",
                      params={"issue": "INV-143", "expect": ["Todo", "In Progress"]})
    out = await run_check(task, deps)

    assert out.result["met"] is True and out.result["acted"] == []
    assert out.result["observed"]["state"] == "Todo"
    assert deps.slack.posts == []


async def test_an_issue_that_has_not_moved_produces_exactly_one_nudge(deps: Deps) -> None:
    task = await wire(deps, kind="check_issue_state", on_unmet="nudge_assignee",
                      params={"issue": "INV-143", "expect": ["Done"]})
    out = await run_check(task, deps)

    assert out.result["met"] is False and len(out.result["acted"]) == 1
    assert len(deps.slack.posts) == 1
    text = deps.slack.posts[0]["text"]
    assert "<@U-nodir>" in text and "INV-143" in text and "still Todo" in text
    assert "open it" in text


async def test_an_issue_that_vanished_is_reported_and_nobody_is_nudged(deps: Deps) -> None:
    task = await wire(deps, kind="check_issue_state", on_unmet="nudge_assignee", issues=[],
                      params={"issue": "INV-143", "expect": ["Done"]})
    out = await run_check(task, deps)

    assert out.result["met"] is False and out.result["observed"]["status"] == "gone"
    assert deps.slack.posts == []


async def test_a_missing_pull_request_is_unmet_and_one_that_exists_is_met(deps: Deps) -> None:
    task = await wire(deps, kind="check_pr_exists", params={"issue": "INV-143"})
    assert (await run_check(task, deps)).result["met"] is False

    task = await wire(deps, kind="check_pr_exists", params={"issue": "INV-143"}, prs=[PR])
    out = await run_check(task, deps)
    assert out.result["met"] is True and out.result["observed"]["pr"] == 7


async def test_a_pull_request_nobody_looked_at_is_unmet(deps: Deps) -> None:
    task = await wire(deps, kind="check_pr_reviewed", params={"issue": "INV-143"}, prs=[PR])
    assert (await run_check(task, deps)).result["met"] is False

    reviewed = [{**PR, "reviews": 2}]
    task = await wire(deps, kind="check_pr_reviewed", params={"issue": "INV-143"}, prs=reviewed)
    out = await run_check(task, deps)
    assert out.result["met"] is True and out.result["observed"]["reviews"] == 2


async def test_merged_means_merged_not_merely_closed(deps: Deps) -> None:
    closed = [{**PR, "state": "closed", "merged": False}]
    task = await wire(deps, kind="check_pr_merged", params={"issue": "INV-143"}, prs=closed)
    assert (await run_check(task, deps)).result["met"] is False

    merged = [{**PR, "state": "closed", "merged": True}]
    task = await wire(deps, kind="check_pr_merged", params={"issue": "INV-143"}, prs=merged)
    assert (await run_check(task, deps)).result["met"] is True


async def test_a_source_that_cannot_be_reached_nudges_nobody(deps: Deps) -> None:
    from app.harness.core.errors import SourceUnavailable

    task = await wire(deps, kind="check_issue_state", on_unmet="nudge_assignee",
                      params={"issue": "INV-143", "expect": ["Done"]})

    async def down(identifier: str) -> dict[str, Any] | None:
        raise SourceUnavailable("linear", "HTTP 503")

    deps.linear.get_issue = down  # type: ignore[method-assign]
    out = await run_check(task, deps)

    assert out.result["met"] is False
    assert out.result["observed"]["status"] == "unavailable"
    assert out.result["acted"] == [] and deps.slack.posts == []


# --- restraint --------------------------------------------------------------------------------

async def test_a_check_with_nothing_to_do_on_failure_stays_silent(deps: Deps) -> None:
    task = await wire(deps, kind="check_issue_state", on_unmet="none",
                      params={"issue": "INV-143", "expect": ["Done"]})
    out = await run_check(task, deps)
    assert out.result["met"] is False and out.result["acted"] == []
    assert deps.slack.posts == []


async def test_the_same_check_run_twice_does_not_nudge_twice(deps: Deps) -> None:
    task = await wire(deps, kind="check_issue_state", on_unmet="nudge_assignee",
                      params={"issue": "INV-143", "expect": ["Done"]})
    await run_check(task, deps)
    await run_check(task, deps)
    assert len(deps.slack.posts) == 1


async def test_a_nudge_in_quiet_hours_defers_the_check_rather_than_waking_someone(
    deps: Deps,
) -> None:
    task = await wire(deps, kind="check_issue_state", on_unmet="nudge_assignee",
                      params={"issue": "INV-143", "expect": ["Done"]})
    deps.clock._now = datetime(2026, 8, 27, 22, 0, tzinfo=UTC)  # type: ignore[attr-defined]
    out = await run_check(task, deps)

    assert out.result["acted"] == [] and deps.slack.posts == []
    stored = await deps.db.get("tasks", task["id"])
    assert stored is not None and stored["status"] == "deferred"
    assert "quiet hours" in stored["defer_reason"]
    assert stored["due_at"] == "2026-08-28T08:00:00+00:00"


async def test_the_daily_ping_cap_stops_the_agent_talking(deps: Deps) -> None:
    task = await wire(deps, kind="check_issue_state", on_unmet="nudge_assignee",
                      params={"issue": "INV-143", "expect": ["Done"]},
                      project={**PROJECT, "policy": {**PROJECT["policy"], "daily_ping_cap": 0}})
    out = await run_check(task, deps)
    assert out.result["acted"] == [] and deps.slack.posts == []
    stored = await deps.db.get("tasks", task["id"])
    assert stored is not None and "ping cap" in stored["defer_reason"]


# --- escalation and phrasing ------------------------------------------------------------------

async def test_an_escalation_goes_to_the_channel_and_names_the_owner(deps: Deps) -> None:
    task = await wire(deps, kind="check_issue_state", on_unmet="escalate_channel",
                      params={"issue": "INV-143", "expect": ["Done"]})
    await run_check(task, deps)

    text = deps.slack.posts[0]["text"]
    assert "has not moved" in text and "Owner: <@U-nodir>" in text


async def test_an_unowned_issue_escalates_without_blaming_anyone(deps: Deps) -> None:
    unowned = [{**ISSUE, "assignee": None}]
    task = await wire(deps, kind="check_issue_state", on_unmet="escalate_channel", issues=unowned,
                      params={"issue": "INV-143", "expect": ["Done"]})
    await run_check(task, deps)
    assert "has no owner" in deps.slack.posts[0]["text"]


def test_every_template_renders_with_the_values_a_check_can_supply() -> None:
    values = {"person": "<@U1>", "issue": "INV-143", "title": "t", "state": "Todo",
              "due": "2026-09-04", "pr_url": "https://x", "link": "<u|open it>"}
    for name in TEMPLATES:
        assert render(name, **values)


def test_an_unknown_template_is_a_bug_not_a_fallback() -> None:
    try:
        render("no_such_template", person="x")
    except KeyError as exc:
        assert "no_such_template" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected a KeyError")


# --- a nudge the planner scheduled directly ---------------------------------------------------

async def test_a_planned_nudge_is_sent_once(deps: Deps) -> None:
    task = await wire(deps, kind="nudge", params={
        "person": "Nodir Rahimov", "about": "INV-143", "template": "pr_missing"})
    out = await run_nudge(task, deps)

    assert out.result["sent"] is True
    assert "<@U-nodir>" in deps.slack.posts[0]["text"]

    again = await run_nudge(task, deps)
    assert again.result["sent"] is False and len(deps.slack.posts) == 1


async def test_a_nudge_says_a_date_the_way_a_person_would(deps: Deps) -> None:
    overdue = [{**ISSUE, "due_date": "2026-09-04", "state": "Todo"}]
    task = await wire(deps, kind="check_issue_state", on_unmet="nudge_assignee", issues=overdue,
                      params={"issue": "INV-143", "expect": ["Done"]})
    await run_check(task, deps)

    text = deps.slack.posts[0]["text"]
    assert "was due Fri Sep 4" in text or "was due Sep 4" in text
    assert "2026-09-04" not in text

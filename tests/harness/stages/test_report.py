"""report is the one stage whose output a human reads without checking anything, so these tests
are about two things: that the reporter is shown the real state of the sprint, and that nothing
it cannot prove ever reaches the channel."""

from typing import Any

import pytest
from app.harness.core.errors import PmError, SourceUnavailable
from app.harness.deps import Deps
from app.harness.stages.report import report_window, run
from app.harness.store.actions import ActionStore
from app.harness.store.db import Doc
from app.harness.verify.ids import IdGate

from tests.conftest import ACME, T0
from tests.fakes.fake_agents import FakeReporter
from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_slack import FakeSlack

SPRINT = {"name": "Sprint 1", "start": "2026-08-20", "end": "2026-09-03"}
PROJECT = {**ACME, "slack_channel_id": "C-product", "sprint": SPRINT}

# Filed as "Move reminders" and since renamed and moved on: the report is about the state of the
# work today, not about what the audit log remembers doing to it.
ISSUE = {"id": "u-143", "identifier": "INV-143", "title": "Move payment reminders",
         "description": "", "state": "In Review", "priority": 3,
         "assignee": {"id": "u-nodir", "name": "Nodir Rahimov"}, "due_date": "2026-09-04",
         "url": "https://linear.app/acme/issue/INV-143", "updated_at": ""}
OLD_ISSUE = {**ISSUE, "id": "u-140", "identifier": "INV-140", "title": "Last sprint's work",
             "url": "https://linear.app/acme/issue/INV-140"}

CONFLICT = {"kind": "code_vs_spec", "about": "reminder window", "sides": [
    {"claim": "7 days", "source": "code:acme/config.py:6"},
    {"claim": "5 days", "source": "notion:page-prd"}]}

GOOD_REPORT = {
    "headline": "Reminders landed a day early; one spec disagreement is still open.",
    "sections": [
        {"name": "shipped", "claims": [
            {"text": "INV-143 reached review ahead of its due date.",
             "refs": ["linear:INV-143"]}]},
        {"name": "decisions", "claims": [
            {"text": "Reminders move to three days before the due date.",
             "refs": ["decision:dec-1"]}]},
    ],
}
BAD_REPORT = {
    "headline": "A busy sprint.",
    "sections": [
        {"name": "shipped", "claims": [
            {"text": "INV-143 reached review ahead of its due date.",
             "refs": ["linear:INV-143"]},
            {"text": "INV-999 shipped on Tuesday.", "refs": ["linear:INV-999"]},
            {"text": "The team feels good about the sprint.", "refs": []}]},
    ],
}
QUIET_REPORT = {"headline": "A quiet sprint: nothing to report.", "sections": []}


async def wire(
    deps: Deps,
    *,
    reporter_results: list[dict[str, Any]],
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    issues: list[dict[str, Any]] | None = None,
    project: dict[str, Any] | None = None,
) -> Doc:
    """A sprint with one filed issue, one check that came back early, one decision, one open
    conflict — and the claimed report task that is about to describe them."""
    await deps.projects.upsert("acme", project if project is not None else PROJECT)
    deps.actions = ActionStore(deps.db, deps.clock)
    deps.slack = FakeSlack()
    deps.linear = FakeLinear(issues=issues if issues is not None else [ISSUE])
    deps.reporter = FakeReporter(reporter_results)
    deps.ids = IdGate(linear=deps.linear, db=deps.db, roster=ACME["roster"])

    await deps.db.set("decisions", "dec-1", {
        "statement": "Reminders move to three days before the due date.",
        "quote": "let's make it three days", "source": "fathom:8841201@00:01:58",
        "project_id": "acme"})

    filed = await deps.actions.begin(
        task_id="t-act", project_id="acme", kind="linear.create_issue",
        idempotency_key="k-filed", inputs={"title": "Move reminders"})
    await deps.actions.finish(filed, target_ids={"identifier": "INV-143", "url": ISSUE["url"]},
                              revert={"op": "archive", "issue": "INV-143"})

    check_id = await deps.queue.enqueue(
        kind="check_pr_merged", project_id="acme", payload={}, params={"issue": "INV-143"},
        reason="did the reminder work land?")
    assert check_id is not None
    await deps.db.update("tasks", check_id, {
        "status": "done", "finished_at": "2026-08-26T12:00:00+00:00",
        "result": {"met": True, "early": True, "acted": [],
                   "observed": {"issue": "INV-143", "pr": 12}}})

    act_id = await deps.queue.enqueue(kind="act", project_id="acme", payload={}, reason="file")
    assert act_id is not None
    await deps.db.update("tasks", act_id, {"status": "done", "result": {"conflicts": [CONFLICT]}})

    tid = await deps.queue.enqueue(
        kind="report", project_id="acme", payload=payload or {},
        params=params if params is not None else {"project": "acme", "window": "sprint"},
        reason="report requested in Slack", root_event_id="slack:Ev1")
    assert tid is not None
    task = await deps.queue.claim(tid)
    assert task is not None
    return task


# --- the window -------------------------------------------------------------------------------

def test_the_window_is_the_projects_sprint_when_it_has_one() -> None:
    assert report_window(PROJECT, {"window": "sprint"}, T0) == SPRINT


def test_a_project_with_no_sprint_still_gets_a_bounded_window() -> None:
    assert report_window({}, {}, T0) == {
        "name": "last 14 days", "start": "2026-08-13", "end": "2026-08-27"}


def test_a_task_that_asks_for_a_number_of_days_gets_exactly_those() -> None:
    assert report_window(PROJECT, {"window": "3d"}, T0) == {
        "name": "last 3 days", "start": "2026-08-24", "end": "2026-08-27"}


# --- what the reporter is shown ---------------------------------------------------------------

async def test_the_reporter_sees_the_sprint_the_live_issues_and_what_landed_early(
    deps: Deps,
) -> None:
    task = await wire(deps, reporter_results=[GOOD_REPORT])
    await run(task, deps)

    sent = deps.reporter.calls[0]
    assert sent["sprint"] == SPRINT
    assert sent["created_issues"] == [{
        "identifier": "INV-143", "title": "Move payment reminders", "state": "In Review",
        "assignee": "Nodir Rahimov", "url": ISSUE["url"]}]
    assert sent["checks"][0]["kind"] == "check_pr_merged"
    assert sent["checks"][0]["early"] is True and sent["checks"][0]["met"] is True
    assert sent["decisions"] == [{
        "id": "dec-1", "statement": "Reminders move to three days before the due date.",
        "quote": "let's make it three days", "source": "fathom:8841201@00:01:58"}]
    assert sent["open_conflicts"] == [CONFLICT]
    assert sent["actions_summary"]["by_kind"] == {"linear.create_issue": 1}
    assert sent["today"] == "2026-08-27" and sent["feedback"] is None


async def test_an_issue_that_has_since_vanished_from_the_tracker_is_left_out(deps: Deps) -> None:
    task = await wire(deps, reporter_results=[QUIET_REPORT], issues=[])
    await run(task, deps)

    assert deps.reporter.calls[0]["created_issues"] == []


async def test_work_filed_before_this_sprint_is_not_reported_as_this_sprints(deps: Deps) -> None:
    task = await wire(deps, reporter_results=[GOOD_REPORT], issues=[ISSUE, OLD_ISSUE])
    assert deps.actions is not None
    stale = await deps.actions.begin(
        task_id="t-old", project_id="acme", kind="linear.create_issue",
        idempotency_key="k-old", inputs={"title": "Last sprint's work"})
    await deps.actions.finish(stale, target_ids={"identifier": "INV-140", "url": ""},
                              revert={"op": "archive", "issue": "INV-140"})
    await deps.db.update("actions", stale, {"created_at": "2026-07-01T09:00:00+00:00"})

    await run(task, deps)
    assert [i["identifier"] for i in deps.reporter.calls[0]["created_issues"]] == ["INV-143"]


# --- the citation gate, from the stage's side -------------------------------------------------

async def test_a_report_whose_claims_all_check_out_comes_back_untouched(deps: Deps) -> None:
    task = await wire(deps, reporter_results=[GOOD_REPORT])
    out = await run(task, deps)

    assert out.result["report"] == GOOD_REPORT
    assert out.result["removed"] == [] and out.result["bounced"] is False
    assert out.result["posted"] is True
    assert out.children == []


async def test_a_fabricated_identifier_is_bounced_once_then_removed_and_named(
    deps: Deps,
) -> None:
    task = await wire(deps, reporter_results=[BAD_REPORT, BAD_REPORT])
    out = await run(task, deps)

    assert out.result["bounced"] is True and len(deps.reporter.calls) == 2
    assert "INV-999" in (deps.reporter.calls[1]["feedback"] or "")
    assert {r["text"] for r in out.result["removed"]} == {
        "INV-999 shipped on Tuesday.", "The team feels good about the sprint."}
    assert [c["text"] for c in out.result["report"]["sections"][0]["claims"]] == [
        "INV-143 reached review ahead of its due date."]


async def test_a_claim_with_no_reference_is_removed_however_true_it_sounds(deps: Deps) -> None:
    uncited = {"headline": "h", "sections": [
        {"name": "moved", "claims": [{"text": "Everything is on track.", "refs": []}]}]}
    task = await wire(deps, reporter_results=[uncited, uncited])
    out = await run(task, deps)

    assert out.result["report"]["sections"] == []
    assert out.result["removed"][0]["reason"] == "no reference"


async def test_a_reporter_that_fixes_its_citations_on_the_bounce_loses_nothing(
    deps: Deps,
) -> None:
    task = await wire(deps, reporter_results=[BAD_REPORT, GOOD_REPORT])
    out = await run(task, deps)

    assert out.result["bounced"] is True and out.result["removed"] == []
    assert out.result["report"] == GOOD_REPORT


# --- telling the team -------------------------------------------------------------------------

async def test_the_report_reaches_the_project_channel_as_one_recorded_action(
    deps: Deps,
) -> None:
    task = await wire(deps, reporter_results=[GOOD_REPORT])
    await run(task, deps)

    assert len(deps.slack.posts) == 1
    post = deps.slack.posts[0]
    assert post["channel"] == "C-product" and post["thread_ts"] is None
    assert "landed a day early" in post["text"]
    rendered = str(post["blocks"])
    assert "Sprint 1" in rendered and "2026-08-20 → 2026-09-03" in rendered
    assert "*Shipped*" in rendered and "linear:INV-143" in rendered

    posted = await deps.db.query("actions", [("kind", "==", "slack.post")])
    assert len(posted) == 1 and posted[0]["status"] == "done"


async def test_a_report_asked_for_in_a_channel_is_answered_in_that_thread(deps: Deps) -> None:
    task = await wire(deps, reporter_results=[GOOD_REPORT],
                      payload={"channel": "C-random", "thread_ts": "1787821201.000100"})
    await run(task, deps)

    assert deps.slack.posts[0]["channel"] == "C-random"
    assert deps.slack.posts[0]["thread_ts"] == "1787821201.000100"


async def test_a_slack_outage_loses_the_message_not_the_report(deps: Deps) -> None:
    task = await wire(deps, reporter_results=[GOOD_REPORT])

    async def down(*args: Any, **kwargs: Any) -> str:
        raise SourceUnavailable("slack", "ratelimited")

    deps.slack.post = down  # type: ignore[method-assign]
    out = await run(task, deps)

    assert out.result["posted"] is False
    assert out.result["report"] == GOOD_REPORT
    failed = await deps.db.query("actions", [("kind", "==", "slack.post")])
    assert failed[0]["status"] == "failed"


async def test_the_same_report_task_run_twice_does_not_post_twice(deps: Deps) -> None:
    task = await wire(deps, reporter_results=[GOOD_REPORT, GOOD_REPORT])
    await run(task, deps)
    out = await run(task, deps)

    assert out.result["posted"] is True
    assert len(deps.slack.posts) == 1


# --- failing closed ---------------------------------------------------------------------------

async def test_with_no_reporter_configured_the_stage_refuses_to_invent_one(deps: Deps) -> None:
    task = await wire(deps, reporter_results=[])
    deps.reporter = None

    with pytest.raises(PmError):
        await run(task, deps)


async def test_with_no_id_gate_nothing_can_be_confirmed_so_nothing_is_claimed(
    deps: Deps,
) -> None:
    task = await wire(deps, reporter_results=[GOOD_REPORT, GOOD_REPORT])
    deps.ids = None
    out = await run(task, deps)

    assert out.result["report"]["sections"] == []
    assert len(out.result["removed"]) == 2

"""The daily review is the one place the agent forms opinions about itself, so these tests are
mostly about the evidence gate: a fluent sentence with an invented source is worth less than
nothing, because it would be believed."""

from typing import Any

import pytest
from app.harness.core.clock import iso
from app.harness.core.errors import PmError
from app.harness.deps import Deps
from app.harness.stages.review import (
    evidence_ids,
    gather,
    keep_evidenced,
    recent_results,
    run,
)
from app.harness.store.actions import ActionStore
from app.harness.store.db import Doc
from app.harness.store.lessons import LessonStore
from app.harness.store.wiki import WikiStore

from tests.conftest import ACME
from tests.fakes.fake_agents import FakeReviewer
from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_slack import FakeSlack

PROJECT = {**ACME, "slack_channel_id": "C-product"}
YESTERDAY = "2026-08-26T18:00:00+00:00"
LAST_WEEK = "2026-08-20T09:00:00+00:00"
MOVED = {"id": "u-26", "identifier": "INV-26", "title": "CSV export", "description": "",
         "state": "In Progress", "priority": 2, "assignee": {"id": "u-priya", "name": "Priya"},
         "due_date": None, "url": "https://linear.app/acme/issue/INV-26", "updated_at": ""}


async def a_check(deps: Deps, *, met: bool, finished_at: str = YESTERDAY,
                  state: str = "Todo", early: bool = False) -> str:
    tid = await deps.queue.enqueue(
        kind="check_pr_exists", project_id="acme", payload={}, params={"issue": "INV-26"},
        reason="a pull request should exist by now")
    assert tid is not None
    await deps.db.update("tasks", tid, {
        "status": "done", "finished_at": finished_at,
        "result": {"met": met, "early": early, "acted": [],
                   "observed": {"status": "ok", "issue": "INV-26", "state": state}}})
    return tid


async def a_nudge(deps: Deps, *, task_id: str, created_at: str = YESTERDAY) -> str:
    assert deps.actions is not None
    action_id = await deps.actions.begin(
        task_id=task_id, project_id="acme", kind="slack.post", idempotency_key=f"k-{task_id}",
        inputs={"channel": "C-product", "template": "pr_missing"})
    await deps.actions.finish(action_id, target_ids={"channel": "C-product", "ts": "1.1"},
                              revert={})
    await deps.db.update("actions", action_id, {"created_at": created_at})
    return action_id


async def wire(deps: Deps, *, reviewer_results: list[dict[str, Any]] | None = None) -> Doc:
    await deps.projects.upsert("acme", PROJECT)
    deps.actions = ActionStore(deps.db, deps.clock)
    deps.lessons = LessonStore(deps.db, deps.clock)
    deps.slack = FakeSlack()
    deps.linear = FakeLinear(issues=[MOVED])
    if reviewer_results is not None:
        deps.reviewer = FakeReviewer(reviewer_results)
    tid = await deps.queue.enqueue(
        kind="daily_review", project_id="acme", payload={}, params={"project": "acme"},
        reason="the morning review of yesterday's outcomes")
    assert tid is not None
    task = await deps.queue.claim(tid)
    assert task is not None
    return task


# --- the evidence gate ---------------------------------------------------------------------------

def test_a_lesson_the_day_supports_is_kept() -> None:
    kept, dropped = keep_evidenced(
        [{"text": "Wait a day.", "evidence": ["task:t-1"]}], {"task:t-1", "action:a-1"})

    assert dropped == []
    assert kept == [{"text": "Wait a day.", "evidence": ["task:t-1"]}]


def test_a_lesson_citing_something_that_did_not_happen_is_dropped() -> None:
    kept, dropped = keep_evidenced(
        [{"text": "Nudge harder.", "evidence": ["task:invented"]}], {"task:t-1"})

    assert kept == []
    assert "task:invented" in dropped[0]["reason"]


def test_a_lesson_needs_every_one_of_its_citations_to_be_real() -> None:
    kept, dropped = keep_evidenced(
        [{"text": "x", "evidence": ["task:t-1", "action:made-up"]}], {"task:t-1"})

    assert kept == [] and "action:made-up" in dropped[0]["reason"]


def test_a_lesson_with_no_citation_at_all_is_dropped() -> None:
    kept, dropped = keep_evidenced([{"text": "Trust me.", "evidence": []}], {"task:t-1"})

    assert kept == [] and dropped[0]["reason"] == "no evidence"


def test_the_citable_set_is_everything_the_reviewer_was_shown() -> None:
    outcomes = {
        "checks": [{"ref": "task:1"}], "nudges": [{"ref": "action:1"}],
        "movements": [{"ref": "action:1"}], "superseded": [{"ref": "task:2"}],
        "failures": [{"ref": "task:3"}],
    }
    assert evidence_ids(outcomes) == {"task:1", "action:1", "task:2", "task:3"}


# --- what a day looks like -----------------------------------------------------------------------

async def test_the_review_gathers_yesterdays_checks_nudges_and_movements(deps: Deps) -> None:
    task = await wire(deps)
    check_id = await a_check(deps, met=False, state="Todo")
    action_id = await a_nudge(deps, task_id=check_id)

    outcomes = await gather(task, deps)

    assert [c["ref"] for c in outcomes["checks"]] == [f"task:{check_id}"]
    assert outcomes["checks"][0]["met"] is False
    assert [n["ref"] for n in outcomes["nudges"]] == [f"action:{action_id}"]
    assert outcomes["movements"] == [{
        "ref": f"action:{action_id}", "issue": "INV-26", "template": "pr_missing",
        "assignee": "Priya",
        "state_when_we_spoke": "Todo", "state_now": "In Progress", "moved": True}]


async def test_the_review_looks_at_one_day_not_at_all_of_history(deps: Deps) -> None:
    task = await wire(deps)
    recent = await a_check(deps, met=True, finished_at=YESTERDAY)
    await a_check(deps, met=True, finished_at=LAST_WEEK)

    outcomes = await gather(task, deps)
    assert [c["ref"] for c in outcomes["checks"]] == [f"task:{recent}"]


async def test_a_nudge_that_changed_nothing_is_recorded_as_such(deps: Deps) -> None:
    task = await wire(deps)
    check_id = await a_check(deps, met=False, state="In Progress")  # already the live state
    await a_nudge(deps, task_id=check_id)

    outcomes = await gather(task, deps)
    assert outcomes["movements"][0]["moved"] is False


async def test_a_tracker_outage_costs_the_reviewer_a_signal_not_the_review(deps: Deps) -> None:
    from app.harness.core.errors import SourceUnavailable

    task = await wire(deps)
    check_id = await a_check(deps, met=False)
    await a_nudge(deps, task_id=check_id)

    async def down(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
        raise SourceUnavailable("linear", "HTTP 503")

    deps.linear.get_issue = down  # type: ignore[method-assign]
    outcomes = await gather(task, deps)

    assert outcomes["movements"] == []
    assert len(outcomes["checks"]) == 1


# --- learning ------------------------------------------------------------------------------------

async def test_a_lesson_the_day_supports_is_stored_and_reported(deps: Deps) -> None:
    task = await wire(deps, reviewer_results=[])
    check_id = await a_check(deps, met=False)
    deps.reviewer = FakeReviewer([{
        "lessons": [{"text": "Give a pull request a full working day before asking about it.",
                     "evidence": [f"task:{check_id}"]}],
        "notes": "One check came back unmet the morning after it was scheduled."}])

    out = await run(task, deps)

    assert out.result["learned"] == [
        "Give a pull request a full working day before asking about it."]
    assert out.result["dropped"] == []
    assert deps.lessons is not None
    stored = await deps.lessons.for_project("acme")
    assert len(stored) == 1
    assert stored[0]["evidence"] == [f"task:{check_id}"]
    assert stored[0]["source_task_id"] == task["id"]


async def test_a_lesson_the_day_does_not_support_is_never_stored(deps: Deps) -> None:
    task = await wire(deps, reviewer_results=[])
    await a_check(deps, met=False)
    deps.reviewer = FakeReviewer([{
        "lessons": [{"text": "Nudge people twice as often.", "evidence": ["task:never-happened"]}],
        "notes": ""}])

    out = await run(task, deps)

    assert out.result["learned"] == []
    assert len(out.result["dropped"]) == 1
    assert deps.lessons is not None
    assert await deps.lessons.for_project("acme") == []


async def test_the_reviewer_sees_the_day_and_what_the_agent_already_believes(
    deps: Deps,
) -> None:
    task = await wire(deps, reviewer_results=[{"lessons": [], "notes": "quiet"}])
    check_id = await a_check(deps, met=True, early=True)
    assert deps.lessons is not None
    await deps.lessons.add(project_id="acme", text="Already known.", evidence=["task:old"])

    await run(task, deps)

    sent = deps.reviewer.calls[0]
    assert [c["ref"] for c in sent["checks"]] == [f"task:{check_id}"]
    assert sent["checks"][0]["early"] is True
    assert sent["lessons_so_far"] == ["Already known."]
    assert sent["window"]["to"] == "2026-08-27T09:00:00+00:00"
    assert sent["feedback"] is None


async def test_a_day_with_nothing_in_it_asks_the_reviewer_nothing(deps: Deps) -> None:
    task = await wire(deps, reviewer_results=[])

    out = await run(task, deps)

    assert deps.reviewer.calls == []  # no evidence, so no question worth the tokens
    assert out.result["learned"] == []


async def test_with_no_reviewer_configured_the_review_still_re_plans(deps: Deps) -> None:
    task = await wire(deps)
    await a_check(deps, met=False)

    out = await run(task, deps)

    assert out.result["learned"] == []
    assert [c["kind"] for c in out.children] == ["plan"]


# --- closing the loop ------------------------------------------------------------------------------

async def test_the_review_hands_yesterdays_outcomes_to_todays_plan(deps: Deps) -> None:
    task = await wire(deps, reviewer_results=[{"lessons": [], "notes": ""}])
    check_id = await a_check(deps, met=False)
    await a_nudge(deps, task_id=check_id)

    out = await run(task, deps)

    assert len(out.children) == 1
    child = out.children[0]
    assert child["kind"] == "plan"
    refs = {row["ref"] for row in child["payload"]["recent_results"]}
    assert f"task:{check_id}" in refs
    assert out.result["checked"] == 1 and out.result["nudged"] == 1 and out.result["moved"] == 1


def test_what_the_planner_reads_is_observations_not_the_whole_day() -> None:
    outcomes = {"checks": [{"ref": "task:1"}], "movements": [{"ref": "action:1"}],
                "failures": [{"ref": "task:2"}], "nudges": [{"ref": "action:9"}],
                "superseded": [{"ref": "task:9"}]}
    assert [row["ref"] for row in recent_results(outcomes)] == [
        "task:1", "action:1", "task:2"]


async def test_a_review_of_a_project_that_does_not_exist_fails_closed(deps: Deps) -> None:
    task = await wire(deps)
    await deps.db.delete("projects", "acme")

    with pytest.raises(PmError):
        await run(task, deps)


# --- the morning standup ---------------------------------------------------------------------------

async def a_due_check(deps: Deps, *, due_at: str, issue: str = "INV-26") -> str:
    tid = await deps.queue.enqueue(
        kind="check_issue_state", project_id="acme", payload={},
        params={"issue": issue, "expect": ["In Progress"]}, reason="is it underway?")
    assert tid is not None
    await deps.db.update("tasks", tid, {"due_at": due_at})
    return tid


def said(deps: Deps) -> str:
    return str(deps.slack.posts[0]["blocks"])


async def test_the_agent_speaks_first_with_what_today_holds(deps: Deps) -> None:
    task = await wire(deps, reviewer_results=[{"lessons": [], "notes": ""}])
    await deps.projects.upsert("acme", {
        **PROJECT, "sprint": {"name": "Sprint 1", "start": "2026-08-25", "end": "2026-09-08"}})
    await a_due_check(deps, due_at="2026-08-27T16:00:00+00:00")
    check_id = await a_check(deps, met=True)
    await a_nudge(deps, task_id=check_id)

    out = await run(task, deps)

    assert out.result["standup"] is True
    assert len(deps.slack.posts) == 1
    assert deps.slack.posts[0]["channel"] == "C-product"
    rendered = said(deps)
    assert "Morning — day 3 of Sprint 1." in rendered
    # No headings on a short standup: five bullets under one greeting is a note, not a form.
    assert "Today I'm watching:" not in rendered and "At risk:" not in rendered
    assert "Today: checking whether INV-26 is underway" in rendered
    assert "Since yesterday: Priya got INV-26 moving." in rendered


async def test_a_quiet_day_says_so_in_two_lines(deps: Deps) -> None:
    task = await wire(deps, reviewer_results=[])
    await a_due_check(deps, due_at="2026-09-04T16:00:00+00:00")  # beyond the 48h horizon

    out = await run(task, deps)

    assert out.result["standup"] is True
    blocks = deps.slack.posts[0]["blocks"]
    assert len(blocks) == 1
    assert "Quiet day ahead — nothing due before Sep 4." in said(deps)


async def test_what_is_slipping_gets_a_line_each(deps: Deps) -> None:
    task = await wire(deps, reviewer_results=[{"lessons": [], "notes": ""}])
    overdue = await a_check(deps, met=False, state="Todo")
    await deps.db.update("tasks", overdue, {"result": {
        "met": False, "early": False,
        "observed": {"status": "ok", "issue": "INV-26", "state": "Todo", "due": "2026-08-20"}}})

    await run(task, deps)

    rendered = said(deps)
    assert "INV-26 — still no pull request." in rendered
    assert "INV-26 was due Aug 20 and is still in Todo" in rendered
    assert "At risk:" not in rendered, "a heading over two lines is a form, not a note"


async def test_a_lesson_learned_this_morning_is_shared_with_the_team(deps: Deps) -> None:
    task = await wire(deps, reviewer_results=[])
    check_id = await a_check(deps, met=False)
    deps.reviewer = FakeReviewer([{
        "lessons": [{"text": "Give a pull request a full working day.",
                     "evidence": [f"task:{check_id}"]}], "notes": ""}])

    await run(task, deps)

    assert "One thing I learned: Give a pull request a full working day." in said(deps)


async def test_the_standup_is_sent_once_a_day_however_often_the_review_runs(
    deps: Deps,
) -> None:
    task = await wire(deps, reviewer_results=[{"lessons": [], "notes": ""},
                                              {"lessons": [], "notes": ""}])
    await a_check(deps, met=True)

    first = await run(task, deps)
    second = await run(task, deps)

    assert first.result["standup"] is True and second.result["standup"] is False
    assert len(deps.slack.posts) == 1


async def test_tomorrows_review_gets_its_own_standup(deps: Deps) -> None:
    task = await wire(deps, reviewer_results=[{"lessons": [], "notes": ""},
                                              {"lessons": [], "notes": ""}])
    await a_check(deps, met=True)
    await run(task, deps)
    deps.clock.advance(days=1)
    await run(task, deps)

    assert len(deps.slack.posts) == 2


async def test_the_standup_is_deliberately_exempt_from_quiet_hours(deps: Deps) -> None:
    """It is scheduled for the start of the working day. Deferring the morning message until
    the morning is over would be a bug wearing a policy's clothes."""
    task = await wire(deps, reviewer_results=[{"lessons": [], "notes": ""}])
    await deps.projects.upsert("acme", {
        **PROJECT, "policy": {**ACME["policy"], "quiet_hours": ["00:00", "23:59"]}})
    await a_check(deps, met=True)

    out = await run(task, deps)

    assert out.result["standup"] is True and len(deps.slack.posts) == 1


async def test_the_daily_ping_budget_still_applies(deps: Deps) -> None:
    """Exempt from the clock is not exempt from the cap."""
    task = await wire(deps, reviewer_results=[{"lessons": [], "notes": ""}])
    await deps.projects.upsert("acme", {
        **PROJECT, "policy": {**ACME["policy"], "daily_ping_cap": 1}})
    check_id = await a_check(deps, met=False)
    await a_nudge(deps, task_id=check_id, created_at="2026-08-27T08:00:00+00:00")

    out = await run(task, deps)

    assert out.result["standup"] is False
    assert deps.slack.posts == []


async def test_a_standup_nobody_received_never_fails_the_review(deps: Deps) -> None:
    from app.harness.core.errors import SourceUnavailable

    task = await wire(deps, reviewer_results=[{"lessons": [], "notes": ""}])
    await a_check(deps, met=True)

    async def down(*args: Any, **kwargs: Any) -> str:
        raise SourceUnavailable("slack", "ratelimited")

    deps.slack.post = down  # type: ignore[method-assign]
    out = await run(task, deps)

    assert out.result["standup"] is False
    assert out.result["checked"] == 1                    # the review still happened
    assert [c["kind"] for c in out.children] == ["plan"]  # and still re-planned
    failed = await deps.db.query("actions", [("kind", "==", "slack.post")])
    assert failed[-1]["status"] == "failed"


async def test_a_project_with_no_channel_simply_does_not_speak(deps: Deps) -> None:
    task = await wire(deps, reviewer_results=[{"lessons": [], "notes": ""}])
    await deps.projects.upsert("acme", {**PROJECT, "slack_channel_id": ""})
    await a_check(deps, met=True)

    out = await run(task, deps)
    assert out.result["standup"] is False


# --- the strongest evidence there is ------------------------------------------------------------

async def test_the_reviewer_is_shown_what_a_person_undid(deps: Deps) -> None:
    """A revert is somebody taking the trouble to say the agent was wrong. Inferring that from
    an unmet check would be reading tea leaves."""
    task = await wire(deps)
    assert deps.actions is not None
    action_id = await deps.actions.begin(
        task_id="t-1", project_id="acme", kind="linear.create_issue",
        idempotency_key="k-1", inputs={"title": "Ship the wrong thing"})
    await deps.actions.finish(action_id, target_ids={"identifier": "INV-99"}, revert={})
    await deps.db.update("actions", action_id, {
        "reverted_at": iso(deps.clock.now()), "reverted_by": "U-maya"})

    gathered = await gather(task, deps)

    assert [r["identifier"] for r in gathered["reverts"]] == ["INV-99"]
    assert gathered["reverts"][0]["by"] == "U-maya"
    assert f"action:{action_id}" in evidence_ids(gathered)


async def test_the_reviewer_is_shown_what_a_person_corrected(deps: Deps) -> None:
    task = await wire(deps)
    deps.wiki = WikiStore(deps.db, deps.clock)
    where = await deps.wiki.add_entry("acme", "correction", {
        "text": "wrong: assigned to Priya; right: billing goes to Nodir",
        "source": "slack:C1:1", "said_by": "Maya Chen"})
    assert where is not None

    gathered = await gather(task, deps)

    assert [c["said_by"] for c in gathered["corrections"]] == ["Maya Chen"]
    assert f"wiki:{where[0]}#{where[1]}" in evidence_ids(gathered)


def test_a_lesson_may_cite_a_correction() -> None:
    """The evidence gate is a membership test, so a new kind of evidence has to be admitted
    deliberately rather than by the model asserting it."""
    allowed = {"wiki:corrections#abc", "action:xyz"}

    kept, dropped = keep_evidenced(
        [{"text": "Ask before reassigning billing", "evidence": ["wiki:corrections#abc"]},
         {"text": "Invented", "evidence": ["wiki:corrections#nope"]}], allowed)

    assert [k["text"] for k in kept] == ["Ask before reassigning billing"]
    assert [d["text"] for d in dropped] == ["Invented"]

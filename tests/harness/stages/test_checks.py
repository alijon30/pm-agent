"""The checks the agent scheduled for itself. Most of these are about restraint: one message,
to one person, only when there is something real to say."""

from datetime import UTC, datetime
from typing import Any

from app.harness.core.errors import SourceUnavailable
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
    project: dict[str, Any] | None = None, context: dict[str, Any] | None = None,
) -> Doc:
    await deps.projects.upsert("acme", project or PROJECT)
    deps.actions = ActionStore(deps.db, deps.clock)
    deps.slack = FakeSlack()
    deps.linear = FakeLinear(issues=issues if issues is not None else [ISSUE])
    deps.github = FakeGitHub(prs if prs is not None else [])
    tid = await deps.queue.enqueue(kind=kind, project_id="acme", payload={}, params=params,
                                   reason="scheduled check", on_unmet=on_unmet,
                                   context=context or {})
    assert tid is not None
    task = await deps.queue.claim(tid)
    assert task is not None
    return task


# --- the catalog is fully executable ----------------------------------------------------------

def test_every_kind_the_planner_may_schedule_has_something_that_runs_it() -> None:
    schedulable = set(KINDS) - {"daily_review", "reconcile_item", "escalate", "intake"}
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
    assert text.startswith("<@U-nodir> — ")
    assert "INV-143" in text and "is still in Todo" in text
    assert "Is it still happening?" in text
    assert "linear.app/acme/issue/INV-143|INV-143" in text, "the link is on the identifier"
    assert not text.endswith("https://linear.app/acme/issue/INV-143")


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
    assert "hasn't moved and is past its date" in text
    assert "<@U-nodir> owns it" in text and "Owner:" not in text


async def test_an_unowned_issue_escalates_without_blaming_anyone(deps: Deps) -> None:
    unowned = [{**ISSUE, "assignee": None}]
    task = await wire(deps, kind="check_issue_state", on_unmet="escalate_channel", issues=unowned,
                      params={"issue": "INV-143", "expect": ["Done"]})
    await run_check(task, deps)
    assert "nobody owns it. Who's picking this up?" in deps.slack.posts[0]["text"]


def test_every_template_renders_with_the_values_a_check_can_supply() -> None:
    """Built by the stage that builds them for real, so a template gaining a variable the
    harness does not supply fails here rather than in somebody's channel."""
    from datetime import UTC, datetime

    from app.harness.stages.checks import _values

    observed = {"issue": "INV-143", "title": "Move payment reminders", "state": "Todo",
                "due": "2026-09-04", "url": "https://linear.app/x/INV-143",
                "pr_url": "https://github.com/x/pull/4"}
    values = _values(observed, {"name": "Nodir Rahimov", "slack_id": "U1"},
                     datetime(2026, 8, 27, 9, 0, tzinfo=UTC))
    for name in TEMPLATES:
        rendered = render(name, **{**values, "finding": "it hasn't started"})
        assert rendered and "{" not in rendered


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


# --- answering the person who asked --------------------------------------------------------------

COMMISSIONED = {"requester_slack_id": "U-maya", "request_channel": "C-random",
                "request_ts": "1787821201.000100"}


async def test_a_check_somebody_asked_for_answers_them_in_their_own_thread(
    deps: Deps,
) -> None:
    task = await wire(deps, kind="check_pr_exists", on_unmet="ping_requester",
                      params={"issue": "INV-143"}, context=COMMISSIONED)
    out = await run_check(task, deps)

    assert out.result["met"] is False and len(out.result["acted"]) == 1
    ping = deps.slack.posts[0]
    assert ping["channel"] == "C-random" and ping["thread_ts"] == "1787821201.000100"
    assert ping["text"].startswith("<@U-maya> — you asked me to watch ")
    assert ping["text"].endswith(": still no pull request.")


async def test_the_ping_reports_the_state_it_actually_saw_not_a_guess(deps: Deps) -> None:
    """"it hasn't started" would be false for an issue in review, and a false sentence in a
    ping is how an agent loses the person it is talking to."""
    in_review = [{**ISSUE, "state": "In Review"}]
    task = await wire(deps, kind="check_issue_state", on_unmet="ping_requester",
                      params={"issue": "INV-143", "expect": ["Done"]}, issues=in_review,
                      context=COMMISSIONED)
    await run_check(task, deps)

    assert "it's still in review" in deps.slack.posts[0]["text"]


async def test_a_check_the_agent_scheduled_for_itself_still_answers_the_assignee(
    deps: Deps,
) -> None:
    task = await wire(deps, kind="check_issue_state", on_unmet="nudge_assignee",
                      params={"issue": "INV-143", "expect": ["Done"]})
    await run_check(task, deps)

    assert deps.slack.posts[0]["channel"] == "C-product"
    assert deps.slack.posts[0]["thread_ts"] is None
    assert "<@U-nodir>" in deps.slack.posts[0]["text"]
    assert "you asked me to watch" not in deps.slack.posts[0]["text"]


async def test_a_requester_ping_with_nobody_to_ping_stays_quiet(deps: Deps) -> None:
    task = await wire(deps, kind="check_pr_exists", on_unmet="ping_requester",
                      params={"issue": "INV-143"})
    out = await run_check(task, deps)

    assert out.result["acted"] == [] and deps.slack.posts == []


async def test_a_requester_ping_obeys_quiet_hours_like_every_other_interruption(
    deps: Deps,
) -> None:
    deps.clock.advance(hours=12)  # 21:00, inside the project's quiet hours
    task = await wire(deps, kind="check_pr_exists", on_unmet="ping_requester",
                      params={"issue": "INV-143"}, context=COMMISSIONED)
    out = await run_check(task, deps)

    assert out.result["acted"] == [] and deps.slack.posts == []
    assert (await deps.db.get("tasks", task["id"]) or {})["status"] == "deferred"


async def test_a_requester_is_pinged_once_however_often_the_check_reruns(deps: Deps) -> None:
    task = await wire(deps, kind="check_pr_exists", on_unmet="ping_requester",
                      params={"issue": "INV-143"}, context=COMMISSIONED)
    await run_check(task, deps)
    await run_check(task, deps)

    assert len(deps.slack.posts) == 1


# --- the first look ---------------------------------------------------------------------------------

async def commissioned(deps: Deps, *, parent: str, issue: str = "INV-143",
                       kind: str = "check_issue_state") -> Doc:
    """A check that came out of an intake commitment, with a sibling parent it shares."""
    params: dict[str, Any] = ({"issue": issue, "expect": ["Todo", "In Progress"]}
                              if kind == "check_issue_state" else {"issue": issue})
    tid = await deps.queue.enqueue(kind=kind, project_id="acme", payload={}, params=params,
                                   reason="you asked", context=COMMISSIONED)
    assert tid is not None
    await deps.db.update("tasks", tid, {"parent_task_id": parent})
    task = await deps.queue.claim(tid)
    assert task is not None
    return task


async def test_the_first_check_of_a_commitment_reports_back_in_the_thread(deps: Deps) -> None:
    """A watch nobody can tell is running is one they stop believing in."""
    await wire(deps, kind="check_issue_state", params={"issue": "INV-143", "expect": ["Todo"]})
    task = await commissioned(deps, parent="intake-1")

    out = await run_check(task, deps)

    assert out.result["met"] is True and len(out.result["acted"]) == 1
    note = deps.slack.posts[0]
    assert note["channel"] == "C-random" and note["thread_ts"] == "1787821201.000100"
    assert note["text"] == (
        "First look at <https://linear.app/acme/issue/INV-143|INV-143> (the reminders to 3 days)"
        ": it's in Todo — I'll keep watching quietly and only speak up if that changes."
    )


async def test_after_the_first_look_a_met_check_says_nothing(deps: Deps) -> None:
    await wire(deps, kind="check_issue_state", params={"issue": "INV-143", "expect": ["Todo"]})
    first = await commissioned(deps, parent="intake-1")
    await run_check(first, deps)
    await deps.db.update("tasks", first["id"], {"status": "done"})

    second = await commissioned(deps, parent="intake-1", kind="check_pr_exists")
    out = await run_check(second, deps)

    assert out.result["acted"] == []
    assert len(deps.slack.posts) == 1, "the watch goes quiet after it has been seen working"


async def test_a_check_nobody_asked_for_never_reports_a_first_look(deps: Deps) -> None:
    task = await wire(deps, kind="check_issue_state",
                      params={"issue": "INV-143", "expect": ["Todo"]})

    out = await run_check(task, deps)

    assert out.result["met"] is True and out.result["acted"] == []
    assert deps.slack.posts == []


async def test_the_first_look_is_sent_once_however_often_the_check_reruns(deps: Deps) -> None:
    await wire(deps, kind="check_issue_state", params={"issue": "INV-143", "expect": ["Todo"]})
    task = await commissioned(deps, parent="intake-1")

    await run_check(task, deps)
    await run_check(task, deps)

    assert len(deps.slack.posts) == 1


async def test_the_first_look_obeys_quiet_hours_and_the_daily_budget(deps: Deps) -> None:
    deps.clock.advance(hours=12)  # 21:00, inside the project's quiet hours
    await wire(deps, kind="check_issue_state", params={"issue": "INV-143", "expect": ["Todo"]})
    task = await commissioned(deps, parent="intake-1")

    out = await run_check(task, deps)

    assert out.result["acted"] == [] and deps.slack.posts == []


# --- work that finished before the check ran --------------------------------------------------

DONE_ISSUE = {**ISSUE, "state": "Done"}


async def test_a_check_never_chases_a_pull_request_for_finished_work(deps: Deps) -> None:
    """An engineer marks INV-143 Done without a branch that names it. Asking "where is the
    pull request?" the next morning reads as the agent not having noticed."""
    task = await wire(deps, kind="check_pr_exists", params={"issue": "INV-143"},
                      on_unmet="nudge_assignee", issues=[DONE_ISSUE], prs=[])

    met, observed = await CHECKS["check_pr_exists"](task, deps)

    assert met is True
    assert observed["moot"] is True
    assert observed["reason"] == "issue is done"


async def test_a_moot_check_sends_nobody_anything(deps: Deps) -> None:
    task = await wire(deps, kind="check_pr_exists", params={"issue": "INV-143"},
                      on_unmet="nudge_assignee", issues=[DONE_ISSUE], prs=[])

    out = await run_check(task, deps)

    assert out.result["met"] is True
    assert not out.result.get("acted"), "no nudge about work that is finished"
    assert deps.slack.posts == []


async def test_work_still_in_flight_is_chased_exactly_as_before(deps: Deps) -> None:
    """The moot rule must not become a way to stop checking."""
    task = await wire(deps, kind="check_pr_exists", params={"issue": "INV-143"},
                      on_unmet="nudge_assignee", issues=[{**ISSUE, "state": "In Progress"}],
                      prs=[])

    met, observed = await CHECKS["check_pr_exists"](task, deps)

    assert met is False
    assert "moot" not in observed


async def test_a_tracker_that_cannot_answer_changes_nothing(deps: Deps) -> None:
    """An outage is not evidence the work is done."""
    class Down(FakeLinear):
        async def get_issue(self, identifier: str) -> dict[str, Any] | None:
            raise SourceUnavailable("linear", "502")

    task = await wire(deps, kind="check_pr_exists", params={"issue": "INV-143"}, prs=[])
    deps.linear = Down(issues=[DONE_ISSUE])

    met, observed = await CHECKS["check_pr_exists"](task, deps)

    assert met is False
    assert "moot" not in observed


async def test_asking_whether_finished_work_has_started_is_moot_too(deps: Deps) -> None:
    task = await wire(deps, kind="check_issue_state",
                      params={"issue": "INV-143", "expect": ["In Progress"]},
                      on_unmet="nudge_assignee", issues=[DONE_ISSUE])

    met, observed = await CHECKS["check_issue_state"](task, deps)

    assert met is True and observed["moot"] is True


async def test_a_check_that_was_waiting_for_done_is_a_success_not_a_moot(deps: Deps) -> None:
    """It got what it asked for. Calling that moot would hide the agent's own win."""
    task = await wire(deps, kind="check_issue_state",
                      params={"issue": "INV-143", "expect": ["Done"]}, issues=[DONE_ISSUE])

    met, observed = await CHECKS["check_issue_state"](task, deps)

    assert met is True
    assert "moot" not in observed

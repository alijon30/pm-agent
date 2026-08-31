"""intake is the one stage a person starts, so these tests are about what they are owed: a
dated commitment they can hold the agent to, a plain refusal, or their work stopped when they
ask — and never silence."""

from typing import Any

import pytest
from app.harness.core.errors import PmError, SourceUnavailable
from app.harness.deps import Deps
from app.harness.stages.intake import commission, commissioned_by, run
from app.harness.store.actions import ActionStore
from app.harness.store.db import Doc
from app.harness.store.wiki import WikiStore
from app.harness.verify.ids import IdGate

from tests.conftest import ACME
from tests.fakes.fake_agents import FakeSteward
from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_slack import FakeSlack

PROJECT = {**ACME, "slack_channel_id": "C-product"}
ISSUE = {"id": "u-26", "identifier": "INV-26", "title": "CSV export behind the flag",
         "description": "", "state": "Todo", "priority": 2,
         "assignee": {"id": "u-priya", "name": "Priya Nair"}, "due_date": "2026-09-04",
         "url": "https://linear.app/acme/issue/INV-26", "updated_at": ""}

COMMITMENT = {
    "tasks": [
        {"key": "started", "kind": "check_issue_state",
         "params": {"issue": "INV-26", "expect": ["In Progress", "Done"]},
         "due": "2026-09-01T16:00:00Z", "depends_on": [],
         "reason": "you asked me to tell you if the CSV export has not started",
         "on_unmet": "ping_requester", "on_dep_failed": "skip", "context": {}},
        {"key": "pr", "kind": "check_pr_exists", "params": {"issue": "INV-26"},
         "due": "2026-09-03T16:00:00Z", "depends_on": ["started"],
         "reason": "and whether a pull request shows up", "on_unmet": "none",
         "on_dep_failed": "skip", "context": {}},
    ],
    "supersedes": [],
    "notes": "I'll watch INV-26 and tell you if it slips.",
}
REFUSAL = {
    "tasks": [], "supersedes": [],
    "notes": "I can watch issues, look for pull requests and reviews, schedule nudges and write "
             "status reports — I can't reassign work in Linear.",
}
GHOST = {
    "tasks": [{"key": "ghost", "kind": "check_issue_state",
               "params": {"issue": "INV-999", "expect": ["Done"]},
               "due": "2026-09-01T16:00:00Z", "depends_on": [], "reason": "watch a phantom",
               "on_unmet": "none", "on_dep_failed": "skip", "context": {}}],
    "supersedes": [], "notes": "",
}


async def wire(
    deps: Deps,
    *,
    steward_results: list[dict[str, Any]],
    params: dict[str, Any] | None = None,
    requester: str = "U-maya",
    users: dict[str, dict[str, Any]] | None = None,
) -> Doc:
    """A claimed intake task, as the Slack route would have queued it."""
    await deps.projects.upsert("acme", PROJECT)
    deps.actions = ActionStore(deps.db, deps.clock)
    deps.slack = FakeSlack(users=users if users is not None else {
        "U-maya": {"id": "U-maya", "name": "Maya Chen", "email": "maya@acme-invoicing.test"}})
    deps.linear = FakeLinear(issues=[ISSUE])
    deps.steward = FakeSteward(steward_results)
    deps.ids = IdGate(linear=deps.linear, roster=ACME["roster"])

    tid = await deps.queue.enqueue(
        kind="intake", project_id="acme",
        params=params if params is not None else {"text": "keep an eye on INV-26 for me please"},
        payload={"channel": "C-random", "thread_ts": "1787821201.000100",
                 "requester": requester},
        reason="a teammate asked for something in Slack", root_event_id="slack:Ev1")
    assert tid is not None
    task = await deps.queue.claim(tid)
    assert task is not None
    return task


# --- stamping the requester onto the work -------------------------------------------------------

def test_who_asked_and_where_travels_with_every_task_the_request_produces() -> None:
    task = {"payload": {"requester": "U-maya", "channel": "C-random", "thread_ts": "1.1"}}
    assert commissioned_by(task) == {
        "requester_slack_id": "U-maya", "request_channel": "C-random", "request_ts": "1.1"}


def test_a_check_nobody_chose_an_action_for_answers_the_person_who_asked() -> None:
    accepted = [
        {"key": "a", "kind": "check_pr_exists", "on_unmet": "none", "context": {"issue": "INV-26"}},
        {"key": "b", "kind": "check_issue_state", "on_unmet": "nudge_assignee", "context": {}},
        {"key": "c", "kind": "nudge", "on_unmet": "none", "context": {}},
    ]
    out = commission(accepted, {"payload": {"requester": "U-maya", "channel": "C1",
                                            "thread_ts": "1.1"}})

    assert [t["on_unmet"] for t in out] == ["ping_requester", "nudge_assignee", "none"]
    assert out[0]["context"] == {"issue": "INV-26", "requester_slack_id": "U-maya",
                                 "request_channel": "C1", "request_ts": "1.1"}


# --- a request the agent can keep ---------------------------------------------------------------

async def test_a_request_becomes_dated_checks_that_carry_who_asked(deps: Deps) -> None:
    task = await wire(deps, steward_results=[COMMITMENT])
    out = await run(task, deps)

    assert out.result["accepted"] == ["started", "pr"]
    assert out.result["bounced"] is False and out.result["replied"] is True
    assert [c["kind"] for c in out.children] == ["check_issue_state", "check_pr_exists"]
    for child in out.children:
        assert child["context"]["requester_slack_id"] == "U-maya"
        assert child["context"]["request_channel"] == "C-random"
        assert child["context"]["request_ts"] == "1787821201.000100"
    assert out.children[1]["on_unmet"] == "ping_requester"  # the steward said "none"


async def test_the_commitment_is_posted_in_the_thread_that_asked_for_it(deps: Deps) -> None:
    task = await wire(deps, steward_results=[COMMITMENT])
    await run(task, deps)

    assert len(deps.slack.posts) == 1
    reply = deps.slack.posts[0]
    assert reply["channel"] == "C-random" and reply["thread_ts"] == "1787821201.000100"
    rendered = str(reply["blocks"])
    assert "Got it — I'll watch INV-26 for you:" in rendered
    assert "Tuesday — check that INV-26 is underway _(if not, I'll let you know)_" in rendered
    assert "look for a pull request on INV-26" in rendered
    assert "I'll watch INV-26 and tell you if it slips." in rendered


async def test_a_kept_promise_is_acknowledged_on_the_message_that_asked(deps: Deps) -> None:
    task = await wire(deps, steward_results=[COMMITMENT])
    await run(task, deps)

    assert deps.slack.reactions == [
        {"channel": "C-random", "ts": "1787821201.000100", "name": "handshake"}]


async def test_the_reply_is_recorded_as_an_action_with_a_way_to_undo_it(deps: Deps) -> None:
    task = await wire(deps, steward_results=[COMMITMENT])
    await run(task, deps)

    posts = await deps.db.query("actions", [("kind", "==", "slack.post")])
    assert len(posts) == 1 and posts[0]["status"] == "done"
    assert posts[0]["revert"]["op"] == "edit_message"
    assert posts[0]["inputs"]["committed"] == 2


async def test_the_steward_is_told_who_asked_what_is_already_watched_and_what_it_can_do(
    deps: Deps,
) -> None:
    task = await wire(deps, steward_results=[COMMITMENT])
    await deps.queue.enqueue(kind="check_issue_state", project_id="acme", payload={},
                             params={"issue": "INV-26", "expect": ["Done"]}, reason="already")
    await run(task, deps)

    sent = deps.steward.calls[0]
    assert sent["request"] == "keep an eye on INV-26 for me please"
    assert sent["requester_name"] == "Maya Chen"
    assert sent["today"] == "2026-08-27"
    assert [t["params"]["issue"] for t in sent["open_tasks"]] == ["INV-26"]
    assert {row["kind"] for row in sent["catalog"]} >= {"check_issue_state", "nudge"}
    assert "intake" not in {row["kind"] for row in sent["catalog"]}
    assert sent["feedback"] is None


async def test_a_requester_slack_cannot_name_is_still_served(deps: Deps) -> None:
    task = await wire(deps, steward_results=[COMMITMENT], users={})
    await run(task, deps)

    assert deps.steward.calls[0]["requester_name"] == "you"


# --- a request the agent cannot keep ------------------------------------------------------------

async def test_a_request_outside_the_catalog_is_refused_in_one_sentence(deps: Deps) -> None:
    task = await wire(deps, steward_results=[REFUSAL],
                      params={"text": "please reassign INV-26 to me"})
    out = await run(task, deps)

    assert out.children == [] and out.result["accepted"] == []
    assert out.result["replied"] is True
    reply = deps.slack.posts[0]
    assert reply["thread_ts"] == "1787821201.000100"
    assert "I can't reassign work in Linear." in str(reply["blocks"])
    assert deps.slack.reactions == []  # nothing was committed, so nothing is shaken on


async def test_a_promise_about_an_issue_that_does_not_exist_is_bounced_then_dropped(
    deps: Deps,
) -> None:
    task = await wire(deps, steward_results=[GHOST, GHOST])
    out = await run(task, deps)

    assert out.result["bounced"] is True and out.children == []
    assert len(deps.steward.calls) == 2
    assert "INV-999" in (deps.steward.calls[1]["feedback"] or "")


async def test_a_steward_that_corrects_itself_on_the_bounce_keeps_the_commitment(
    deps: Deps,
) -> None:
    task = await wire(deps, steward_results=[GHOST, COMMITMENT])
    out = await run(task, deps)

    assert out.result["bounced"] is True
    assert [c["kind"] for c in out.children] == ["check_issue_state", "check_pr_exists"]


async def test_a_slack_outage_loses_the_reply_not_the_commitment(deps: Deps) -> None:
    task = await wire(deps, steward_results=[COMMITMENT])

    async def down(*args: Any, **kwargs: Any) -> str:
        raise SourceUnavailable("slack", "ratelimited")

    deps.slack.post = down  # type: ignore[method-assign]
    out = await run(task, deps)

    assert len(out.children) == 2 and out.result["replied"] is False


# --- stopping what was asked for -----------------------------------------------------------------

async def commissioned_check(deps: Deps, *, issue: str = "INV-26",
                             requester: str = "U-maya") -> str:
    tid = await deps.queue.enqueue(
        kind="check_issue_state", project_id="acme", payload={},
        params={"issue": issue, "expect": ["Done"]}, reason="you asked",
        context={"requester_slack_id": requester, "request_channel": "C-random",
                 "request_ts": "1787821201.000100"})
    assert tid is not None
    return tid


async def test_stopping_cancels_the_checks_that_person_asked_for(deps: Deps) -> None:
    task = await wire(deps, steward_results=[], params={"cancel": "INV-26"})
    mine = await commissioned_check(deps)
    out = await run(task, deps)

    assert out.result["cancelled"] == [mine]
    assert (await deps.db.get("tasks", mine) or {})["status"] == "cancelled"
    assert "Done — I've stopped watching INV-26." in deps.slack.posts[0]["text"]
    assert deps.slack.posts[0]["thread_ts"] == "1787821201.000100"


async def test_stopping_leaves_alone_what_somebody_else_asked_for(deps: Deps) -> None:
    task = await wire(deps, steward_results=[], params={"cancel": "INV-26"})
    theirs = await commissioned_check(deps, requester="U-nodir")
    unrequested = await deps.queue.enqueue(
        kind="check_pr_exists", project_id="acme", payload={}, params={"issue": "INV-26"},
        reason="the agent's own follow-through")
    out = await run(task, deps)

    assert out.result["cancelled"] == []
    assert (await deps.db.get("tasks", theirs) or {})["status"] == "queued"
    assert (await deps.db.get("tasks", unrequested) or {})["status"] == "queued"
    assert "I'm not watching anything on INV-26 for you" in deps.slack.posts[0]["text"]


async def test_stopping_takes_the_checks_that_were_waiting_on_it_too(deps: Deps) -> None:
    task = await wire(deps, steward_results=[], params={"cancel": "INV-26"})
    first = await commissioned_check(deps)
    dependent = await deps.queue.enqueue(
        kind="check_pr_exists", project_id="acme", payload={}, params={"issue": "INV-26"},
        reason="after that", depends_on=[first])
    out = await run(task, deps)

    assert set(out.result["cancelled"]) == {first, dependent}
    assert "Done — I've stopped watching INV-26." in deps.slack.posts[0]["text"]


# --- failing closed ------------------------------------------------------------------------------

async def test_an_intake_carrying_neither_a_request_nor_an_identifier_is_a_bug(
    deps: Deps,
) -> None:
    task = await wire(deps, steward_results=[], params={})

    with pytest.raises(PmError):
        await run(task, deps)


async def test_with_no_steward_configured_the_stage_refuses_rather_than_guessing(
    deps: Deps,
) -> None:
    task = await wire(deps, steward_results=[])
    deps.steward = None

    with pytest.raises(PmError):
        await run(task, deps)


async def test_what_the_agent_learned_about_itself_reaches_the_steward(deps: Deps) -> None:
    from app.harness.store.lessons import LessonStore

    task = await wire(deps, steward_results=[COMMITMENT])
    deps.lessons = LessonStore(deps.db, deps.clock)
    await deps.lessons.add(project_id="acme", text="Ask before Friday afternoon, not after.",
                           evidence=["task:t-1"])
    await run(task, deps)

    assert deps.steward.calls[0]["lessons"] == ["Ask before Friday afternoon, not after."]


# --- being told how to work -------------------------------------------------------------------

OWNERSHIP = {"tasks": [], "supersedes": [], "notes": "",
             "memory": {"kind": "ownership", "subject": ["billing", "statements"],
                        "person": "Nodir Rahimov",
                        "text": "Billing and statements go to Nodir"}}
PREFERENCE = {"tasks": [], "supersedes": [], "notes": "",
              "memory": {"kind": "preference", "subject": ["nudge"], "person": None,
                         "text": "never nudge anyone before ten"}}
STRANGER = {"tasks": [], "supersedes": [], "notes": "",
            "memory": {"kind": "ownership", "subject": ["billing"], "person": "Dave",
                       "text": "Billing goes to Dave"}}


def brain_of(deps: Deps) -> WikiStore:
    assert deps.wiki is not None
    return deps.wiki


async def with_brain(deps: Deps, **kwargs: Any) -> Doc:
    task = await wire(deps, **kwargs)
    deps.wiki = WikiStore(deps.db, deps.clock)
    return task


async def test_an_instruction_is_remembered_rather_than_scheduled(deps: Deps) -> None:
    task = await with_brain(deps, steward_results=[OWNERSHIP],
                            params={"text": "from now on assign billing to Nodir",
                                    "instruct": True})

    out = await run(task, deps)

    assert out.children == [], "a rule is not a check"
    assert out.result["remembered"]["person"] == "Nodir Rahimov"
    found = await brain_of(deps).relevant("acme", "the statements page", kinds=("ownership",))
    assert [e["person"] for e in found] == ["Nodir Rahimov"]


async def test_it_says_back_what_it_will_do_from_now_on(deps: Deps) -> None:
    task = await with_brain(deps, steward_results=[OWNERSHIP],
                            params={"text": "assign billing to Nodir", "instruct": True})

    out = await run(task, deps)

    assert out.result["notes"] == "Noted — billing statements go to Nodir from now on."
    assert deps.slack.posts, "and says it in the thread"


async def test_a_preference_is_said_back_in_their_own_words(deps: Deps) -> None:
    task = await with_brain(deps, steward_results=[PREFERENCE],
                            params={"text": "never nudge before ten", "instruct": True})

    out = await run(task, deps)

    assert out.result["notes"] == "Noted — from now on: never nudge anyone before ten."


async def test_an_owner_who_is_not_on_the_roster_is_refused_and_nothing_is_stored(
    deps: Deps,
) -> None:
    """A name the agent invented would be handed back to the team for weeks as though they
    had chosen it."""
    task = await with_brain(deps, steward_results=[STRANGER],
                            params={"text": "assign billing to Dave", "instruct": True})

    out = await run(task, deps)

    assert out.result["remembered"] is None
    assert out.result["notes"] == "I don't know a Dave on this project — who did you mean?"
    assert await brain_of(deps).pages("acme") == []


async def test_the_same_instruction_twice_is_remembered_once(deps: Deps) -> None:
    task = await with_brain(deps, steward_results=[OWNERSHIP],
                            params={"text": "assign billing to Nodir", "instruct": True})
    await run(task, deps)

    again = await deps.queue.enqueue(
        kind="intake", project_id="acme", params={"text": "assign billing to Nodir"},
        payload={"channel": "C-random", "thread_ts": "1787821201.000100",
                 "requester": "U-maya"},
        reason="again", root_event_id="slack:Ev1")
    assert again is not None
    claimed = await deps.queue.claim(again)
    assert claimed is not None
    deps.steward = FakeSteward([OWNERSHIP])
    await run(claimed, deps)

    pages = await brain_of(deps).pages("acme")
    assert len(pages[0]["entries"]) == 1, "one memory, not one per telling"


async def test_the_steward_is_shown_what_it_has_already_been_told(deps: Deps) -> None:
    task = await with_brain(deps, steward_results=[OWNERSHIP],
                            params={"text": "assign billing to Nodir", "instruct": True})
    await run(task, deps)

    later = await deps.queue.enqueue(
        kind="intake", project_id="acme", params={"text": "who owns billing statements?"},
        payload={"channel": "C-random", "thread_ts": "2.0", "requester": "U-maya"},
        reason="asked", root_event_id="slack:Ev2")
    assert later is not None
    claimed = await deps.queue.claim(later)
    assert claimed is not None
    fake = FakeSteward([{"tasks": [], "supersedes": [], "notes": "", "memory": None}])
    deps.steward = fake
    await run(claimed, deps)

    brain = fake.calls[0]["brain"]
    assert [e["text"] for e in brain] == ["Billing and statements go to Nodir"]
    assert brain[0]["ref"].startswith("wiki:ownership#")


async def test_the_answer_edits_the_on_it_ack_instead_of_posting_again(deps: Deps) -> None:
    """The events route leaves "✻ On it…" in the thread; the reply becomes that message.
    One message that fills itself in — the same shape as a call summary."""
    task = await wire(deps, steward_results=[COMMITMENT])
    task["payload"]["ack"] = {"channel": "C-random", "ts": "42.000100"}

    out = await run(task, deps)

    assert out.result["replied"] is True
    assert deps.slack.posts == [], "the ack is already there; nothing new is posted"
    assert deps.slack.updates[-1]["ts"] == "42.000100"
    assert "watch INV-26" in deps.slack.updates[-1]["text"]

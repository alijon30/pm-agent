"""act is the only stage that changes anything outside this system, so these tests are about
what it refuses to do as much as what it does."""

from typing import Any

from app.harness.deps import Deps
from app.harness.stages.act import build_description, decide, run
from app.harness.store.actions import ActionStore
from app.harness.store.db import Doc

from tests.conftest import ACME
from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_slack import FakeSlack

MEETING = {"id": "8841201", "title": "Q3 Billing planning", "url": "https://f.video/abc"}

ITEM = {
    "index": 0,
    "title": "Move payment reminders to 3 days",
    "description": "Decided in the Q3 planning call.",
    "disposition": "new",
    "target_issue": None,
    "owner": "Nodir Rahimov",
    "priority": 3,
    "due": "2026-09-04",
    "due_hint": "next Friday",
    "citations": ["fathom:8841201@00:01:58"],
    "conflicts": [{"kind": "code_vs_spec", "about": "reminder window", "sides": [
        {"claim": "7 days", "source": "code:acme/config.py:6"},
        {"claim": "5 days", "source": "notion:page-prd"}]}],
    "facts": [],
    "quotes": ["I can have that done by next Friday"],
}

PROJECT = {
    **ACME,
    "id": "acme",
    "linear_team_id": "team-1",
    "linear_project_id": "proj-1",
    "slack_channel_id": "C-product",
    "roster": [
        {**m, "linear_user_id": f"u-{m['name'].split()[0].lower()}"} for m in ACME["roster"]
    ],
    "policy": {**ACME["policy"], "priority_band": [2, 4],
               # The shipped list, verbatim from fixtures/projects/acme.json: a gate tested
               # against a narrower policy than production runs is a gate tested on nothing.
               "escalation_phrases": ["urgent", "blocker", "blocked", "p0", "asap"],
               "daily_write_cap": 40,
               "daily_ping_cap": 10, "quiet_hours": ["20:00", "08:00"]},
}


async def wire(deps: Deps, *, items: list[dict[str, Any]],
               unverified: list[dict[str, Any]] | None = None,
               issues: list[dict[str, Any]] | None = None) -> Doc:
    """A finished reconcile task, the act task after it (claimed), and live fakes on deps."""
    await deps.projects.upsert("acme", PROJECT)
    deps.actions = ActionStore(deps.db, deps.clock)
    deps.linear = FakeLinear(
        issues=issues or [{"id": "u-104", "identifier": "INV-104", "title": "Overdue dashboard",
                           "description": "", "state": "Backlog", "priority": 4, "assignee": None,
                           "due_date": None, "url": "", "updated_at": ""}],
        members=[{"id": f"u-{m['name'].split()[0].lower()}", "name": m["name"], "email": ""}
                 for m in ACME["roster"]],
    )
    deps.slack = FakeSlack()
    event_id = await deps.events.record(provider="fathom", provider_event_id="msg_1",
                                        payload={}, project_id="acme")
    rec_id = await deps.queue.enqueue(kind="reconcile", project_id="acme", payload={},
                                      reason="t", root_event_id=event_id)
    assert rec_id is not None
    await deps.db.update("tasks", rec_id, {"status": "done", "result": {
        "meeting": MEETING, "items": items, "unverified": unverified or [],
        "decision_conflicts": [], "decision_ids": ["dec-1"], "bounced": False}})
    tid = await deps.queue.enqueue(kind="act", project_id="acme",
                                   payload={"event_id": event_id, "reconcile_task_id": rec_id},
                                   reason="t", root_event_id=event_id)
    assert tid is not None
    task = await deps.queue.claim(tid)
    assert task is not None
    return task


# --- the decision, before anything is written -------------------------------------------------

def test_a_roster_owner_a_banded_priority_and_a_spoken_date_all_pass_through() -> None:
    decided = decide(ITEM, PROJECT)
    assert (decided["owner"] or {})["name"] == "Nodir Rahimov"
    assert decided["priority"] == 3 and decided["due"] == "2026-09-04"
    assert decided["notes"] == []
    assert decided["checks_passed"] == ["roster", "priority", "dates"]


def test_an_owner_who_is_not_on_the_project_is_dropped_and_named() -> None:
    decided = decide({**ITEM, "owner": "Sam"}, PROJECT)
    assert decided["owner"] is None
    assert "'Sam' — not on this project's roster" in decided["notes"][0]


def test_urgent_without_the_words_is_clamped_and_the_reason_is_recorded() -> None:
    decided = decide({**ITEM, "priority": 1}, PROJECT)
    assert decided["priority"] == 2
    assert any("nobody said this was urgent" in n for n in decided["notes"])


def test_urgent_survives_when_someone_actually_said_it() -> None:
    escalated = {**ITEM, "priority": 1, "quotes": ["This is urgent, a customer is blocked."]}
    assert decide(escalated, PROJECT)["priority"] == 1


def test_a_date_nobody_spoke_never_becomes_a_commitment() -> None:
    decided = decide({**ITEM, "due_hint": "by tomorrow"}, PROJECT)
    assert decided["due"] is None
    assert any("was not spoken" in n for n in decided["notes"])


def test_the_description_shows_the_quote_the_conflict_and_what_was_checked() -> None:
    body = build_description(ITEM, MEETING, "key-abc", ["owner not on the roster"])
    assert "> I can have that done by next Friday" in body
    assert "Sources disagree** on reminder window" in body
    assert "`code:acme/config.py:6`" in body and "`notion:page-prd`" in body
    assert "`fathom:8841201@00:01:58`" in body
    assert "_owner not on the roster_" in body
    assert "<!-- pm-agent:key-abc -->" in body


# --- the writes -------------------------------------------------------------------------------

async def test_a_verified_item_becomes_one_cited_assigned_issue(deps: Deps) -> None:
    task = await wire(deps, items=[ITEM])
    out = await run(task, deps)

    assert [c["identifier"] for c in out.result["created"]] == ["INV-105"]
    assert out.result["created"][0]["owner"] == "Nodir Rahimov"
    write = deps.linear.writes[0]
    assert write["op"] == "create" and write["assignee_id"] == "u-nodir"
    assert write["priority"] == 3 and write["due_date"] == "2026-09-04"
    assert "pm-agent:" in write["description"]

    action = (await deps.actions.list_since("acme", "2026-01-01T00:00:00+00:00"))[0]
    assert action["status"] == "done" and action["kind"] == "linear.create_issue"
    assert action["revert"] == {"op": "archive", "issue": "INV-105"}
    assert action["checks_passed"] == ["roster", "priority", "dates"]


async def test_an_update_comments_on_the_existing_issue_instead_of_filing_another(
    deps: Deps,
) -> None:
    updating = {**ITEM, "disposition": "update", "target_issue": "INV-104"}
    task = await wire(deps, items=[updating])
    out = await run(task, deps)

    assert out.result["created"] == []
    assert [u["identifier"] for u in out.result["updated"]] == ["INV-104"]
    assert deps.linear.writes[0]["op"] == "comment"
    action = (await deps.actions.list_since("acme", "2026-01-01T00:00:00+00:00"))[0]
    assert action["revert"]["op"] == "delete_comment"


async def test_a_crashed_run_does_not_file_the_same_issue_twice(deps: Deps) -> None:
    task = await wire(deps, items=[ITEM])
    await run(task, deps)
    writes_after_first = len(deps.linear.writes)

    # The process died before the task was marked done; the queue hands it back.
    again = await run(task, deps)
    assert len(deps.linear.writes) == writes_after_first
    assert again.result["created"][0]["identifier"] == "INV-105"


async def test_items_that_never_verified_are_reported_as_skipped_not_filed(deps: Deps) -> None:
    task = await wire(deps, items=[], unverified=[
        {"title": "Ship SMS reminders", "gate_reason": "unknown identifier(s): linear:INV-999"}])
    out = await run(task, deps)
    assert out.result["created"] == [] and deps.linear.writes == []
    assert out.result["skipped"][0]["reason"] == "unknown identifier(s): linear:INV-999"


async def test_the_daily_write_cap_stops_the_remainder_and_keeps_what_was_written(
    deps: Deps,
) -> None:
    project = {**PROJECT, "policy": {**PROJECT["policy"], "daily_write_cap": 1}}
    task = await wire(deps, items=[ITEM, {**ITEM, "index": 1, "title": "Second thing"}])
    await deps.projects.upsert("acme", project)
    out = await run(task, deps)

    assert len(out.result["created"]) == 1
    assert out.result["skipped"][0]["title"] == "Second thing"
    assert "daily write cap reached" in out.result["skipped"][0]["reason"]


async def test_a_tracker_outage_fails_that_item_alone_and_the_others_still_land(
    deps: Deps,
) -> None:
    from app.harness.core.errors import SourceUnavailable

    task = await wire(deps, items=[ITEM, {**ITEM, "index": 1, "title": "Second thing"}])
    real_create = deps.linear.create_issue
    calls = {"n": 0}

    async def flaky(**kwargs: Any) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise SourceUnavailable("linear", "HTTP 503")
        return await real_create(**kwargs)

    deps.linear.create_issue = flaky  # type: ignore[method-assign]
    out = await run(task, deps)

    assert len(out.result["created"]) == 1
    assert out.result["skipped"][0]["reason"] == "linear unavailable: HTTP 503"


# --- a spoken emergency, all the way to the tracker -----------------------------------------------

# The two halves of an escalation as a call actually delivers them: one person says it is on
# fire, another says who will fix it, a minute apart. The extractor is told to attach both to
# the item, which is the only reason the priority gate can find the words later.
ON_FIRE = "Honestly this is a blocker, customers are getting spammed"
WHO_FIXES = "Nodir, can you own the duplicate reminder emails bug?"

URGENT_ITEM = {
    **ITEM,
    "title": "Fix the duplicate reminder emails",
    "priority": 1,
    "due": None,
    "due_hint": None,
    "quotes": [ON_FIRE, WHO_FIXES],
}


async def test_a_spoken_emergency_reaches_linear_as_priority_one(deps: Deps) -> None:
    task = await wire(deps, items=[URGENT_ITEM])
    out = await run(task, deps)

    assert len(out.result["created"]) == 1
    write = deps.linear.writes[0]
    assert write["op"] == "create" and write["priority"] == 1

    assert deps.actions is not None
    action = await deps.actions.get(out.result["action_ids"][0])
    assert action is not None
    assert action["inputs"]["priority"] == 1
    assert "priority" in action["checks_passed"]


async def test_the_same_urgency_with_nobody_saying_it_is_clamped_to_the_band(
    deps: Deps,
) -> None:
    """Identical item, identical claim — only the spoken words are missing. The band holds."""
    unspoken = {**URGENT_ITEM, "quotes": [WHO_FIXES]}
    task = await wire(deps, items=[unspoken])
    await run(task, deps)

    assert deps.linear.writes[0]["priority"] == 2  # the band's urgent edge, not 1
    # And the team is told why, in the channel and in the issue body.
    rendered = str(deps.slack.posts[0]["blocks"])
    assert "clamped to 2" in rendered and "nobody said this was urgent" in rendered
    assert "nobody said this was urgent" in deps.linear.writes[0]["description"]


def test_the_gate_reads_the_items_own_quotes_and_nothing_else() -> None:
    """Why the extractor has to attach the urgent line to the item: a priority_hint the model
    wrote is not evidence, and the gate never sees it."""
    hinted = {**URGENT_ITEM, "quotes": [WHO_FIXES], "priority_hint": ON_FIRE}
    assert decide(hinted, PROJECT)["priority"] == 2

    quoted = {**URGENT_ITEM, "quotes": [ON_FIRE, WHO_FIXES], "priority_hint": None}
    assert decide(quoted, PROJECT)["priority"] == 1


async def test_the_urgency_the_team_hears_is_the_urgency_that_was_written(deps: Deps) -> None:
    task = await wire(deps, items=[URGENT_ITEM])
    await run(task, deps)

    body = deps.linear.writes[0]["description"]
    assert ON_FIRE in body, "the words that unlocked priority 1 are in the issue"


# --- the summary ------------------------------------------------------------------------------

async def test_one_summary_is_posted_with_a_revert_button_per_write(deps: Deps) -> None:
    task = await wire(deps, items=[ITEM])
    out = await run(task, deps)

    assert len(deps.slack.posts) == 1
    post = deps.slack.posts[0]
    assert post["channel"] == "C-product"
    assert post["text"] == "Q3 Billing planning — filed 1 ticket · 1 conflict"
    actions = [b for b in post["blocks"] if b["type"] == "actions"][0]["elements"]
    assert actions[0]["action_id"].startswith("revert:")
    assert actions[-1]["action_id"].startswith("wrong:")
    assert out.result["summary_action_id"] is not None


async def test_conflicts_reach_the_team_and_are_never_resolved(deps: Deps) -> None:
    task = await wire(deps, items=[ITEM])
    out = await run(task, deps)
    assert len(out.result["conflicts"]) == 1
    rendered = str(deps.slack.posts[0]["blocks"])
    assert "Sources disagree* on reminder window" in rendered
    assert "7 days" in rendered and "5 days" in rendered
    assert "config.py:6" in rendered and "code:acme/config.py:6" not in rendered


async def test_a_slack_outage_never_undoes_work_that_already_landed(deps: Deps) -> None:
    from app.harness.core.errors import SourceUnavailable

    task = await wire(deps, items=[ITEM])

    async def down(*args: Any, **kwargs: Any) -> str:
        raise SourceUnavailable("slack", "ratelimited")

    deps.slack.post = down  # type: ignore[method-assign]
    out = await run(task, deps)

    assert len(out.result["created"]) == 1
    assert out.result["summary_action_id"] is None


async def status_message(deps: Deps, channel: str = "C-product", ts: str = "1787821200.000100",
                         event_id: str = "fathom:msg_1") -> dict[str, str]:
    """The 'reading the call…' message the webhook left behind for this call."""
    message = {"channel": channel, "ts": ts}
    await deps.db.update("events", event_id, {"status_message": message})
    return message


async def test_the_summary_edits_the_message_that_said_it_was_reading_the_call(
    deps: Deps,
) -> None:
    task = await wire(deps, items=[ITEM])
    message = await status_message(deps)
    await run(task, deps)

    assert deps.slack.posts == []  # no second message: Slack notifies nobody for an edit
    assert len(deps.slack.updates) == 1
    edit = deps.slack.updates[0]
    assert edit["channel"] == message["channel"] and edit["ts"] == message["ts"]
    assert edit["text"] == "Q3 Billing planning — filed 1 ticket · 1 conflict"
    assert [b for b in edit["blocks"] if b["type"] == "actions"], "the buttons survive the edit"


async def test_the_recorded_action_points_at_the_message_it_edited(deps: Deps) -> None:
    task = await wire(deps, items=[ITEM])
    message = await status_message(deps)
    out = await run(task, deps)

    assert deps.actions is not None
    action = await deps.actions.get(out.result["summary_action_id"])
    assert action is not None and action["status"] == "done"
    assert action["target_ids"] == message
    assert action["revert"] == {"op": "edit_message", **message}
    assert action["inputs"]["edited"] is True


async def test_a_call_with_no_status_message_posts_a_fresh_summary(deps: Deps) -> None:
    task = await wire(deps, items=[ITEM])
    out = await run(task, deps)

    assert len(deps.slack.posts) == 1 and deps.slack.updates == []
    assert deps.actions is not None
    action = await deps.actions.get(out.result["summary_action_id"])
    assert action is not None and action["inputs"]["edited"] is False
    assert action["revert"]["ts"] == deps.slack.posts[0]["ts"]


async def test_a_replayed_root_still_finds_the_original_calls_status_message(
    deps: Deps,
) -> None:
    task = await wire(deps, items=[ITEM])
    message = await status_message(deps)
    task["root_event_id"] = "fathom:msg_1#retry1"
    await run(task, deps)

    assert deps.slack.posts == []
    assert deps.slack.updates[0]["ts"] == message["ts"]


async def test_an_outage_while_editing_leaves_the_work_and_records_the_failure(
    deps: Deps,
) -> None:
    from app.harness.core.errors import SourceUnavailable

    task = await wire(deps, items=[ITEM])
    await status_message(deps)

    async def down(*args: Any, **kwargs: Any) -> None:
        raise SourceUnavailable("slack", "ratelimited")

    deps.slack.update = down  # type: ignore[method-assign]
    out = await run(task, deps)

    assert len(out.result["created"]) == 1
    assert out.result["summary_action_id"] is None
    failed = await deps.db.query("actions", [("kind", "==", "slack.post")])
    assert failed[0]["status"] == "failed"


# --- what happens next ------------------------------------------------------------------------

async def test_act_hands_the_planner_what_it_just_filed(deps: Deps) -> None:
    task = await wire(deps, items=[ITEM])
    out = await run(task, deps)

    assert [c["kind"] for c in out.children] == ["plan"]
    context = out.children[0]["context"]
    assert context["created"][0]["identifier"] == "INV-105"
    assert context["items"][0] == {"identifier": "INV-105", "owner": "Nodir Rahimov",
                                   "due": "2026-09-04"}
    assert context["decision_ids"] == ["dec-1"]


async def test_a_call_that_produced_nothing_plans_nothing(deps: Deps) -> None:
    task = await wire(deps, items=[])
    out = await run(task, deps)
    assert out.children == []
    assert len(deps.slack.posts) == 1  # the team still hears that nothing was filed


def test_the_same_disagreement_reported_twice_reaches_the_team_once() -> None:
    from app.harness.stages.act import dedupe_conflicts

    code_vs_spec = {"kind": "code_vs_spec", "about": "reminder window", "sides": [
        {"claim": "7 days", "source": "code:acme/config.py:6"},
        {"claim": "5 days", "source": "notion:page-prd"}]}
    same_pair_relabelled = {**code_vs_spec, "kind": "spec_vs_call"}
    spec_vs_call = {"kind": "spec_vs_call", "about": "Reminder Window", "sides": [
        {"claim": "5 days", "source": "notion:page-prd"},
        {"claim": "3 days", "source": "fathom:8841201@00:01:42"}]}

    kept = dedupe_conflicts([code_vs_spec, spec_vs_call, code_vs_spec, same_pair_relabelled])
    assert len(kept) == 2
    assert kept[0]["kind"] == "code_vs_spec"

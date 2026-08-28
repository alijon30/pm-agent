"""The buttons on a summary. Revert is what makes acting without asking acceptable, so most of
these tests are about it working, and working exactly once."""

import hashlib
import hmac
import json
from typing import Any
from urllib.parse import urlencode

from app.harness.deps import Deps
from app.harness.store.actions import ActionStore
from app.harness.store.corrections import CorrectionStore, matcher_for
from fastapi.testclient import TestClient

from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_slack import FakeSlack

SECRET = "s3cr3t-signing"  # noqa: S105 — a test fixture
TS = 1_787_821_200  # matches conftest T0


def signed(body: bytes) -> dict[str, str]:
    base = f"v0:{TS}:".encode() + body
    digest = hmac.new(SECRET.encode(), base, hashlib.sha256).hexdigest()
    return {"x-slack-request-timestamp": str(TS), "x-slack-signature": f"v0={digest}",
            "content-type": "application/x-www-form-urlencoded"}


def interaction(payload: dict[str, Any]) -> bytes:
    return urlencode({"payload": json.dumps(payload)}).encode()


def block_action(action_id: str, user: str = "U-maya") -> dict[str, Any]:
    return {"type": "block_actions", "user": {"id": user}, "trigger_id": "trig-1",
            "actions": [{"action_id": action_id, "value": action_id.split(":", 1)[1]}]}


async def wire(deps: Deps) -> str:
    """A completed create-issue action, ready to be reverted."""
    deps.settings.slack_signing_secret = SECRET
    deps.actions = ActionStore(deps.db, deps.clock)
    deps.corrections = CorrectionStore(deps.db, deps.clock)
    deps.linear = FakeLinear(issues=[
        {"id": "u-143", "identifier": "INV-143", "title": "Move reminders", "description": "",
         "state": "Todo", "priority": 3, "assignee": None, "due_date": None, "url": "",
         "updated_at": ""}])
    deps.slack = FakeSlack()
    action_id = await deps.actions.begin(
        task_id="task-1", project_id="acme", kind="linear.create_issue",
        idempotency_key="k1", inputs={"title": "Move reminders"})
    await deps.actions.finish(action_id, target_ids={"identifier": "INV-143"},
                              revert={"op": "archive", "issue": "INV-143"})
    return action_id


# --- the door ---------------------------------------------------------------------------------

def test_an_unsigned_interaction_is_rejected(client: TestClient, deps: Deps) -> None:
    deps.settings.slack_signing_secret = SECRET
    assert client.post("/slack/interactions", content=interaction(block_action("revert:x"))
                       ).status_code == 401


def test_an_interaction_is_rejected_when_no_signing_secret_is_configured(
    client: TestClient,
) -> None:
    body = interaction(block_action("revert:x"))
    assert client.post("/slack/interactions", content=body, headers=signed(body)
                       ).status_code == 401


# --- revert -----------------------------------------------------------------------------------

async def test_revert_undoes_the_write_and_records_who_did_it(
    client: TestClient, deps: Deps
) -> None:
    action_id = await wire(deps)
    body = interaction(block_action(f"revert:{action_id}"))
    response = client.post("/slack/interactions", content=body, headers=signed(body))

    assert response.status_code == 200
    assert "reverted INV-143" in response.json()["text"]
    assert deps.linear.writes[-1] == {"op": "update", "identifier": "INV-143",
                                      "fields": {"archived": True}}
    action = await deps.actions.get(action_id)
    assert action is not None
    assert action["status"] == "reverted" and action["reverted_by"] == "U-maya"


async def test_reverting_twice_says_so_and_does_not_write_again(
    client: TestClient, deps: Deps
) -> None:
    action_id = await wire(deps)
    body = interaction(block_action(f"revert:{action_id}"))
    client.post("/slack/interactions", content=body, headers=signed(body))
    writes = len(deps.linear.writes)

    again = client.post("/slack/interactions", content=body, headers=signed(body))
    assert again.json()["text"] == "already reverted"
    assert len(deps.linear.writes) == writes


async def test_reverting_a_created_issue_cancels_the_follow_ups_that_watched_it(
    client: TestClient, deps: Deps
) -> None:
    action_id = await wire(deps)
    watching = await deps.queue.enqueue(
        kind="check_issue_state", project_id="acme", payload={}, reason="in progress?",
        params={"issue": "INV-143", "expect": ["In Progress"]})
    assert watching is not None
    dependent = await deps.queue.enqueue(
        kind="check_pr_exists", project_id="acme", payload={}, reason="pr?",
        params={"issue": "INV-143"}, depends_on=[watching])
    unrelated = await deps.queue.enqueue(
        kind="check_issue_state", project_id="acme", payload={}, reason="other",
        params={"issue": "INV-104", "expect": ["Done"]})

    body = interaction(block_action(f"revert:{action_id}"))
    text = client.post("/slack/interactions", content=body, headers=signed(body)).json()["text"]
    assert "cancelled 2 follow-up(s)" in text

    assert (await deps.db.get("tasks", watching) or {})["status"] == "cancelled"
    assert (await deps.db.get("tasks", dependent) or {})["status"] == "cancelled"
    assert (await deps.db.get("tasks", unrelated) or {})["status"] == "queued"


async def test_reverting_a_comment_leaves_a_note_rather_than_erasing_history(
    client: TestClient, deps: Deps
) -> None:
    await wire(deps)
    assert deps.actions is not None
    action_id = await deps.actions.begin(
        task_id="t", project_id="acme", kind="linear.comment", idempotency_key="k2", inputs={})
    await deps.actions.finish(
        action_id, target_ids={"identifier": "INV-143", "comment_id": "c-1"},
        revert={"op": "delete_comment", "issue": "INV-143", "comment_id": "c-1"})

    body = interaction(block_action(f"revert:{action_id}"))
    client.post("/slack/interactions", content=body, headers=signed(body))
    assert deps.linear.writes[-1]["op"] == "comment"
    assert "reverted by the team" in deps.linear.writes[-1]["body"]


async def test_reverting_a_slack_post_edits_the_message(client: TestClient, deps: Deps) -> None:
    await wire(deps)
    assert deps.actions is not None
    action_id = await deps.actions.begin(
        task_id="t", project_id="acme", kind="slack.post", idempotency_key="k3", inputs={})
    await deps.actions.finish(
        action_id, target_ids={"channel": "C1", "ts": "1.1"},
        revert={"op": "edit_message", "channel": "C1", "ts": "1.1"})

    body = interaction(block_action(f"revert:{action_id}"))
    client.post("/slack/interactions", content=body, headers=signed(body))
    assert deps.slack.updates[-1]["ts"] == "1.1"


async def test_reverting_something_that_never_happened_says_so(
    client: TestClient, deps: Deps
) -> None:
    await wire(deps)
    body = interaction(block_action("revert:no-such-action"))
    text = client.post("/slack/interactions", content=body, headers=signed(body)).json()["text"]
    assert "no longer on record" in text


async def test_a_tracker_outage_during_revert_reports_it_instead_of_lying(
    client: TestClient, deps: Deps
) -> None:
    from app.harness.core.errors import SourceUnavailable

    action_id = await wire(deps)

    async def down(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise SourceUnavailable("linear", "HTTP 503")

    deps.linear.update_issue = down  # type: ignore[method-assign]
    body = interaction(block_action(f"revert:{action_id}"))
    text = client.post("/slack/interactions", content=body, headers=signed(body)).json()["text"]
    assert "could not undo it" in text
    action = await deps.actions.get(action_id)
    assert action is not None and action["status"] == "done"  # not falsely marked reverted


# --- corrections ------------------------------------------------------------------------------

async def test_the_wrong_button_opens_the_correction_form(
    client: TestClient, deps: Deps
) -> None:
    await wire(deps)
    body = interaction(block_action("wrong:post-1"))
    assert client.post("/slack/interactions", content=body, headers=signed(body)
                       ).status_code == 200
    assert deps.slack.modals[0]["view"]["private_metadata"] == "post-1"


async def test_submitting_the_form_stores_a_correction_with_its_scope(
    client: TestClient, deps: Deps
) -> None:
    await wire(deps)
    submission = {
        "type": "view_submission",
        "user": {"id": "U-maya"},
        "view": {"private_metadata": "act-1", "state": {"values": {
            "wrong": {"value": {"value": "assigned design work to a backend engineer"}},
            "right": {"value": {"value": "design tickets go to Priya"}},
            "scope": {"value": {"selected_option": {"value": "project"}}},
        }}},
    }
    body = interaction(submission)
    assert client.post("/slack/interactions", content=body, headers=signed(body)
                       ).status_code == 200

    assert deps.corrections is not None
    stored = await deps.corrections.for_stage("acme", "reconcile")
    assert len(stored) == 1
    assert stored[0]["right"] == "design tickets go to Priya"
    assert stored[0]["scope"] == "project" and stored[0]["author_slack_id"] == "U-maya"
    assert stored[0]["source_action_id"] == "act-1"


def test_the_matcher_keeps_the_words_worth_matching_on() -> None:
    words = matcher_for("assigned design work to a backend engineer", "design tickets go to Priya")
    assert "design" in words and "backend" in words and "tickets" in words
    assert "to" not in words and "go" not in words


async def test_a_global_correction_reaches_every_project(deps: Deps) -> None:
    store = CorrectionStore(deps.db, deps.clock)
    await store.add(project_id="acme", wrong="a", right="b", scope="global")
    await store.add(project_id="acme", wrong="c", right="d", scope="project")
    assert len(await store.for_stage("acme", "reconcile")) == 2
    assert len(await store.for_stage("other-project", "reconcile")) == 1


async def test_a_stage_only_sees_corrections_meant_for_it(deps: Deps) -> None:
    store = CorrectionStore(deps.db, deps.clock)
    await store.add(project_id="acme", wrong="a", right="b", stage="extract")
    await store.add(project_id="acme", wrong="c", right="d", stage="any")
    assert len(await store.for_stage("acme", "extract")) == 2
    assert len(await store.for_stage("acme", "reconcile")) == 1


# --- events -----------------------------------------------------------------------------------

def test_slack_url_verification_is_echoed_back(client: TestClient, deps: Deps) -> None:
    deps.settings.slack_signing_secret = SECRET
    body = json.dumps({"type": "url_verification", "challenge": "abc123"}).encode()
    response = client.post("/slack/events", content=body, headers=signed(body))
    assert response.json() == {"challenge": "abc123"}


async def test_a_mention_is_recorded_once(client: TestClient, deps: Deps) -> None:
    deps.settings.slack_signing_secret = SECRET
    body = json.dumps({
        "type": "event_callback", "event_id": "Ev123",
        "event": {"type": "app_mention", "text": "<@U0> report", "user": "U-maya",
                  "channel": "C-product", "ts": "1.1"},
    }).encode()
    assert client.post("/slack/events", content=body, headers=signed(body)).json() == {"ok": True}
    client.post("/slack/events", content=body, headers=signed(body))

    event = await deps.events.get("slack:Ev123")
    assert event is not None and event["payload"]["text"] == "<@U0> report"
    assert await deps.db.count("events", [("provider", "==", "slack")]) == 1


def mention(text: str, event_id: str = "Ev200", channel: str = "C-random") -> bytes:
    return json.dumps({
        "type": "event_callback", "event_id": event_id,
        "event": {"type": "app_mention", "text": text, "user": "U-maya",
                  "channel": channel, "ts": "1787821201.000100"},
    }).encode()


async def test_a_mention_asking_for_a_report_queues_one_aimed_at_that_thread(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.slack_signing_secret = SECRET
    body = mention("<@U0> can we get a Report on the sprint?")
    client.post("/slack/events", content=body, headers=signed(body))

    queued = await deps.db.query("tasks", [("kind", "==", "report")])
    assert len(queued) == 1
    assert queued[0]["params"] == {"project": "acme", "window": "sprint"}
    assert queued[0]["payload"] == {"channel": "C-random", "thread_ts": "1787821201.000100"}
    assert queued[0]["root_event_id"] == "slack:Ev200"
    assert queued[0]["status"] == "queued" and queued[0]["due_at"] == "2026-08-27T09:00:00+00:00"


async def test_a_mention_about_anything_else_queues_nothing(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.slack_signing_secret = SECRET
    body = mention("<@U0> who owns INV-143?")
    client.post("/slack/events", content=body, headers=signed(body))

    assert await deps.db.count("tasks", [("kind", "==", "report")]) == 0


async def test_a_redelivered_report_mention_does_not_queue_a_second_report(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.slack_signing_secret = SECRET
    body = mention("<@U0> report please")
    client.post("/slack/events", content=body, headers=signed(body))
    client.post("/slack/events", content=body, headers=signed(body))

    assert await deps.db.count("tasks", [("kind", "==", "report")]) == 1

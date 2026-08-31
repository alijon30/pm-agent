"""The buttons on a summary. Revert is what makes acting without asking acceptable, so most of
these tests are about it working, and working exactly once."""

import hashlib
import hmac
import json
from typing import Any
from urllib.parse import urlencode

from app.harness.deps import Deps
from app.harness.http.slack import intent_of
from app.harness.store.actions import ActionStore
from app.harness.store.corrections import CorrectionStore, matcher_for
from fastapi.testclient import TestClient

from tests.fakes.fake_agents import FakeTriage
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
    assert response.json()["text"].startswith("Reverted INV-143.")
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
    assert again.json()["text"] == "That was already reverted."
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
    assert "I've also stopped 2 checks that were watching it." in text

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
    assert text == "I don't have that action on record any more."


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
    assert text.startswith("I can't undo that right now:")
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
    # No Slack configured in this test, so there is no "On it…" to point back at — and the
    # payload says so honestly instead of omitting the field.
    assert queued[0]["payload"] == {"channel": "C-random", "thread_ts": "1787821201.000100",
                                    "requester": "U-maya", "ack": {}}
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


async def test_a_queued_report_request_is_acknowledged_with_eyes_on_the_mention(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.slack_signing_secret = SECRET
    deps.slack = FakeSlack()
    body = mention("<@U0> report please")
    client.post("/slack/events", content=body, headers=signed(body))

    assert deps.slack.reactions == [
        {"channel": "C-random", "ts": "1787821201.000100", "name": "eyes"}
    ]
    # "On it…" lands in the thread within Slack's three seconds; the answering stage will
    # edit this exact message rather than posting a second one.
    assert [p["text"] for p in deps.slack.posts] == ["✻ On it…"]
    assert deps.slack.posts[0]["thread_ts"] == "1787821201.000100"
    queued = await deps.db.query("tasks", [("kind", "==", "report")])
    assert queued[0]["payload"]["ack"] == {
        "channel": "C-random", "ts": deps.slack.posts[0]["ts"]
    }


async def test_a_mention_that_queues_nothing_is_not_acknowledged(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.slack_signing_secret = SECRET
    deps.slack = FakeSlack()
    body = mention("<@U0> who owns INV-143?")
    client.post("/slack/events", content=body, headers=signed(body))

    assert deps.slack.reactions == []


async def test_a_slack_outage_while_acknowledging_still_leaves_the_report_queued(
    client: TestClient, deps: Deps
) -> None:
    from app.harness.core.errors import SourceUnavailable

    deps.settings.slack_signing_secret = SECRET
    deps.slack = FakeSlack()

    async def down(*args: Any, **kwargs: Any) -> None:
        raise SourceUnavailable("slack", "ratelimited")

    deps.slack.react = down  # type: ignore[method-assign]
    body = mention("<@U0> report please")
    response = client.post("/slack/events", content=body, headers=signed(body))

    assert response.json() == {"ok": True}
    assert await deps.db.count("tasks", [("kind", "==", "report")]) == 1


# --- what a mention is asking for ---------------------------------------------------------------

def test_a_mention_asking_for_a_report_routes_to_the_report_stage() -> None:
    assert intent_of("<@U0> can we get a Report on the sprint?", "acme") == {
        "kind": "report", "params": {"project": "acme", "window": "sprint"},
        "reason": "report requested in Slack"}


def test_a_mention_asking_the_agent_to_stop_routes_to_a_cancellation() -> None:
    for text in ("<@U0> stop watching INV-26", "<@U0> please cancel INV-26",
                 "<@U0> forget about INV-26 for now"):
        intent = intent_of(text, "acme")
        assert intent is not None
        assert intent["kind"] == "intake" and intent["params"] == {"cancel": "INV-26"}
        assert "INV-26" in intent["reason"]


def test_anything_else_of_substance_is_a_request(deps: Deps) -> None:
    intent = intent_of("<@U0> keep an eye on INV-26 until Friday please", "acme")
    assert intent is not None
    assert intent["kind"] == "intake"
    assert intent["params"] == {"text": "keep an eye on INV-26 until Friday please"}


def test_a_greeting_is_not_a_request() -> None:
    assert intent_of("<@U0> thanks!", "acme") is None
    assert intent_of("<@U0>", "acme") is None
    assert intent_of("<@U0> nice one", "acme") is None


def test_a_lowercase_identifier_is_not_an_identifier() -> None:
    """Issue keys are capitals. "stop the inv-26 thing" is a request, not a cancellation."""
    intent = intent_of("<@U0> stop the inv-26 thing please", "acme")
    assert intent is not None and intent["kind"] == "intake"
    assert "cancel" not in intent["params"]


async def test_a_request_is_queued_as_an_intake_carrying_who_asked_and_where(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.slack_signing_secret = SECRET
    deps.slack = FakeSlack()
    body = mention("<@U0> keep an eye on INV-26 until Friday")
    client.post("/slack/events", content=body, headers=signed(body))

    queued = await deps.db.query("tasks", [("kind", "==", "intake")])
    assert len(queued) == 1
    assert queued[0]["params"] == {"text": "keep an eye on INV-26 until Friday"}
    assert queued[0]["payload"] == {"channel": "C-random", "thread_ts": "1787821201.000100",
                                    "requester": "U-maya",
                                    "ack": {"channel": "C-random",
                                            "ts": deps.slack.posts[0]["ts"]}}
    assert queued[0]["root_event_id"] == "slack:Ev200"
    assert deps.slack.reactions[0]["name"] == "eyes"


async def test_a_cancellation_is_queued_as_an_intake_naming_the_issue(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.slack_signing_secret = SECRET
    deps.slack = FakeSlack()
    body = mention("<@U0> stop watching INV-26")
    client.post("/slack/events", content=body, headers=signed(body))

    queued = await deps.db.query("tasks", [("kind", "==", "intake")])
    assert len(queued) == 1 and queued[0]["params"] == {"cancel": "INV-26"}
    assert deps.slack.reactions[0]["name"] == "eyes"


# --- the classifier decides, the keywords catch it -----------------------------------------------

async def test_the_classifier_routes_a_request_the_keywords_would_have_missed(
    client: TestClient, deps: Deps
) -> None:
    """"any word on the dashboard" has no keyword in it; Gemma reads it as a request."""
    deps.settings.slack_signing_secret = SECRET
    deps.slack = FakeSlack()
    deps.triage = FakeTriage("request")
    body = mention("<@U0> any word on the dashboard")
    client.post("/slack/events", content=body, headers=signed(body))

    queued = await deps.db.query("tasks", [("kind", "==", "intake")])
    assert len(queued) == 1 and queued[0]["params"] == {"text": "any word on the dashboard"}
    assert deps.triage.classified == ["<@U0> any word on the dashboard"]


async def test_the_classifier_can_call_a_report_without_the_word_report(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.slack_signing_secret = SECRET
    deps.slack = FakeSlack()
    deps.triage = FakeTriage("report")
    body = mention("<@U0> how are we doing this sprint?")
    client.post("/slack/events", content=body, headers=signed(body))

    assert await deps.db.count("tasks", [("kind", "==", "report")]) == 1


async def test_a_cancellation_still_needs_the_regex_to_find_the_identifier(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.slack_signing_secret = SECRET
    deps.slack = FakeSlack()
    deps.triage = FakeTriage("cancel")
    body = mention("<@U0> you can drop INV-26 now")
    client.post("/slack/events", content=body, headers=signed(body))

    queued = await deps.db.query("tasks", [("kind", "==", "intake")])
    assert len(queued) == 1 and queued[0]["params"] == {"cancel": "INV-26"}


async def test_a_cancellation_naming_nothing_is_re_read_as_a_request(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.slack_signing_secret = SECRET
    deps.slack = FakeSlack()
    deps.triage = FakeTriage("cancel")
    body = mention("<@U0> stop doing that thing please")
    client.post("/slack/events", content=body, headers=signed(body))

    queued = await deps.db.query("tasks", [("kind", "==", "intake")])
    assert len(queued) == 1 and "text" in queued[0]["params"]


async def test_noise_is_seen_and_left_alone(client: TestClient, deps: Deps) -> None:
    deps.settings.slack_signing_secret = SECRET
    deps.slack = FakeSlack()
    deps.triage = FakeTriage("noise")
    body = mention("<@U0> haha nice one, thanks for that")
    client.post("/slack/events", content=body, headers=signed(body))

    assert await deps.db.count("tasks", []) == 0
    assert deps.slack.reactions[0]["name"] == "eyes"  # seen, and deliberately not acted on
    assert deps.slack.posts == []


async def test_a_classifier_that_falls_over_never_costs_a_colleague_their_answer(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.slack_signing_secret = SECRET
    deps.slack = FakeSlack()
    deps.triage = FakeTriage(raises=True)
    body = mention("<@U0> can I get a report please")
    client.post("/slack/events", content=body, headers=signed(body))

    assert await deps.db.count("tasks", [("kind", "==", "report")]) == 1


async def test_a_classifier_that_hangs_is_not_waited_for(
    client: TestClient, deps: Deps
) -> None:
    """Slack wants a 200 in three seconds; the keyword router answered fine before Gemma."""
    import asyncio

    class Hangs(FakeTriage):
        async def classify_intent(self, text: str) -> str:
            await asyncio.sleep(30)
            return "noise"

    deps.settings.slack_signing_secret = SECRET
    deps.slack = FakeSlack()
    deps.triage = Hangs()
    from app.harness.http import slack as route

    route.CLASSIFY_SECONDS = 0.01
    try:
        body = mention("<@U0> stop watching INV-26")
        response = client.post("/slack/events", content=body, headers=signed(body))
    finally:
        route.CLASSIFY_SECONDS = 2.0

    assert response.json() == {"ok": True}
    queued = await deps.db.query("tasks", [("kind", "==", "intake")])
    assert len(queued) == 1 and queued[0]["params"] == {"cancel": "INV-26"}


# --- being told how to work -------------------------------------------------------------------

def test_a_rule_for_next_time_is_not_a_request_for_a_check() -> None:
    """"assign billing to Nodir" has nowhere to live in the queue. It belongs in the brain."""
    for said in ("from now on assign billing to Nodir", "always cc the channel",
                 "never nudge before ten", "remember that rates allow six decimals",
                 "don't ping people on Fridays"):
        got = intent_of(f"<@U1> {said}", "acme") or {}
        assert got.get("kind") == "intake", said
        assert (got.get("params") or {}).get("instruct") is True, said


def test_stopping_one_watch_is_still_a_cancellation_not_a_rule() -> None:
    """"stop watching INV-27" is about one ticket; "stop nudging people" is a rule."""
    cancel = intent_of("<@U1> stop watching INV-27", "acme") or {}

    assert (cancel.get("params") or {}).get("cancel") == "INV-27"
    assert not (cancel.get("params") or {}).get("instruct")


def test_an_ordinary_request_is_untouched() -> None:
    got = intent_of("<@U1> please look at INV-30 this week", "acme") or {}

    assert got.get("kind") == "intake"
    assert not (got.get("params") or {}).get("instruct")


def test_a_rule_about_reports_is_a_rule_not_a_report_request() -> None:
    got = intent_of("<@U1> always put the report in the thread", "acme") or {}

    assert (got.get("params") or {}).get("instruct") is True

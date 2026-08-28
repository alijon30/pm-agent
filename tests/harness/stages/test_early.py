"""Reality overtaking the schedule: good news resolves early, bad news waits for its deadline."""

import hashlib
import hmac
import json
from typing import Any

from app.harness.deps import Deps
from app.harness.http.webhooks import verify_linear_signature
from app.harness.stages.early import issue_identifier_of, resolve_early
from app.harness.store.actions import ActionStore
from fastapi.testclient import TestClient

from tests.conftest import ACME
from tests.fakes.fake_github import FakeGitHub
from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_slack import FakeSlack

SECRET = "linear-signing-secret"  # noqa: S105 — a test fixture

IN_PROGRESS = {"id": "u-26", "identifier": "INV-26", "title": "CSV export behind the flag",
               "description": "", "state": "In Progress", "priority": 2,
               "assignee": {"id": "u-priya", "name": "Priya Nair"}, "due_date": "2026-09-04",
               "url": "https://linear.app/acme/issue/INV-26", "updated_at": ""}
TODO = {**IN_PROGRESS, "state": "Todo"}
PR = {"number": 9, "title": "CSV export (INV-26)", "state": "open", "merged": False,
      "url": "https://github.com/x/y/pull/9", "branch": "inv-26", "reviews": 0,
      "updated_at": "2026-08-28T10:00:00Z", "mentions": ["INV-26"]}


async def schedule_chain(deps: Deps, *, issues: list[dict[str, Any]],
                         prs: list[dict[str, Any]] | None = None) -> tuple[str, str]:
    """The planner's graph as it exists in production: a state check, and a PR check blocked
    behind it, both due days from now."""
    await deps.projects.upsert("acme", {**ACME, "slack_channel_id": "C-product"})
    deps.actions = ActionStore(deps.db, deps.clock)
    deps.slack = FakeSlack()
    deps.linear = FakeLinear(issues=issues)
    deps.github = FakeGitHub(prs or [])
    from datetime import timedelta
    first = await deps.queue.enqueue(
        kind="check_issue_state", project_id="acme", payload={},
        params={"issue": "INV-26", "expect": ["In Progress", "Done"]},
        reason="underway?", due_at=deps.clock.now() + timedelta(days=4),
        on_unmet="nudge_assignee")
    assert first is not None
    second = await deps.queue.enqueue(
        kind="check_pr_exists", project_id="acme", payload={}, params={"issue": "INV-26"},
        reason="pr?", due_at=deps.clock.now() + timedelta(days=6), depends_on=[first],
        on_unmet="nudge_assignee")
    assert second is not None
    return first, second


async def status(deps: Deps, tid: str) -> str:
    doc = await deps.db.get("tasks", tid)
    assert doc is not None
    return str(doc["status"])


# --- the sweep --------------------------------------------------------------------------------

async def test_work_finished_early_completes_the_check_days_before_its_due_date(
    deps: Deps,
) -> None:
    first, second = await schedule_chain(deps, issues=[IN_PROGRESS])
    resolved = await resolve_early("INV-26", deps)

    assert resolved == [first]
    assert await status(deps, first) == "done"
    doc = await deps.db.get("tasks", first)
    assert doc is not None and doc["result"]["early"] is True
    # the dependent is unblocked now, but keeps its own due date
    assert await status(deps, second) == "queued"


async def test_unfinished_work_is_left_for_its_deadline_and_nobody_is_nudged(
    deps: Deps,
) -> None:
    first, second = await schedule_chain(deps, issues=[TODO])
    assert await resolve_early("INV-26", deps) == []
    assert await status(deps, first) == "queued"
    assert await status(deps, second) == "blocked"
    assert deps.slack.posts == []


async def test_a_change_to_one_issue_never_touches_checks_about_another(deps: Deps) -> None:
    first, _ = await schedule_chain(deps, issues=[IN_PROGRESS])
    assert await resolve_early("INV-999", deps) == []
    assert await status(deps, first) == "queued"


async def test_even_a_blocked_check_completes_when_reality_already_satisfied_it(
    deps: Deps,
) -> None:
    # The PR appeared before the state check ever ran: both facts are true, both resolve.
    first, second = await schedule_chain(deps, issues=[IN_PROGRESS], prs=[PR])
    resolved = await resolve_early("INV-26", deps)
    assert set(resolved) == {first, second}
    assert await status(deps, second) == "done"


async def test_the_early_note_lands_in_the_plan_announcements_thread(deps: Deps) -> None:
    first, _ = await schedule_chain(deps, issues=[IN_PROGRESS])
    assert deps.actions is not None
    announce = await deps.actions.begin(
        task_id="plan-1", project_id="acme", kind="slack.post", idempotency_key="k-plan",
        inputs={"channel": "C-product", "tasks": 2})
    await deps.actions.finish(announce, target_ids={"channel": "C-product", "ts": "42.1"},
                              revert={})
    await resolve_early("INV-26", deps)
    assert len(deps.slack.posts) == 1
    note = deps.slack.posts[0]
    assert note["thread_ts"] == "42.1" and "resolved early" in note["text"]


# --- the webhook door -------------------------------------------------------------------------

def sign(body: bytes) -> str:
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def test_the_signature_check_fails_closed() -> None:
    body = b'{"type": "Issue"}'
    assert verify_linear_signature(SECRET, body, sign(body)) is True
    assert verify_linear_signature(SECRET, b'{"type": "tampered"}', sign(body)) is False
    assert verify_linear_signature("", body, sign(body)) is False
    assert verify_linear_signature(SECRET, body, "") is False


def test_the_identifier_is_read_from_either_payload_shape() -> None:
    assert issue_identifier_of({"data": {"identifier": "INV-26"}}) == "INV-26"
    assert issue_identifier_of({"data": {"number": 26, "team": {"key": "INV"}}}) == "INV-26"
    assert issue_identifier_of({"data": {}}) is None


async def test_an_issue_update_webhook_resolves_the_checks_it_satisfies(
    client: TestClient, deps: Deps,
) -> None:
    first, _ = await schedule_chain(deps, issues=[IN_PROGRESS])
    deps.settings.linear_webhook_secret = SECRET
    body = json.dumps({"type": "Issue", "action": "update", "webhookTimestamp": 1,
                       "data": {"id": "u-26", "identifier": "INV-26"}}).encode()
    response = client.post("/webhooks/linear", content=body,
                           headers={"linear-signature": sign(body),
                                    "linear-delivery": "d-1"})
    assert response.json() == {"status": "ok", "issue": "INV-26", "resolved_early": 1}
    assert await status(deps, first) == "done"

    again = client.post("/webhooks/linear", content=body,
                        headers={"linear-signature": sign(body), "linear-delivery": "d-1"})
    assert again.json() == {"status": "duplicate"}


def test_non_issue_webhooks_are_acknowledged_and_ignored(client: TestClient, deps: Deps) -> None:
    deps.settings.linear_webhook_secret = SECRET
    body = json.dumps({"type": "Comment", "data": {}}).encode()
    response = client.post("/webhooks/linear", content=body,
                           headers={"linear-signature": sign(body), "linear-delivery": "d-2"})
    assert response.json() == {"status": "ignored"}

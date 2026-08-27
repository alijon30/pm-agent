import hashlib
import hmac
import json
from typing import Any

import httpx
import pytest
from app.harness.connectors.slack import SlackClient, verify_slack_signature
from app.harness.connectors.slack_blocks import (
    MAX_BLOCKS,
    call_summary_blocks,
    plan_summary_blocks,
    revert_button,
    wrong_button,
    wrong_modal,
)
from app.harness.core.errors import SourceUnavailable

from tests.fakes.fake_slack import FakeSlack

SECRET = "s3cr3t-signing"  # noqa: S105 — a test fixture, not a credential
TS = 1_787_821_200


def sign(body: bytes, timestamp: int = TS) -> dict[str, str]:
    basestring = f"v0:{timestamp}:".encode() + body
    digest = hmac.new(SECRET.encode(), basestring, hashlib.sha256).hexdigest()
    return {"x-slack-request-timestamp": str(timestamp), "x-slack-signature": f"v0={digest}"}


# --- signature verification -------------------------------------------------------------------

def test_a_correctly_signed_fresh_request_verifies() -> None:
    body = b"payload=%7B%22type%22%3A%22block_actions%22%7D"
    assert verify_slack_signature(SECRET, sign(body), body, TS + 5) is True


def test_a_tampered_body_or_wrong_secret_fails() -> None:
    body = b"payload=a"
    headers = sign(body)
    assert verify_slack_signature(SECRET, headers, b"payload=b", TS) is False
    assert verify_slack_signature("other-secret", headers, body, TS) is False


def test_a_stale_request_is_rejected_even_with_a_valid_signature() -> None:
    body = b"payload=a"
    assert verify_slack_signature(SECRET, sign(body), body, TS + 301) is False


def test_missing_headers_or_secret_never_verify() -> None:
    body = b"payload=a"
    assert verify_slack_signature(SECRET, {}, body, TS) is False
    assert verify_slack_signature("", sign(body), body, TS) is False
    assert verify_slack_signature(
        SECRET, {"x-slack-request-timestamp": "not-a-number",
                 "x-slack-signature": "v0=x"}, body, TS
    ) is False


# --- block builders ---------------------------------------------------------------------------

MEETING = {"title": "Q3 Billing planning", "url": "https://fathom.video/share/abc"}
CREATED = [{"identifier": "INV-143", "title": "Move payment reminders to 3 days",
            "url": "https://linear.app/acme/issue/INV-143", "owner": "Nodir Rahimov"}]
UPDATED = [{"identifier": "INV-104", "url": "https://linear.app/acme/issue/INV-104",
            "note": "commented: raised again in the Q3 call"}]
SKIPPED = [{"title": "Ship SMS reminders", "reason": "no verbatim quote found in transcript"}]
CONFLICTS = [{"about": "reminder window", "sides": [
    {"claim": "7 days", "source": "code:acme/config.py:6"},
    {"claim": "5 days", "source": "notion:page-prd"},
    {"claim": "3 days", "source": "fathom:8841201@00:01:42"}]}]
ACTIONS = [{"id": "act-1", "label": "INV-143"}, {"id": "act-2", "label": "assignee"}]


def render(blocks: list[dict[str, Any]]) -> str:
    """Flatten to text for substring assertions; ensure_ascii would escape the separators."""
    return json.dumps(blocks, ensure_ascii=False)


def test_the_call_summary_names_what_was_filed_updated_skipped_and_disputed() -> None:
    blocks = call_summary_blocks(MEETING, CREATED, UPDATED, SKIPPED, CONFLICTS, ACTIONS,
                                 post_ref="post-1")
    rendered = render(blocks)
    assert "Q3 Billing planning" in rendered
    assert "1 filed · 1 updated · 1 skipped · 1 conflict(s)" in rendered
    assert "INV-143" in rendered and "Nodir Rahimov" in rendered
    assert "no verbatim quote found in transcript" in rendered
    assert "sources disagree" in rendered and "code:acme/config.py:6" in rendered


def test_the_summary_carries_one_revert_button_per_action_and_one_wrong_button() -> None:
    blocks = call_summary_blocks(MEETING, CREATED, UPDATED, SKIPPED, CONFLICTS, ACTIONS,
                                 post_ref="post-1")
    actions = [b for b in blocks if b["type"] == "actions"][0]["elements"]
    assert [e["action_id"] for e in actions] == [
        "revert:act-1", "revert:act-2", "wrong:post-1"
    ]


def test_a_summary_with_nothing_to_report_still_renders() -> None:
    blocks = call_summary_blocks(MEETING, [], [], [], [], [])
    assert blocks and "0 filed" in render(blocks)
    assert not [b for b in blocks if b["type"] == "actions"]


def test_an_oversized_summary_is_truncated_and_says_so_while_keeping_the_buttons() -> None:
    many = [{"identifier": f"INV-{i}", "title": f"t{i}", "url": "", "owner": "x"}
            for i in range(80)]
    blocks = call_summary_blocks(MEETING, many, [], [], [], ACTIONS, post_ref="p")
    assert len(blocks) <= MAX_BLOCKS
    assert "more not shown" in render(blocks)
    assert blocks[-1]["type"] == "actions"


def test_the_plan_summary_lists_each_check_with_its_reason_and_due_date() -> None:
    tasks = [
        {"kind": "check_issue_state", "reason": "in progress by Thursday",
         "due_at": "2026-08-28T16:00:00+00:00"},
        {"kind": "check_pr_exists", "reason": "PR open", "due_at": "2026-08-29T16:00:00+00:00"},
    ]
    rendered = render(plan_summary_blocks(tasks, trimmed=["review: unknown issue"]))
    assert "Planned 2 follow-up(s)" in rendered
    assert "check_issue_state" in rendered and "2026-08-28" in rendered
    assert "1 proposed task(s) rejected" in rendered


def test_an_empty_plan_says_nothing_was_scheduled() -> None:
    assert "No follow-ups scheduled" in render(plan_summary_blocks([], []))


def test_button_action_ids_carry_their_target_so_the_route_can_parse_them() -> None:
    assert revert_button("act-9")["action_id"] == "revert:act-9"
    assert revert_button("act-9")["value"] == "act-9"
    assert wrong_button("post-9")["action_id"] == "wrong:post-9"


def test_the_correction_modal_asks_what_was_wrong_what_is_right_and_the_scope() -> None:
    view = wrong_modal("post-1")
    assert view["callback_id"] == "correction" and view["private_metadata"] == "post-1"
    assert [b["block_id"] for b in view["blocks"]] == ["wrong", "right", "scope"]


# --- the client over a mock transport ---------------------------------------------------------

def client_with(handler: httpx.MockTransport) -> SlackClient:
    return SlackClient("xoxb-TESTTOKEN", transport=handler)


async def test_post_sends_text_and_blocks_and_returns_the_message_ts() -> None:
    seen: dict[str, Any] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer xoxb-TESTTOKEN"
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "ts": "1787821201.000100"})

    ts = await client_with(httpx.MockTransport(respond)).post(
        "C123", "fallback", [{"type": "divider"}], thread_ts="1787821200.000100")
    assert ts == "1787821201.000100"
    assert seen["channel"] == "C123" and seen["text"] == "fallback"
    assert seen["blocks"] == [{"type": "divider"}]
    assert seen["thread_ts"] == "1787821200.000100"


async def test_an_application_level_error_is_an_outage_even_on_http_200() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "error": "channel_not_found"})

    with pytest.raises(SourceUnavailable) as err:
        await client_with(httpx.MockTransport(respond)).post("C404", "x")
    assert "channel_not_found" in str(err.value)


async def test_transport_failures_become_source_unavailable() -> None:
    def explode(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns down")

    with pytest.raises(SourceUnavailable):
        await client_with(httpx.MockTransport(explode)).post("C1", "x")


async def test_user_info_is_none_for_an_unknown_user_but_raises_on_an_outage() -> None:
    def missing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "error": "user_not_found"})

    assert await client_with(httpx.MockTransport(missing)).user_info("U404") is None

    def broken(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "error": "ratelimited"})

    with pytest.raises(SourceUnavailable):
        await client_with(httpx.MockTransport(broken)).user_info("U1")


async def test_user_info_normalises_the_profile() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "user": {
            "id": "U1", "name": "nodir", "real_name": "Nodir Rahimov",
            "profile": {"email": "nodir@acme-invoicing.test"}}})

    assert await client_with(httpx.MockTransport(respond)).user_info("U1") == {
        "id": "U1", "name": "Nodir Rahimov", "email": "nodir@acme-invoicing.test"}


# --- the fake ---------------------------------------------------------------------------------

async def test_the_fake_records_posts_updates_and_modals_with_increasing_ts() -> None:
    fake = FakeSlack(users={"U1": {"id": "U1", "name": "Maya Chen", "email": "maya@x.test"}})
    first = await fake.post("C1", "one")
    second = await fake.post("C1", "two", [{"type": "divider"}])
    assert first < second and len(fake.posts) == 2
    assert fake.posts[1]["blocks"] == [{"type": "divider"}]
    await fake.update("C1", first, "edited")
    assert fake.updates[0]["ts"] == first
    await fake.open_modal("trigger-1", wrong_modal("post-1"))
    assert fake.modals[0]["view"]["callback_id"] == "correction"
    assert (await fake.user_info("U1") or {})["name"] == "Maya Chen"
    assert await fake.user_info("U404") is None

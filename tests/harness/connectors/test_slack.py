import hashlib
import hmac
import json
from typing import Any

import httpx
import pytest
from app.harness.connectors.slack import SlackClient, react_quietly, verify_slack_signature
from app.harness.connectors.slack_blocks import (
    CHECK_SENTENCES,
    MAX_BLOCKS,
    call_summary_blocks,
    count_of,
    human_check,
    human_date,
    human_due,
    plan_summary_blocks,
    ref_chip,
    ref_chips,
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
    assert "filed 1 ticket · updated 1 · 1 conflict · 1 skipped" in rendered
    assert "INV-143> Move payment reminders to 3 days — Nodir Rahimov" in rendered
    assert "Left alone: Ship SMS reminders — no verbatim quote found in transcript" in rendered
    assert "Sources disagree* on reminder window" in rendered


def test_the_summary_headline_never_reports_a_count_of_zero() -> None:
    rendered = render(call_summary_blocks(MEETING, CREATED, [], [], [], ACTIONS))
    assert "filed 1 ticket" in rendered
    assert "updated" not in rendered and "skipped" not in rendered and "conflict" not in rendered


def test_a_ticket_nobody_was_named_for_carries_no_owner_at_all() -> None:
    unowned = [{**CREATED[0], "owner": None}]
    rendered = render(call_summary_blocks(MEETING, unowned, [], [], [], []))
    assert "Move payment reminders to 3 days" in rendered
    assert "unassigned" not in rendered and "owner" not in rendered


def test_a_disagreement_cites_its_sources_the_way_a_person_reads_them() -> None:
    rendered = render(call_summary_blocks(MEETING, [], [], [], CONFLICTS, []))
    assert "config.py:6" in rendered and "spec" in rendered and "call @ 01:42" in rendered
    assert "code:acme/config.py:6" not in rendered and "notion:page-prd" not in rendered


def test_the_summary_carries_one_revert_button_per_action_and_one_wrong_button() -> None:
    blocks = call_summary_blocks(MEETING, CREATED, UPDATED, SKIPPED, CONFLICTS, ACTIONS,
                                 post_ref="post-1")
    actions = [b for b in blocks if b["type"] == "actions"][0]["elements"]
    assert [e["action_id"] for e in actions] == [
        "revert:act-1", "revert:act-2", "wrong:post-1"
    ]


def test_a_summary_with_nothing_to_report_says_so_in_words() -> None:
    blocks = call_summary_blocks(MEETING, [], [], [], [], [])
    assert blocks and "nothing needed filing" in render(blocks)
    assert "0" not in render(blocks)
    assert not [b for b in blocks if b["type"] == "actions"]


def test_an_oversized_summary_is_truncated_and_says_so_while_keeping_the_buttons() -> None:
    many = [{"identifier": f"INV-{i}", "title": f"t{i}", "url": "", "owner": "x"}
            for i in range(80)]
    blocks = call_summary_blocks(MEETING, many, [], [], [], ACTIONS, post_ref="p")
    assert len(blocks) <= MAX_BLOCKS
    assert "more not shown" in render(blocks)
    assert blocks[-1]["type"] == "actions"


PLANNED = [
    {"kind": "check_issue_state", "params": {"issue": "INV-26", "expect": ["In Progress"]},
     "reason": "in progress by Thursday", "due_at": "2026-09-01T16:00:00+00:00",
     "on_unmet": "nudge_assignee"},
    {"kind": "check_pr_exists", "params": {"issue": "INV-26"}, "reason": "PR open",
     "due_at": "2026-09-03T16:00:00+00:00", "on_unmet": "none"},
]


def test_the_plan_summary_promises_something_a_person_can_hold_it_to() -> None:
    rendered = render(plan_summary_blocks(PLANNED, trimmed=["review: unknown issue"]))
    assert "I'll follow up on this:" in rendered
    assert "Tue Sep 1 — check that INV-26 is underway _(if not, I'll nudge the assignee)_" \
        in rendered
    assert "Thu Sep 3 — look for a pull request on INV-26" in rendered
    assert "I dropped 1 idea I could not verify" in rendered


def test_the_plan_summary_never_shows_a_task_kind_or_an_iso_date() -> None:
    rendered = render(plan_summary_blocks(PLANNED, []))
    assert "check_issue_state" not in rendered and "check_pr_exists" not in rendered
    assert "2026-09-01" not in rendered and "T16:00" not in rendered


def test_a_check_with_no_consequence_promises_nothing_it_will_not_do() -> None:
    rendered = render(plan_summary_blocks([PLANNED[1]], []))
    assert "if not" not in rendered


def test_every_kind_the_planner_may_schedule_can_be_said_in_a_sentence() -> None:
    from app.harness.kinds.registry import KINDS

    unsayable = {k for k in KINDS if k.startswith("check_") or k in ("nudge", "escalate")} - set(
        CHECK_SENTENCES
    )
    assert unsayable == set(), f"no sentence for: {unsayable}"


def test_an_unfamiliar_kind_falls_back_to_the_reason_a_human_wrote() -> None:
    assert human_check({"kind": "check_moon_phase", "reason": "the moon must be full"}) == (
        "the moon must be full")


def test_an_empty_plan_says_there_is_nothing_to_watch() -> None:
    assert "Nothing needs watching right now" in render(plan_summary_blocks([], []))


# --- reading a citation ------------------------------------------------------------------------

def test_a_citation_is_rendered_as_something_a_person_can_read() -> None:
    assert ref_chip("linear:INV-26") == "INV-26"
    assert ref_chip("fathom:8841201@00:01:58") == "call @ 01:58"
    assert ref_chip("fathom:8841201@01:23:45") == "call @ 01:23:45"
    assert ref_chip("decision:9f2a1b4c") == "ledger"
    assert ref_chip("code:acme/invoices/export.py:41") == "export.py:41"
    assert ref_chip("notion:page-prd") == "spec"


def test_a_reference_shaped_like_nothing_we_know_is_shown_as_it_is() -> None:
    assert ref_chip("something-else") == "something-else"
    assert ref_chip("") == ""


def test_three_decisions_on_one_claim_read_as_one_ledger() -> None:
    assert ref_chips(["decision:a", "decision:b", "linear:INV-1", "linear:INV-1"]) == [
        "ledger", "INV-1"]


def test_dates_are_written_the_way_people_say_them() -> None:
    assert human_due("2026-09-01T16:00:00+00:00") == "Tue Sep 1"
    assert human_date("2026-09-01T16:00:00+00:00") == "Sep 1"
    assert human_due("not a date") == "" and human_date("") == ""


def test_one_pluralisation_rule_so_nothing_ever_says_check_s() -> None:
    assert count_of(1, "ticket") == "1 ticket"
    assert count_of(2, "ticket") == "2 tickets"
    assert count_of(0, "planned check") == "0 planned checks"


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


async def test_a_reaction_names_the_message_and_the_emoji_without_colons() -> None:
    seen: dict[str, Any] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/reactions.add")
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"ok": True})

    await client_with(httpx.MockTransport(respond)).react("C1", "1787821200.000100", "eyes")
    assert seen == {"channel": "C1", "timestamp": "1787821200.000100", "name": "eyes"}


async def test_reacting_twice_is_success_because_the_state_is_already_what_we_wanted() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "error": "already_reacted"})

    await client_with(httpx.MockTransport(respond)).react("C1", "1.1", "eyes")  # must not raise


async def test_any_other_reaction_error_is_an_outage() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "error": "missing_scope"})

    with pytest.raises(SourceUnavailable) as err:
        await client_with(httpx.MockTransport(respond)).react("C1", "1.1", "eyes")
    assert "missing_scope" in str(err.value)


# --- reacting is never worth failing over -------------------------------------------------------

async def test_a_reaction_that_lands_says_so() -> None:
    fake = FakeSlack()
    assert await react_quietly(fake, "C1", "1.1", "eyes") is True
    assert fake.reactions == [{"channel": "C1", "ts": "1.1", "name": "eyes"}]


async def test_there_is_nothing_to_react_to_without_a_channel_a_ts_or_a_client() -> None:
    fake = FakeSlack()
    assert await react_quietly(None, "C1", "1.1", "eyes") is False
    assert await react_quietly(fake, "", "1.1", "eyes") is False
    assert await react_quietly(fake, "C1", None, "eyes") is False
    assert fake.reactions == []


async def test_an_outage_while_reacting_is_a_shrug() -> None:
    class Down:
        async def react(self, channel: str, ts: str, name: str) -> None:
            raise SourceUnavailable("slack", "ratelimited")

    assert await react_quietly(Down(), "C1", "1.1", "eyes") is False


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


async def test_the_fake_records_reactions_and_is_idempotent_like_slack_is() -> None:
    fake = FakeSlack()
    await fake.react("C1", "1.1", "eyes")
    await fake.react("C1", "1.1", "eyes")
    await fake.react("C1", "1.1", "white_check_mark")

    assert fake.reactions == [
        {"channel": "C1", "ts": "1.1", "name": "eyes"},
        {"channel": "C1", "ts": "1.1", "name": "white_check_mark"},
    ]

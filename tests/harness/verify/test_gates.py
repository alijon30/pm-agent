"""The gates that stand between the model and the team's workspace."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from app.harness.connectors.code import CodeSearch
from app.harness.core.errors import SourceUnavailable
from app.harness.verify.caps import check_caps, in_quiet_hours, next_window
from app.harness.verify.dates import resolve_due
from app.harness.verify.ids import IdGate
from app.harness.verify.priority import check_priority
from app.harness.verify.roster import resolve_owner

from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_notion import FakeNotion

REPO = Path(__file__).parents[3] / "fixtures" / "acme-invoicing"

ROSTER = [
    {"name": "Maya Chen", "aliases": ["Maya"], "role": "pm"},
    {"name": "Nodir Rahimov", "aliases": ["Nodir"], "role": "backend"},
    {"name": "Priya Nair", "aliases": [], "role": "frontend"},
    {"name": "Tom Alvarez", "aliases": [], "role": "support"},
]
POLICY = {"priority_band": [2, 4], "escalation_phrases": ["urgent", "blocker", "blocked", "p0"],
          "daily_write_cap": 40, "daily_ping_cap": 10, "quiet_hours": ["20:00", "08:00"]}


# --- roster -----------------------------------------------------------------------------------

def test_a_full_name_alias_or_unambiguous_first_name_resolves() -> None:
    assert (resolve_owner("Nodir Rahimov", ROSTER) or {})["role"] == "backend"
    assert (resolve_owner("nodir", ROSTER) or {})["role"] == "backend"
    assert (resolve_owner("  PRIYA  ", ROSTER) or {})["role"] == "frontend"


def test_a_name_nobody_on_the_project_answers_to_is_not_guessed() -> None:
    assert resolve_owner("Sam", ROSTER) is None
    assert resolve_owner("", ROSTER) is None
    assert resolve_owner(None, ROSTER) is None


def test_an_ambiguous_first_name_resolves_to_nobody_rather_than_the_wrong_person() -> None:
    two_marias = [{"name": "Maria Lopez", "aliases": []}, {"name": "Maria Silva", "aliases": []}]
    assert resolve_owner("Maria", two_marias) is None


# --- priority ---------------------------------------------------------------------------------

def test_a_priority_inside_the_band_passes_through_untouched() -> None:
    assert check_priority(3, [], POLICY) == check_priority(3, [], POLICY)
    verdict = check_priority(3, ["nothing urgent here"], POLICY)
    assert verdict.priority == 3 and verdict.note == ""


def test_urgent_is_allowed_only_when_someone_actually_said_so() -> None:
    quotes = ["This is urgent, a customer is blocked."]
    allowed = check_priority(1, quotes, POLICY)
    assert allowed.priority == 1 and "escalated" in allowed.note

    clamped = check_priority(1, ["let's get to it this week"], POLICY)
    assert clamped.priority == 2 and "nobody said this was urgent" in clamped.note


def test_a_priority_below_the_band_is_clamped_upward() -> None:
    verdict = check_priority(0, [], POLICY)
    assert verdict.priority == 2


def test_no_proposed_priority_stays_no_priority() -> None:
    assert check_priority(None, ["urgent"], POLICY).priority is None


# --- dates ------------------------------------------------------------------------------------

QUOTES = ["Sure, I can have that done by next Friday.", "Ship the export this week."]


def test_a_due_date_needs_both_a_resolved_date_and_the_words_that_were_spoken() -> None:
    assert resolve_due("2026-09-04", "by next Friday", QUOTES) == "2026-09-04"
    assert resolve_due("2026-09-04", None, QUOTES) is None
    assert resolve_due(None, "by next Friday", QUOTES) is None


def test_a_hint_nobody_spoke_never_becomes_a_commitment() -> None:
    assert resolve_due("2026-09-04", "by tomorrow", QUOTES) is None


def test_a_malformed_date_is_refused() -> None:
    assert resolve_due("next Friday", "by next Friday", QUOTES) is None
    assert resolve_due("2026-9-4", "by next Friday", QUOTES) is None


# --- caps -------------------------------------------------------------------------------------

def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 27, hour, minute, tzinfo=UTC)


def test_quiet_hours_wrap_past_midnight() -> None:
    quiet = ["20:00", "08:00"]
    assert in_quiet_hours(at(21), quiet) is True
    assert in_quiet_hours(at(3), quiet) is True
    assert in_quiet_hours(at(9), quiet) is False
    assert in_quiet_hours(at(19, 59), quiet) is False


def test_a_ping_inside_quiet_hours_is_deferred_to_the_next_morning_not_dropped() -> None:
    verdict = check_caps("ping", {}, at(22), POLICY)
    assert verdict.ok is False
    assert verdict.defer_until == at(8) .replace(day=28)
    assert "quiet hours" in verdict.reason


def test_a_ping_before_the_window_opens_defers_to_this_morning() -> None:
    assert next_window(at(3), ["20:00", "08:00"]) == at(8)


def test_the_daily_ping_cap_defers_to_the_next_day() -> None:
    verdict = check_caps("ping", {"ping": 10}, at(10), POLICY)
    assert verdict.ok is False and "daily ping cap reached (10/10)" in verdict.reason
    assert verdict.defer_until == datetime(2026, 8, 28, tzinfo=UTC)


def test_writes_ignore_quiet_hours_because_a_ticket_wakes_nobody() -> None:
    assert check_caps("write", {"write": 3}, at(23), POLICY).ok is True


def test_the_daily_write_cap_defers_the_remainder() -> None:
    verdict = check_caps("write", {"write": 40}, at(10), POLICY)
    assert verdict.ok is False and "daily write cap reached (40/40)" in verdict.reason


# --- the id gate ------------------------------------------------------------------------------

def make_gate(**overrides: Any) -> IdGate:
    linear = FakeLinear(issues=[
        {"id": "u-142", "identifier": "INV-142", "title": "Reminders", "description": "",
         "state": "Todo", "priority": 3, "assignee": None, "due_date": None, "url": "",
         "updated_at": ""},
    ])
    notion = FakeNotion({"page-prd": {"title": "Reminders PRD", "url": "", "markdown": "5 days"}})
    kwargs: dict[str, Any] = {
        "linear": linear, "notion": notion, "code": CodeSearch(REPO), "roster": ROSTER,
        "known_meeting": _known_meeting,
    }
    kwargs.update(overrides)
    return IdGate(**kwargs)


async def _known_meeting(meeting_id: str) -> bool:
    return meeting_id == "8841201"


async def test_a_real_issue_page_code_line_and_meeting_all_confirm() -> None:
    gate = make_gate()
    assert await gate.ref_exists("linear:INV-142") is True
    assert await gate.ref_exists("notion:page-prd") is True
    assert await gate.ref_exists("code:acme/config.py:6") is True
    assert await gate.ref_exists("fathom:8841201@00:01:42") is True


async def test_a_fabricated_reference_of_every_kind_is_caught() -> None:
    gate = make_gate()
    assert await gate.ref_exists("linear:INV-999") is False
    assert await gate.ref_exists("notion:page-ghost") is False
    assert await gate.ref_exists("code:acme/ghost.py:1") is False
    assert await gate.ref_exists("fathom:0000000@00:01:00") is False


async def test_a_code_reference_past_the_end_of_the_file_is_not_real() -> None:
    gate = make_gate()
    assert await gate.ref_exists("code:acme/config.py:9999") is False
    assert await gate.ref_exists("code:acme/config.py") is True


async def test_text_that_is_not_a_reference_at_all_is_refused() -> None:
    gate = make_gate()
    assert await gate.ref_exists("INV-142") is False
    assert await gate.ref_exists("") is False
    assert await gate.ref_exists("slack:C123") is False


async def test_missing_refs_names_exactly_what_could_not_be_confirmed() -> None:
    gate = make_gate()
    missing = await gate.missing_refs(
        ["linear:INV-142", "linear:INV-999", "code:acme/config.py:6", "notion:ghost"]
    )
    assert missing == ["linear:INV-999", "notion:ghost"]


async def test_a_source_outage_propagates_instead_of_deleting_a_real_citation() -> None:
    class DownLinear:
        async def get_issue(self, identifier: str) -> dict[str, Any] | None:
            raise SourceUnavailable("linear", "HTTP 503")

    gate = make_gate(linear=DownLinear())
    with pytest.raises(SourceUnavailable):
        await gate.ref_exists("linear:INV-142")


async def test_the_plan_gates_bare_token_lookup_handles_issues_and_people() -> None:
    gate = make_gate()
    assert await gate.exists("INV-142") is True
    assert await gate.exists("INV-999") is False
    assert await gate.exists("Nodir Rahimov") is True
    assert await gate.exists("Sam") is False
    assert await gate.exists("") is False


async def test_a_gate_with_no_connector_confirms_nothing_rather_than_assuming() -> None:
    gate = IdGate(roster=ROSTER)
    assert await gate.ref_exists("linear:INV-142") is False
    assert await gate.ref_exists("code:acme/config.py") is False
    assert gate.person_exists("Maya") is True

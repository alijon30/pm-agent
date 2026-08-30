"""The dashboard numbers.

A judge reads these and decides whether to believe the rest of the page, so each one is pinned
to a fixture small enough to check by hand: one sprint, two calls, mixed checks, one revert."""

from datetime import UTC, datetime
from typing import Any

from app.harness.http.stats import (
    call_to_ticket,
    coverage,
    days_saved,
    in_window,
    median_minutes,
    percent,
    spoken_duration,
    sprint_stats,
    trust_stats,
    working_stats,
)

NOW = datetime(2026, 8, 30, 17, 0, tzinfo=UTC)
PROJECT: dict[str, Any] = {
    "sprint": {"name": "Sprint 1", "start": "2026-08-28", "end": "2026-09-11"},
    "policy": {"daily_write_cap": 40, "daily_ping_cap": 10,
               "quiet_hours": ["18:00", "09:00"]},
}

EVENTS = [
    {"id": "ev-1", "provider": "fathom", "received_at": "2026-08-28T17:00:00+00:00"},
    {"id": "ev-2", "provider": "fathom", "received_at": "2026-08-29T17:00:00+00:00"},
]
TASKS: list[dict[str, Any]] = [
    {"kind": "extract", "status": "done", "finished_at": "2026-08-28T17:01:00+00:00",
     "root_event_id": "ev-1", "result": {}},
    {"kind": "extract", "status": "done", "finished_at": "2026-08-29T17:01:00+00:00",
     "root_event_id": "ev-2", "result": {"bounced": True}},
    {"kind": "act", "status": "done", "finished_at": "2026-08-28T17:04:00+00:00",
     "root_event_id": "ev-1", "result": {}},
    {"kind": "act", "status": "done", "finished_at": "2026-08-29T17:10:00+00:00",
     "root_event_id": "ev-2", "result": {}},
    # a check that met its promise, one that came back four days early, one that did not
    {"kind": "check_issue_state", "status": "done", "due_at": "2026-08-29T17:00:00+00:00",
     "finished_at": "2026-08-29T17:00:00+00:00", "result": {"met": True}},
    {"kind": "check_issue_state", "status": "done", "due_at": "2026-09-01T17:00:00+00:00",
     "finished_at": "2026-08-28T17:00:00+00:00", "result": {"met": True, "early": True}},
    {"kind": "check_pr_exists", "status": "done", "due_at": "2026-08-29T17:00:00+00:00",
     "finished_at": "2026-08-29T18:00:00+00:00", "result": {"met": False}},
    {"kind": "check_pr_exists", "status": "queued", "due_at": "2026-09-03T17:00:00+00:00"},
    {"kind": "check_issue_state", "status": "blocked", "due_at": "2026-09-04T17:00:00+00:00"},
    {"kind": "check_issue_state", "status": "deferred",
     "defer_reason": "quiet hours until 09:00"},
]
ACTIONS: list[dict[str, Any]] = [
    {"kind": "linear.create_issue", "status": "done", "day": "2026-08-30",
     "cap_kind": "write", "created_at": "2026-08-28T17:03:00+00:00",
     "citations": ["fathom:m1@00:14"], "checks_passed": ["ids", "evidence", "roster"]},
    {"kind": "linear.create_issue", "status": "done", "day": "2026-08-30",
     "cap_kind": "write", "created_at": "2026-08-29T17:03:00+00:00",
     "citations": [], "checks_passed": ["evidence"]},
    {"kind": "linear.comment", "status": "done", "day": "2026-08-29",
     "cap_kind": "write", "created_at": "2026-08-28T17:05:00+00:00", "citations": []},
    {"kind": "slack.post", "status": "done", "day": "2026-08-30", "cap_kind": "ping",
     "created_at": "2026-08-30T10:00:00+00:00", "inputs": {"template": "nudge"}},
    {"kind": "linear.create_issue", "status": "done", "day": "2026-08-28",
     "cap_kind": "write", "created_at": "2026-08-28T17:06:00+00:00",
     "reverted_at": "2026-08-28T18:00:00+00:00", "citations": ["fathom:m1@00:20"],
     "checks_passed": ["citations"]},
]
DECISIONS = [
    {"id": "d1", "statement": "Move payment reminders to three days after the due date.",
     "created_at": "2026-08-28T17:02:00+00:00"},
    {"id": "d2", "statement": "Move payment reminders to three days after due.",
     "created_at": "2026-08-28T17:03:00+00:00"},
    {"id": "d3", "statement": "Ship the invoice CSV export behind a flag.",
     "created_at": "2026-08-29T17:02:00+00:00"},
]


def by_label(tiles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {t["label"]: t for t in tiles}


# --- the pieces ---------------------------------------------------------------------------------

def test_a_sprint_with_no_dates_holds_everything() -> None:
    """A dashboard reading zero because nobody filled in a field is worse than one that counts
    a little too much."""
    assert in_window("2026-01-01T00:00:00+00:00", "", "")
    assert in_window("2026-08-30T00:00:00+00:00", "2026-08-28", "2026-09-11")
    assert not in_window("2026-08-01T00:00:00+00:00", "2026-08-28", "2026-09-11")


def test_a_median_of_nothing_is_nothing_rather_than_zero() -> None:
    assert median_minutes([]) is None
    assert median_minutes([4.0]) == 4.0
    assert median_minutes([2.0, 4.0]) == 3.0
    assert median_minutes([1.0, 5.0, 9.0]) == 5.0


def test_a_duration_is_said_the_way_somebody_says_it() -> None:
    assert spoken_duration(None) == "—"
    assert spoken_duration(3.4) == "3 min"
    assert spoken_duration(0.2) == "1 min", "something that happened took at least a minute"
    assert spoken_duration(60) == "1 h"
    assert spoken_duration(80) == "1 h 20 min"


def test_nothing_over_nothing_is_not_zero_percent() -> None:
    assert percent(0, 0) == "—"
    assert percent(1, 2) == "50%"
    assert percent(3, 3) == "100%"


def test_how_long_a_call_takes_to_become_tickets() -> None:
    """Webhook to filed, which is the span a person actually waits."""
    assert call_to_ticket(EVENTS, TASKS) == 7.0  # 4 min and 10 min
    assert call_to_ticket([], TASKS) is None


def test_days_saved_counts_only_checks_that_came_back_early() -> None:
    assert days_saved(TASKS) == 4


def test_citation_coverage_counts_filed_issues_not_every_action() -> None:
    assert coverage(ACTIONS) == (2, 3)


# --- the tiles -----------------------------------------------------------------------------------

def test_this_sprint_counts_what_the_sprint_produced() -> None:
    tiles = by_label(sprint_stats(TASKS, ACTIONS, EVENTS, DECISIONS, PROJECT, NOW))

    assert tiles["Calls heard"]["value"] == "2"
    # the two reminder statements are one decision said twice
    assert tiles["Decisions recorded"]["value"] == "2"
    assert tiles["Issues filed"]["value"] == "3"
    assert tiles["Issues filed"]["footnote"] == "1 updated instead of re-filed"
    assert tiles["Checks run"]["value"] == "3"
    assert tiles["Checks run"]["footnote"] == "2 met · 1 early · 1 unmet"
    assert tiles["Open watches"]["value"] == "2", "queued and blocked; deferred waits on a clock"


def test_a_tile_may_say_zero_where_a_journal_line_may_not() -> None:
    tiles = by_label(sprint_stats([], [], [], [], PROJECT, NOW))

    assert tiles["Calls heard"]["value"] == "0"
    assert tiles["Issues filed"]["value"] == "0"


def test_the_next_watch_is_named_when_there_is_one() -> None:
    tiles = by_label(sprint_stats(TASKS, ACTIONS, EVENTS, DECISIONS, PROJECT, NOW,
                                  next_check="check that INV-29 is underway, Sun Aug 30"))

    assert tiles["Open watches"]["footnote"] == (
        "next: check that INV-29 is underway, Sun Aug 30")


def test_how_it_works_reports_the_loop_not_the_model() -> None:
    tiles = by_label(working_stats(TASKS, ACTIONS, EVENTS, PROJECT, "2026-08-30"))

    assert tiles["Call → tickets"]["value"] == "7 min"
    assert tiles["Days saved"]["value"] == "4"
    assert tiles["Writes today"]["value"] == "2 / 40"
    assert tiles["Pings today"]["value"] == "1 / 10"
    assert tiles["Held for quiet hours"]["value"] == "1"
    assert tiles["Held for quiet hours"]["footnote"] == "18:00–09:00 local"


def test_trust_counts_only_what_was_written_down_at_the_time() -> None:
    tiles = by_label(trust_stats(TASKS, ACTIONS, []))

    assert tiles["Citation coverage"]["value"] == "67%"
    assert tiles["Citation coverage"]["footnote"] == "2 of 3 filed issues"
    assert tiles["References verified"]["value"] == "2", "one citation on each of two actions"
    assert tiles["References verified"]["footnote"] == "0 fabricated"
    assert tiles["Gates passed"]["value"] == "5"
    assert tiles["Gates passed"]["footnote"] == "1 retried after feedback"
    assert tiles["Reverted"]["value"] == "1"


def test_a_record_this_project_does_not_keep_gets_no_tile() -> None:
    """An empty Corrections tile is furniture. It appears when somebody has corrected the
    agent and not before."""
    assert "Corrections" not in by_label(trust_stats(TASKS, ACTIONS, []))
    assert by_label(trust_stats(TASKS, ACTIONS, [{"id": "c1"}]))["Corrections"]["value"] == "1"

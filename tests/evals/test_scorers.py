"""The scorers decide what the headline numbers say, so a scorer that is wrong is worse than no
eval at all. These tests are about the two things that could silently mislead: an identifier
scan that misses an invented ticket, and one that invents a violation out of ordinary prose."""

from typing import Any

from evals.scorers import (
    SCORERS,
    fabricated_identifiers,
    identifier_pattern,
    no_fabricated_identifiers,
    priority_band_respected,
    roster_miss_unassigned,
    written_identifiers,
)

TRACKER = [
    {"identifier": "INV-101", "title": "Overdue invoices dashboard", "description": ""},
    {"identifier": "INV-116", "title": "Move payment reminders", "description": ""},
]


def run(**fields: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "issues": TRACKER, "reconcile": {"items": []}, "report": {"report": {"sections": []}},
        "actions": [], "scheduled": [], "policy": {}, "roster": [],
    }
    return {**base, **fields}


def test_the_identifier_scan_only_looks_for_keys_this_tracker_uses() -> None:
    pattern = identifier_pattern({"INV-101", "INV-116"})
    assert pattern is not None
    assert pattern.findall("cites INV-116 and INV-999") == ["INV-116", "INV-999"]
    assert pattern.findall("encoded as UTF-8 over HTTP-2") == []


def test_an_empty_tracker_gives_nothing_to_scan_for() -> None:
    assert identifier_pattern(set()) is None
    assert written_identifiers(run(issues=[])) == []


def test_an_invented_ticket_in_an_issue_body_is_caught() -> None:
    bundle = run(issues=[
        *TRACKER,
        {"identifier": "INV-117", "title": "x", "description": "Related to INV-404, see there."},
    ])
    assert fabricated_identifiers(bundle) == ["INV-404"]


def test_an_invented_ticket_in_a_citation_is_caught() -> None:
    bundle = run(reconcile={"items": [{"title": "t", "citations": ["linear:INV-900"]}]})
    assert fabricated_identifiers(bundle) == ["INV-900"]


def test_an_invented_ticket_in_a_report_reference_is_caught() -> None:
    bundle = run(report={"report": {"sections": [
        {"name": "shipped", "claims": [{"text": "shipped", "refs": ["linear:INV-901"]}]}]}})
    assert fabricated_identifiers(bundle) == ["INV-901"]


def test_an_invented_ticket_in_a_scheduled_check_is_caught() -> None:
    bundle = run(scheduled=[{"kind": "check_pr_exists", "params": {"issue": "INV-902"}}])
    assert fabricated_identifiers(bundle) == ["INV-902"]


def test_real_identifiers_written_everywhere_count_as_zero_fabrications() -> None:
    bundle = run(
        reconcile={"items": [{"title": "t", "citations": ["linear:INV-101"],
                              "conflicts": [{"about": "x", "sides": [
                                  {"claim": "a", "source": "linear:INV-116"}]}]}]},
        scheduled=[{"kind": "check_pr_exists", "params": {"issue": "INV-116"}}],
        actions=[{"kind": "linear.create_issue", "status": "done",
                  "target_ids": {"identifier": "INV-116"}, "inputs": {}}],
    )
    outcome = no_fabricated_identifiers({"expected": {}}, bundle)

    assert fabricated_identifiers(bundle) == []
    assert outcome.passed is True and "all real" in outcome.detail


def test_the_same_invented_ticket_written_twice_is_reported_once() -> None:
    bundle = run(
        reconcile={"items": [{"title": "t", "citations": ["linear:INV-404"]}]},
        scheduled=[{"kind": "check_pr_exists", "params": {"issue": "INV-404"}}],
    )
    assert fabricated_identifiers(bundle) == ["INV-404"]


# --- the policy guarantees ----------------------------------------------------------------------

def test_leaving_the_priority_band_is_a_violation_when_nobody_said_it_was_urgent() -> None:
    bundle = run(
        policy={"priority_band": [2, 4], "escalation_phrases": ["urgent"]},
        reconcile={"items": [{"title": "Export", "quotes": ["can you take the export"]}]},
        actions=[{"kind": "linear.create_issue", "status": "done",
                  "target_ids": {"identifier": "INV-116"},
                  "inputs": {"title": "Export", "priority": 1}}],
    )
    assert priority_band_respected({"expected": {}}, bundle).passed is False


def test_leaving_the_priority_band_is_allowed_when_the_call_said_it_was_urgent() -> None:
    bundle = run(
        policy={"priority_band": [2, 4], "escalation_phrases": ["urgent"]},
        reconcile={"items": [{"title": "Export", "quotes": ["This is urgent, a customer is "
                                                            "blocked"]}]},
        actions=[{"kind": "linear.create_issue", "status": "done",
                  "target_ids": {"identifier": "INV-116"},
                  "inputs": {"title": "Export", "priority": 1}}],
    )
    assert priority_band_respected({"expected": {}}, bundle).passed is True


def test_assigning_work_to_someone_off_the_roster_fails_the_guarantee() -> None:
    bundle = run(
        roster=["Nodir Rahimov", "Priya Nair"],
        actions=[{"kind": "linear.create_issue", "status": "done", "target_ids": {},
                  "inputs": {"title": "Stripe webhook retries", "owner": "Sam"}}],
    )
    outcome = roster_miss_unassigned({"expected": {"name": "Sam"}}, bundle)

    assert outcome.passed is False and "Sam" in outcome.detail


def test_every_scorer_is_reachable_by_name() -> None:
    assert SCORERS["no_fabricated_identifiers"] is no_fabricated_identifiers
    assert all(callable(scorer) for scorer in SCORERS.values())

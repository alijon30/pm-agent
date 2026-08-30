"""The scorers decide what the headline numbers say, so a scorer that is wrong is worse than no
eval at all. These tests are about the two things that could silently mislead: an identifier
scan that misses an invented ticket, and one that invents a violation out of ordinary prose."""

from typing import Any

from evals.scorers import (
    SCORERS,
    duplicate_detected,
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


# --- an update the harness resolved itself ------------------------------------------------------

def _run(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "reconcile": {"items": items},
        "issues": [{"identifier": "INV-25", "title": "Add invoice CSV export"}],
        "seeded_identifiers": ["INV-25"],
    }


def test_an_update_the_harness_matched_itself_still_counts_as_catching_the_duplicate() -> None:
    """The reconciler said "update" and named nothing; the stage found the one issue that
    answered to the title. The team got the right outcome, so the eval must say so."""
    row = {"expected": {"title_contains": "csv export"}}

    score = duplicate_detected(row, _run([
        {"title": "Put the invoice CSV export behind a flag", "disposition": "update",
         "target_issue": "INV-25", "match_note": "matched to INV-25 by title"}]))

    assert score.passed


def test_an_update_that_was_downgraded_is_not_counted_as_catching_it() -> None:
    """A labelled possible duplicate is the honest fallback, not a success. Scoring it as one
    would hide the reconciler's miss behind the harness's recovery."""
    row = {"expected": {"title_contains": "csv export"}}

    score = duplicate_detected(row, _run([
        {"title": "Put the invoice CSV export behind a flag", "disposition": "new",
         "target_issue": None,
         "description": "Possibly duplicates existing work — the call referred to something "
                        "already tracked but I couldn't tell which."}]))

    assert not score.passed


def test_a_brain_nothing_reads_is_reported_as_such() -> None:
    """Something stored and never handed to a stage is worse than not stored, because it looks
    like memory. This is the plumbing question, not the judgment one."""
    from evals.run_evals import brain_reached

    brain = [{"slug": "ownership", "entries": [
        {"id": "a", "page": "ownership"}, {"id": "b", "page": "ownership"}]}]

    assert brain_reached({"brain": brain, "payloads": [
        {"brain": [{"ref": "wiki:ownership#a"}]}]}) == "1/2"
    assert brain_reached({"brain": brain, "payloads": []}) == "0/2"
    assert brain_reached({"brain": [], "payloads": []}) == "n/a", "nothing stored, nothing owed"


def test_a_retired_rule_is_not_counted_against_the_plumbing() -> None:
    from evals.run_evals import brain_reached

    brain = [{"slug": "ownership", "entries": [
        {"id": "a", "page": "ownership"},
        {"id": "old", "page": "ownership", "retired_at": "2026-08-30T00:00:00+00:00"}]}]

    assert brain_reached({"brain": brain,
                          "payloads": [{"brain": [{"ref": "wiki:ownership#a"}]}]}) == "1/1"

from datetime import UTC, datetime
from typing import Any

from app.harness.deps import Deps
from app.harness.store.decisions import DecisionStore

from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_db import FakeDb


async def test_decisions_are_stored_with_a_fathom_source_pointer_and_empty_links() -> None:
    db = FakeDb()
    store = DecisionStore(db, FakeClock(datetime(2026, 8, 27, 9, 0, tzinfo=UTC)))
    ids = await store.add_many("acme", "fathom:msg_1", [
        {"statement": "Reminders move to 3 days", "rejected_options": ["SMS"],
         "evidence": [{"quote": "move payment reminders to three days", "timestamp": "00:01:42",
                       "speaker": "Maya Chen"}]},
    ], meeting={"meeting_id": "8841201", "title": "Q3", "url": "https://fathom.video/share/abc"})
    assert len(ids) == 1
    doc = await db.get("decisions", ids[0])
    assert doc is not None
    assert doc["source"] == "fathom:8841201@00:01:42"
    assert doc["quote"] == "move payment reminders to three days"
    assert doc["rejected_options"] == ["SMS"] and doc["linked_issue_ids"] == []
    assert doc["project_id"] == "acme" and doc["event_id"] == "fathom:msg_1"
    assert doc["created_at"] == "2026-08-27T09:00:00+00:00"


# --- the same decision, said twice ------------------------------------------------------------------

MEETING = {"meeting_id": "8841201", "title": "Q3 Billing planning", "url": "https://f.video/x"}


def spoken(statement: str, quote: str, at: str) -> dict[str, Any]:
    return {"statement": statement, "rejected_options": [],
            "evidence": [{"quote": quote, "timestamp": at, "speaker": "Maya Chen"}]}


async def test_a_decision_restated_later_in_the_call_is_one_entry(deps: Deps) -> None:
    """A model asked to extract decisions from two moments faithfully returns two. They are one
    decision, and a ledger that lists both makes a reader wonder which the team took."""
    store = DecisionStore(deps.db, deps.clock)

    ids = await store.add_many("acme", "ev-1", [
        spoken("Move payment reminders to three days after the due date.",
               "let's move payment reminders to three days after the due date", "00:01:42"),
        spoken("Move payment reminders to three days after due.",
               "so, three days after due, agreed", "00:04:10"),
    ], MEETING)

    assert ids[0] == ids[1], "the second reference points at the first entry"
    assert await deps.db.count("decisions", [("project_id", "==", "acme")]) == 1


async def test_the_second_moment_is_kept_as_evidence_rather_than_thrown_away(
    deps: Deps,
) -> None:
    store = DecisionStore(deps.db, deps.clock)
    ids = await store.add_many("acme", "ev-1", [
        spoken("Move payment reminders to three days after the due date.",
               "let's move payment reminders to three days after the due date", "00:01:42"),
        spoken("Move payment reminders to three days after due.",
               "so, three days after due, agreed", "00:04:10"),
    ], MEETING)

    kept = await deps.db.get("decisions", ids[0])
    assert kept is not None
    assert kept["quote"] == "let's move payment reminders to three days after the due date"
    assert kept["also_quoted"] == [
        {"quote": "so, three days after due, agreed", "source": "fathom:8841201@00:04:10"}]


async def test_a_decision_restated_on_a_later_call_still_finds_the_first(deps: Deps) -> None:
    store = DecisionStore(deps.db, deps.clock)
    first = await store.add_many("acme", "ev-1", [
        spoken("Keep SMS reminders off for now.", "no SMS for now", "00:02:00")], MEETING)
    again = await store.add_many("acme", "ev-2", [
        spoken("Keep SMS reminders off for now, email only.", "still no SMS", "00:03:00")],
        MEETING)

    assert again == first
    assert await deps.db.count("decisions", []) == 1


async def test_two_different_decisions_are_two_entries(deps: Deps) -> None:
    store = DecisionStore(deps.db, deps.clock)

    ids = await store.add_many("acme", "ev-1", [
        spoken("Move payment reminders to three days after the due date.", "three days", "00:01"),
        spoken("Ship the invoice CSV export behind a flag.", "behind the flag", "00:02"),
    ], MEETING)

    assert len(set(ids)) == 2
    assert await deps.db.count("decisions", []) == 2


async def test_another_project_never_absorbs_this_ones_decision(deps: Deps) -> None:
    store = DecisionStore(deps.db, deps.clock)
    mine = await store.add_many("acme", "ev-1", [
        spoken("Move payment reminders to three days.", "three days", "00:01")], MEETING)
    theirs = await store.add_many("other", "ev-1", [
        spoken("Move payment reminders to three days.", "three days", "00:01")], MEETING)

    assert mine != theirs
    assert await deps.db.count("decisions", []) == 2

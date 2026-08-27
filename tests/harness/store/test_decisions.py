from datetime import UTC, datetime

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

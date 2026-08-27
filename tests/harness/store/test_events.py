from datetime import UTC, datetime

from app.harness.store.events import EventStore

from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_db import FakeDb


async def test_recording_the_same_provider_event_twice_returns_none_the_second_time() -> None:
    db = FakeDb()
    events = EventStore(db, FakeClock(datetime(2026, 8, 27, 9, 0, tzinfo=UTC)))
    first = await events.record(provider="fathom", provider_event_id="msg_1",
                                payload={"a": 1}, project_id="acme")
    assert first == "fathom:msg_1"
    second = await events.record(provider="fathom", provider_event_id="msg_1",
                                payload={"a": 2}, project_id="acme")
    assert second is None
    doc = await events.get("fathom:msg_1")
    assert doc is not None
    assert doc["payload"] == {"a": 1} and doc["received_at"] == "2026-08-27T09:00:00+00:00"


async def test_note_appends_without_touching_the_payload() -> None:
    db = FakeDb()
    events = EventStore(db, FakeClock(datetime(2026, 8, 27, 9, 0, tzinfo=UTC)))
    await events.record(provider="fathom", provider_event_id="m", payload={}, project_id="acme")
    await events.note("fathom:m", "no transcript")
    doc = await events.get("fathom:m")
    assert doc is not None and doc["notes"] == ["no transcript"]

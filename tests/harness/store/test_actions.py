from datetime import UTC, datetime

from app.harness.store.actions import ActionStore, cap_kind

from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_db import FakeDb

T0 = datetime(2026, 8, 27, 9, 0, tzinfo=UTC)


def make() -> tuple[ActionStore, FakeDb, FakeClock]:
    db, clock = FakeDb(), FakeClock(T0)
    return ActionStore(db, clock), db, clock


async def begin(store: ActionStore, **kw: object) -> str:
    payload: dict[str, object] = {
        "task_id": "task-1", "project_id": "acme", "kind": "linear.create_issue",
        "idempotency_key": "key-1", "inputs": {"title": "Move reminders to 3 days"},
    }
    payload.update(kw)
    return await store.begin(**payload)  # type: ignore[arg-type]


def test_pings_and_writes_spend_different_budgets() -> None:
    assert cap_kind("slack.post") == "ping"
    assert cap_kind("linear.create_issue") == "write"
    assert cap_kind("linear.comment") == "write"


async def test_begin_records_the_intent_before_the_effect_happens() -> None:
    store, db, _ = make()
    action_id = await begin(store, citations=["fathom:8841201@00:01:42"],
                            checks_passed=["roster", "priority"])
    doc = await db.get("actions", action_id)
    assert doc is not None
    assert doc["status"] == "pending" and doc["target_ids"] == {} and doc["revert"] == {}
    assert doc["idempotency_key"] == "key-1" and doc["cap_kind"] == "write"
    assert doc["citations"] == ["fathom:8841201@00:01:42"]
    assert doc["checks_passed"] == ["roster", "priority"]
    assert doc["created_at"] == "2026-08-27T09:00:00+00:00" and doc["day"] == "2026-08-27"


async def test_finish_records_what_was_touched_and_how_to_undo_it() -> None:
    store, db, _ = make()
    action_id = await begin(store)
    await store.finish(action_id, target_ids={"identifier": "INV-143"},
                       revert={"op": "archive", "issue": "INV-143"})
    doc = await db.get("actions", action_id)
    assert doc is not None
    assert doc["status"] == "done" and doc["target_ids"] == {"identifier": "INV-143"}
    assert doc["revert"] == {"op": "archive", "issue": "INV-143"}
    assert doc["finished_at"] == "2026-08-27T09:00:00+00:00"


async def test_a_failed_action_records_its_reason_and_stops_counting() -> None:
    store, db, _ = make()
    action_id = await begin(store)
    await store.fail(action_id, "linear unavailable")
    doc = await db.get("actions", action_id)
    assert doc is not None and doc["status"] == "failed" and doc["error"] == "linear unavailable"
    assert await store.counts_today("acme") == {"write": 0, "ping": 0}


async def test_find_by_key_lets_a_retry_recognise_a_write_it_already_performed() -> None:
    store, _, _ = make()
    action_id = await begin(store)
    await store.finish(action_id, target_ids={"identifier": "INV-143"}, revert={})
    earlier = await store.find_by_key("key-1")
    assert earlier is not None
    assert earlier["id"] == action_id and earlier["target_ids"]["identifier"] == "INV-143"
    assert await store.find_by_key("key-unknown") is None


async def test_a_pending_action_is_still_found_so_a_crashed_write_is_not_repeated_blindly(
) -> None:
    store, _, _ = make()
    action_id = await begin(store)  # crash happens here, before finish()
    found = await store.find_by_key("key-1")
    assert found is not None and found["id"] == action_id and found["status"] == "pending"


async def test_counts_today_separates_writes_from_pings_and_is_scoped_to_the_project() -> None:
    store, _, _ = make()
    await store.finish(await begin(store, idempotency_key="k1"), target_ids={}, revert={})
    await store.finish(await begin(store, idempotency_key="k2", kind="linear.comment"),
                       target_ids={}, revert={})
    await store.finish(await begin(store, idempotency_key="k3", kind="slack.post"),
                       target_ids={}, revert={})
    await store.finish(await begin(store, idempotency_key="k4", project_id="other"),
                       target_ids={}, revert={})
    assert await store.counts_today("acme") == {"write": 2, "ping": 1}
    assert await store.counts_today("other") == {"write": 1, "ping": 0}


async def test_yesterdays_actions_do_not_count_against_todays_budget() -> None:
    store, _, clock = make()
    await store.finish(await begin(store), target_ids={}, revert={})
    clock.advance(days=1)
    assert await store.counts_today("acme") == {"write": 0, "ping": 0}
    assert await store.counts_today("acme", day="2026-08-27") == {"write": 1, "ping": 0}


async def test_a_reverted_action_still_counts_because_the_interruption_happened() -> None:
    store, _, _ = make()
    action_id = await begin(store, kind="slack.post")
    await store.finish(action_id, target_ids={"ts": "1.1"}, revert={"op": "edit"})
    await store.mark_reverted(action_id, by="U-maya")
    doc = await store.get(action_id)
    assert doc is not None and doc["status"] == "reverted" and doc["reverted_by"] == "U-maya"
    assert doc["reverted_at"] == "2026-08-27T09:00:00+00:00"
    assert await store.counts_today("acme") == {"write": 0, "ping": 1}


async def test_list_since_returns_this_projects_actions_oldest_first() -> None:
    store, _, clock = make()
    first = await begin(store, idempotency_key="k1")
    clock.advance(hours=1)
    second = await begin(store, idempotency_key="k2")
    clock.advance(hours=1)
    await begin(store, idempotency_key="k3", project_id="other")
    rows = await store.list_since("acme", "2026-08-27T00:00:00+00:00")
    assert [r["id"] for r in rows] == [first, second]
    assert await store.list_since("acme", "2026-08-27T09:30:00+00:00") == [
        r for r in rows if r["id"] == second
    ]

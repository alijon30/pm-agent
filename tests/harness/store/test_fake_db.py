from tests.fakes.fake_db import FakeDb


async def test_create_is_first_writer_wins() -> None:
    db = FakeDb()
    assert await db.create("events", "fathom:1", {"a": 1}) is True
    assert await db.create("events", "fathom:1", {"a": 2}) is False
    doc = await db.get("events", "fathom:1")
    assert doc == {"id": "fathom:1", "a": 1}


async def test_get_returns_none_for_missing_docs() -> None:
    db = FakeDb()
    assert await db.get("tasks", "nope") is None


async def test_update_merges_fields_and_set_replaces() -> None:
    db = FakeDb()
    await db.set("tasks", "t1", {"status": "queued", "attempts": 0})
    await db.update("tasks", "t1", {"status": "leased"})
    assert await db.get("tasks", "t1") == {"id": "t1", "status": "leased", "attempts": 0}
    await db.set("tasks", "t1", {"status": "done"})
    assert await db.get("tasks", "t1") == {"id": "t1", "status": "done"}


async def test_query_filters_orders_and_limits() -> None:
    db = FakeDb()
    await db.set("tasks", "a", {"status": "queued", "due_at": "2026-08-27T09:02:00+00:00"})
    await db.set("tasks", "b", {"status": "queued", "due_at": "2026-08-27T09:00:00+00:00"})
    await db.set("tasks", "c", {"status": "done", "due_at": "2026-08-27T08:00:00+00:00"})
    await db.set("tasks", "d", {"status": "queued", "due_at": "2026-08-27T10:00:00+00:00"})
    rows = await db.query(
        "tasks",
        [("status", "==", "queued"), ("due_at", "<=", "2026-08-27T09:05:00+00:00")],
        order_by="due_at",
        limit=5,
    )
    assert [r["id"] for r in rows] == ["b", "a"]
    rows = await db.query("tasks", [("status", "in", ["queued", "done"])], order_by="due_at", limit=2)
    assert [r["id"] for r in rows] == ["c", "b"]


async def test_count_counts_matching_docs() -> None:
    db = FakeDb()
    await db.set("tasks", "a", {"parent_task_id": "p"})
    await db.set("tasks", "b", {"parent_task_id": "p"})
    await db.set("tasks", "c", {"parent_task_id": "q"})
    assert await db.count("tasks", [("parent_task_id", "==", "p")]) == 2


async def test_cas_applies_updater_and_creates_only_when_predicate_holds() -> None:
    db = FakeDb()
    await db.set("tasks", "t1", {"status": "queued", "attempts": 0})
    ok = await db.cas(
        "tasks", "t1",
        predicate=lambda d: d["status"] == "queued",
        updater=lambda d: {"status": "leased", "attempts": d["attempts"] + 1},
        creates=[("tasks", "child", {"status": "queued"})],
    )
    assert ok is True
    assert (await db.get("tasks", "t1"))["status"] == "leased"  # type: ignore[index]
    assert (await db.get("tasks", "t1"))["attempts"] == 1  # type: ignore[index]
    assert await db.get("tasks", "child") is not None

    ok = await db.cas(
        "tasks", "t1",
        predicate=lambda d: d["status"] == "queued",
        updater=lambda d: {"status": "leased"},
        creates=[("tasks", "child2", {"status": "queued"})],
    )
    assert ok is False
    assert await db.get("tasks", "child2") is None


async def test_cas_on_a_missing_doc_is_false_and_creates_nothing() -> None:
    db = FakeDb()
    ok = await db.cas("tasks", "ghost", lambda d: True, lambda d: {}, [("tasks", "x", {})])
    assert ok is False
    assert await db.get("tasks", "x") is None


async def test_cas_applies_extra_updates_to_other_docs_in_the_same_transaction() -> None:
    db = FakeDb()
    await db.set("tasks", "t1", {"status": "leased"})
    await db.set("tasks", "old", {"status": "queued"})
    ok = await db.cas("tasks", "t1", lambda d: d["status"] == "leased", lambda d: {"status": "done"},
                      updates=[("tasks", "old", {"status": "cancelled"})])
    assert ok is True
    assert (await db.get("tasks", "old"))["status"] == "cancelled"  # type: ignore[index]
    ok = await db.cas("tasks", "t1", lambda d: d["status"] == "leased", lambda d: {},
                      updates=[("tasks", "old", {"status": "queued"})])
    assert ok is False
    assert (await db.get("tasks", "old"))["status"] == "cancelled"  # type: ignore[index]


async def test_array_contains_matches_list_fields() -> None:
    db = FakeDb()
    await db.set("tasks", "a", {"depends_on": ["x", "y"]})
    await db.set("tasks", "b", {"depends_on": ["z"]})
    await db.set("tasks", "c", {"depends_on": []})
    rows = await db.query("tasks", [("depends_on", "array_contains", "y")])
    assert [r["id"] for r in rows] == ["a"]


async def test_delete_removes_a_doc_and_deleting_a_missing_one_is_a_no_op() -> None:
    db = FakeDb()
    await db.set("tasks", "t1", {"status": "queued"})
    await db.delete("tasks", "t1")
    assert await db.get("tasks", "t1") is None
    await db.delete("tasks", "never-existed")

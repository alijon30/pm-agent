from datetime import UTC, datetime, timedelta

from app.store.tasks import TaskQueue

from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_db import FakeDb

T0 = datetime(2026, 8, 27, 9, 0, tzinfo=UTC)


def make() -> tuple[TaskQueue, FakeDb, FakeClock]:
    db, clock = FakeDb(), FakeClock(T0)
    return TaskQueue(db, clock, lease_minutes=15), db, clock


async def enqueue(q: TaskQueue, **kw) -> str:  # type: ignore[no-untyped-def]
    kw.setdefault("kind", "extract")
    kw.setdefault("project_id", "acme")
    kw.setdefault("payload", {})
    kw.setdefault("reason", "test")
    tid = await q.enqueue(**kw)
    assert tid is not None
    return tid


async def status(db: FakeDb, tid: str) -> str:
    doc = await db.get("tasks", tid)
    assert doc is not None
    return str(doc["status"])


# --- basics -----------------------------------------------------------------------------------

async def test_enqueue_creates_a_queued_root_task_due_now_by_default() -> None:
    q, db, _ = make()
    tid = await enqueue(q, payload={"event_id": "e1"}, reason="call finished", root_event_id="e1")
    doc = await db.get("tasks", tid)
    assert doc is not None
    assert doc["status"] == "queued" and doc["depth"] == 0 and doc["attempts"] == 0
    assert doc["due_at"] == "2026-08-27T09:00:00+00:00"
    assert doc["root_event_id"] == "e1" and doc["parent_task_id"] is None
    assert doc["depends_on"] == [] and doc["on_dep_failed"] == "skip" and doc["on_unmet"] == "none"


async def test_due_returns_only_matching_kinds_that_are_due_oldest_first() -> None:
    q, _, clock = make()
    a = await enqueue(q, reason="a", due_at=T0 + timedelta(minutes=2))
    b = await enqueue(q, reason="b")
    await enqueue(q, kind="reconcile", reason="c")
    await enqueue(q, reason="d", due_at=T0 + timedelta(hours=1))
    clock.advance(minutes=3)
    assert [t["id"] for t in await q.due(["extract"], limit=10)] == [b, a]


async def test_claim_leases_a_due_task_and_counts_the_attempt() -> None:
    q, _, _ = make()
    tid = await enqueue(q)
    claimed = await q.claim(tid)
    assert claimed is not None
    assert claimed["status"] == "leased" and claimed["attempts"] == 1
    assert claimed["lease_until"] == "2026-08-27T09:15:00+00:00"
    assert await q.claim(tid) is None


async def test_an_expired_lease_is_reclaimable_and_a_live_one_is_not() -> None:
    q, _, clock = make()
    tid = await enqueue(q)
    await q.claim(tid)
    clock.advance(minutes=14)
    assert await q.due(["extract"], limit=10) == []
    clock.advance(minutes=2)
    assert [t["id"] for t in await q.due(["extract"], limit=10)] == [tid]
    reclaimed = await q.claim(tid)
    assert reclaimed is not None and reclaimed["attempts"] == 2


async def test_complete_marks_done_and_creates_children_atomically_with_lineage() -> None:
    q, db, _ = make()
    tid = await enqueue(q, root_event_id="e1")
    task = await q.claim(tid)
    assert task is not None
    ids = await q.complete(task, {"n": 3}, [
        {"kind": "reconcile", "payload": {"k": 1}, "reason": "reconcile 3 items"},
    ])
    assert len(ids) == 1
    parent = await db.get("tasks", tid)
    child = await db.get("tasks", ids[0])
    assert parent is not None and child is not None
    assert parent["status"] == "done" and parent["result"] == {"n": 3}
    assert child["status"] == "queued" and child["depth"] == 1
    assert child["parent_task_id"] == tid and child["root_event_id"] == "e1"
    assert child["project_id"] == "acme" and child["plan_id"] is not None


async def test_complete_refuses_children_beyond_max_depth_and_records_it() -> None:
    q, db, _ = make()
    tid = await enqueue(q, kind="check_issue_state")
    await db.update("tasks", tid, {"depth": 4})
    task = await q.claim(tid)
    assert task is not None
    ids = await q.complete(task, {}, [{"kind": "nudge", "payload": {}, "reason": "again"}])
    assert ids == []
    parent = await db.get("tasks", tid)
    assert parent is not None and parent["status"] == "done"
    assert parent["refused_enqueues"][0]["kind"] == "nudge"
    assert "max_depth" in parent["refused_enqueues"][0]["reason"]


async def test_complete_is_a_no_op_if_the_lease_was_lost() -> None:
    q, db, _ = make()
    tid = await enqueue(q)
    task = await q.claim(tid)
    assert task is not None
    await db.update("tasks", tid, {"status": "queued"})
    ids = await q.complete(task, {"n": 1}, [{"kind": "reconcile", "payload": {}, "reason": "r"}])
    assert ids == []
    assert await db.count("tasks", [("kind", "==", "reconcile")]) == 0


async def test_fail_requeues_with_backoff_then_marks_failed_on_the_third_attempt() -> None:
    q, db, clock = make()
    tid = await enqueue(q)
    t = await q.claim(tid)
    assert t is not None and await q.fail(t, "boom") == "queued"
    doc = await db.get("tasks", tid)
    assert doc is not None and doc["due_at"] == "2026-08-27T09:01:00+00:00"
    clock.advance(minutes=2)
    t = await q.claim(tid)
    assert t is not None and await q.fail(t, "boom") == "queued"
    doc = await db.get("tasks", tid)
    assert doc is not None and doc["due_at"] == "2026-08-27T09:07:00+00:00"
    clock.advance(minutes=6)
    t = await q.claim(tid)
    assert t is not None and await q.fail(t, "boom") == "failed"
    assert await status(db, tid) == "failed"


async def test_defer_pushes_due_at_and_a_deferred_task_becomes_due_again() -> None:
    q, db, clock = make()
    tid = await enqueue(q, kind="nudge")
    t = await q.claim(tid)
    assert t is not None
    await q.defer(t, T0 + timedelta(hours=12), "quiet hours")
    doc = await db.get("tasks", tid)
    assert doc is not None and doc["status"] == "deferred" and doc["defer_reason"] == "quiet hours"
    assert await q.due(["nudge"], limit=10) == []
    clock.advance(hours=12)
    assert [x["id"] for x in await q.due(["nudge"], limit=10)] == [tid]


# --- dependencies -----------------------------------------------------------------------------

async def test_a_task_with_an_unfinished_dependency_is_blocked_and_not_due() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state", reason="in progress?")
    b = await enqueue(q, kind="check_pr_exists", reason="pr?", depends_on=[a])
    assert await status(db, b) == "blocked"
    assert [t["id"] for t in await q.due(["check_issue_state", "check_pr_exists"], 10)] == [a]


async def test_completing_a_dependency_promotes_the_dependent_on_the_next_due_sweep() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state")
    b = await enqueue(q, kind="check_pr_exists", depends_on=[a])
    ta = await q.claim(a)
    assert ta is not None
    await q.complete(ta, {"met": True}, [])
    assert [t["id"] for t in await q.due(["check_pr_exists"], 10)] == [b]
    assert await status(db, b) == "queued"


async def test_a_dependent_waits_for_all_of_its_dependencies() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state")
    b = await enqueue(q, kind="check_pr_exists")
    c = await enqueue(q, kind="check_pr_reviewed", depends_on=[a, b])
    ta = await q.claim(a)
    assert ta is not None
    await q.complete(ta, {}, [])
    await q.due(["check_pr_reviewed"], 10)
    assert await status(db, c) == "blocked"
    tb = await q.claim(b)
    assert tb is not None
    await q.complete(tb, {}, [])
    await q.due(["check_pr_reviewed"], 10)
    assert await status(db, c) == "queued"


async def test_a_failed_dependency_skips_the_dependent_by_default() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state")
    b = await enqueue(q, kind="check_pr_exists", depends_on=[a])
    await db.update("tasks", a, {"status": "failed"})
    await q.promote_ready()
    assert await status(db, b) == "skipped"


async def test_run_anyway_treats_a_failed_dependency_as_satisfied() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state")
    b = await enqueue(q, kind="check_pr_exists", depends_on=[a], on_dep_failed="run_anyway")
    await db.update("tasks", a, {"status": "failed"})
    await q.promote_ready()
    assert await status(db, b) == "queued"


async def test_cancel_on_dep_failed_cascades_down_the_chain() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state")
    b = await enqueue(q, kind="check_pr_exists", depends_on=[a], on_dep_failed="cancel")
    c = await enqueue(q, kind="check_pr_reviewed", depends_on=[b])
    await db.update("tasks", a, {"status": "failed"})
    await q.promote_ready()
    assert await status(db, b) == "cancelled"
    assert await status(db, c) == "cancelled"


async def test_cancel_cascades_to_dependents_and_reports_every_id() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state")
    b = await enqueue(q, kind="check_pr_exists", depends_on=[a])
    c = await enqueue(q, kind="check_pr_reviewed", depends_on=[b])
    d = await enqueue(q, kind="nudge")  # unrelated
    cancelled = await q.cancel(a, "issue reverted")
    assert set(cancelled) == {a, b, c}
    assert await status(db, d) == "queued"
    doc = await db.get("tasks", c)
    assert doc is not None and doc["error"] == "cancelled: issue reverted"


async def test_a_done_task_cannot_be_cancelled() -> None:
    q, db, _ = make()
    a = await enqueue(q)
    ta = await q.claim(a)
    assert ta is not None
    await q.complete(ta, {}, [])
    assert await q.cancel(a, "late") == []
    assert await status(db, a) == "done"


# --- plans ------------------------------------------------------------------------------------

PLAN = [
    {"key": "impl", "kind": "check_issue_state", "payload": {}, "reason": "in progress by Thu",
     "params": {"issue": "INV-142", "expect": ["In Progress", "Done"]},
     "due_at": "2026-08-28T16:00:00+00:00", "on_unmet": "nudge_assignee"},
    {"key": "pr", "kind": "check_pr_exists", "payload": {}, "reason": "pr open",
     "params": {"issue": "INV-142"}, "depends_on": ["impl"],
     "due_at": "2026-08-29T16:00:00+00:00", "on_unmet": "nudge_assignee"},
    {"key": "review", "kind": "check_pr_reviewed", "payload": {}, "reason": "reviewed",
     "params": {"issue": "INV-142"}, "depends_on": ["pr"],
     "due_at": "2026-08-30T16:00:00+00:00", "on_unmet": "nudge_reviewer"},
]


async def test_a_plan_materialises_as_a_graph_with_keys_resolved_to_ids() -> None:
    q, db, _ = make()
    planner_task = await enqueue(q, kind="plan", root_event_id="e1")
    tp = await q.claim(planner_task)
    assert tp is not None
    ids = await q.complete(tp, {"plan": "ok"}, PLAN)
    assert len(ids) == 3
    impl = await db.get("tasks", ids[0])
    pr = await db.get("tasks", ids[1])
    review = await db.get("tasks", ids[2])
    assert impl is not None and pr is not None and review is not None
    assert impl["status"] == "queued" and impl["depends_on"] == []
    assert pr["status"] == "blocked" and pr["depends_on"] == [impl["id"]]
    assert review["status"] == "blocked" and review["depends_on"] == [pr["id"]]
    assert impl["key"] == "impl" and impl["params"]["issue"] == "INV-142"
    assert impl["on_unmet"] == "nudge_assignee" and pr["plan_id"] == impl["plan_id"]
    assert impl["depth"] == 1 and impl["root_event_id"] == "e1"


async def test_a_plan_may_depend_on_an_existing_open_task_by_id() -> None:
    q, db, _ = make()
    existing = await enqueue(q, kind="check_issue_state")
    planner_task = await enqueue(q, kind="plan")
    tp = await q.claim(planner_task)
    assert tp is not None
    ids = await q.complete(tp, {}, [
        {"kind": "nudge", "payload": {}, "reason": "after", "depends_on": [existing]},
    ])
    doc = await db.get("tasks", ids[0])
    assert doc is not None and doc["status"] == "blocked" and doc["depends_on"] == [existing]


async def test_supersedes_cancels_the_named_open_tasks_and_their_dependents() -> None:
    q, db, _ = make()
    old_a = await enqueue(q, kind="check_issue_state")
    old_b = await enqueue(q, kind="check_pr_exists", depends_on=[old_a])
    planner_task = await enqueue(q, kind="plan")
    tp = await q.claim(planner_task)
    assert tp is not None
    ids = await q.complete(tp, {}, [{"kind": "check_issue_state", "payload": {}, "reason": "new"}],
                           supersedes=[old_a])
    assert len(ids) == 1
    assert await status(db, old_a) == "cancelled" and await status(db, old_b) == "cancelled"


async def test_open_count_counts_only_open_statuses() -> None:
    q, _, _ = make()
    a = await enqueue(q)
    await enqueue(q, kind="check_pr_exists", depends_on=[a])
    done = await enqueue(q)
    td = await q.claim(done)
    assert td is not None
    await q.complete(td, {}, [])
    assert await q.open_count("acme") == 2

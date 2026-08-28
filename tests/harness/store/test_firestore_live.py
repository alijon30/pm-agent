"""Runs the FakeDb contract against real Firestore. Needs ADC and PM_GCP_PROJECT; skipped in CI."""

import os

import pytest
from app.harness.store.firestore import FirestoreDb

pytestmark = pytest.mark.live
live = pytest.mark.skipif(not os.environ.get("PM_GCP_PROJECT"), reason="no PM_GCP_PROJECT")


@live
async def test_firestore_db_honours_the_fake_db_contract() -> None:
    db = FirestoreDb(os.environ["PM_GCP_PROJECT"])
    # A fixed collection, because the filtered-and-ordered queries below need composite indexes
    # and Firestore indexes are declared per collection group (deploy/secrets.md lists them).
    col = "_contract"
    for doc_id in ("t1", "t2", "t3", "child"):
        await db.delete(col, doc_id)
    assert await db.create(col, "t1", {"status": "queued", "attempts": 0, "due_at": "b"}) is True
    assert await db.create(col, "t1", {"status": "x"}) is False
    await db.set(col, "t2", {"status": "queued", "attempts": 0, "due_at": "a"})
    rows = await db.query(col, [("status", "==", "queued")], order_by="due_at", limit=5)
    assert [r["id"] for r in rows] == ["t2", "t1"]
    assert await db.count(col, [("status", "==", "queued")]) == 2
    ok = await db.cas(col, "t1", lambda d: d["status"] == "queued",
                      lambda d: {"status": "leased", "attempts": d["attempts"] + 1},
                      [(col, "child", {"status": "queued"})])
    assert ok is True
    assert (await db.get(col, "t1")) == {"id": "t1", "status": "leased", "attempts": 1, "due_at": "b"}
    assert await db.get(col, "child") is not None
    assert await db.cas(col, "t1", lambda d: d["status"] == "queued", lambda d: {}) is False
    ok = await db.cas(col, "t1", lambda d: d["status"] == "leased", lambda d: {"status": "done"},
                      updates=[(col, "t2", {"status": "cancelled"})])
    assert ok is True and (await db.get(col, "t2"))["status"] == "cancelled"  # type: ignore[index]
    await db.set(col, "t3", {"depends_on": ["t1"]})
    assert [r["id"] for r in await db.query(col, [("depends_on", "array_contains", "t1")])] == ["t3"]

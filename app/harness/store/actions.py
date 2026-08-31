"""The audit log: one document per side effect the harness performed."""

from __future__ import annotations

from typing import Any

from app.harness.core.clock import Clock, iso
from app.harness.core.keys import new_id
from app.harness.store.db import Db, Doc

PING_KINDS = ("slack.post", "slack.dm")


def cap_kind(action_kind: str) -> str:
    """Which daily budget this action spends."""
    return "ping" if action_kind in PING_KINDS else "write"


class ActionStore:
    def __init__(self, db: Db, clock: Clock) -> None:
        self._db = db
        self._clock = clock

    async def begin(
        self,
        *,
        task_id: str,
        project_id: str,
        kind: str,
        idempotency_key: str,
        inputs: dict[str, Any],
        citations: list[str] | None = None,
        checks_passed: list[str] | None = None,
    ) -> str:
        """Record the intent. Returns the action id; the caller performs the effect next."""
        action_id = new_id()
        await self._db.create("actions", action_id, {
            "kind": kind,
            "status": "pending",
            "idempotency_key": idempotency_key,
            "cap_kind": cap_kind(kind),
            "inputs": inputs,
            "citations": list(citations or []),
            "checks_passed": list(checks_passed or []),
            "target_ids": {},
            "revert": {},
            "error": None,
            "reverted_at": None,
            "reverted_by": None,
            "task_id": task_id,
            "project_id": project_id,
            "created_at": iso(self._clock.now()),
            "day": iso(self._clock.now())[:10],
            "finished_at": None,
        })
        return action_id

    async def finish(
        self, action_id: str, *, target_ids: dict[str, Any], revert: dict[str, Any]
    ) -> None:
        await self._db.update("actions", action_id, {
            "status": "done",
            "target_ids": target_ids,
            "revert": revert,
            "finished_at": iso(self._clock.now()),
        })

    async def fail(self, action_id: str, error: str) -> None:
        await self._db.update("actions", action_id, {
            "status": "failed",
            "error": error,
            "finished_at": iso(self._clock.now()),
        })

    async def find_by_key(self, idempotency_key: str) -> Doc | None:
        """The earlier attempt at this exact write, if there was one. A retry uses this to skip
        a write it already performed — including one whose `done` mark never landed."""
        rows = await self._db.query(
            "actions", [("idempotency_key", "==", idempotency_key)], order_by="created_at"
        )
        return rows[0] if rows else None

    async def get(self, action_id: str) -> Doc | None:
        return await self._db.get("actions", action_id)

    async def mark_reverted(self, action_id: str, by: str) -> None:
        await self._db.update("actions", action_id, {
            "status": "reverted",
            "reverted_at": iso(self._clock.now()),
            "reverted_by": by,
        })

    async def counts_today(self, project_id: str, day: str | None = None) -> dict[str, int]:
        """What the caps gate reads. Reverted actions still count — the interruption happened."""
        target_day = day or iso(self._clock.now())[:10]
        rows = await self._db.query(
            "actions", [("project_id", "==", project_id), ("day", "==", target_day)]
        )
        counts = {"write": 0, "ping": 0}
        for row in rows:
            if row.get("status") == "failed":
                continue
            counts[str(row.get("cap_kind") or "write")] += 1
        return counts

    async def list_since(self, project_id: str, since_iso: str) -> list[Doc]:
        rows = await self._db.query(
            "actions", [("project_id", "==", project_id), ("created_at", ">=", since_iso)],
            order_by="created_at",
        )
        return rows

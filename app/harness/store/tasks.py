"""The durable task-graph queue. Firestore documents are the tasks; a lease is the claim;
dependencies make a task `blocked` until every dependency is done; a cas() that marks a task
done and creates its children (a plan) in one transaction is what makes "did the work but
failed to schedule the follow-up" impossible. The model never touches this module: stages hand
the runner child specs, and the runner calls complete()."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from app.harness.core.clock import Clock, iso, parse_iso
from app.harness.core.keys import new_id
from app.harness.store.db import Create, Db, Doc, Update
from app.harness.verify.lineage import DEFAULT_POLICY, check_lineage

BACKOFF_SECONDS = (60, 300, 900)
OPEN_STATUSES = ("queued", "blocked", "leased", "deferred")
TERMINAL_BAD = ("failed", "cancelled", "skipped")
DEP_POLICIES = ("skip", "run_anyway", "cancel")


class TaskQueue:
    def __init__(self, db: Db, clock: Clock, *, lease_minutes: int = 15) -> None:
        self._db = db
        self._clock = clock
        self._lease = timedelta(minutes=lease_minutes)

    # --- documents ----------------------------------------------------------------------------

    def _doc(
        self,
        *,
        kind: str,
        project_id: str,
        payload: dict[str, Any],
        reason: str,
        due_at: str,
        depth: int,
        parent_task_id: str | None,
        root_event_id: str | None,
        params: dict[str, Any] | None = None,
        depends_on: Sequence[str] = (),
        blocked: bool = False,
        on_dep_failed: str = "skip",
        on_unmet: str = "none",
        context: dict[str, Any] | None = None,
        key: str | None = None,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        if on_dep_failed not in DEP_POLICIES:
            raise ValueError(f"on_dep_failed must be one of {DEP_POLICIES}, got {on_dep_failed!r}")
        return {
            "kind": kind,
            "params": params or {},
            "project_id": project_id,
            "payload": payload,
            "reason": reason,
            "status": "blocked" if blocked else "queued",
            "due_at": due_at,
            "created_at": iso(self._clock.now()),
            "lease_until": None,
            "attempts": 0,
            "result": None,
            "error": None,
            "root_event_id": root_event_id,
            "parent_task_id": parent_task_id,
            "depth": depth,
            "refused_enqueues": [],
            "finished_at": None,
            "defer_reason": None,
            "key": key,
            "plan_id": plan_id,
            "depends_on": list(depends_on),
            "on_dep_failed": on_dep_failed,
            "on_unmet": on_unmet,
            "context": context or {},
        }

    async def _deps_state(self, dep_ids: Sequence[str]) -> tuple[bool, bool]:
        """(all_done, any_bad) over the dependency ids. A missing dependency counts as bad —
        we never run work whose precondition vanished."""
        all_done, any_bad = True, False
        for dep_id in dep_ids:
            dep = await self._db.get("tasks", dep_id)
            if dep is None or dep["status"] in TERMINAL_BAD:
                any_bad = True
                all_done = False
            elif dep["status"] != "done":
                all_done = False
        return all_done, any_bad

    # --- enqueue ------------------------------------------------------------------------------

    async def enqueue(
        self,
        *,
        kind: str,
        project_id: str,
        payload: dict[str, Any],
        reason: str,
        due_at: datetime | None = None,
        parent: Doc | None = None,
        root_event_id: str | None = None,
        policy: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        depends_on: Sequence[str] = (),
        on_dep_failed: str = "skip",
        on_unmet: str = "none",
        context: dict[str, Any] | None = None,
        key: str | None = None,
        plan_id: str | None = None,
    ) -> str | None:
        """Create one task. None when the lineage gate refuses (recorded on the parent).
        Blocked when any dependency is not yet done; dependency failure is resolved later by
        promote_ready() according to on_dep_failed."""
        existing = 0
        if parent is not None:
            existing = await self._db.count("tasks", [("parent_task_id", "==", parent["id"])])
        verdict = check_lineage(parent, existing, policy or DEFAULT_POLICY)
        if not verdict.ok:
            if parent is not None:
                refused = list(parent.get("refused_enqueues") or [])
                refused.append({"kind": kind, "reason": verdict.reason})
                await self._db.update("tasks", parent["id"], {"refused_enqueues": refused})
            return None
        all_done, _ = await self._deps_state(depends_on)
        task_id = new_id()
        doc = self._doc(
            kind=kind, project_id=project_id, payload=payload, reason=reason,
            due_at=iso(due_at or self._clock.now()), depth=verdict.depth,
            parent_task_id=parent["id"] if parent else None,
            root_event_id=root_event_id or (parent or {}).get("root_event_id"),
            params=params, depends_on=depends_on, blocked=bool(depends_on) and not all_done,
            on_dep_failed=on_dep_failed, on_unmet=on_unmet, context=context, key=key,
            plan_id=plan_id,
        )
        await self._db.create("tasks", task_id, doc)
        return task_id

    # --- dependencies -------------------------------------------------------------------------

    async def promote_ready(self) -> int:
        """Resolve every blocked task against its dependencies: all done → queued; any failed /
        cancelled / skipped / missing → skip, run_anyway or cancel per on_dep_failed. Idempotent;
        called by due() on every tick, so a crash between a completion and its promotion heals
        within a minute."""
        promoted = 0
        for task in await self._db.query("tasks", [("status", "==", "blocked")], limit=500):
            all_done, any_bad = await self._deps_state(task.get("depends_on") or [])
            if any_bad:
                policy = task.get("on_dep_failed", "skip")
                if policy == "cancel":
                    await self.cancel(task["id"], "a dependency failed")
                elif policy == "skip":
                    await self._db.cas(
                        "tasks", task["id"], lambda t: t["status"] == "blocked",
                        lambda t: {"status": "skipped", "error": "skipped: a dependency failed",
                                   "finished_at": iso(self._clock.now())},
                    )
                else:  # run_anyway: a bad dependency counts as satisfied
                    remaining = 0
                    for dep_id in task.get("depends_on") or []:
                        dep = await self._db.get("tasks", dep_id)
                        if dep is not None and dep["status"] not in (*TERMINAL_BAD, "done"):
                            remaining += 1
                    if remaining == 0:
                        ok = await self._db.cas(
                            "tasks", task["id"], lambda t: t["status"] == "blocked",
                            lambda t: {"status": "queued"},
                        )
                        promoted += int(ok)
            elif all_done:
                ok = await self._db.cas(
                    "tasks", task["id"], lambda t: t["status"] == "blocked",
                    lambda t: {"status": "queued"},
                )
                promoted += int(ok)
        return promoted

    async def cancel(self, task_id: str, reason: str) -> list[str]:
        """Cancel an open task and, recursively, everything that depends on it. Done tasks are
        left alone. Returns every id that was cancelled."""
        cancelled: list[str] = []
        ok = await self._db.cas(
            "tasks", task_id, lambda t: t["status"] in OPEN_STATUSES,
            lambda t: {"status": "cancelled", "error": f"cancelled: {reason}",
                       "finished_at": iso(self._clock.now()), "lease_until": None},
        )
        if not ok:
            return cancelled
        cancelled.append(task_id)
        dependents = await self._db.query("tasks", [("depends_on", "array_contains", task_id)])
        for dep in dependents:
            cancelled.extend(await self.cancel(dep["id"], reason))
        return cancelled

    # --- tick ---------------------------------------------------------------------------------

    async def due(self, kinds: Sequence[str], limit: int) -> list[Doc]:
        """Due work for the kinds this process can run: queued or deferred tasks past due_at,
        plus leased tasks whose lease expired (a crashed worker). Promotes blocked tasks first."""
        await self.promote_ready()
        now = iso(self._clock.now())
        queued = await self._db.query(
            "tasks", [("status", "in", ["queued", "deferred"]), ("due_at", "<=", now)],
            order_by="due_at", limit=limit,
        )
        expired = await self._db.query(
            "tasks", [("status", "==", "leased"), ("lease_until", "<=", now)],
            order_by="lease_until", limit=limit,
        )
        rows = [t for t in queued + expired if t["kind"] in kinds]
        rows.sort(key=lambda t: t["due_at"])
        return rows[:limit]

    async def claim(self, task_id: str) -> Doc | None:
        now = self._clock.now()
        now_s = iso(now)
        lease_until = iso(now + self._lease)

        def claimable(t: Doc) -> bool:
            if t["status"] in ("queued", "deferred"):
                return bool(t["due_at"] <= now_s)
            if t["status"] == "leased":
                return bool((t.get("lease_until") or "") <= now_s)
            return False

        ok = await self._db.cas(
            "tasks", task_id, claimable,
            lambda t: {"status": "leased", "lease_until": lease_until,
                       "attempts": int(t.get("attempts", 0)) + 1},
        )
        return await self._db.get("tasks", task_id) if ok else None

    # --- completion ---------------------------------------------------------------------------

    async def complete(
        self,
        task: Doc,
        result: dict[str, Any],
        children: Sequence[dict[str, Any]],
        *,
        supersedes: Sequence[str] = (),
    ) -> list[str]:
        """Mark done and, in the same transaction, create the children (a plan) and cancel the
        superseded open tasks with their dependents. Children may depend on each other by `key`
        or on existing tasks by id. Children failing the lineage gate are recorded in
        refused_enqueues. Returns created child ids; [] if the lease was lost (nothing written)."""
        existing = await self._db.count("tasks", [("parent_task_id", "==", task["id"])])
        plan_id = new_id()
        key_to_id: dict[str, str] = {}
        accepted: list[tuple[dict[str, Any], str, int]] = []
        refused: list[dict[str, str]] = list(task.get("refused_enqueues") or [])
        for spec in children:
            verdict = check_lineage(task, existing, spec.get("policy") or DEFAULT_POLICY)
            if not verdict.ok:
                refused.append({"kind": spec["kind"], "reason": verdict.reason})
                continue
            existing += 1
            child_id = new_id()
            if spec.get("key"):
                key_to_id[str(spec["key"])] = child_id
            accepted.append((spec, child_id, verdict.depth))

        sibling_ids = {cid for _, cid, _ in accepted}
        creates: list[Create] = []
        for spec, child_id, depth in accepted:
            deps = [key_to_id.get(str(d), str(d)) for d in spec.get("depends_on") or []]
            external = [d for d in deps if d not in sibling_ids]
            all_done, _ = await self._deps_state(external)
            blocked = bool(deps) and (any(d in sibling_ids for d in deps) or not all_done)
            creates.append((
                "tasks", child_id,
                self._doc(
                    kind=spec["kind"], project_id=task["project_id"],
                    payload=spec.get("payload") or {}, reason=spec["reason"],
                    due_at=spec.get("due_at") or iso(self._clock.now()), depth=depth,
                    parent_task_id=task["id"], root_event_id=task.get("root_event_id"),
                    params=spec.get("params"), depends_on=deps, blocked=blocked,
                    on_dep_failed=spec.get("on_dep_failed", "skip"),
                    on_unmet=spec.get("on_unmet", "none"), context=spec.get("context"),
                    key=spec.get("key"), plan_id=plan_id,
                ),
            ))

        updates: list[Update] = []
        finished = iso(self._clock.now())
        for sid in await self._cascade_ids(supersedes):
            updates.append(("tasks", sid, {
                "status": "cancelled", "error": f"cancelled: superseded by plan {plan_id}",
                "finished_at": finished, "lease_until": None,
            }))

        ok = await self._db.cas(
            "tasks", task["id"],
            lambda t: t["status"] == "leased",
            lambda t: {"status": "done", "result": result, "refused_enqueues": refused,
                       "finished_at": finished, "lease_until": None},
            creates, updates,
        )
        return [cid for _, cid, _ in accepted] if ok else []

    async def _cascade_ids(self, roots: Sequence[str]) -> list[str]:
        """Open tasks among `roots` plus everything open that depends on them, transitively."""
        seen: list[str] = []
        stack = list(roots)
        while stack:
            tid = stack.pop()
            if tid in seen:
                continue
            doc = await self._db.get("tasks", tid)
            if doc is None or doc["status"] not in OPEN_STATUSES:
                continue
            seen.append(tid)
            for dep in await self._db.query("tasks", [("depends_on", "array_contains", tid)]):
                stack.append(dep["id"])
        return seen

    # --- failure ------------------------------------------------------------------------------

    async def fail(self, task: Doc, reason: str, *, max_attempts: int = 3) -> str:
        """Retry with backoff while attempts remain; otherwise mark failed. Dependents are
        resolved by promote_ready() on the next tick. Returns the new status."""
        now = self._clock.now()
        attempts = int(task.get("attempts", 0))
        if attempts >= max_attempts:
            await self._db.update("tasks", task["id"], {
                "status": "failed", "error": reason, "finished_at": iso(now), "lease_until": None,
            })
            return "failed"
        delay = BACKOFF_SECONDS[min(attempts - 1, len(BACKOFF_SECONDS) - 1)]
        await self._db.update("tasks", task["id"], {
            "status": "queued", "error": reason, "lease_until": None,
            "due_at": iso(now + timedelta(seconds=delay)),
        })
        return "queued"

    async def defer(self, task: Doc, until: datetime, reason: str) -> None:
        await self._db.update("tasks", task["id"], {
            "status": "deferred", "due_at": iso(until), "defer_reason": reason,
            "lease_until": None,
        })

    async def open_count(self, project_id: str) -> int:
        return await self._db.count(
            "tasks", [("project_id", "==", project_id), ("status", "in", list(OPEN_STATUSES))]
        )

    @staticmethod
    def due_at_of(task: Doc) -> datetime:
        return parse_iso(task["due_at"])

"""Claim → run → complete-or-fail. The only code that both runs a stage and touches the queue."""

from __future__ import annotations

import asyncio

from app.harness.core.redact import redact
from app.harness.deps import Deps
from app.harness.stages import act, extract, plan, reconcile
from app.harness.stages.base import StageHandler
from app.harness.store.db import Doc

STAGES: dict[str, StageHandler] = {
    "extract": extract.run,
    "reconcile": reconcile.run,
    "act": act.run,
    "plan": plan.run,
}


async def run_task(task: Doc, deps: Deps) -> str:
    """Returns the task's status after this attempt: done, queued (retry), failed, or skipped."""
    claimed = await deps.queue.claim(task["id"])
    if claimed is None:
        return "skipped"
    handler = STAGES.get(claimed["kind"])
    if handler is None:
        return await deps.queue.fail(claimed, f"no handler for kind {claimed['kind']!r}")
    try:
        outcome = await asyncio.wait_for(
            handler(claimed, deps), timeout=deps.settings.stage_timeout_seconds
        )
    except Exception as exc:  # noqa: BLE001 — the queue owns retry policy; we only classify
        return await deps.queue.fail(claimed, redact(f"{type(exc).__name__}: {exc}"))
    await deps.queue.complete(
        claimed, outcome.result, outcome.children, supersedes=outcome.supersedes
    )
    return "done"

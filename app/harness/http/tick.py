"""The heartbeat. Cloud Scheduler POSTs here once a minute with the shared token; we run every
due task whose kind we know how to handle, sequentially, oldest first."""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.harness.deps import Deps
from app.harness.stages.runner import STAGES, run_task

router = APIRouter()


@router.post("/tick")
async def tick(request: Request) -> dict[str, Any]:
    deps: Deps = request.app.state.deps
    expected = deps.settings.tick_token
    given = request.headers.get("x-tick-token", "")
    if not expected or not hmac.compare_digest(given, expected):
        raise HTTPException(status_code=401, detail="bad tick token")
    # Drain in rounds: a stage's children are due immediately, and a call should flow through
    # extract → reconcile → act → plan in one tick, not one stage per minute. The budget keeps
    # a busy queue from outliving the request; whatever is left waits for the next tick.
    started = deps.clock.now()
    outcomes: list[str] = []
    for _ in range(10):
        due = await deps.queue.due(list(STAGES), deps.settings.tick_batch)
        if not due:
            break
        outcomes.extend([await run_task(task, deps) for task in due])
        if (deps.clock.now() - started).total_seconds() > deps.settings.tick_budget_seconds:
            break
    return {"processed": len(outcomes), "outcomes": outcomes}

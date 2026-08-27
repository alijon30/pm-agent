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
    due = await deps.queue.due(list(STAGES), deps.settings.tick_batch)
    outcomes = [await run_task(task, deps) for task in due]
    return {"processed": len(outcomes), "outcomes": outcomes}

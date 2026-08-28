"""The heartbeat. Cloud Scheduler POSTs here once a minute with the shared token; we run every
due task whose kind we know how to handle, sequentially, oldest first."""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.harness.deps import Deps
from app.harness.stages.runner import STAGES, run_task

router = APIRouter()

TICK_KIND_HEADER = "x-tick-kind"
DAILY_REVIEW = "daily_review"


async def _ensure_daily_review(deps: Deps) -> str | None:
    """Queue the morning review, unless today already has one.

    Cloud Scheduler retries, and a retry that queued a second review would give the agent two
    chances to learn the same lesson and two plans for one day. The queue hands out random ids,
    so "already done today" is a question about what is in the collection rather than about a
    document id we could have chosen."""
    project = await deps.projects.get(deps.settings.default_project_slug)
    if project is None:
        return None
    today = deps.clock.now().date().isoformat()
    already = await deps.db.query(
        "tasks", [("project_id", "==", project["id"]), ("kind", "==", DAILY_REVIEW)], limit=50
    )
    if any(str(row.get("created_at") or "").startswith(today) for row in already):
        return None
    return await deps.queue.enqueue(
        kind=DAILY_REVIEW, project_id=project["id"], payload={},
        params={"project": project["id"]},
        reason="the morning review of yesterday's outcomes",
        policy=project.get("policy"),
    )


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
    # The same endpoint, a different job on the scheduler: one header decides whether this tick
    # also starts the day. It then drains as usual, so the review runs inside this same request.
    queued_review = (
        await _ensure_daily_review(deps)
        if request.headers.get(TICK_KIND_HEADER, "") == DAILY_REVIEW else None
    )
    started = deps.clock.now()
    outcomes: list[str] = []
    for _ in range(10):
        due = await deps.queue.due(list(STAGES), deps.settings.tick_batch)
        if not due:
            break
        outcomes.extend([await run_task(task, deps) for task in due])
        if (deps.clock.now() - started).total_seconds() > deps.settings.tick_budget_seconds:
            break
    return {"processed": len(outcomes), "outcomes": outcomes,
            "daily_review": queued_review}

"""The heartbeat. Cloud Scheduler POSTs here once a minute with the shared token."""

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
    """Queue the morning review, unless today already has one (Cloud Scheduler retries)."""
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
    # Drain in rounds: a call flows extract → reconcile → act → plan in one tick, within budget.
    # The x-tick-kind header decides whether this tick also queues the daily review first.
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

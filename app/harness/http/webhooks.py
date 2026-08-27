"""Inbound webhooks. Verify, store, enqueue, return — no model work happens on this path."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.harness.connectors.fathom import parse_meeting, verify_signature
from app.harness.deps import Deps

router = APIRouter()


@router.post("/webhooks/fathom")
async def fathom_webhook(request: Request) -> dict[str, Any]:
    deps: Deps = request.app.state.deps
    raw = await request.body()
    secret = deps.settings.fathom_webhook_secret
    now_epoch = int(deps.clock.now().timestamp())
    if not verify_signature(secret, request.headers, raw, now_epoch):
        raise HTTPException(status_code=401, detail="bad signature")

    payload = json.loads(raw)
    provider_event_id = request.headers.get("webhook-id") or str(payload.get("recording_id") or "")
    project = await deps.projects.default()
    event_id = await deps.events.record(
        provider="fathom", provider_event_id=provider_event_id, payload=payload,
        project_id=project["id"],
    )
    if event_id is None:
        return {"status": "duplicate"}

    meeting = parse_meeting(payload)
    if not meeting["transcript"]:
        # Plan 2 adds the one-line Slack notice; today the note in the event is the record.
        await deps.events.note(event_id, "no transcript in payload")
        return {"status": "no_transcript"}

    task_id = await deps.queue.enqueue(
        kind="extract",
        project_id=project["id"],
        payload={"event_id": event_id},
        reason=f"Fathom call '{meeting['title']}' finished; extract decisions and action items",
        root_event_id=event_id,
        policy=project.get("policy"),
    )
    return {"status": "queued", "task_id": task_id}

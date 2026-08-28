"""Inbound webhooks. Verify, store, act on the change, return — no model runs on this path."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.harness.connectors.fathom import parse_meeting, verify_signature
from app.harness.core.errors import SourceUnavailable
from app.harness.deps import Deps
from app.harness.stages.early import issue_identifier_of, resolve_early

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
    await _post_status(event_id, meeting, project, deps)
    return {"status": "queued", "task_id": task_id}


async def _post_status(
    event_id: str, meeting: dict[str, Any], project: dict[str, Any], deps: Deps
) -> None:
    """Say that the call is being read, and remember where that message is.

    The team learns within seconds that something is happening, and the act stage later edits
    this same message into the summary rather than posting a second one — so the channel gets
    one message per call that fills itself in, not a running commentary.

    It is scaffolding rather than an action: nothing is written outside this system, there is
    nothing to revert, and the audit log records the edit that turns it into the summary. It
    runs after the work is queued and swallows an outage, so a Slack problem costs the team a
    message and costs the pipeline nothing."""
    channel = project.get("slack_channel_id")
    if deps.slack is None or not channel:
        return
    title = meeting.get("title") or "the call"
    try:
        ts = await deps.slack.post(
            channel,
            f"✻ Reading *{title}*… I'll file what was agreed and set up the follow-through.",
        )
    except SourceUnavailable:
        return
    await deps.db.update("events", event_id, {"status_message": {"channel": channel, "ts": ts}})


def verify_linear_signature(secret: str, raw_body: bytes, given: str) -> bool:
    """Linear signs the raw body with HMAC-SHA256, hex-encoded, in the linear-signature header.
    Fails closed on a missing secret or header."""
    if not secret or not given:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, given)


@router.post("/webhooks/linear")
async def linear_webhook(request: Request) -> dict[str, Any]:
    """An issue changed. Record it, then let reality overtake the schedule: any open check this
    change already satisfies completes now instead of at its due time."""
    deps: Deps = request.app.state.deps
    raw = await request.body()
    if not verify_linear_signature(
        deps.settings.linear_webhook_secret, raw, request.headers.get("linear-signature", "")
    ):
        raise HTTPException(status_code=401, detail="bad linear signature")

    payload = json.loads(raw)
    if payload.get("type") != "Issue":
        return {"status": "ignored"}
    project = await deps.projects.default()
    delivery = request.headers.get("linear-delivery") or (
        f"{(payload.get('data') or {}).get('id', '')}:{payload.get('webhookTimestamp', '')}"
    )
    event_id = await deps.events.record(
        provider="linear", provider_event_id=delivery, payload=payload,
        project_id=project["id"],
    )
    if event_id is None:
        return {"status": "duplicate"}

    identifier = issue_identifier_of(payload)
    if not identifier:
        return {"status": "no_identifier"}
    resolved = await resolve_early(identifier, deps)
    return {"status": "ok", "issue": identifier, "resolved_early": len(resolved)}

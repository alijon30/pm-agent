"""Slack's side of the conversation: the buttons on a summary, and mentions.

Revert is the promise that makes full autonomy acceptable — the agent acts without asking, and
anyone can undo any single action in one click. It is deliberately dumb: replay the inverse
payload the action recorded, cancel the follow-ups that only existed because of it, and edit the
message so the record in the channel matches the record in the tracker."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request, Response

from app.harness.connectors.slack import react_quietly, verify_slack_signature
from app.harness.connectors.slack_blocks import wrong_modal
from app.harness.core.errors import SourceUnavailable
from app.harness.core.redact import redact
from app.harness.deps import Deps

router = APIRouter()


async def _authorised(request: Request, deps: Deps) -> bytes:
    raw = await request.body()
    now = int(deps.clock.now().timestamp())
    if not verify_slack_signature(deps.settings.slack_signing_secret, request.headers, raw, now):
        raise HTTPException(status_code=401, detail="bad slack signature")
    return raw


def _payload(raw: bytes) -> dict[str, Any]:
    form = parse_qs(raw.decode())
    body: dict[str, Any] = json.loads(form.get("payload", ["{}"])[0])
    return body


async def _revert(action_id: str, who: str, deps: Deps) -> str:
    """Undo one action. Returns what to tell the human."""
    if deps.actions is None:
        return "nothing to revert: no action log"
    action = await deps.actions.get(action_id)
    if action is None:
        return "that action is no longer on record"
    if action.get("status") == "reverted":
        return "already reverted"
    if action.get("status") != "done":
        return "that action never completed, so there is nothing to undo"

    revert = action.get("revert") or {}
    op = revert.get("op")
    try:
        if op == "archive" and deps.linear is not None:
            await deps.linear.update_issue(revert["issue"], {"archived": True})
        elif op == "delete_comment" and deps.linear is not None:
            await deps.linear.comment(
                revert["issue"], "_This comment was reverted by the team._"
            )
        elif op == "edit_message" and deps.slack is not None:
            await deps.slack.update(revert["channel"], revert["ts"], "_reverted_", [])
        else:
            return f"no way to undo a {op!r} action"
    except SourceUnavailable as exc:
        return f"could not undo it: {redact(str(exc))}"

    await deps.actions.mark_reverted(action_id, by=who)

    # Follow-ups exist only because the thing they watch exists. Cancel them with it.
    identifier = (action.get("target_ids") or {}).get("identifier")
    cancelled = 0
    if identifier:
        for task in await deps.db.query(
            "tasks", [("project_id", "==", action["project_id"])]
        ):
            params = task.get("params") or {}
            if params.get("issue") == identifier and task.get("status") in (
                "queued", "blocked", "deferred"
            ):
                cancelled += len(await deps.queue.cancel(task["id"], f"{identifier} was reverted"))
    suffix = f"; cancelled {cancelled} follow-up(s)" if cancelled else ""
    return f"reverted {identifier or 'the action'}{suffix}"


@router.post("/slack/interactions")
async def interactions(request: Request) -> Response:
    """Slack expects a 200 within three seconds, so this path never calls a model."""
    deps: Deps = request.app.state.deps
    body = _payload(await _authorised(request, deps))
    kind = body.get("type")

    if kind == "block_actions":
        action = (body.get("actions") or [{}])[0]
        action_id = str(action.get("action_id") or "")
        who = (body.get("user") or {}).get("id", "")
        if action_id.startswith("revert:"):
            message = await _revert(action_id.split(":", 1)[1], who, deps)
            return Response(content=json.dumps({"text": message}), media_type="application/json")
        if action_id.startswith("wrong:") and deps.slack is not None:
            await deps.slack.open_modal(
                body.get("trigger_id", ""), wrong_modal(action_id.split(":", 1)[1])
            )
        return Response(status_code=200)

    if kind == "view_submission":
        view = body.get("view") or {}
        values = view.get("state", {}).get("values", {})

        def field(block: str) -> str:
            element = (values.get(block) or {}).get("value") or {}
            selected = element.get("selected_option") or {}
            return str(selected.get("value") or element.get("value") or "")

        if deps.corrections is not None:
            project = await deps.projects.default()
            await deps.corrections.add(
                project_id=project["id"],
                wrong=field("wrong"),
                right=field("right"),
                scope=field("scope") or "project",
                source_action_id=view.get("private_metadata") or None,
                author=(body.get("user") or {}).get("id", ""),
            )
        return Response(status_code=200)

    return Response(status_code=200)


@router.post("/slack/events")
async def events(request: Request) -> dict[str, Any]:
    """Mentions land here: recorded once, and a mention asking for a report becomes a queued
    report task. No model runs on this path — Slack wants a 200 in three seconds — and the
    enqueue hangs off the recorded event id, so a redelivered mention writes nothing twice."""
    deps: Deps = request.app.state.deps
    raw = await _authorised(request, deps)
    body: dict[str, Any] = json.loads(raw)

    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge", "")}

    event = body.get("event") or {}
    if event.get("type") == "app_mention":
        project = await deps.projects.default()
        event_id = await deps.events.record(
            provider="slack",
            provider_event_id=str(body.get("event_id") or event.get("ts") or ""),
            payload=event,
            project_id=project["id"],
        )
        if event_id is not None and "report" in str(event.get("text") or "").lower():
            # Answer where it was asked: the stage posts into this channel and thread rather
            # than the project channel, so a question in one room is not answered in another.
            task_id = await deps.queue.enqueue(
                kind="report",
                project_id=project["id"],
                params={"project": project["id"], "window": "sprint"},
                payload={"channel": event.get("channel"), "thread_ts": event.get("ts")},
                reason="report requested in Slack",
                root_event_id=event_id,
            )
            if task_id is not None:
                # 👀 on the mention: the asker sees the request landed, in the three seconds
                # Slack gives this route, without a message anyone has to read. The report
                # stage adds ✅ to the same message when the answer is in the thread.
                await react_quietly(deps.slack, event.get("channel"), event.get("ts"), "eyes")
    return {"ok": True}

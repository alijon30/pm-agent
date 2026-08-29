"""Slack's side of the conversation: the buttons on a summary, and mentions.

Revert is the promise that makes full autonomy acceptable — the agent acts without asking, and
anyone can undo any single action in one click. It is deliberately dumb: replay the inverse
payload the action recorded, cancel the follow-ups that only existed because of it, and edit the
message so the record in the channel matches the record in the tracker."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request, Response

from app.harness.connectors.slack import react_quietly, verify_slack_signature
from app.harness.connectors.slack_blocks import wrong_modal
from app.harness.core.errors import SourceUnavailable
from app.harness.core.redact import redact
from app.harness.core.words import count_of
from app.harness.deps import Deps

router = APIRouter()

# Two different jobs, deliberately two different patterns. CANCEL *detects* a cancellation from
# words alone, for when no classifier answered. ISSUE_KEY only *extracts* the identifier, and is
# what a classified cancellation uses — once Gemma has said "cancel", requiring the word "stop"
# as well would be the keyword router quietly overruling it.
CANCEL = re.compile(r"\b(stop|cancel|forget|drop)\b.*\b[A-Z][A-Z0-9]*-\d+\b")
ISSUE_KEY = re.compile(r"\b([A-Z][A-Z0-9]*-\d+)\b")
MENTION_TOKEN = re.compile(r"<@[^>]+>")
# Below this a mention is a greeting, not a request. "@pm-agent thanks" deserves no task.
MIN_REQUEST_WORDS = 4
KNOWN_INTENTS = ("report", "request", "cancel", "noise")
# Slack wants a 200 in three seconds. A classifier that has not answered in two is one we do not
# wait for — the keyword router below was good enough before Gemma existed.
CLASSIFY_SECONDS = 2.0


def issue_key(text: str) -> str | None:
    """The first issue key in a message. Read over the raw text so the identifier keeps its
    capitals, which is the only shape an issue key ever has."""
    found = ISSUE_KEY.search(text or "")
    return found.group(1) if found is not None else None


def request_text(text: str) -> str:
    return MENTION_TOKEN.sub("", str(text or "")).strip()


def task_for(intent: str, text: str, project_id: str) -> dict[str, Any] | None:
    """The task one classified intent becomes, or None when this intent cannot be actioned from
    this text — a cancellation with no identifier in it, for instance, which the caller then
    re-reads as an ordinary request."""
    if intent == "report":
        return {"kind": "report", "params": {"project": project_id, "window": "sprint"},
                "reason": "report requested in Slack"}
    if intent == "cancel":
        identifier = issue_key(text)
        if identifier is None:
            return None
        return {"kind": "intake", "params": {"cancel": identifier},
                "reason": f"asked in Slack to stop watching {identifier}"}
    if intent == "request":
        request = request_text(text)
        if not request:
            return None
        return {"kind": "intake", "params": {"text": request},
                "reason": "a teammate asked for something in Slack"}
    return None


def intent_of(text: str, project_id: str) -> dict[str, Any] | None:
    """What a mention is asking for, decided by keywords alone — the fallback for when the
    classifier is unavailable, unsure, or too slow, and the rule the tests pin down.

    Pure, because the routing rule is the part worth reading in a test rather than inferring
    from a Slack fixture."""
    raw = str(text or "")
    if "report" in raw.lower():
        return task_for("report", raw, project_id)
    if CANCEL.search(raw) is not None:
        return task_for("cancel", raw, project_id)
    if len(request_text(raw).split()) >= MIN_REQUEST_WORDS:
        return task_for("request", raw, project_id)
    return None


async def classify(deps: Deps, text: str) -> str:
    """Ask the triage model what this is. Anything other than a word we recognise — an
    abstention, a failure, a timeout — comes back as "" and the keyword router takes over."""
    try:
        intent = await asyncio.wait_for(deps.triage.classify_intent(text), CLASSIFY_SECONDS)
    except Exception:  # noqa: BLE001 — no classifier failure may cost a colleague their answer
        return ""
    return intent if intent in KNOWN_INTENTS else ""


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
        return "I can't undo that — there's no action log for this project."
    action = await deps.actions.get(action_id)
    if action is None:
        return "I don't have that action on record any more."
    if action.get("status") == "reverted":
        return "That was already reverted."
    if action.get("status") != "done":
        return "That never completed, so there's nothing to undo."

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
            return "I don't know how to undo that one."
    except SourceUnavailable as exc:
        return f"I can't undo that right now: {redact(str(exc))}."

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
    suffix = (f" I've also stopped {count_of(cancelled, 'check')} that were watching it."
              if cancelled else "")
    return f"Reverted {identifier or 'it'}.{suffix}"


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
        said = str(event.get("text") or "")
        classified = await classify(deps, said)
        # A classified intent wins; anything it could not action falls back to the keywords.
        # "noise" is the one answer that stops here: the agent saw it and has nothing to do.
        intent = task_for(classified, said, str(project["id"])) if classified else None
        if intent is None and classified != "noise":
            intent = intent_of(said, str(project["id"]))

        if event_id is not None and classified == "noise" and intent is None:
            # Seen, and deliberately not acted on. The reaction is the whole reply.
            await react_quietly(deps.slack, event.get("channel"), event.get("ts"), "eyes")
        elif event_id is not None and intent is not None:
            # Answer where it was asked: every stage this queues posts into this channel and
            # thread rather than the project channel, so a question in one room is never
            # answered in another. The requester travels with the work.
            task_id = await deps.queue.enqueue(
                kind=intent["kind"],
                project_id=project["id"],
                params=intent["params"],
                payload={"channel": event.get("channel"), "thread_ts": event.get("ts"),
                         "requester": event.get("user")},
                reason=intent["reason"],
                root_event_id=event_id,
            )
            if task_id is not None:
                # 👀 on the mention: the asker sees the request landed, in the three seconds
                # Slack gives this route, without a message anyone has to read. The stage that
                # runs it adds ✅ or 🤝 to the same message when it has an answer.
                await react_quietly(deps.slack, event.get("channel"), event.get("ts"), "eyes")
    return {"ok": True}

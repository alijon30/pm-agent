"""reconcile: take what a call produced and check it against everything that already exists.

The model proposes; this stage verifies. Every identifier the model names is re-fetched before
the proposal may reach Act, because an issue key that looks right and is wrong is the fastest
way to lose a team's trust. A source that is down produces `unverified`, never a guess: the
items that needed it are held back and retried once, and Act simply does not see them."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.agents.base.schemas import ReconcileResult
from app.harness.connectors.fathom import parse_meeting
from app.harness.core.clock import iso
from app.harness.core.errors import PmError, SourceUnavailable
from app.harness.deps import Deps
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc
from app.harness.verify.ids import IdGate

RETRY_MINUTES = 30


def item_refs(item: dict[str, Any]) -> list[str]:
    """Every reference an item asserts: its citations, its conflict sources, its fact sources,
    and — as a typed ref — the issue it claims to update or duplicate."""
    refs = list(item.get("citations") or [])
    for conflict in item.get("conflicts") or []:
        refs.extend(side.get("source", "") for side in conflict.get("sides") or [])
    refs.extend(fact.get("source", "") for fact in item.get("facts") or [])
    target = item.get("target_issue")
    if target and item.get("disposition") in ("update", "duplicate_of"):
        refs.append(f"linear:{target}")
    return [r for r in refs if r]


def quotes_for(index: int, action_items: list[dict[str, Any]]) -> list[str]:
    """The verbatim quotes behind one action item — what the priority and date gates weigh."""
    if 0 <= index < len(action_items):
        return [e.get("quote", "") for e in action_items[index].get("evidence") or []]
    return []


async def _verify(
    items: list[dict[str, Any]], ids: IdGate
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    """Split items into verified and unverified. The third value says whether a source outage
    was the reason, which is what makes a retry worth scheduling."""
    verified: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    outage = False
    for item in items:
        try:
            missing = await ids.missing_refs(item_refs(item))
        except SourceUnavailable as exc:
            outage = True
            unverified.append({**item, "gate_reason": f"{exc.source} unavailable"})
            continue
        if missing:
            unverified.append({
                **item, "gate_reason": f"unknown identifier(s): {', '.join(missing)}"
            })
        else:
            verified.append(item)
    return verified, unverified, outage


def _feedback(unverified: list[dict[str, Any]]) -> str:
    lines = "; ".join(
        f"{u.get('title', '?')} — {u.get('gate_reason', '')}" for u in unverified
    )
    return (
        "These items were rejected because they name things that could not be confirmed: "
        f"{lines}. Re-check each identifier with the tools before citing it. Never write a "
        "reference you did not open; omit the citation and say what you could not verify."
    )


async def run(task: Doc, deps: Deps) -> StageResult:
    event = await deps.events.get(task["payload"]["event_id"])
    if event is None:
        raise PmError(f"event {task['payload']['event_id']} not found")
    project = await deps.projects.get(task["project_id"])
    if project is None:
        raise PmError(f"project {task['project_id']} not found")
    if deps.reconciler is None or deps.ids is None:
        raise PmError("reconcile needs a reconciler and an id gate")
    ids = deps.ids

    extract_task = await deps.db.get("tasks", task["payload"]["extract_task_id"])
    if extract_task is None or not extract_task.get("result"):
        raise PmError("the extract result this reconcile depends on is missing")
    extracted: dict[str, Any] = extract_task["result"]
    action_items: list[dict[str, Any]] = extracted.get("action_items") or []

    meeting = parse_meeting(event["payload"])
    decisions = [
        d for d in [await deps.db.get("decisions", i) for i in extracted.get("decision_ids") or []]
        if d is not None
    ]
    payload: dict[str, Any] = {
        "action_items": action_items,
        "decisions": [
            {"statement": d["statement"], "quote": d.get("quote", ""), "source": d.get("source")}
            for d in decisions
        ],
        "meeting": {"id": meeting["meeting_id"], "title": meeting["title"], "url": meeting["url"]},
        "roster": [{"name": m["name"], "role": m.get("role")} for m in project.get("roster", [])],
        "today": iso(deps.clock.now())[:10],
        "feedback": None,
    }

    parsed = ReconcileResult.model_validate(await deps.reconciler.run(payload)).model_dump()
    verified, unverified, outage = await _verify(parsed.get("items") or [], ids)

    bounced = False
    if unverified:
        bounced = True
        rescued = ReconcileResult.model_validate(
            await deps.reconciler.run({**payload, "feedback": _feedback(unverified)})
        ).model_dump()
        verified, unverified, outage = await _verify(rescued.get("items") or [], ids)
        parsed = rescued

    for item in verified:
        item["quotes"] = quotes_for(int(item.get("index", -1)), action_items)

    result: dict[str, Any] = {
        "meeting": payload["meeting"],
        "items": verified,
        "unverified": unverified,
        "decision_conflicts": parsed.get("decision_conflicts") or [],
        "decision_ids": extracted.get("decision_ids") or [],
        "bounced": bounced,
    }

    children: list[dict[str, Any]] = [{
        "kind": "act",
        "payload": {"event_id": event["id"], "reconcile_task_id": task["id"]},
        "reason": (
            f"file {len(verified)} verified item(s) from '{meeting['title']}'"
            if verified else f"report on '{meeting['title']}': nothing survived verification"
        ),
    }]

    # An outage is the one failure worth retrying: the items were probably fine, the source was
    # not. Retry once, only for the items that were held back.
    if outage and not task["payload"].get("retry"):
        children.append({
            "kind": "reconcile",
            "payload": {**task["payload"], "retry": 1},
            "due_at": iso(deps.clock.now() + timedelta(minutes=RETRY_MINUTES)),
            "reason": f"retry {len(unverified)} item(s) whose sources were unavailable",
        })

    return StageResult(result=result, children=children)

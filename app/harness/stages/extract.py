"""extract: transcript → decisions, action items, open questions — each with verbatim evidence,
or not at all. One bounce on a gate failure, then an honest drop."""

from __future__ import annotations

from typing import Any

from app.agents.base.schemas import ExtractResult
from app.harness.connectors.fathom import parse_meeting, render_transcript, transcript_plain
from app.harness.core.errors import PmError
from app.harness.deps import Deps
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc
from app.harness.verify.evidence import check_evidence

SECTIONS = ("decisions", "action_items", "open_questions")


def select_with_context(
    segments: list[dict[str, Any]], flags: list[bool], window: int = 2
) -> list[dict[str, Any]]:
    """Flagged segments plus `window` neighbours on each side, original order, no duplicates."""
    keep: set[int] = set()
    for i, flagged in enumerate(flags):
        if flagged:
            keep.update(range(max(0, i - window), min(len(segments), i + window + 1)))
    return [segments[i] for i in sorted(keep)]


def _gate(
    parsed: dict[str, Any], plain: str
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    kept: dict[str, list[dict[str, Any]]] = {}
    dropped: list[dict[str, Any]] = []
    for section in SECTIONS:
        verdict = check_evidence(parsed.get(section, []), plain)
        kept[section] = verdict.kept
        dropped.extend({**d, "section": section} for d in verdict.dropped)
    return kept, dropped


def _label(item: dict[str, Any]) -> str:
    return str(item.get("title") or item.get("statement") or item.get("question") or "?")


async def run(task: Doc, deps: Deps) -> StageResult:
    event = await deps.events.get(task["payload"]["event_id"])
    if event is None:
        raise PmError(f"event {task['payload']['event_id']} not found")
    project = await deps.projects.get(task["project_id"])
    if project is None:
        raise PmError(f"project {task['project_id']} not found")

    meeting = parse_meeting(event["payload"])
    flags = await deps.triage.decision_bearing(meeting["transcript"])
    selected = select_with_context(meeting["transcript"], flags)
    payload: dict[str, Any] = {
        "transcript": render_transcript(selected),
        "roster_names": [m["name"] for m in project.get("roster", [])],
        "feedback": None,
    }
    plain = transcript_plain(meeting)

    parsed = ExtractResult.model_validate(await deps.extractor.run(payload)).model_dump()
    kept, dropped = _gate(parsed, plain)
    bounced = False
    if dropped:
        bounced = True
        names = "; ".join(_label(d) for d in dropped)
        feedback = (
            "These items were dropped because none of their quotes appear verbatim in the "
            f"transcript: {names}. Re-extract; every quote must be copied exactly from the "
            "transcript text. Omit any item you cannot support with an exact quote."
        )
        parsed = ExtractResult.model_validate(
            await deps.extractor.run({**payload, "feedback": feedback})
        ).model_dump()
        kept, dropped = _gate(parsed, plain)

    decision_ids = await deps.decisions.add_many(
        task["project_id"], event["id"], kept["decisions"], meeting
    )
    result: dict[str, Any] = {
        "meeting": {"id": meeting["meeting_id"], "title": meeting["title"], "url": meeting["url"]},
        "action_items": kept["action_items"],
        "open_questions": kept["open_questions"],
        "decision_ids": decision_ids,
        "dropped": dropped,
        "bounced": bounced,
        # What the model was actually shown. Triage decides what the agent could possibly have
        # heard, so the number is worth keeping: without it the console can only say the call
        # was read, not how much of it.
        "triage": {"kept": len(selected), "total": len(meeting["transcript"])},
    }
    children: list[dict[str, Any]] = []
    if kept["action_items"] or kept["decisions"]:
        children.append({
            "kind": "reconcile",
            "payload": {"event_id": event["id"], "extract_task_id": task["id"]},
            "reason": (
                f"reconcile {len(kept['action_items'])} action item(s) and "
                f"{len(kept['decisions'])} decision(s) from '{meeting['title']}' against "
                "Linear, Notion and code"
            ),
        })
    return StageResult(result=result, children=children)

"""daily_review: every morning the agent reads yesterday, learns at most three things, and plans.

The stage is two halves that must not be confused. The first is deterministic: what ran, what it
saw, who was interrupted, and what moved afterwards — gathered from the queue and the audit log,
with the tracker consulted only to ask what an issue looks like now. The second is a model doing
the one thing a model is good for here: noticing a pattern across a day and saying it in a
sentence.

Between them sits the evidence gate, which is the only reason the second half is safe. A lesson
may cite only the references the first half handed over; anything else is dropped before it is
stored. The model cannot expand its own evidence, and it cannot learn from a day it did not have.

The stage ends by enqueueing a plan with the day's outcomes attached, which is what closes the
loop: what happened yesterday is what the planner reads before deciding today."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.agents.base.schemas import Lessons
from app.harness.core.clock import iso
from app.harness.core.errors import PmError, SourceUnavailable
from app.harness.deps import Deps
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc

WINDOW_HOURS = 24
SCAN_LIMIT = 500


def keep_evidenced(
    lessons: list[dict[str, Any]], allowed: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split lessons into those the day can support and those it cannot.

    A lesson needs at least one reference, and every reference must be one the stage actually
    gathered. This is a membership test against a set built from real documents, not a judgment:
    the model has no way to talk past it."""
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for lesson in lessons:
        refs = [str(r).strip() for r in lesson.get("evidence") or [] if str(r).strip()]
        missing = [r for r in refs if r not in allowed]
        if not refs:
            dropped.append({**lesson, "reason": "no evidence"})
        elif missing:
            dropped.append({**lesson, "reason": f"evidence not from this day: {missing}"})
        else:
            kept.append({**lesson, "evidence": refs})
    return kept, dropped


async def _movements(
    nudges: list[dict[str, Any]], tasks_by_id: dict[str, Doc], deps: Deps
) -> list[dict[str, Any]]:
    """What happened to an issue after the agent spoke about it. The state the check observed is
    the state at the moment of the nudge; the tracker says what it is now. Best-effort — an
    outage costs the reviewer this signal, not the review."""
    if deps.linear is None:
        return []
    seen: list[dict[str, Any]] = []
    for nudge in nudges:
        task = tasks_by_id.get(str(nudge.get("task_id") or ""))
        if task is None:
            continue
        observed = (task.get("result") or {}).get("observed") or {}
        identifier = str(observed.get("issue") or (task.get("params") or {}).get("issue") or "")
        if not identifier:
            continue
        try:
            live = await deps.linear.get_issue(identifier)
        except SourceUnavailable:
            continue
        if live is None:
            continue
        was, now = str(observed.get("state") or ""), str(live.get("state") or "")
        seen.append({
            "ref": nudge["ref"], "issue": identifier, "template": nudge.get("template"),
            "state_when_we_spoke": was, "state_now": now, "moved": bool(was and was != now),
        })
    return seen


async def gather(task: Doc, deps: Deps) -> dict[str, Any]:
    """One day of the agent's own behaviour, from the records it already keeps."""
    project_id = task["project_id"]
    now = deps.clock.now()
    since = iso(now - timedelta(hours=WINDOW_HOURS))

    tasks = await deps.db.query(
        "tasks", [("project_id", "==", project_id)], order_by="created_at", limit=SCAN_LIMIT
    )
    recent = [t for t in tasks if str(t.get("finished_at") or "") >= since]
    tasks_by_id = {str(t["id"]): t for t in tasks}

    checks = [
        {"ref": f"task:{t['id']}", "kind": t["kind"], "issue": (t.get("params") or {}).get("issue"),
         "expected": (t.get("params") or {}).get("expect"),
         "met": bool((t.get("result") or {}).get("met")),
         "early": bool((t.get("result") or {}).get("early")),
         "observed": (t.get("result") or {}).get("observed") or {},
         "reason": t.get("reason"), "finished_at": t.get("finished_at")}
        for t in recent
        if str(t["kind"]).startswith("check_") and t["status"] == "done"
    ]
    failures = [
        {"ref": f"task:{t['id']}", "kind": t["kind"], "reason": t.get("reason"),
         "error": t.get("error"), "finished_at": t.get("finished_at")}
        for t in recent if t["status"] == "failed"
    ]
    superseded = [
        {"ref": f"task:{t['id']}", "kind": t["kind"], "reason": t.get("reason"),
         "error": t.get("error")}
        for t in recent
        if t["status"] == "cancelled" and "superseded" in str(t.get("error") or "")
    ]

    actions = await deps.db.query(
        "actions", [("project_id", "==", project_id)], order_by="created_at", limit=SCAN_LIMIT
    )
    nudges = [
        {"ref": f"action:{a['id']}", "template": (a.get("inputs") or {}).get("template"),
         "task_id": a.get("task_id"), "created_at": a.get("created_at"),
         "status": a.get("status")}
        for a in actions
        if str(a.get("created_at") or "") >= since
        and a.get("kind") == "slack.post" and (a.get("inputs") or {}).get("template")
    ]

    return {
        "window": {"from": since, "to": iso(now)},
        "checks": checks,
        "nudges": nudges,
        "movements": await _movements(nudges, tasks_by_id, deps),
        "superseded": superseded,
        "failures": failures,
    }


def evidence_ids(outcomes: dict[str, Any]) -> set[str]:
    """Every reference the reviewer was shown — the whole of what a lesson may cite."""
    return {
        str(row["ref"])
        for section in ("checks", "nudges", "movements", "superseded", "failures")
        for row in outcomes.get(section) or []
        if row.get("ref")
    }


def recent_results(outcomes: dict[str, Any]) -> list[dict[str, Any]]:
    """What the planner reads before deciding today. Yesterday's observations, plainly."""
    return [
        *(outcomes.get("checks") or []),
        *(outcomes.get("movements") or []),
        *(outcomes.get("failures") or []),
    ]


async def run(task: Doc, deps: Deps) -> StageResult:
    project = await deps.projects.get(task["project_id"])
    if project is None:
        raise PmError(f"project {task['project_id']} not found")

    outcomes = await gather(task, deps)
    held = (
        [str(row.get("text") or "") for row in await deps.lessons.for_project(task["project_id"])]
        if deps.lessons is not None else []
    )

    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    notes = ""
    if deps.reviewer is not None and evidence_ids(outcomes):
        parsed = Lessons.model_validate(await deps.reviewer.run({
            **outcomes, "lessons_so_far": held, "feedback": None,
        })).model_dump()
        notes = str(parsed.get("notes") or "")
        kept, dropped = keep_evidenced(parsed.get("lessons") or [], evidence_ids(outcomes))
        if deps.lessons is not None:
            for lesson in kept:
                await deps.lessons.add(
                    project_id=task["project_id"], text=lesson["text"],
                    evidence=lesson["evidence"], source_task_id=str(task["id"]),
                )

    # The point of the review: today's plan is made against yesterday's outcomes, not against a
    # blank slate. The planner is a child rather than a call so the queue owns it like any work.
    children = [{
        "kind": "plan",
        "payload": {"recent_results": recent_results(outcomes)},
        "reason": "re-plan the project against what actually happened yesterday",
        "context": {},
    }]
    return StageResult(
        result={
            "checked": len(outcomes["checks"]),
            "nudged": len(outcomes["nudges"]),
            "moved": sum(1 for m in outcomes["movements"] if m["moved"]),
            "failed": len(outcomes["failures"]),
            "learned": [lesson["text"] for lesson in kept],
            "dropped": dropped,
            "notes": notes,
        },
        children=children,
    )

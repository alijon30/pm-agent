"""plan: turn the planner's proposal into scheduled work, or into nothing.

The gate runs first and the queue runs last, and between them the plan is only data. Whatever
survives becomes the children of this task, which means the queue creates them in the same
transaction that marks this task done — a plan is never half-scheduled.

When the model gives us nothing usable, the fallback is not silence: a deterministic
`-1d / due / +3d` chain per issue, which is what a careful person would do anyway."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.agents.base.schemas import Plan
from app.harness.connectors.slack_blocks import count_of, plan_summary_blocks
from app.harness.core.clock import iso, parse_iso
from app.harness.core.errors import PmError, SourceUnavailable
from app.harness.core.keys import idempotency_key
from app.harness.core.redact import redact
from app.harness.deps import Deps
from app.harness.kinds.registry import KINDS
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc
from app.harness.verify.plan import check_plan

OFFSET_UNITS = {"d": "days", "h": "hours"}


def parse_offset(offset: str, anchor: datetime) -> datetime:
    """'-1d' → a day before the anchor; '+3d' → three days after; '0d' → the anchor."""
    sign = -1 if offset.startswith("-") else 1
    body = offset.lstrip("+-")
    amount, unit = int(body[:-1] or 0), body[-1]
    return anchor + timedelta(**{OFFSET_UNITS.get(unit, "days"): sign * amount})


def default_followups(context: dict[str, Any], policy: dict[str, Any], now: datetime) -> Plan:
    """What to check when the planner had nothing better to say: has it started, is there a
    pull request, did it land — spaced around the date that was actually promised."""
    offsets = policy.get("default_followup_offsets") or ["-1d", "0d", "+3d"]
    tasks: list[dict[str, Any]] = []
    for item in context.get("items") or []:
        identifier = item.get("identifier")
        if not identifier:
            continue
        anchor = now + timedelta(days=3)
        if item.get("due"):
            try:
                anchor = parse_iso(f"{item['due']}T16:00:00+00:00")
            except ValueError:
                pass
        slug = identifier.lower().replace("-", "")
        started = parse_offset(offsets[0], anchor)
        tasks.append({
            "key": f"{slug}_started", "kind": "check_issue_state",
            "params": {"issue": identifier, "expect": ["In Progress", "In Review", "Done"]},
            "due": iso(max(started, now + timedelta(hours=1))),
            "reason": f"{identifier} should be underway by now",
            "on_unmet": "nudge_assignee", "depends_on": [],
            "context": {"issue": identifier},
        })
        tasks.append({
            "key": f"{slug}_pr", "kind": "check_pr_exists",
            "params": {"issue": identifier},
            "due": iso(parse_offset(offsets[1], anchor)),
            "reason": f"a pull request should reference {identifier} by its due date",
            "on_unmet": "nudge_assignee", "depends_on": [f"{slug}_started"],
            "context": {"issue": identifier},
        })
        tasks.append({
            "key": f"{slug}_done", "kind": "check_issue_state",
            "params": {"issue": identifier, "expect": ["Done"]},
            "due": iso(parse_offset(offsets[2], anchor)),
            "reason": f"{identifier} should have landed",
            "on_unmet": "escalate_channel", "depends_on": [f"{slug}_pr"],
            "context": {"issue": identifier},
        })
    return Plan.model_validate({"tasks": tasks, "supersedes": [], "notes": "default follow-ups"})


def _catalog() -> list[dict[str, str]]:
    return [
        {"kind": spec.name, "params": ", ".join(spec.params_schema.model_fields),
         "unmet_actions": ", ".join(spec.unmet_actions) or "none",
         "description": spec.description}
        for spec in KINDS.values()
    ]


async def _context_for(task: Doc, deps: Deps) -> dict[str, Any]:
    """Whatever produced this plan task hands over its own context; a daily review builds it."""
    if task.get("context"):
        return dict(task["context"])
    act_task_id = task["payload"].get("act_task_id")
    if act_task_id:
        act = await deps.db.get("tasks", act_task_id)
        if act is not None and act.get("context"):
            return dict(act["context"])
    return {}


async def run(task: Doc, deps: Deps) -> StageResult:
    project = await deps.projects.get(task["project_id"])
    if project is None:
        raise PmError(f"project {task['project_id']} not found")
    policy = project.get("policy") or {}
    now = deps.clock.now()

    context = await _context_for(task, deps)
    open_tasks = [
        {"id": t["id"], "kind": t["kind"], "params": t.get("params") or {},
         "due_at": t.get("due_at"), "reason": t.get("reason")}
        for t in await deps.db.query(
            "tasks", [("project_id", "==", task["project_id"]),
                      ("status", "in", ["queued", "blocked", "deferred"])], limit=50
        )
        if t["kind"] in KINDS
    ]
    open_ids = {t["id"] for t in open_tasks}

    payload: dict[str, Any] = {
        "context": context,
        "open_tasks": open_tasks,
        "recent_results": task["payload"].get("recent_results") or [],
        "catalog": _catalog(),
        "policy": {k: policy.get(k) for k in
                   ("plan_horizon_days", "max_plan_size", "default_followup_offsets")},
        "now": iso(now),
        "feedback": None,
    }

    proposal, notes = await _propose(payload, deps)
    verdict = await check_plan(
        proposal, now=now, policy=policy,
        open_tasks=await deps.queue.open_count(task["project_id"]),
        existing_ids=lambda tid: tid in open_ids,
        id_exists=deps.ids.exists if deps.ids is not None else _nothing_exists,
    )

    bounced = False
    if (verdict.rejected or verdict.reasons) and deps.planner is not None:
        bounced = True
        problems = "; ".join(
            [f"{r['key']}: {r['reason']}" for r in verdict.rejected] + verdict.reasons
        )
        retry, notes = await _propose(
            {**payload, "feedback": f"Your previous plan was rejected — {problems}. "
                                    "Fix those tasks and keep the rest."}, deps
        )
        verdict = await check_plan(
            retry, now=now, policy=policy,
            open_tasks=await deps.queue.open_count(task["project_id"]),
            existing_ids=lambda tid: tid in open_ids,
            id_exists=deps.ids.exists if deps.ids is not None else _nothing_exists,
        )
        proposal = retry

    if not verdict.tasks and not (proposal.get("tasks") or []):
        fallback = default_followups(context, policy, now).model_dump()
        verdict = await check_plan(
            fallback, now=now, policy=policy,
            open_tasks=await deps.queue.open_count(task["project_id"]),
            existing_ids=lambda tid: tid in open_ids,
            id_exists=deps.ids.exists if deps.ids is not None else _nothing_exists,
        )
        notes = "no plan from the planner; using the default follow-up chain"

    supersedes = [s for s in (proposal.get("supersedes") or []) if s in open_ids]
    # Reasons only: the plan key is this system's handle for a task the team never saw, so it
    # means nothing in a channel. The full rejection, key and all, is in the result and console.
    trimmed = [r["reason"] for r in verdict.rejected] + verdict.reasons
    await _announce(task, project, verdict.tasks, trimmed, deps)

    result: dict[str, Any] = {
        "notes": notes,
        "accepted": [t["key"] for t in verdict.tasks],
        "rejected": verdict.rejected,
        "reasons": verdict.reasons,
        "supersedes": supersedes,
        "bounced": bounced,
    }
    children = [
        {"kind": t["kind"], "payload": {}, "params": t["params"], "key": t["key"],
         "depends_on": t["depends_on"], "due_at": t["due_at"], "reason": t["reason"],
         "on_unmet": t["on_unmet"], "on_dep_failed": t["on_dep_failed"],
         "context": t["context"]}
        for t in verdict.tasks
    ]
    return StageResult(result=result, children=children, supersedes=supersedes)


async def _nothing_exists(token: str) -> bool:
    """With no id gate configured nothing can be confirmed, so nothing is scheduled about it."""
    return False


async def _propose(payload: dict[str, Any], deps: Deps) -> tuple[dict[str, Any], str]:
    if deps.planner is None:
        return {"tasks": [], "supersedes": [], "notes": ""}, "no planner configured"
    parsed = Plan.model_validate(await deps.planner.run(payload)).model_dump()
    return parsed, str(parsed.get("notes") or "")


async def _announce(
    task: Doc, project: dict[str, Any], tasks: list[dict[str, Any]], trimmed: list[str], deps: Deps
) -> None:
    """Say what will be watched. Best-effort: a Slack outage never unschedules the work."""
    channel = project.get("slack_channel_id")
    if deps.slack is None or deps.actions is None or not channel or not tasks:
        return
    key = idempotency_key(str(task.get("root_event_id") or task["id"]), 0, "slack.plan")
    if await deps.actions.find_by_key(key) is not None:
        return
    action_id = await deps.actions.begin(
        task_id=task["id"], project_id=task["project_id"], kind="slack.post",
        idempotency_key=key, inputs={"channel": channel, "tasks": len(tasks)},
    )
    try:
        ts = await deps.slack.post(
            channel, f"I'll follow up on {count_of(len(tasks), 'thing')}",
            plan_summary_blocks(tasks, trimmed),
        )
    except SourceUnavailable as exc:
        await deps.actions.fail(action_id, redact(str(exc)))
        return
    await deps.actions.finish(
        action_id, target_ids={"channel": channel, "ts": ts},
        revert={"op": "edit_message", "channel": channel, "ts": ts},
    )

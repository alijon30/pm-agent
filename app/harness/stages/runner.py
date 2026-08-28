"""Claim → run → complete-or-fail. The only code that both runs a stage and touches the queue."""

from __future__ import annotations

import asyncio

from app.harness.connectors.slack_blocks import human_check
from app.harness.core.keys import idempotency_key
from app.harness.core.redact import redact
from app.harness.deps import Deps
from app.harness.stages import (
    act,
    checks,
    extract,
    intake,
    plan,
    reconcile,
    report,
    review,
)
from app.harness.stages.base import StageHandler
from app.harness.store.db import Doc
from app.harness.verify.caps import check_caps

STAGES: dict[str, StageHandler] = {
    "extract": extract.run,
    "reconcile": reconcile.run,
    "act": act.run,
    "plan": plan.run,
    "report": report.run,
    "intake": intake.run,
    "daily_review": review.run,
    "check_issue_state": checks.run_check,
    "check_pr_exists": checks.run_check,
    "check_pr_reviewed": checks.run_check,
    "check_pr_merged": checks.run_check,
    "nudge": checks.run_nudge,
}


async def run_task(task: Doc, deps: Deps) -> str:
    """Returns the task's status after this attempt: done, queued (retry), failed, or skipped."""
    claimed = await deps.queue.claim(task["id"])
    if claimed is None:
        return "skipped"
    handler = STAGES.get(claimed["kind"])
    if handler is None:
        return await deps.queue.fail(claimed, f"no handler for kind {claimed['kind']!r}")
    try:
        outcome = await asyncio.wait_for(
            handler(claimed, deps), timeout=deps.settings.stage_timeout_seconds
        )
    except Exception as exc:  # noqa: BLE001 — the queue owns retry policy; we only classify
        reason = redact(f"{type(exc).__name__}: {exc}")
        status = await deps.queue.fail(claimed, reason)
        if status == "failed":
            await _tell_the_requester(claimed, reason, deps)
        return status
    await deps.queue.complete(
        claimed, outcome.result, outcome.children, supersedes=outcome.supersedes
    )
    return "done"


async def _tell_the_requester(task: Doc, reason: str, deps: Deps) -> None:
    """When work somebody asked for runs out of retries, say so to the person who asked.

    An agent that accepts a request and then quietly gives up is worse than one that refuses:
    the requester is still waiting, and has no way to know they should stop. This is the only
    place a failure speaks. Best-effort, capped like any other interruption, and it never raises
    — the task is already failed and nothing here may change that."""
    context = task.get("context") or {}
    slack_id = str(context.get("requester_slack_id") or "")
    channel = str(context.get("request_channel") or "")
    if not slack_id or not channel or deps.slack is None or deps.actions is None:
        return
    project = await deps.projects.get(task["project_id"])
    if project is None:
        return
    if not check_caps("ping", await deps.actions.counts_today(task["project_id"]),
                      deps.clock.now(), project.get("policy") or {}).ok:
        return

    key = idempotency_key(task["id"], 0, "slack.blocked")
    if await deps.actions.find_by_key(key) is not None:
        return
    action_id = await deps.actions.begin(
        task_id=task["id"], project_id=task["project_id"], kind="slack.post",
        idempotency_key=key, inputs={"channel": channel, "template": "blocked"},
    )
    try:
        ts = await deps.slack.post(
            channel,
            f"<@{slack_id}>, I'm blocked on {human_check(task)} — {reason}. "
            "I'll leave this with you.",
            thread_ts=str(context.get("request_ts") or "") or None,
        )
    except Exception:  # noqa: BLE001 — a failed task must not fail harder on the way out
        await deps.actions.fail(action_id, "could not deliver the blocked note")
        return
    await deps.actions.finish(
        action_id, target_ids={"channel": channel, "ts": ts},
        revert={"op": "edit_message", "channel": channel, "ts": ts},
    )

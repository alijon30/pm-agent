"""report: what happened this sprint, in sixty seconds, with a reference under every sentence."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from app.agents.base.schemas import Report
from app.harness.connectors.slack import react_quietly
from app.harness.connectors.slack_blocks import report_blocks
from app.harness.core.clock import iso
from app.harness.core.errors import PmError, SourceUnavailable
from app.harness.core.keys import idempotency_key
from app.harness.core.redact import redact
from app.harness.deps import Deps
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc
from app.harness.verify.citations import check_citations
from app.harness.verify.ids import IdGate

CREATE_KIND = "linear.create_issue"
DEFAULT_WINDOW_DAYS = 14
RELATIVE_WINDOW = re.compile(r"^(\d+)d$")
TASK_SCAN_LIMIT = 500


def report_window(
    project: dict[str, Any], params: dict[str, Any], now: datetime
) -> dict[str, str]:
    """The period this report covers: the project's sprint, or the `<N>d` window the task asked
    for. A project with no sprint configured still gets a bounded window."""
    relative = RELATIVE_WINDOW.match(str(params.get("window") or ""))
    sprint = project.get("sprint") or {}
    if relative is None and sprint.get("start") and sprint.get("end"):
        return {
            "name": str(sprint.get("name") or "current sprint"),
            "start": str(sprint["start"]),
            "end": str(sprint["end"]),
        }
    days = int(relative.group(1)) if relative else DEFAULT_WINDOW_DAYS
    return {
        "name": f"last {days} days",
        "start": (now - timedelta(days=days)).date().isoformat(),
        "end": now.date().isoformat(),
    }


async def created_issues(actions: list[Doc], deps: Deps) -> list[dict[str, Any]]:
    """Every issue this agent filed in the window, as the tracker holds it now. An issue that
    has since vanished is left out entirely rather than reported from stale inputs."""
    if deps.linear is None:
        return []
    live: list[dict[str, Any]] = []
    for action in actions:
        if action.get("kind") != CREATE_KIND or action.get("status") != "done":
            continue
        identifier = (action.get("target_ids") or {}).get("identifier")
        if not identifier:
            continue
        issue = await deps.linear.get_issue(str(identifier))
        if issue is None:
            continue
        live.append({
            "identifier": issue.get("identifier", identifier),
            "title": issue.get("title", ""),
            "state": issue.get("state", ""),
            "assignee": (issue.get("assignee") or {}).get("name"),
            "url": issue.get("url", ""),
        })
    return live


def check_summary(task: Doc) -> dict[str, Any]:
    """One finished check, as JSON the model can read: what was expected, what was seen, and
    whether reality got there ahead of the deadline."""
    result = task.get("result") or {}
    return {
        "kind": task["kind"],
        "params": task.get("params") or {},
        "reason": task.get("reason") or "",
        "met": bool(result.get("met")),
        "early": bool(result.get("early")),
        "observed": result.get("observed") or {},
        "finished_at": task.get("finished_at"),
    }


async def gather(task: Doc, project: dict[str, Any], deps: Deps) -> dict[str, Any]:
    """Everything the reporter is allowed to know, read from the systems that own it."""
    project_id = task["project_id"]
    window = report_window(project, task.get("params") or {}, deps.clock.now())
    since = f"{window['start']}T00:00:00+00:00"

    done = await deps.db.query(
        "tasks", [("project_id", "==", project_id), ("status", "==", "done")],
        limit=TASK_SCAN_LIMIT,
    )
    checks = [check_summary(t) for t in done if str(t["kind"]).startswith("check_")]

    # Newest act picked in Python: ordering while filtering needs a composite index.
    acts = [t for t in done if t["kind"] == "act"]
    latest = max(acts, key=lambda t: str(t.get("created_at") or "")) if acts else None
    conflicts = ((latest or {}).get("result") or {}).get("conflicts") or []

    decisions = [
        {"id": d["id"], "statement": d.get("statement", ""), "quote": d.get("quote", ""),
         "source": d.get("source", "")}
        for d in await deps.db.query("decisions", [("project_id", "==", project_id)])
    ]

    actions = await deps.actions.list_since(project_id, since) if deps.actions else []
    counts: dict[str, int] = {}
    for action in actions:
        counts[str(action.get("kind"))] = counts.get(str(action.get("kind")), 0) + 1

    return {
        "sprint": window,
        "created_issues": await created_issues(actions, deps),
        "checks": checks,
        "decisions": decisions,
        "open_conflicts": conflicts,
        "actions_summary": {
            "total": len(actions),
            "by_kind": counts,
            "failed": sum(1 for a in actions if a.get("status") == "failed"),
        },
        "today": iso(deps.clock.now())[:10],
        "feedback": None,
    }


def _feedback(removed: list[dict[str, str]]) -> str:
    lines = "; ".join(f"{r['text']} — {r['reason']}" for r in removed)
    return (
        "These claims were removed from your previous report because they cite something that "
        f"could not be confirmed: {lines}. Every claim needs at least one reference, and every "
        "reference must be one that appears in the JSON you were given. Rewrite those claims "
        "with references you can point at, or leave them out."
    )


async def run(task: Doc, deps: Deps) -> StageResult:
    project = await deps.projects.get(task["project_id"])
    if project is None:
        raise PmError(f"project {task['project_id']} not found")
    if deps.reporter is None:
        raise PmError("report needs a reporter")
    # With no id gate nothing can be confirmed, so nothing is claimed.
    ids = deps.ids if deps.ids is not None else IdGate()

    payload = await gather(task, project, deps)
    proposal = Report.model_validate(await deps.reporter.run(payload)).model_dump()
    verdict = await check_citations(proposal, ids)

    bounced = False
    if not verdict.ok:
        bounced = True
        retry = Report.model_validate(
            await deps.reporter.run({**payload, "feedback": _feedback(verdict.removed)})
        ).model_dump()
        verdict = await check_citations(retry, ids)

    posted = await _post(task, project, verdict.report, payload["sprint"], deps)
    if posted:
        # ✅ on the mention that asked: thread_ts IS that message's ts. Best-effort.
        await react_quietly(deps.slack, task["payload"].get("channel"),
                            task["payload"].get("thread_ts"), "white_check_mark")
    return StageResult(result={
        "report": verdict.report,
        "removed": verdict.removed,
        "bounced": bounced,
        "posted": posted,
    })


async def _post(
    task: Doc, project: dict[str, Any], report: dict[str, Any], sprint: dict[str, Any], deps: Deps
) -> bool:
    """Post the report where it was asked for — the thread of the mention that requested it, or
    the project channel for a scheduled one. Best-effort: a Slack outage loses the message, not
    the report."""
    channel = task["payload"].get("channel") or project.get("slack_channel_id")
    if deps.slack is None or deps.actions is None or not channel:
        return False

    # Distinct root: must not collide with the act stage's summary key for the same event.
    key = idempotency_key(str(task.get("root_event_id") or task["id"]) + "report", 0, "slack.post")
    earlier = await deps.actions.find_by_key(key)
    if earlier is not None and earlier.get("status") == "done":
        return True

    action_id = await deps.actions.begin(
        task_id=task["id"], project_id=task["project_id"], kind="slack.post",
        idempotency_key=key, inputs={"channel": channel, "sprint": sprint.get("name", "")},
    )
    text = str(report.get("headline") or f"{sprint.get('name', 'Status')} report")
    ack = task["payload"].get("ack") or {}
    try:
        # A report asked for in a thread edits the "On it…" that acknowledged the ask.
        if ack.get("ts"):
            await deps.slack.update(str(ack.get("channel") or channel), str(ack["ts"]),
                                    text, report_blocks(report, sprint))
            ts = str(ack["ts"])
        else:
            ts = await deps.slack.post(
                channel, text, report_blocks(report, sprint),
                thread_ts=task["payload"].get("thread_ts"),
            )
    except SourceUnavailable as exc:
        await deps.actions.fail(action_id, redact(str(exc)))
        return False
    await deps.actions.finish(
        action_id, target_ids={"channel": channel, "ts": ts},
        revert={"op": "edit_message", "channel": channel, "ts": ts},
    )
    return True

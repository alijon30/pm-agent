"""The checks the agent scheduled for itself, and what it does when one comes back unmet.

This is the half of autonomy people actually feel. Filing a ticket is cheap; coming back three
days later to see whether it moved — and saying something, once, to the right person, at a
reasonable hour — is the part that makes the agent useful rather than noisy.

Every executor is deterministic and answers one question with a yes or a no plus what it saw. An
unreachable source is neither: it records `unavailable` and nudges nobody, because interrupting
someone over a network failure is worse than staying quiet."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.harness.core.clock import when_phrase
from app.harness.core.errors import PmError, SourceUnavailable
from app.harness.core.keys import idempotency_key
from app.harness.core.redact import redact
from app.harness.core.voice import first_name, issue_phrase
from app.harness.deps import Deps
from app.harness.kinds.phrasing import human_finding
from app.harness.kinds.templates import render
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc
from app.harness.verify.caps import check_caps
from app.harness.verify.roster import resolve_owner


async def check_issue_state(task: Doc, deps: Deps) -> tuple[bool, dict[str, Any]]:
    """Is the issue in one of the states we expected by now?"""
    if deps.linear is None:
        return False, {"status": "unavailable", "reason": "no tracker configured"}
    identifier = task["params"]["issue"]
    expected = [s.lower() for s in task["params"]["expect"]]
    try:
        issue = await deps.linear.get_issue(identifier)
    except SourceUnavailable as exc:
        return False, {"status": "unavailable", "reason": redact(str(exc))}
    if issue is None:
        return False, {"status": "gone", "issue": identifier}
    state = issue.get("state") or ""
    return state.lower() in expected, {
        "status": "ok", "issue": identifier, "state": state, "title": issue.get("title", ""),
        "assignee": (issue.get("assignee") or {}).get("name"),
        "due": issue.get("due_date"), "url": issue.get("url", ""),
    }


async def _newest_pr(task: Doc, deps: Deps) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    identifier = task["params"].get("issue")
    if deps.github is None:
        return None, {"status": "unavailable", "reason": "no code host configured"}
    try:
        if task["params"].get("pr"):
            pr = await deps.github.get_pr(int(task["params"]["pr"]))
            prs = [pr] if pr else []
        else:
            prs = await deps.github.find_prs_for_issue(identifier)
    except SourceUnavailable as exc:
        return None, {"status": "unavailable", "reason": redact(str(exc))}
    if not prs:
        return None, {"status": "ok", "issue": identifier, "prs": 0}
    return prs[0], {"status": "ok", "issue": identifier, "prs": len(prs)}


async def check_pr_exists(task: Doc, deps: Deps) -> tuple[bool, dict[str, Any]]:
    """Has anyone opened a pull request that references this issue?"""
    pr, observed = await _newest_pr(task, deps)
    if pr is None:
        return False, observed
    return True, {**observed, "pr": pr["number"], "pr_url": pr["url"], "state": pr["state"]}


async def check_pr_reviewed(task: Doc, deps: Deps) -> tuple[bool, dict[str, Any]]:
    """Has the newest pull request been looked at by a person?"""
    pr, observed = await _newest_pr(task, deps)
    if pr is None:
        return False, observed
    return bool(pr.get("reviews")), {
        **observed, "pr": pr["number"], "pr_url": pr["url"], "reviews": pr.get("reviews", 0),
    }


async def check_pr_merged(task: Doc, deps: Deps) -> tuple[bool, dict[str, Any]]:
    """Did the work actually land?"""
    pr, observed = await _newest_pr(task, deps)
    if pr is None:
        return False, observed
    return bool(pr.get("merged")), {
        **observed, "pr": pr["number"], "pr_url": pr["url"], "merged": bool(pr.get("merged")),
    }


CHECKS = {
    "check_issue_state": check_issue_state,
    "check_pr_exists": check_pr_exists,
    "check_pr_reviewed": check_pr_reviewed,
    "check_pr_merged": check_pr_merged,
}


def requester_of(task: Doc) -> dict[str, str] | None:
    """Who commissioned this check, if anyone did. Intake stamps this on; the planner's own
    follow-through has no requester and answers the assignee instead."""
    context = task.get("context") or {}
    slack_id = str(context.get("requester_slack_id") or "")
    if not slack_id:
        return None
    return {
        "slack_id": slack_id,
        "channel": str(context.get("request_channel") or ""),
        "ts": str(context.get("request_ts") or ""),
    }


def _template_for(task: Doc, observed: dict[str, Any]) -> str:
    kind, action = task["kind"], task.get("on_unmet")
    if action == "escalate_channel":
        return "escalate_no_owner" if not observed.get("assignee") else "escalate_stalled"
    if kind == "check_issue_state":
        return "issue_overdue" if observed.get("due") else "issue_not_started"
    if kind == "check_pr_exists":
        return "pr_missing"
    if kind == "check_pr_reviewed":
        return "pr_unreviewed"
    return "pr_unmerged"


def _values(
    observed: dict[str, Any], person: dict[str, Any] | None, now: datetime
) -> dict[str, str]:
    """Everything a template needs, already in the voice: a first name, a ticket that reads as a
    thing, a day rather than a date. The person is mentioned because a nudge is asking them to
    do something and a name they never see is not a nudge."""
    pr_url = str(observed.get("pr_url") or "")
    return {
        "person": first_name(person, mention=True) or "Nobody's on this",
        "issue": issue_phrase(
            str(observed.get("issue") or ""), str(observed.get("title") or ""),
            str(observed.get("url") or ""),
        ),
        "state": str(observed.get("state") or "open"),
        "when": when_phrase(str(observed.get("due") or ""), now) or "by now",
        "pr": f"<{pr_url}|the pull request>" if pr_url else "the pull request",
    }


async def on_unmet(task: Doc, deps: Deps, observed: dict[str, Any]) -> list[str]:
    """Say something, once, to one person, within the project's limits. Returns the action ids
    performed — empty when the agent decided to stay quiet, which is a real outcome.

    Who hears about it depends on who asked for the check: `ping_requester` answers the teammate
    who commissioned it, in their own thread, because they are the one waiting. Everything else
    goes to the project channel and is addressed to the owner."""
    action = task.get("on_unmet") or "none"
    if action == "none" or observed.get("status") != "ok":
        return []
    if deps.slack is None or deps.actions is None:
        return []
    project = await deps.projects.get(task["project_id"])
    if project is None:
        return []

    requester = requester_of(task) if action == "ping_requester" else None
    if action == "ping_requester" and requester is None:
        # Commissioned by nobody: there is no one to answer, and the assignee never agreed to
        # anything, so the agent stays quiet.
        return []
    channel = (requester or {}).get("channel") or project.get("slack_channel_id")
    if not channel:
        return []

    allowed = check_caps("ping", await deps.actions.counts_today(task["project_id"]),
                         deps.clock.now(), project.get("policy") or {})
    if not allowed.ok:
        # Deferring the whole task, not just the message: when it runs again it will re-observe,
        # and by then the nudge may no longer be warranted at all.
        await deps.queue.defer(task, allowed.defer_until or deps.clock.now(), allowed.reason)
        return []

    now = deps.clock.now()
    if requester is not None:
        template = "requester_unmet"
        text = render(template, **{**_values(observed, None, now),
                                   "person": f"<@{requester['slack_id']}>",
                                   "finding": human_finding(task, observed)})
    else:
        template = _template_for(task, observed)
        person = resolve_owner(observed.get("assignee"), project.get("roster") or [])
        text = render(template, **_values(observed, person, now))

    key = idempotency_key(task["id"], 0, "slack.nudge")
    if await deps.actions.find_by_key(key) is not None:
        return []
    action_id = await deps.actions.begin(
        task_id=task["id"], project_id=task["project_id"], kind="slack.post",
        idempotency_key=key, inputs={"channel": channel, "template": template},
    )
    try:
        ts = await deps.slack.post(
            channel, text, thread_ts=(requester or {}).get("ts") or None
        )
    except SourceUnavailable as exc:
        await deps.actions.fail(action_id, redact(str(exc)))
        return []
    await deps.actions.finish(
        action_id, target_ids={"channel": channel, "ts": ts},
        revert={"op": "edit_message", "channel": channel, "ts": ts},
    )
    return [action_id]


async def first_look(task: Doc, deps: Deps, observed: dict[str, Any]) -> list[str]:
    """The first check of a commitment reports back; the rest go quiet.

    Somebody asked for this and heard a promise. If the promise then works perfectly they hear
    nothing at all, and a watch you cannot tell is running is one you stop believing in. So the
    first check that comes back met says so once, tells them the silence that follows is the
    good outcome, and never speaks again unless something changes."""
    requester = requester_of(task)
    parent = str(task.get("parent_task_id") or "")
    if requester is None or not parent or observed.get("status") != "ok":
        return []
    channel = requester["channel"]
    if deps.slack is None or deps.actions is None or not channel:
        return []
    # This task is still leased while its handler runs, so any done sibling is an earlier check
    # of the same commitment — and this is only the first look when there are none.
    earlier = await deps.db.query(
        "tasks", [("parent_task_id", "==", parent), ("status", "==", "done")], limit=50
    )
    if earlier:
        return []

    project = await deps.projects.get(task["project_id"])
    if project is None:
        return []
    if not check_caps("ping", await deps.actions.counts_today(task["project_id"]),
                      deps.clock.now(), project.get("policy") or {}).ok:
        return []
    key = idempotency_key(task["id"], 0, "slack.firstlook")
    if await deps.actions.find_by_key(key) is not None:
        return []

    action_id = await deps.actions.begin(
        task_id=task["id"], project_id=task["project_id"], kind="slack.post",
        idempotency_key=key, inputs={"channel": channel, "template": "first_look"},
    )
    issue = issue_phrase(str(observed.get("issue") or ""), str(observed.get("title") or ""),
                         str(observed.get("url") or ""))
    try:
        ts = await deps.slack.post(
            channel,
            f"First look at {issue or 'it'}: {human_finding(task, observed, met=True)} — "
            "I'll keep watching quietly and only speak up if that changes.",
            thread_ts=requester["ts"] or None,
        )
    except SourceUnavailable as exc:
        await deps.actions.fail(action_id, redact(str(exc)))
        return []
    await deps.actions.finish(
        action_id, target_ids={"channel": channel, "ts": ts},
        revert={"op": "edit_message", "channel": channel, "ts": ts},
    )
    return [action_id]


async def run_check(task: Doc, deps: Deps) -> StageResult:
    """One scheduled check: observe, say something if it is worth saying, and record both."""
    executor = CHECKS.get(task["kind"])
    if executor is None:
        raise PmError(f"no executor for kind {task['kind']!r}")
    met, observed = await executor(task, deps)
    acted = await first_look(task, deps, observed) if met else await on_unmet(task, deps, observed)
    return StageResult(result={"met": met, "observed": observed, "acted": acted})


async def run_nudge(task: Doc, deps: Deps) -> StageResult:
    """A nudge the planner scheduled directly, rather than one a failed check produced."""
    if deps.slack is None or deps.actions is None:
        raise PmError("nudge needs Slack and an action log")
    project = await deps.projects.get(task["project_id"])
    if project is None:
        raise PmError(f"project {task['project_id']} not found")
    channel = project.get("slack_channel_id")
    if not channel:
        return StageResult(result={"sent": False, "reason": "no channel configured"})

    allowed = check_caps("ping", await deps.actions.counts_today(task["project_id"]),
                         deps.clock.now(), project.get("policy") or {})
    if not allowed.ok:
        await deps.queue.defer(task, allowed.defer_until or deps.clock.now(), allowed.reason)
        return StageResult(result={"sent": False, "reason": allowed.reason})

    params = task["params"]
    person = resolve_owner(params.get("person"), project.get("roster") or [])
    observed = {"issue": params.get("about", ""), "title": "", "state": "open", "url": ""}
    text = render(params["template"], **_values(observed, person, deps.clock.now()))

    key = idempotency_key(task["id"], 0, "slack.nudge")
    if await deps.actions.find_by_key(key) is not None:
        return StageResult(result={"sent": False, "reason": "already sent"})
    action_id = await deps.actions.begin(
        task_id=task["id"], project_id=task["project_id"], kind="slack.post",
        idempotency_key=key, inputs={"channel": channel, "template": params["template"]},
    )
    try:
        ts = await deps.slack.post(channel, text)
    except SourceUnavailable as exc:
        await deps.actions.fail(action_id, redact(str(exc)))
        return StageResult(result={"sent": False, "reason": redact(str(exc))})
    await deps.actions.finish(
        action_id, target_ids={"channel": channel, "ts": ts},
        revert={"op": "edit_message", "channel": channel, "ts": ts},
    )
    return StageResult(result={"sent": True, "acted": [action_id]})

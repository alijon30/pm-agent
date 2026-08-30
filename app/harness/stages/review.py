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
from app.harness.connectors.slack_blocks import standup_blocks
from app.harness.core.clock import iso
from app.harness.core.errors import PmError, SourceUnavailable
from app.harness.core.redact import redact
from app.harness.core.voice import first_name
from app.harness.deps import Deps
from app.harness.kinds.phrasing import DONE_STATES
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc
from app.harness.store.tasks import OPEN_STATUSES
from app.harness.verify.caps import check_caps

WINDOW_HOURS = 24
SCAN_LIMIT = 500
# What "today" means in a standup: anything due in the next two days is near enough to plan
# around, and five lines is as many promises as anyone reads before breakfast.
WATCH_HOURS = 48
WATCH_LINES = 5


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
            # Who owns it, so the standup can say "Priya got INV-26 moving" rather than
            # counting the things that moved.
            "assignee": str((live.get("assignee") or {}).get("name") or ""),
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
        {"ref": f"task:{t['id']}", "kind": t["kind"], "params": t.get("params") or {},
         "issue": (t.get("params") or {}).get("issue"),
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

    # A person taking the trouble to say "that was wrong", or to undo something, is the
    # strongest evidence of a mistake this agent ever gets. It should not have to infer it
    # from a check that came back unmet.
    reverted = [
        {"ref": f"action:{a['id']}", "kind": a.get("kind"),
         "identifier": (a.get("target_ids") or {}).get("identifier"),
         "by": a.get("reverted_by"), "at": a.get("reverted_at")}
        for a in actions
        if a.get("reverted_at") and str(a.get("reverted_at") or "") >= since
    ]
    corrections: list[dict[str, Any]] = []
    if deps.wiki is not None:
        for page in await deps.wiki.pages(project_id):
            if str(page.get("kind")) != "correction":
                continue
            corrections.extend(
                {"ref": f"wiki:{page.get('slug')}#{e.get('id')}", "text": e.get("text"),
                 "said_by": e.get("said_by"), "at": e.get("created_at")}
                for e in page.get("entries") or []
                if str(e.get("created_at") or "") >= since
            )

    return {
        "window": {"from": since, "to": iso(now)},
        "checks": checks,
        "nudges": nudges,
        "movements": await _movements(nudges, tasks_by_id, deps),
        "superseded": superseded,
        "failures": failures,
        "corrections": corrections,
        "reverts": reverted,
    }


def evidence_ids(outcomes: dict[str, Any]) -> set[str]:
    """Every reference the reviewer was shown — the whole of what a lesson may cite."""
    return {
        str(row["ref"])
        for section in ("checks", "nudges", "movements", "superseded", "failures",
                        "corrections", "reverts")
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


async def at_risk(outcomes: dict[str, Any], today: str) -> tuple[list[Doc], list[dict[str, Any]]]:
    """What is slipping, from what the checks already saw: the ones that came back with nothing,
    and any issue observed past its own date and not finished. No extra fetch — a standup should
    not cost a round of tracker calls."""
    unmet = [c for c in outcomes.get("checks") or [] if not c.get("met")]
    overdue: dict[str, dict[str, Any]] = {}
    for check in outcomes.get("checks") or []:
        observed = check.get("observed") or {}
        due, state = str(observed.get("due") or ""), str(observed.get("state") or "")
        identifier = str(observed.get("issue") or "")
        if identifier and due and due < today and state.lower() not in DONE_STATES:
            overdue[identifier] = {"issue": identifier, "due": due, "state": state or "open"}
    return unmet, list(overdue.values())


async def watching(project_id: str, deps: Deps) -> tuple[list[Doc], str]:
    """The checks due soon, and — when there are none — the date of the next one, so a quiet day
    can say how long it will stay quiet."""
    open_checks = sorted(
        (
            t for t in await deps.db.query(
                "tasks", [("project_id", "==", project_id),
                          ("status", "in", list(OPEN_STATUSES))], limit=SCAN_LIMIT)
            if str(t["kind"]).startswith("check_") and t.get("due_at")
        ),
        key=lambda t: str(t["due_at"]),
    )
    if not open_checks:
        return [], ""
    horizon = iso(deps.clock.now() + timedelta(hours=WATCH_HOURS))
    soon = [t for t in open_checks if str(t["due_at"]) <= horizon]
    return soon[:WATCH_LINES], "" if soon else str(open_checks[0]["due_at"])


def _owners(outcomes: dict[str, Any], project: Doc) -> dict[str, str]:
    """Which first name goes with which ticket, from what the checks already observed. The
    standup addresses people, so it needs names it did not have to look anything up for."""
    owners: dict[str, str] = {}
    for check in outcomes.get("checks") or []:
        observed = check.get("observed") or {}
        identifier, who = str(observed.get("issue") or ""), str(observed.get("assignee") or "")
        if identifier and who:
            owners.setdefault(identifier, first_name(who))
    for mover in outcomes.get("movements") or []:
        identifier, who = str(mover.get("issue") or ""), str(mover.get("assignee") or "")
        if identifier and who:
            owners.setdefault(identifier, first_name(who))
    return owners


def _titles(outcomes: dict[str, Any]) -> dict[str, str]:
    """What each ticket is, from what the checks saw. Costs nothing — the observation is already
    in hand — and turns a key in a standup line into a thing the reader recognises."""
    titles: dict[str, str] = {}
    for check in outcomes.get("checks") or []:
        observed = check.get("observed") or {}
        identifier, title = str(observed.get("issue") or ""), str(observed.get("title") or "")
        if identifier and title:
            titles.setdefault(identifier, title)
    return titles


async def _standup(
    task: Doc, project: Doc, outcomes: dict[str, Any], lesson: str, deps: Deps
) -> bool:
    """The agent speaking first, once a day, before anybody asks it anything.

    Exempt from quiet hours on purpose: this runs at the start of the working day by design, and
    deferring the morning message until the morning is over would be a bug wearing a policy's
    clothes. The daily ping budget still applies."""
    channel = project.get("slack_channel_id")
    if deps.slack is None or deps.actions is None or not channel:
        return False

    today = deps.clock.now().date().isoformat()
    key = f"standup:{project['id']}:{today}"
    if await deps.actions.find_by_key(key) is not None:
        return False
    allowed = check_caps(
        "ping", await deps.actions.counts_today(str(project["id"])), deps.clock.now(),
        project.get("policy") or {}, respect_quiet_hours=False,
    )
    if not allowed.ok:
        return False

    soon, next_due = await watching(str(project["id"]), deps)
    unmet, overdue = await at_risk(outcomes, today)
    blocks = standup_blocks(
        sprint=project.get("sprint") or {}, today=today, watching=soon,
        since={
            "met": sum(1 for c in outcomes["checks"] if c["met"] and not c["early"]),
            "early": sum(1 for c in outcomes["checks"] if c["early"]),
            "nudged": len(outcomes["nudges"]),
            "movers": [
                {"who": m.get("assignee") or "", "issue": m["issue"]}
                for m in outcomes["movements"] if m["moved"]
            ],
        },
        unmet=unmet, overdue=overdue, lesson=lesson, next_due=next_due,
        owners=_owners(outcomes, project), titles=_titles(outcomes),
        now=deps.clock.now(),
    )

    action_id = await deps.actions.begin(
        task_id=str(task["id"]), project_id=str(project["id"]), kind="slack.post",
        idempotency_key=key, inputs={"channel": channel, "template": "standup"},
    )
    try:
        first = str((blocks[0].get("text") or {}).get("text") or "").splitlines()[0]
        ts = await deps.slack.post(str(channel), first.strip("*"), blocks)
    except SourceUnavailable as exc:
        # A standup nobody received is a shame, not a failure: the review still learned and
        # still re-planned, and tomorrow brings another one.
        await deps.actions.fail(action_id, redact(str(exc)))
        return False
    await deps.actions.finish(
        action_id, target_ids={"channel": channel, "ts": ts},
        revert={"op": "edit_message", "channel": channel, "ts": ts},
    )
    return True


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

    posted = await _standup(task, project, outcomes, kept[0]["text"] if kept else "", deps)

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
            "standup": posted,
        },
        children=children,
    )

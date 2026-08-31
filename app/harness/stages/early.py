"""Early resolution: reality moved, so the schedule follows it."""

from __future__ import annotations

import logging
from typing import Any

from app.harness.core.clock import when_phrase
from app.harness.core.errors import SourceUnavailable
from app.harness.core.redact import redact
from app.harness.core.voice import first_name
from app.harness.core.words import count_of
from app.harness.deps import Deps
from app.harness.kinds.phrasing import human_check
from app.harness.stages.checks import CHECKS

log = logging.getLogger(__name__)

RESOLVABLE = ("queued", "blocked", "deferred")


async def resolve_early(identifier: str, deps: Deps) -> list[str]:
    """Re-evaluate every open check about this issue. Returns the ids of checks that completed
    ahead of schedule."""
    resolved: list[str] = []
    open_checks = [
        t for t in await deps.db.query("tasks", [("status", "in", list(RESOLVABLE))])
        if t["kind"] in CHECKS and (t.get("params") or {}).get("issue") == identifier
    ]
    for task in open_checks:
        met, observed = await CHECKS[task["kind"]](task, deps)
        if not met:
            continue
        done = await deps.queue.complete_early(
            task, {"met": True, "observed": observed, "early": True, "acted": []}
        )
        if done:
            resolved.append(task["id"])
    if resolved:
        await deps.queue.promote_ready()
        await _note_in_thread(identifier, resolved, deps)
    return resolved


async def _good_news(identifier: str, resolved: list[str], deps: Deps) -> str:
    """One line of good news, with the person in it."""
    cleared = [t for t in [await deps.db.get("tasks", tid) for tid in resolved] if t]
    who = first_name(str(
        ((cleared[0] if cleared else {}).get("result") or {}).get("observed", {}).get("assignee")
        or ""
    ))
    # moot: the work finished outright rather than somebody getting ahead of the schedule.
    moot = bool(cleared) and all(
        ((t.get("result") or {}).get("observed") or {}).get("moot") for t in cleared
    )
    opening = f"{identifier} is done" if moot else (
        f"{who}'s already on {identifier}" if who else f"{identifier} is already underway"
    )
    dates = sorted(when_phrase(str(t.get("due_at") or ""), deps.clock.now()) for t in cleared)
    when = f" the {dates[0]} check" if len(dates) == 1 and dates[0] and not moot else (
        f" {count_of(len(cleared), 'remaining check' if moot else 'check')}"
    )
    upcoming = [
        t for t in await deps.db.query("tasks", [("status", "in", list(RESOLVABLE))])
        if (t.get("params") or {}).get("issue") == identifier and t["id"] not in resolved
    ]
    if upcoming:
        nxt = min(upcoming, key=lambda t: str(t.get("due_at") or ""))
        return (f"{opening} — I've cleared{when}. Next up: {human_check(nxt)}, "
                f"{when_phrase(str(nxt.get('due_at') or ''), deps.clock.now())}.")
    # "early" is wrong when the work simply finished.
    return f"{opening} — I've cleared{when}." if moot else f"{opening} — I've cleared{when} early."


async def _note_in_thread(identifier: str, resolved: list[str], deps: Deps) -> None:
    """A quiet line under the plan announcement, so the channel sees progress without a ping.
    Best-effort: the early completion stands whether or not this lands."""
    if deps.slack is None or deps.actions is None:
        return
    plan_posts = [
        a for a in await deps.db.query("actions", [("kind", "==", "slack.post")])
        if a.get("status") == "done" and (a.get("inputs") or {}).get("tasks")
    ]
    if not plan_posts:
        return
    # No order_by: Firestore returns these in any order, so the newest is chosen here.
    newest = max(plan_posts, key=lambda a: str(a.get("created_at") or ""))
    target = newest.get("target_ids") or {}
    channel, ts = target.get("channel"), target.get("ts")
    if not channel or not ts:
        return
    try:
        await deps.slack.post(channel, await _good_news(identifier, resolved, deps), thread_ts=ts)
    except SourceUnavailable as exc:
        log.warning("early note for %s not posted: %s", identifier, redact(str(exc)))
    except Exception:  # noqa: BLE001 — decoration never outranks the work, but it must not vanish
        log.warning("early note for %s failed unexpectedly", identifier, exc_info=True)


def issue_identifier_of(payload: dict[str, Any]) -> str | None:
    """The Linear webhook body's issue identifier, wherever this payload shape carries it."""
    data = payload.get("data") or {}
    identifier = data.get("identifier")
    if identifier:
        return str(identifier)
    number, team = data.get("number"), (data.get("team") or {}).get("key")
    if number and team:
        return f"{team}-{number}"
    return None

"""Early resolution: reality moved, so the schedule follows it.

Scheduled checks are deadlines, not appointments. When an issue changes, every open check about
it is re-evaluated immediately: a check whose condition is already met completes now — ahead of
its due date — and whatever depended on it unblocks now too. A check that is still unmet is left
alone until its due time, because the deadline is the promise; chasing someone early about
unfinished work is how an agent gets muted.

Nothing here fires on_unmet, posts, or nudges. It only turns future good news into present
fact — the one kind of action that cannot annoy anyone."""

from __future__ import annotations

import logging
from typing import Any

from app.harness.connectors.slack_blocks import count_of
from app.harness.core.errors import SourceUnavailable
from app.harness.core.redact import redact
from app.harness.deps import Deps
from app.harness.stages.checks import CHECKS

log = logging.getLogger(__name__)

RESOLVABLE = ("queued", "blocked", "deferred")


async def resolve_early(identifier: str, deps: Deps) -> list[str]:
    """Re-evaluate every open check about this issue. Returns the ids of checks that completed
    ahead of schedule. Dependency order does not matter: a met condition is met regardless of
    which check was scheduled to notice it first, and promote_ready() reconciles the graph."""
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


async def _note_in_thread(identifier: str, resolved: list[str], deps: Deps) -> None:
    """A quiet line under the plan announcement, so the channel sees progress without a ping.
    Best-effort: the early completion stands whether or not this lands.

    Best-effort is not the same as silent. A bare `except Exception: return` here hid the fact
    that this note was never reaching the channel at all, so anything unexpected is logged with
    its traceback; only an outage is shrugged off, because that one is ordinary."""
    if deps.slack is None or deps.actions is None:
        return
    plan_posts = [
        a for a in await deps.db.query("actions", [("kind", "==", "slack.post")])
        if a.get("status") == "done" and (a.get("inputs") or {}).get("tasks")
    ]
    if not plan_posts:
        return
    # The query has no order_by — Firestore returns these in whatever order it likes, so the
    # newest announcement is chosen here rather than by taking the last row.
    newest = max(plan_posts, key=lambda a: str(a.get("created_at") or ""))
    target = newest.get("target_ids") or {}
    channel, ts = target.get("channel"), target.get("ts")
    if not channel or not ts:
        return
    try:
        await deps.slack.post(
            channel,
            f"✓ {identifier} is already underway — I've closed "
            f"{count_of(len(resolved), 'planned check')} early.",
            thread_ts=ts,
        )
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

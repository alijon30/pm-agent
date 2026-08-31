"""The status message as a live checklist: the plan, and where the agent is in it.

The webhook posts the plan the moment a call lands; extract and reconcile tick their step off
as they finish, each with a short honest note; the act stage then replaces the whole message
with the call summary, which is the payoff. All of it is decoration — a Slack hiccup here must
never undo or delay pipeline work, so every edit is best-effort."""

from __future__ import annotations

import logging
from typing import Any

from app.harness.core.voice import spelled
from app.harness.store.db import Doc

log = logging.getLogger(__name__)

TODO = (
    "read the call",
    "check it against Linear, the docs and the code",
    "file what was agreed",
    "set up the follow-through",
)
DONE = (
    "read the call",
    "checked it against Linear, the docs and the code",
    "filed what was agreed",
    "set up the follow-through",
)


def spoken(count: int, noun: str) -> str:
    """`spoken(2, "action item")` → "two action items". Zero is the caller's problem: a step
    with nothing to say should say something specific, not "zero things"."""
    return f"{spelled(count)} {noun}{'' if count == 1 else 's'}"


def read_note(action_items: int, decisions: int) -> str:
    """What reading the call turned up, e.g. "two action items, one decision"."""
    parts = []
    if action_items:
        parts.append(spoken(action_items, "action item"))
    if decisions:
        parts.append(spoken(decisions, "decision"))
    return ", ".join(parts) or "nothing that needs filing"


def check_note(verified: int) -> str:
    return spoken(verified, "item") + " checked out" if verified else "nothing survived verification"


def checklist(title: str, *, doing: int, notes: dict[int, str] | None = None) -> str:
    """The whole status message: a header line Slack can preview, then one line per step."""
    notes = notes or {}
    lines = [f"✻ *{title}* — on it. The plan:"]
    for index, step in enumerate(TODO):
        if index < doing:
            note = notes.get(index, "")
            lines.append(f"✓ {DONE[index]}" + (f" — {note}" if note else ""))
        elif index == doing:
            lines.append(f"▸ {step}")
        else:
            lines.append(f"○ {step}")
    return "\n".join(lines)


async def show(task: Doc, deps: Any, *, title: str, doing: int, notes: dict[int, str]) -> None:
    """Edit the call's status message to the current state of the plan. Quietly does nothing
    when there is no Slack, no status message, or Slack is down — the record does not depend
    on the decoration."""
    if deps.slack is None:
        return
    from app.harness.stages.act import _status_message

    status = await _status_message(task, deps)
    if status is None:
        return
    try:
        await deps.slack.update(
            status["channel"], status["ts"], checklist(title, doing=doing, notes=notes)
        )
    except Exception as exc:  # noqa: BLE001 — decoration never outranks the pipeline
        log.warning("could not update the status checklist: %s", exc)

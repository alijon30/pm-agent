"""Block Kit builders. Pure functions: dicts in, dicts out, no I/O — so the exact shape of what
the team sees is unit-testable, and the summary can never fail the run that produced it.

The copy rule for everything in this module: a team lead reads these messages at a glance,
between other things. So nothing here prints the vocabulary this system happens to use for
itself — no task kinds, no ISO timestamps, no typed references, no counts of zero. The agent
says what it did and what it will do, in the words a colleague would use.

Slack rejects a message with more than 50 blocks, so every builder truncates and says so rather
than losing the whole post."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

MAX_BLOCKS = 50
REVERT_ACTION = "revert"
WRONG_ACTION = "wrong"

# What each scheduled check means, said the way the person waiting for it would say it.
CHECK_SENTENCES = {
    "check_issue_state": "check that {issue} is underway",
    "check_pr_exists": "look for a pull request on {issue}",
    "check_pr_reviewed": "make sure {issue}'s PR gets a review",
    "check_pr_merged": "confirm {issue} landed",
    "nudge": "remind {person} about {about}",
    "escalate": "raise {about} in the channel",
}

# What happens if a check comes back unmet — the half of a promise that makes it worth reading.
UNMET_CONSEQUENCES = {
    "nudge_assignee": "if not, I'll nudge the assignee",
    "nudge_reviewer": "if not, I'll ask for a reviewer",
    "escalate_channel": "if not, I'll raise it here",
}

SECTION_TITLES = {
    "shipped": "Shipped",
    "moved": "In motion",
    "blocked": "Blocked",
    "at_risk": "At risk",
    "conflicts": "Sources disagree",
    "open_questions": "Open questions",
    "decisions": "Decided",
}

REF = re.compile(r"^([a-z]+):(.+)$", re.IGNORECASE)


def count_of(number: int, singular: str) -> str:
    """"1 ticket", "2 tickets". One pluralisation rule, so no message ever says "check(s)"."""
    return f"{number} {singular}" if number == 1 else f"{number} {singular}s"


def _parsed(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def human_date(value: str) -> str:
    """"Sep 1". Empty for anything unparseable, so a caller can leave the date out entirely."""
    when = _parsed(value)
    return f"{when:%b} {when.day}" if when else ""


def human_due(value: str) -> str:
    """"Mon Sep 1" — the weekday is what tells someone whether a date is soon."""
    when = _parsed(value)
    return f"{when:%a %b} {when.day}" if when else ""


def human_check(task: dict[str, Any]) -> str:
    """One scheduled check as a sentence. An unfamiliar kind falls back to the reason the
    planner gave, which is already written for a human."""
    params = task.get("params") or {}
    sentence = CHECK_SENTENCES.get(str(task.get("kind") or ""))
    if sentence is None:
        return str(task.get("reason") or task.get("kind") or "check on this")
    return sentence.format(
        issue=params.get("issue") or "it",
        person=params.get("person") or "them",
        about=params.get("about") or "it",
    )


def ref_chip(ref: str) -> str:
    """A citation as something a person can read: `linear:INV-26` → "INV-26", a Fathom moment →
    "call @ 1:58", a decision id → "ledger". The typed form is how the gate checks a claim; it
    is not how anyone should have to read one."""
    match = REF.match((ref or "").strip())
    if not match:
        return (ref or "").strip()
    kind, target = match.group(1).lower(), match.group(2).strip()
    if kind == "linear":
        return target
    if kind == "decision":
        return "ledger"
    if kind == "notion":
        return "spec"
    if kind == "wiki":
        return "brain"
    if kind == "fathom":
        _meeting, _, timestamp = target.partition("@")
        stamp = timestamp.removeprefix("00:") if timestamp.startswith("00:") else timestamp
        return f"call @ {stamp}" if stamp else "call"
    if kind == "code":
        path, _, line = target.rpartition(":")
        if path and line.isdigit():
            return f"{path.rsplit('/', 1)[-1]}:{line}"
        return target.rsplit("/", 1)[-1]
    return ref.strip()


def ref_chips(refs: list[str] | tuple[str, ...]) -> list[str]:
    """Readable citations, in order, without repeats — three decisions cited on one claim are
    one "ledger", not three."""
    chips: list[str] = []
    for ref in refs or []:
        chip = ref_chip(str(ref))
        if chip and chip not in chips:
            chips.append(chip)
    return chips


def _section(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _context(text: str) -> dict[str, Any]:
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}


def revert_button(action_id: str, label: str = "Revert") -> dict[str, Any]:
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": label},
        "action_id": f"{REVERT_ACTION}:{action_id}",
        "value": action_id,
        "style": "danger",
    }


def wrong_button(post_ref: str, label: str = "Something's wrong") -> dict[str, Any]:
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": label},
        "action_id": f"{WRONG_ACTION}:{post_ref}",
        "value": post_ref,
    }


def _truncate(blocks: list[dict[str, Any]], keep_last: int = 1) -> list[dict[str, Any]]:
    """Trim the middle, not the end: the action buttons must survive."""
    if len(blocks) <= MAX_BLOCKS:
        return blocks
    head = blocks[: MAX_BLOCKS - keep_last - 1]
    tail = blocks[-keep_last:] if keep_last else []
    dropped = len(blocks) - len(head) - len(tail)
    return [*head, _context(f"_… {dropped} more not shown; see the console_"), *tail]


def call_summary_blocks(
    meeting: dict[str, Any],
    created: list[dict[str, Any]],
    updated: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    *,
    post_ref: str = "",
) -> list[dict[str, Any]]:
    """One message per call: what was filed, what was skipped, what disagrees, and a revert
    button per action performed.

    The headline counts only what happened. A call that filed two tickets says "filed 2
    tickets" and stops — nobody needs to be told that nothing was skipped."""
    title = meeting.get("title") or "call"
    url = meeting.get("url") or ""
    heading = f"*<{url}|{title}>*" if url else f"*{title}*"
    blocks: list[dict[str, Any]] = [
        _section(f"{heading} — {what_happened(created, updated, skipped, conflicts)}")
    ]

    for item in created:
        line = f"• <{item.get('url', '')}|{item.get('identifier', '?')}> {item.get('title', '')}"
        if item.get("owner"):
            line += f" — {item['owner']}"
        blocks.append(_section(line))
        if item.get("note"):
            blocks.append(_context(item["note"]))

    for item in updated:
        blocks.append(
            _section(f"• <{item.get('url', '')}|{item.get('identifier', '?')}> "
                     f"{item.get('note') or 'raised again in this call'}")
        )

    for item in skipped:
        blocks.append(
            _context(f"Left alone: {item.get('title', '?')} — {item.get('reason', '')}")
        )

    for conflict in conflicts:
        sides = "\n".join(
            f"    · {s.get('claim', '')}  _{ref_chip(str(s.get('source', '')))}_"
            for s in conflict.get("sides", [])
        )
        blocks.append(
            _section(f"⚠️ *Sources disagree* on {conflict.get('about', '')}\n{sides}")
        )

    elements = [revert_button(a["id"], f"Revert {a.get('label', 'action')}") for a in actions]
    if post_ref:
        elements.append(wrong_button(post_ref))
    if elements:
        blocks.append({"type": "actions", "elements": elements[:5]})
    return _truncate(blocks)


def what_happened(
    created: list[dict[str, Any]],
    updated: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
) -> str:
    """The headline of a call summary, and the notification line above it: only the parts
    that are not zero. Both say the same thing, so the preview never reads differently from the
    message it previews."""
    parts: list[str] = []
    if created:
        parts.append(f"filed {count_of(len(created), 'ticket')}")
    if updated:
        parts.append(f"updated {len(updated)}")
    if conflicts:
        parts.append(count_of(len(conflicts), "conflict"))
    if skipped:
        parts.append(f"{len(skipped)} skipped")
    return " · ".join(parts) or "nothing needed filing"


def plan_summary_blocks(tasks: list[dict[str, Any]], trimmed: list[str]) -> list[dict[str, Any]]:
    """The agent saying what it will check, and when — the visible half of the planner.

    Each line is a promise with a date and a consequence, because "check_pr_exists on
    2026-09-04" tells a reader nothing they can act on."""
    if not tasks:
        return [_section("_Nothing needs watching right now._")]
    lines: list[str] = []
    for task in tasks:
        when = human_due(str(task.get("due_at") or ""))
        consequence = UNMET_CONSEQUENCES.get(str(task.get("on_unmet") or "none"))
        lines.append(
            f"• {f'{when} — ' if when else ''}{human_check(task)}"
            f"{f' _({consequence})_' if consequence else ''}"
        )
    blocks = [_section("*I'll follow up on this:*\n" + "\n".join(lines))]
    if trimmed:
        blocks.append(_context(
            f"_I dropped {count_of(len(trimmed), 'idea')} I could not verify: "
            f"{'; '.join(trimmed)}_"
        ))
    return _truncate(blocks)


def report_blocks(report: dict[str, Any], sprint: dict[str, Any]) -> list[dict[str, Any]]:
    """The sprint report as the team sees it: a headline, then one block per section with every
    claim carrying the references that were checked before it was allowed to be said."""
    span = f" ({human_date(str(sprint.get('start', '')))} → " \
           f"{human_date(str(sprint.get('end', '')))})" if sprint.get("start") else ""
    heading = f"*{sprint.get('name') or 'This sprint'}*{span}"
    blocks: list[dict[str, Any]] = [_section(f"{heading}\n{report.get('headline') or ''}")]

    for section in report.get("sections") or []:
        claims = section.get("claims") or []
        if not claims:
            continue
        name = str(section.get("name") or "")
        title = SECTION_TITLES.get(name, name.replace("_", " ").capitalize())
        lines = [
            f"• {c.get('text', '')} _({' · '.join(ref_chips(c.get('refs') or []))})_"
            for c in claims
        ]
        blocks.append(_section(f"*{title}*\n" + "\n".join(lines)))

    if len(blocks) == 1:
        blocks.append(_context("_Nothing I can back up with a source yet — see the console._"))
    return _truncate(blocks, keep_last=0)


def wrong_modal(post_ref: str) -> dict[str, Any]:
    """The correction form. Its callback_id carries the post it is about."""
    return {
        "type": "modal",
        "callback_id": "correction",
        "private_metadata": post_ref,
        "title": {"type": "plain_text", "text": "Correct the agent"},
        "submit": {"type": "plain_text", "text": "Save"},
        "blocks": [
            {
                "type": "input",
                "block_id": "wrong",
                "label": {"type": "plain_text", "text": "What did it get wrong?"},
                "element": {"type": "plain_text_input", "action_id": "value", "multiline": True},
            },
            {
                "type": "input",
                "block_id": "right",
                "label": {"type": "plain_text", "text": "What should it do instead?"},
                "element": {"type": "plain_text_input", "action_id": "value", "multiline": True},
            },
            {
                "type": "input",
                "block_id": "scope",
                "label": {"type": "plain_text", "text": "Applies to"},
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "This project"},
                        "value": "project",
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "This project"},
                         "value": "project"},
                        {"text": {"type": "plain_text", "text": "Everywhere"}, "value": "global"},
                    ],
                },
            },
        ],
    }

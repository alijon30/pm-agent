"""Block Kit builders. Pure functions: dicts in, dicts out, no I/O — so the exact shape of what
the team sees is unit-testable, and the summary can never fail the run that produced it.

The copy rule for everything in this module: a team lead reads these messages at a glance,
between other things. So nothing here prints the vocabulary this system happens to use for
itself — no task kinds, no ISO timestamps, no typed references, no counts of zero. The agent
says what it did and what it will do, in the words a colleague would use.

Slack rejects a message with more than 50 blocks, so every builder truncates and says so rather
than losing the whole post."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.harness.core.clock import human_date, human_due, readable, when_phrase
from app.harness.core.refs import ref_chip, ref_chips
from app.harness.core.voice import (
    consequence_phrase,
    first_name,
    issue_phrase,
    noun_phrase,
    sentence_list,
    spelled,
)
from app.harness.core.words import count_of
from app.harness.kinds.phrasing import human_check, human_finding, human_working

MAX_BLOCKS = 50
REVERT_ACTION = "revert"
WRONG_ACTION = "wrong"

# Charter rule 10: three to five one-line bullets. A standup that grows with the backlog stops
# being read, so the ceiling is enforced here rather than hoped for.
STANDUP_BULLETS = 5

SECTION_TITLES = {
    "shipped": "Shipped",
    "moved": "In motion",
    "blocked": "Blocked",
    "at_risk": "At risk",
    "conflicts": "Sources disagree",
    "open_questions": "Open questions",
    "decisions": "Decided",
}

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
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """One message per call: what was filed, what was skipped, what disagrees, and a revert
    button per action performed.

    The headline counts only what happened. A call that filed two tickets says "filed 2
    tickets" and stops — nobody needs to be told that nothing was skipped."""
    title = meeting.get("title") or "call"
    url = meeting.get("url") or ""
    heading = f"*<{url}|{title}>*" if url else f"*{title}*"
    blocks: list[dict[str, Any]] = [
        _section(f"{heading} — {what_happened(created, updated, skipped, conflicts)}.")
    ]

    for item in created:
        line = "• " + issue_phrase(
            str(item.get("identifier") or "?"), str(item.get("title") or ""),
            str(item.get("url") or ""),
        )
        owner = first_name(str(item.get("owner") or ""))
        if owner:
            line += f" — {owner}"
        line += _from_the_call(item, now)
        blocks.append(_section(line))
        if item.get("note"):
            blocks.append(_context(item["note"]))

    for item in updated:
        blocks.append(_section(
            "• " + issue_phrase(str(item.get("identifier") or "?"), "", str(item.get("url") or ""))
            + f" — {item.get('note') or 'raised again on the call'}"
        ))

    for item in skipped:
        blocks.append(_context(
            f"Left out on purpose: {noun_phrase(str(item.get('title') or '?'))} "
            f"({item.get('reason', '')})"
        ))

    for conflict in conflicts:
        sides = "\n".join(
            f"    • {s.get('claim', '')} — {ref_chip(str(s.get('source', '')))}"
            for s in conflict.get("sides", [])
        )
        blocks.append(_section(
            f"⚠️ *Two answers on {conflict.get('about', 'this')}, and I can't pick one.*"
            f"\n{sides}"
        ))

    elements = [revert_button(a["id"], f"Revert {a.get('label', 'action')}") for a in actions]
    if post_ref:
        elements.append(wrong_button(post_ref))
    if elements:
        blocks.append({"type": "actions", "elements": elements[:5]})
    return _truncate(blocks)


def _from_the_call(item: dict[str, Any], now: datetime | None) -> str:
    """A date the agent resolved is a small inference, so it says where it came from in the same
    breath rather than leaving a reader to trust it. One clause, never a footnote."""
    due, spoken = str(item.get("due") or ""), str(item.get("due_hint") or "")
    if not due:
        return ""
    when = when_phrase(due, now) if now else human_date(due)
    return f", due {when}" + (f' (from "{spoken}" on the call)' if spoken else "")


def what_happened(
    created: list[dict[str, Any]],
    updated: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
) -> str:
    """What came out of a call, as a sentence somebody would say.

    "filed 2 tickets · updated 1 · 1 conflict · 1 skipped" is a receipt. A colleague says "two
    new tickets, one update to INV-26, and one thing I need a human on" — same facts, and the
    reader learns what is being asked of them."""
    parts: list[str] = []
    if created:
        parts.append(f"{spelled(len(created))} new {'ticket' if len(created) == 1 else 'tickets'}")
    if updated:
        named = ", ".join(str(u.get("identifier") or "") for u in updated if u.get("identifier"))
        parts.append(f"one update to {named}" if len(updated) == 1 and named
                     else f"{spelled(len(updated))} updates")
    if conflicts:
        parts.append(f"{spelled(len(conflicts))} thing{'' if len(conflicts) == 1 else 's'} "
                     "I need a human on")
    if skipped and not parts:
        parts.append(f"{spelled(len(skipped))} thing{'' if len(skipped) == 1 else 's'} left out")
    # A clause, not a sentence: it is read after "Sprint 1 kickoff sync — ", where a capital
    # letter mid-line is the tell that a machine assembled it.
    return sentence_list(parts) or "nothing needed filing"


def _promises(
    tasks: list[dict[str, Any]], owners: dict[str, str] | None = None, now: datetime | None = None
) -> str:
    """One line per scheduled check: when, what, and who I'll go to if the answer is no.

    "if not, I'll nudge the assignee" describes this system to itself. "if not, I'll check in
    with Nodir" is a promise a person can hold me to."""
    lines: list[str] = []
    for task in tasks:
        issue = str((task.get("params") or {}).get("issue") or "")
        when = (when_phrase(str(task.get("due_at") or ""), now) if now
                else human_due(str(task.get("due_at") or "")))
        consequence = consequence_phrase(
            str(task.get("on_unmet") or "none"), owner=(owners or {}).get(issue, "")
        )
        lines.append(
            f"• {f'{when[0].upper()}{when[1:]} — ' if when else ''}{human_check(task)}"
            f"{f' _({consequence})_' if consequence else ''}"
        )
    return "\n".join(lines)


def commitment_blocks(
    tasks: list[dict[str, Any]], notes: str, owners: dict[str, str] | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """The reply to a teammate who asked for something: what I'll watch and when, addressed to
    them. When there is nothing I can do, the sentence saying so instead of a shrug."""
    if not tasks:
        return [_section(notes or "I couldn't turn that into anything I know how to watch.")]
    issues = list(dict.fromkeys(
        str((t.get("params") or {}).get("issue") or "") for t in tasks
    ))
    named = [i for i in issues if i]
    opening = (f"Got it — I'll watch {named[0]} for you:" if len(named) == 1
               else "Got it — here's what I'll keep an eye on:")
    blocks = [_section(f"{opening}\n" + _promises(tasks, owners, now))]
    if notes:
        blocks.append(_context(notes))
    return _truncate(blocks)


def plan_summary_blocks(
    tasks: list[dict[str, Any]], trimmed: list[str], owners: dict[str, str] | None = None,
    now: datetime | None = None, defaulted: bool = False,
) -> list[dict[str, Any]]:
    """The agent saying what it will check, and when — the visible half of the planner.

    Each line is a promise with a date and a named person, because "check_pr_exists on
    2026-09-04" tells a reader nothing they can act on."""
    if not tasks:
        return [_section("_Nothing needs watching right now._")]
    blocks = [_section("Here's how I'll follow through:\n" + _promises(tasks, owners, now))]
    if defaulted:
        # Said once, not per line: the assumption is about all of them, and a clause repeated
        # three times stops being an assumption and becomes noise.
        blocks.append(_context("I picked these dates myself — nobody named one on the call."))
    if trimmed:
        blocks.append(_context(
            f"I left out {count_of(len(trimmed), 'idea')} I couldn't verify: "
            f"{'; '.join(trimmed)}"
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


def sprint_day(sprint: dict[str, Any], today: str) -> str:
    """"day 3 of Sprint 1", or nothing at all. A sprint is a shared sense of where in the week
    everyone is, and it is the one number that makes a standup feel situated."""
    start, name = str(sprint.get("start") or ""), str(sprint.get("name") or "")
    first, now = readable(start), readable(today)
    if not name or first is None or now is None:
        return ""
    day = (now.date() - first.date()).days + 1
    return f"day {day} of {name}" if day >= 1 else f"{name} starts {human_date(start)}"


def _since_yesterday(since: dict[str, Any]) -> str:
    """What changed overnight, named. "1 check came back clear · 2 issues moved" is a scoreboard;
    "Priya got INV-26 moving; INV-25 moved too" tells you who did what."""
    movers: list[str] = []
    for mover in since.get("movers") or []:
        who, issue = first_name(str(mover.get("who") or "")), str(mover.get("issue") or "")
        if not issue:
            continue
        movers.append(f"{who} got {issue} moving" if who else f"{issue} moved")
    if movers:
        return sentence_list(movers[:3]) + "."
    parts: list[str] = []
    if since.get("met"):
        parts.append(f"{count_of(int(since['met']), 'check')} came back clear")
    if since.get("early"):
        parts.append(f"{since['early']} landed early")
    if since.get("nudged"):
        parts.append(f"I chased {count_of(int(since['nudged']), 'thing')}")
    sentence = sentence_list(parts)
    return f"{sentence[0].upper()}{sentence[1:]}." if sentence else ""


def standup_blocks(
    *,
    sprint: dict[str, Any],
    today: str,
    watching: list[dict[str, Any]],
    since: dict[str, Any],
    unmet: list[dict[str, Any]],
    overdue: list[dict[str, Any]],
    lesson: str = "",
    next_due: str = "",
    owners: dict[str, str] | None = None,
    titles: dict[str, str] | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """The message the agent sends before anybody asks it anything.

    Three to five one-line bullets under one greeting, and no headings — a heading over two
    bullets is a form, not a note from a colleague. A quiet day says so in two lines rather than
    padding itself out to look busy."""
    day = sprint_day(sprint, today)
    greeting = f"Morning — {day}." if day else "Morning."
    happened = _since_yesterday(since)
    at_risk = _at_risk_lines(unmet, overdue, owners or {}, now, titles or {})

    if not watching and not happened and not at_risk:
        when = f" before {when_phrase(next_due, now)}" if next_due and now else ""
        return [_section(f"*{greeting}*\nQuiet day ahead — nothing due{when}.")]

    # What is slipping is never trimmed; a day with four things at risk should not spend its
    # lines on what is merely scheduled.
    room = max(0, STANDUP_BULLETS - len(at_risk) - (1 if happened else 0))
    lines: list[str] = []
    for task in watching[:room]:
        issue = str((task.get("params") or {}).get("issue") or "")
        when = when_phrase(str(task.get("due_at") or ""), now) if now else ""
        owner = (owners or {}).get(issue, "")
        lines.append(
            f"• {when.capitalize() + ': ' if when else ''}"
            f"{_about(human_working(task), issue, (titles or {}).get(issue, ''))}"
            f"{f' — {owner}' if owner else ''}"
        )
    if happened:
        lines.append(f"• Since yesterday: {happened}")
    lines.extend(at_risk)

    blocks = [_section(f"*{greeting}*\n" + "\n".join(lines))]
    if lesson:
        blocks.append(_context(f"One thing I learned: {lesson}"))
    return _truncate(blocks, keep_last=0)


def _about(sentence: str, issue: str, title: str) -> str:
    """Put what a ticket is next to its key, once, inside a sentence that already names it.
    "checking whether INV-27 has started" becomes "checking whether INV-27 (the duplicate
    reminders bug) has started" — the reader stops having to remember what INV-27 was."""
    phrase = issue_phrase(issue, title)
    return sentence.replace(issue, phrase, 1) if issue and phrase != issue else sentence


def _at_risk_lines(
    unmet: list[dict[str, Any]], overdue: list[dict[str, Any]], owners: dict[str, str],
    now: datetime | None, titles: dict[str, str] | None = None,
) -> list[str]:
    """What is slipping, each as one line that leads with the ticket and ends in a question
    somebody can answer."""
    lines: list[str] = []
    for check in unmet[:2]:
        issue = str((check.get("params") or {}).get("issue") or "")
        owner = owners.get(issue, "")
        lines.append(
            f"• {issue_phrase(issue, (titles or {}).get(issue, '')) or 'something I watch'} — "
            f"{human_finding(check, check.get('observed') or {})}"
            f"{f'. {owner}, any news?' if owner else '.'}"
        )
    for late in overdue[:2]:
        identifier = str(late.get("issue") or "")
        owner = owners.get(identifier, "")
        due = str(late.get("due") or "")
        when = when_phrase(due, now) if now else human_date(due)
        lines.append(
            f"• {identifier} was due {when} and is still in {late.get('state', 'open')}"
            f"{f' — {owner}, is it still happening?' if owner else '.'}"
        )
    return lines


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

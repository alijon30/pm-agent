"""How the agent refers to a person, a ticket and a consequence.

A colleague talks about four things: a person by their first name, an issue by what it is, a
date in human terms, and what happens next. Everything this system used to say was assembled
instead from its own vocabulary — task kinds, states, counts, `<@id>` mentions, dangling URLs —
which is why it read like a log line rather than like someone writing to you.

These functions are the only place those four things get turned into words, so every surface
says them the same way. They live in core because the channel, the console and the graph all
need them and none of them owns the vocabulary. Kind-specific phrasing ("look for a pull
request on INV-27") stays with the catalog in kinds/phrasing.py; this is about everything else.

One rule worth stating: a mention notifies somebody. Addressing a person who owes the next
action is worth a notification; attributing a ticket to its owner in a list is not. So
`first_name` writes plain text by default and mentions only when asked."""

from __future__ import annotations

import re
from typing import Any

ISSUE_KEY = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")

# Ticket titles are written as instructions — "Fix the duplicate emails" — and a sentence needs
# the thing, not the instruction. Dropping a leading imperative is the whole transformation;
# anything cleverer would start inventing words nobody wrote.
LEADING_VERBS = frozenset({
    "add", "build", "check", "confirm", "create", "draft", "fix", "handle", "investigate",
    "make", "move", "put", "remove", "ship", "set", "update", "write",
})

SPELLED = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")

CONSEQUENCES = {
    "nudge_assignee": "if not, I'll check in with {owner}",
    "nudge_reviewer": "if not, I'll find it a reviewer",
    "escalate_channel": "if not, I'll raise it here",
    "ping_requester": "if not, I'll let you know",
}


def spelled(number: int) -> str:
    """"Two new tickets" reads like a person; "2 new tickets" reads like a report. Only up to
    nine, past which digits are what anyone would write."""
    return SPELLED[number] if 0 <= number < len(SPELLED) else str(number)


def count_in_words(number: int, singular: str) -> str:
    """"one check", "two messages" — the same pluralisation as count_of, said aloud. Small
    numbers read as words everywhere a person is being spoken to."""
    return f"{spelled(number)} {singular}" if number == 1 else f"{spelled(number)} {singular}s"


def first_name(member: dict[str, Any] | str | None, *, mention: bool = False) -> str:
    """What to call someone. `mention=True` when they owe the next action and should be
    notified; plain text when the name is only attribution and a ping would be noise."""
    if member is None:
        return ""
    if isinstance(member, str):
        return member.split()[0] if member.strip() else ""
    name = str(member.get("name") or "").strip()
    given = name.split()[0] if name else ""
    slack_id = str(member.get("slack_id") or "").strip()
    return f"<@{slack_id}>" if mention and slack_id else given


def noun_phrase(title: str) -> str:
    """A ticket title as something that can follow "the". Deterministic and small: drop a
    leading imperative, then lowercase the first word unless it is a name or an acronym."""
    words = str(title or "").strip().split()
    if not words:
        return ""
    if len(words) > 1 and words[0].lower().strip(":") in LEADING_VERBS:
        words = words[1:]
    head = words[0]
    if not (head.isupper() or ISSUE_KEY.match(head)):
        words[0] = head[:1].lower() + head[1:]
    return " ".join(words)


def issue_phrase(identifier: str, title: str = "", url: str = "") -> str:
    """"INV-27 (the duplicate reminder emails bug)", with the link on the identifier.

    The link belongs on the thing it points at, not trailing off the end of the sentence where
    it reads as an afterthought and wraps badly on a phone."""
    key = str(identifier or "").strip()
    if not key:
        return ""
    linked = f"<{url}|{key}>" if url else key
    phrase = noun_phrase(title)
    if not phrase:
        return linked
    article = "" if phrase.lower().startswith(("the ", "a ", "an ")) else "the "
    return f"{linked} ({article}{phrase})"


def consequence_phrase(
    on_unmet: str, owner: str = "", requester: str = ""
) -> str:
    """What I'll do if the answer is no, said as a promise to a named person where there is one.

    "I'll nudge the assignee" tells a reader about this system's internals. "I'll check in with
    Nodir" tells them what will actually happen."""
    template = CONSEQUENCES.get(str(on_unmet or ""))
    if template is None:
        return ""
    return template.format(owner=owner or "whoever owns it", requester=requester or "you")


def sentence_list(parts: list[str]) -> str:
    """"a, b, and c" — the Oxford comma included, because these are read aloud in standups."""
    kept = [p for p in parts if p]
    if len(kept) <= 1:
        return kept[0] if kept else ""
    if len(kept) == 2:
        return f"{kept[0]} and {kept[1]}"
    return ", ".join(kept[:-1]) + f", and {kept[-1]}"

"""When two sentences are the same decision said twice.

A call says the same thing more than once — "move reminders to three days after the due date"
and, a minute later, "move reminders to three days after due" — and a model asked to extract
decisions from both moments faithfully returns two. They are not two decisions, and a ledger
that lists them both makes a reader wonder which one the team actually took.

Two things have to be true before we merge.

**The sentences mostly share words.** Token-set overlap, not string distance: word order and
punctuation move around freely when somebody restates a point, but the words themselves barely
change. Jaccard, at a threshold low enough to catch a restatement that adds a trailing clause
("keep SMS off for now" / "keep SMS off for now, email only" — 0.75).

**And they name the same values.** Overlap alone is not safe at any useful threshold, because
the sentences that share the most words are often the ones that disagree:

    Move payment reminders to three days after the due date.
    Move payment reminders to five days after the due date.     <- 0.82 overlap, opposite meaning

A decision's payload is usually a quantity or a name, and those are exactly the tokens a
similarity score treats as one word out of twelve. So the numbers and proper names on each side
must match exactly, whatever the score says. "three days" and "five days" are never one
decision; neither are the same sentence assigned to Priya and to Nodir.

Deliberately not clever beyond that. No stemming, no stopword list, no trailing-phrase
stripping: each of those silently merges a pair somebody meant to keep apart, and the costs are
not symmetric — a missed merge is a duplicate line, a wrong merge is a lost decision."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Any

WORD = re.compile(r"[a-z0-9]+")
# A capitalised word that does not open a sentence: a name, a product, an acronym.
PROPER = re.compile(r"(?<![.!?]\s)(?<!^)\b([A-Z][A-Za-z]*[A-Za-z0-9-]*)\b")
# Anything carrying a digit is a value: "3", "2%", "INV-27", "v2", "48h".
NUMERIC = re.compile(r"\b\w*\d[\w%-]*\b")

DUPLICATE_AT = 0.72
"""Low enough for a restatement that adds a clause, safe only because of the value guard."""

NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12",
}


def tokens(text: str) -> frozenset[str]:
    """The words of a sentence, lowercased, punctuation gone, order and repetition discarded."""
    return frozenset(WORD.findall(str(text or "").lower()))


def values(text: str) -> frozenset[str]:
    """The numbers and proper names a sentence commits to.

    These are what a decision is actually about — three days, 2%, Priya, INV-27 — and what a
    similarity score is worst at noticing. Spelled numbers are folded onto their digits so
    "three days" and "3 days" stay one decision."""
    raw = str(text or "")
    found = {m.lower() for m in NUMERIC.findall(raw)}
    found |= {m.group(1) for m in PROPER.finditer(raw)}
    found |= {w for w in tokens(raw) if w in NUMBER_WORDS}
    return frozenset(NUMBER_WORDS.get(t, t) for t in found)


def overlap(left: str, right: str) -> float:
    """How much two sentences share, 0 to 1. Two empty sentences are identical; one empty one
    matches nothing."""
    a, b = tokens(left), tokens(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def near_duplicate(left: str, right: str, threshold: float = DUPLICATE_AT) -> bool:
    """Whether these are one decision said twice.

    Disagreeing about a number or a name is disqualifying on its own: a sentence that differs
    only in "three" vs "five" scores higher than most genuine restatements."""
    if values(left) != values(right):
        return False
    return overlap(left, right) >= threshold


def collapse[T](
    rows: Sequence[T], text_of: Callable[[T], str], threshold: float = DUPLICATE_AT
) -> list[T]:
    """The first of each near-duplicate cluster, in the order given.

    First rather than best on purpose: the earliest record is the one other documents already
    point at, so keeping it means a read-side collapse never orphans a reference."""
    kept: list[T] = []
    for row in rows:
        text = text_of(row)
        if not any(near_duplicate(text, text_of(seen), threshold) for seen in kept):
            kept.append(row)
    return kept


def duplicate_of(
    text: str, rows: Sequence[dict[str, Any]], field: str = "statement",
    threshold: float = DUPLICATE_AT,
) -> dict[str, Any] | None:
    """The existing row this sentence restates, if there is one."""
    for row in rows:
        if near_duplicate(text, str(row.get(field) or ""), threshold):
            return row
    return None

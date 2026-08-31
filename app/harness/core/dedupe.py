"""When two sentences are the same decision said twice."""

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
    """The numbers and proper names a sentence commits to. Spelled numbers are folded onto
    their digits so "three days" and "3 days" stay one decision."""
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
    """Whether these are one decision said twice. Disagreeing about a number or a name is
    disqualifying on its own."""
    if values(left) != values(right):
        return False
    return overlap(left, right) >= threshold


def collapse[T](
    rows: Sequence[T], text_of: Callable[[T], str], threshold: float = DUPLICATE_AT
) -> list[T]:
    """The first of each near-duplicate cluster, in the order given. Keeping the earliest
    record means a read-side collapse never orphans a reference."""
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

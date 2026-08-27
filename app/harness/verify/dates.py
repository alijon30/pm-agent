"""When something is due.

A due date is a commitment, so the agent may only set one that a human actually spoke. That
needs two things to agree: a resolved ISO date from reconcile, and a `due_hint` — the words as
said — that appears verbatim in the evidence. Either alone is a guess."""

from __future__ import annotations

import re

from app.harness.verify.evidence import normalize

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def resolve_due(
    due_iso: str | None, due_hint: str | None, evidence_quotes: list[str] | tuple[str, ...]
) -> str | None:
    """The ISO date to set, or None. None is the common case and is not a failure."""
    if not due_iso or not due_hint:
        return None
    if not ISO_DATE.match(due_iso.strip()):
        return None
    hint = normalize(due_hint).strip(" .,;:!?\"'")
    if not hint:
        return None
    haystack = normalize(" ".join(evidence_quotes))
    return due_iso.strip() if hint in haystack else None

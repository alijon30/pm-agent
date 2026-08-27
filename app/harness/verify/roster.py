"""Who may be assigned. The model proposes a name; this decides whether that name is a real
person on this project. An unknown name is never guessed at — the issue ships unassigned with
the spoken name quoted, which is the honest outcome."""

from __future__ import annotations

from typing import Any


def _candidates(member: dict[str, Any]) -> list[str]:
    names = [member.get("name") or "", *(member.get("aliases") or [])]
    return [n.strip().lower() for n in names if n]


def resolve_owner(name: str | None, roster: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Exact, alias, then first-name match, all case-insensitive. None when nothing matches or
    when a first name is ambiguous across two people."""
    if not name:
        return None
    needle = name.strip().lower()
    if not needle:
        return None

    for member in roster:
        if needle in _candidates(member):
            return member

    first_name_hits = [
        m for m in roster if (m.get("name") or "").strip().lower().split(" ")[0] == needle
    ]
    if len(first_name_hits) == 1:
        return first_name_hits[0]
    return None

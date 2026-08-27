"""Structural loop prevention. Every enqueue passes here; a chain cannot exceed max_depth and a
task cannot fan out beyond max_children, so a runaway agent is impossible rather than unlikely.
Plan generations count as depth: a planner that keeps planning follow-ups to its follow-ups
stops at the limit and says so."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_POLICY: dict[str, Any] = {"max_depth": 4, "max_children": 12}


@dataclass(frozen=True)
class LineageVerdict:
    ok: bool
    depth: int
    reason: str = ""


def check_lineage(
    parent: dict[str, Any] | None, existing_children: int, policy: dict[str, Any]
) -> LineageVerdict:
    max_depth = int(policy.get("max_depth", DEFAULT_POLICY["max_depth"]))
    max_children = int(policy.get("max_children", DEFAULT_POLICY["max_children"]))
    if parent is None:
        return LineageVerdict(ok=True, depth=0)
    depth = int(parent.get("depth", 0)) + 1
    if depth > max_depth:
        return LineageVerdict(False, depth, f"depth {depth} exceeds max_depth {max_depth}")
    if existing_children >= max_children:
        return LineageVerdict(
            False,
            depth,
            f"parent {parent.get('id')} already has {existing_children} children "
            f"(max_children {max_children})",
        )
    return LineageVerdict(ok=True, depth=depth)

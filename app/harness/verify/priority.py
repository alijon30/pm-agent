"""How urgent the agent may say something is.

Linear's scale is 0 none, 1 urgent, 2 high, 3 medium, 4 low — lower is more urgent. The project
policy sets a band the agent may assign freely; leaving that band upward requires someone to
have actually said an escalation word, quoted verbatim. Without that the priority is clamped,
never silently accepted: an agent that can mark its own work urgent stops being trustworthy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.harness.verify.evidence import normalize


@dataclass(frozen=True)
class PriorityVerdict:
    priority: int | None
    note: str = ""


def has_escalation(quotes: list[str] | tuple[str, ...], phrases: list[str] | tuple[str, ...]) -> bool:
    haystack = normalize(" ".join(quotes))
    return any(normalize(p) in haystack for p in phrases if p)


def check_priority(
    proposed: int | None,
    evidence_quotes: list[str] | tuple[str, ...],
    policy: dict[str, Any],
) -> PriorityVerdict:
    """Inside the band → as proposed. Above it (more urgent) → allowed only with an escalation
    quote, otherwise clamped to the band's edge with a note explaining why."""
    if proposed is None:
        return PriorityVerdict(None)
    band = policy.get("priority_band") or [2, 4]
    most_urgent, least_urgent = int(band[0]), int(band[1])

    if most_urgent <= proposed <= least_urgent:
        return PriorityVerdict(proposed)

    if proposed < most_urgent:
        phrases = policy.get("escalation_phrases") or []
        if has_escalation(evidence_quotes, phrases):
            return PriorityVerdict(proposed, "escalated: the call used escalation language")
        return PriorityVerdict(
            most_urgent,
            f"priority {proposed} clamped to {most_urgent}: nobody said this was urgent",
        )

    return PriorityVerdict(
        least_urgent, f"priority {proposed} clamped to {least_urgent}: below the project band"
    )

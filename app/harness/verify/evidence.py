"""The evidence gate: an extracted item survives only if at least one of its quotes appears
verbatim in the transcript. This single rule removes most hallucinated action items."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MIN_QUOTE_CHARS = 12

_FOLD = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-"})


def normalize(text: str) -> str:
    return " ".join(text.translate(_FOLD).lower().split())


def quote_in_transcript(quote: str, transcript_norm: str) -> bool:
    q = normalize(quote).strip(" .,;:!?\"'")
    return len(q) >= MIN_QUOTE_CHARS and q in transcript_norm


@dataclass(frozen=True)
class EvidenceVerdict:
    kept: list[dict[str, Any]]
    dropped: list[dict[str, Any]]


def check_evidence(items: list[dict[str, Any]], transcript_text: str) -> EvidenceVerdict:
    """Keep each item with only its verified quotes; drop items with none, tagging the reason
    so the stage can bounce the model once and report the drop honestly."""
    norm = normalize(transcript_text)
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for item in items:
        good = [e for e in item.get("evidence", []) if quote_in_transcript(e.get("quote", ""), norm)]
        if good:
            kept.append({**item, "evidence": good})
        else:
            dropped.append({**item, "gate_reason": "no verbatim quote found in transcript"})
    return EvidenceVerdict(kept=kept, dropped=dropped)

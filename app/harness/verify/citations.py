"""The citation gate: a claim ships only if something the agent can re-open supports it.

A status report is read, believed and forwarded. Nobody checks it, so nothing in it may be
unverifiable: every claim must carry at least one reference, and every reference is re-fetched
from the system that owns it (see verify/ids.py). Claims that fail are removed rather than
softened — an agent that hedges an invented ticket number has still invented it — and the
removal is reported, so a thin report is visibly thin instead of quietly wrong.

A source outage is not a fake citation. SourceUnavailable propagates out of this gate so the
stage can fail and retry, rather than deleting a real claim because Linear was down."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.harness.verify.ids import IdGate


@dataclass(frozen=True)
class CitationVerdict:
    ok: bool
    report: dict[str, Any]
    removed: list[dict[str, str]] = field(default_factory=list)


async def check_citations(report: dict[str, Any], ids: IdGate) -> CitationVerdict:
    """Return the report with every uncitable claim removed, plus what was removed and why.

    `ok` is False when anything was removed, which is what the stage bounces on. Sections left
    with no claims are dropped: an empty heading reads as "nothing happened here", which is a
    different and false statement. Raises SourceUnavailable if a source could not be reached."""
    sections: list[dict[str, Any]] = []
    removed: list[dict[str, str]] = []

    for section in report.get("sections") or []:
        name = str(section.get("name") or "")
        kept: list[dict[str, Any]] = []
        for claim in section.get("claims") or []:
            text = str(claim.get("text") or "")
            refs = [str(r).strip() for r in claim.get("refs") or [] if str(r).strip()]
            if not refs:
                removed.append({"section": name, "text": text, "reason": "no reference"})
                continue
            missing = await ids.missing_refs(refs)
            if missing:
                removed.append({
                    "section": name, "text": text,
                    "reason": f"unknown reference(s): {', '.join(missing)}",
                })
                continue
            kept.append({**claim, "refs": refs})
        if kept:
            sections.append({**section, "claims": kept})

    return CitationVerdict(
        ok=not removed, report={**report, "sections": sections}, removed=removed
    )

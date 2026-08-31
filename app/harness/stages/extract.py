"""extract: transcript → decisions, action items, open questions — each with verbatim evidence,
or not at all. One bounce on a gate failure, then an honest drop."""

from __future__ import annotations

import re
from typing import Any

from app.agents.base.schemas import ExtractResult
from app.harness.connectors.fathom import parse_meeting, render_transcript, transcript_plain
from app.harness.core.errors import PmError
from app.harness.deps import Deps
from app.harness.stages import progress
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc
from app.harness.verify.evidence import check_evidence

SECTIONS = ("decisions", "action_items", "open_questions")
MIN_MISSED = 2
MISSED_SHARE = 0.4
CUE_LINES = 12


def select_with_context(
    segments: list[dict[str, Any]], flags: list[bool], window: int = 2
) -> list[dict[str, Any]]:
    """Flagged segments plus `window` neighbours on each side, original order, no duplicates."""
    keep: set[int] = set()
    for i, flagged in enumerate(flags):
        if flagged:
            keep.update(range(max(0, i - window), min(len(segments), i + window + 1)))
    return [segments[i] for i in sorted(keep)]


# --- the recall backstop -------------------------------------------------------------------------
#
# The evidence gate stops the model inventing; nothing stopped it from being quiet. On a live
# standup it returned two action items where a person finds six, and every miss was an ordinary
# sentence — "can you add the doc link", "I'll run the migration by today". The prompt's own
# "prefer fewer" read as permission to drop.
#
# So the harness reads the transcript for commitment language itself. It cannot write an action
# item — only the model can do that, and only with a verbatim quote — but it can tell when a
# line that sounds like a promise produced nothing, and ask once.

COMMITMENT_CUES = (
    "can you", "could you", "would you", "will you",
    "i'll", "i will", "let me", "let's", "lets",
    "we're going to", "we are going to", "we need to", "i need to", "you need to",
    "please", "make sure", "don't forget",
    "add a comment", "comment on", "send", "post", "run", "tag", "check with",
    "follow up", "take a look", "write up", "put together",
)
"""Language a person uses when work changes hands. Not an extractor — a smoke alarm: it says a
line sounded like a commitment, and the model still has to find the item and quote it."""

# "can you see my screen?" is not a commitment, and neither are the other pleasantries that
# open every call. A cue followed by one of these is meeting furniture.
NOT_COMMITMENTS = (
    # the opening minute of every call
    "see my", "see the screen", "hear me", "hear you", "share your screen", "share my screen",
    "see that", "go ahead", "say that again", "repeat that",
    # the closing one
    "talk to you later", "have a good", "see you then",
    # a line saying something is impossible is describing a constraint, not handing out work
    "can't", "cannot", "couldn't",
)

WORD_EDGE = re.compile(r"[a-z0-9']+")


def _says_commitment(text: str) -> bool:
    """Whether one line hands work to somebody."""
    lowered = " " + " ".join(WORD_EDGE.findall(text.lower())) + " "
    if not any(f" {cue} " in lowered for cue in COMMITMENT_CUES):
        return False
    return not any(f" {phrase} " in lowered for phrase in NOT_COMMITMENTS)


def commitment_cues(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every transcript line that hands work to somebody, with who said it and when.

    Pure, so the recall claim is testable without a model."""
    return [
        {"timestamp": str(seg.get("timestamp") or ""),
         "speaker": str(seg.get("speaker") or "someone"),
         "text": str(seg.get("text") or "")}
        for seg in segments
        if _says_commitment(str(seg.get("text") or ""))
    ]


def covered(cue: dict[str, Any], items: list[dict[str, Any]]) -> bool:
    """Whether some action item was drawn from this line.

    Either the item cites the moment, or it quotes words the line actually contains."""
    stamp = str(cue.get("timestamp") or "")
    line = str(cue.get("text") or "").lower()
    for item in items:
        for evidence in item.get("evidence") or []:
            if stamp and str(evidence.get("timestamp") or "") == stamp:
                return True
            quote = str(evidence.get("quote") or "").strip().lower()
            if quote and quote in line:
                return True
    return False


def uncovered(cues: list[dict[str, Any]], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [cue for cue in cues if not covered(cue, items)]


def thin_recall(cues: list[dict[str, Any]], items: list[dict[str, Any]]) -> bool:
    """Whether the miss is big enough to be worth one more turn.

    Two lines and forty per cent: below that a bounce costs a call and a delay to argue about
    a single sentence somebody may well have meant rhetorically."""
    if not cues:
        return False
    missed = len(uncovered(cues, items))
    return missed >= MIN_MISSED and missed / len(cues) >= MISSED_SHARE


def recall_feedback(missed: list[dict[str, Any]]) -> str:
    lines = "\n".join(
        f"[{cue['timestamp']}] {cue['speaker']}: {cue['text']}" for cue in missed[:CUE_LINES]
    )
    return (
        "These lines contain commitments you did not turn into action items. For each one, "
        "either add an item with this line as its evidence, or say in `dropped` why it is not "
        f"an action item:\n{lines}"
    )


def _gate(
    parsed: dict[str, Any], plain: str
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    kept: dict[str, list[dict[str, Any]]] = {}
    dropped: list[dict[str, Any]] = []
    for section in SECTIONS:
        verdict = check_evidence(parsed.get(section, []), plain)
        kept[section] = verdict.kept
        dropped.extend({**d, "section": section} for d in verdict.dropped)
    return kept, dropped


def _label(item: dict[str, Any]) -> str:
    return str(item.get("title") or item.get("statement") or item.get("question") or "?")


async def run(task: Doc, deps: Deps) -> StageResult:
    event = await deps.events.get(task["payload"]["event_id"])
    if event is None:
        raise PmError(f"event {task['payload']['event_id']} not found")
    project = await deps.projects.get(task["project_id"])
    if project is None:
        raise PmError(f"project {task['project_id']} not found")

    meeting = parse_meeting(event["payload"])
    flags = await deps.triage.decision_bearing(meeting["transcript"])
    selected = select_with_context(meeting["transcript"], flags)
    payload: dict[str, Any] = {
        "transcript": render_transcript(selected),
        "roster_names": [m["name"] for m in project.get("roster", [])],
        "feedback": None,
    }
    plain = transcript_plain(meeting)

    parsed = ExtractResult.model_validate(await deps.extractor.run(payload)).model_dump()
    kept, dropped = _gate(parsed, plain)

    cues = commitment_cues(meeting["transcript"])
    covered_first = len(cues) - len(uncovered(cues, kept["action_items"]))
    covered_final = covered_first

    bounced = False
    # One bounce, whichever gate wants it. A drop and a silence are both worth exactly one more
    # turn, and asking twice is how a pipeline starts arguing with itself.
    reasons: list[str] = []
    if dropped:
        names = "; ".join(_label(d) for d in dropped)
        reasons.append(
            "These items were dropped because none of their quotes appear verbatim in the "
            f"transcript: {names}. Re-extract; every quote must be copied exactly from the "
            "transcript text. Omit any item you cannot support with an exact quote."
        )
    if thin_recall(cues, kept["action_items"]):
        reasons.append(recall_feedback(uncovered(cues, kept["action_items"])))

    if reasons:
        bounced = True
        rescued = ExtractResult.model_validate(
            await deps.extractor.run({**payload, "feedback": " ".join(reasons)})
        ).model_dump()
        second, second_dropped = _gate(rescued, plain)
        # A second pass that found less is a worse answer, not a newer one. The evidence gate
        # still governs what survives either way, so the retry can only ever add cited items.
        if len(second["action_items"]) >= len(kept["action_items"]):
            parsed, kept, dropped = rescued, second, second_dropped
        covered_final = len(cues) - len(uncovered(cues, kept["action_items"]))

    decision_ids = await deps.decisions.add_many(
        task["project_id"], event["id"], kept["decisions"], meeting
    )
    result: dict[str, Any] = {
        "meeting": {"id": meeting["meeting_id"], "title": meeting["title"], "url": meeting["url"]},
        "action_items": kept["action_items"],
        "open_questions": kept["open_questions"],
        "decision_ids": decision_ids,
        "dropped": dropped,
        "bounced": bounced,
        # What the model was actually shown. Triage decides what the agent could possibly have
        # heard, so the number is worth keeping: without it the console can only say the call
        # was read, not how much of it.
        "triage": {"kept": len(selected), "total": len(meeting["transcript"])},
        # How many lines that sounded like commitments became action items. The console shows
        # it because a recall number nobody looks at is a recall number nobody fixes.
        "recall": {"cues": len(cues), "covered_first": covered_first,
                   "covered_final": covered_final, "bounced": bounced},
    }
    children: list[dict[str, Any]] = []
    if kept["action_items"] or kept["decisions"]:
        children.append({
            "kind": "reconcile",
            "payload": {"event_id": event["id"], "extract_task_id": task["id"]},
            "reason": (
                f"reconcile {len(kept['action_items'])} action item(s) and "
                f"{len(kept['decisions'])} decision(s) from '{meeting['title']}' against "
                "Linear, Notion and code"
            ),
        })
        await progress.show(
            task, deps, title=meeting["title"], doing=1,
            notes={0: progress.read_note(len(kept["action_items"]), len(decision_ids))},
        )
    return StageResult(result=result, children=children)

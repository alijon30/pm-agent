"""reconcile: take what a call produced and check it against everything that already exists.

The model proposes; this stage verifies. Every identifier the model names is re-fetched before
the proposal may reach Act, because an issue key that looks right and is wrong is the fastest
way to lose a team's trust. A source that is down produces `unverified`, never a guess: the
items that needed it are held back and retried once, and Act simply does not see them."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Protocol

from app.agents.base.schemas import ReconcileResult
from app.harness.connectors.fathom import parse_meeting
from app.harness.core.clock import iso
from app.harness.core.errors import PmError, SourceUnavailable
from app.harness.core.voice import LEADING_VERBS
from app.harness.core.words import count_of
from app.harness.deps import Deps
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc
from app.harness.verify.ids import IdGate

RETRY_MINUTES = 30


def item_refs(item: dict[str, Any]) -> list[str]:
    """Every reference an item asserts: its citations, its conflict sources, its fact sources,
    and — as a typed ref — the issue it claims to update or duplicate."""
    refs = list(item.get("citations") or [])
    for conflict in item.get("conflicts") or []:
        refs.extend(side.get("source", "") for side in conflict.get("sides") or [])
    refs.extend(fact.get("source", "") for fact in item.get("facts") or [])
    target = item.get("target_issue")
    if target and item.get("disposition") in ("update", "duplicate_of"):
        refs.append(f"linear:{target}")
    return [r for r in refs if r]


def _situation(action_items: list[dict[str, Any]]) -> str:
    """The words this call is about, for asking the brain what it knows."""
    return " ".join(
        f"{i.get('title', '')} {i.get('description', '')}" for i in action_items
    )


async def _remember_facts(
    items: list[dict[str, Any]], deps: Deps, project_id: str
) -> list[dict[str, Any]]:
    """File each verified fact in the brain. Returns what was learned, for the journal."""
    if deps.wiki is None:
        return []
    learned: list[dict[str, Any]] = []
    for item in items:
        for fact in item.get("facts") or []:
            text, source = str(fact.get("text") or ""), str(fact.get("source") or "")
            if not text or not source:
                continue
            where = await deps.wiki.add_entry(project_id, "fact", {
                "text": text, "source": source, "said_by": str(item.get("owner") or ""),
            })
            if where is not None:
                learned.append({"text": text, "ref": f"wiki:{where[0]}#{where[1]}"})
    return learned


def call_citation(
    item: dict[str, Any], meeting_id: str, action_items: list[dict[str, Any]]
) -> str:
    """The moment in the call this item came from, as a typed reference the gate can check.

    Every item exists because somebody said something, so the call is always citable — and the
    harness knows which line it was without asking anyone: the item carries the index of the
    action item it reconciles, and that action item carries the evidence the extractor took it
    from. Nothing here is inferred. An item whose evidence has no timestamp gets no reference,
    because a fabricated one would be worse than none."""
    if not meeting_id:
        return ""
    index = item.get("index")
    if not isinstance(index, int) or not 0 <= index < len(action_items):
        return ""
    for evidence in action_items[index].get("evidence") or []:
        timestamp = str(evidence.get("timestamp") or "").strip()
        if timestamp:
            return f"fathom:{meeting_id}@{timestamp}"
    return ""


def with_call_citation(
    items: list[dict[str, Any]], meeting_id: str, action_items: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Give every item the call moment it came from, and say which ones could not have one.

    A backstop, not a replacement: the prompt still asks for citations, and everything the model
    produced is kept. This exists because a smaller model reliably skips the step, and a citation
    the harness can compute is not worth begging for. The reference it adds is checked by the
    same identifier gate as the model's own — a citation written here is still a citation."""
    cited: list[dict[str, Any]] = []
    uncitable: list[str] = []
    for item in items:
        citations = [str(c) for c in item.get("citations") or [] if str(c).strip()]
        reference = call_citation(item, meeting_id, action_items)
        if reference and reference not in citations:
            citations = [*citations, reference]
        if not any(c.startswith("fathom:") for c in citations):
            uncitable.append(str(item.get("title") or "?"))
        cited.append({**item, "citations": citations})
    return cited, uncitable


def quotes_for(index: int, action_items: list[dict[str, Any]]) -> list[str]:
    """The verbatim quotes behind one action item — what the priority and date gates weigh."""
    if 0 <= index < len(action_items):
        return [e.get("quote", "") for e in action_items[index].get("evidence") or []]
    return []


def moments_for(index: int, action_items: list[dict[str, Any]], meeting_id: str) -> list[str]:
    """The moment in the call behind each quote in `quotes_for`, position for position.

    The same evidence list in the same order, one entry each — an empty string where a segment
    carried no timestamp, so the pairing stays aligned instead of silently shifting by one. The
    reference is built exactly as `call_citation` builds it, from the meeting id the identifier
    gate re-checks; a quote whose moment nobody recorded gets nothing rather than a guess."""
    if not 0 <= index < len(action_items):
        return []
    return [
        f"fathom:{meeting_id}@{timestamp}" if meeting_id and timestamp else ""
        for timestamp in (
            str(e.get("timestamp") or "").strip()
            for e in action_items[index].get("evidence") or []
        )
    ]


def with_investigation_refs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cite every file the investigation names.

    A path in a ticket is a claim about the code like any other, so it faces the same gate as an
    issue key: a file the model did not actually open bounces the item once with that reference
    named, and a second miss holds it back. Moving the refs into `citations` is what does that —
    `item_refs` reads them there — and it is also what puts them in the line a human audits the
    ticket from."""
    cited: list[dict[str, Any]] = []
    for item in items:
        citations = [str(c) for c in item.get("citations") or []]
        for ref in ((item.get("investigation") or {}).get("files") or []):
            reference = str(ref).strip()
            if reference and reference not in citations:
                citations.append(reference)
        cited.append({**item, "citations": citations})
    return cited


# --- an "update" that names no issue ------------------------------------------------------------

class IssueSearch(Protocol):
    async def search_issues(
        self, team_id: str, text: str, *, limit: int = 8
    ) -> list[dict[str, Any]]: ...


NEEDS_TARGET = ("update", "duplicate_of")
CLOSED_STATES = frozenset({"completed", "canceled", "cancelled"})
MIN_SEARCH_WORDS = 2
SEARCH_STOPWORDS = frozenset({
    "a", "an", "and", "the", "to", "for", "of", "on", "in", "at", "by", "with", "from", "into",
    "behind", "that", "this", "it", "its", "as", "be", "is", "are", "was", "were", "so", "or",
    "but", "we", "our", "should", "will", "need", "needs", "after", "before", "when", "then",
    "also", "up", "out", "off", "all", "any", "new",
})
DOWNGRADE_PREFIX = (
    "Possibly duplicates existing work — the call referred to something already tracked but I "
    "couldn't tell which."
)


def search_words(title: str) -> list[str]:
    """The words worth searching a tracker on, in the order the title said them.

    The leading verb goes ("Put the invoice CSV export…" is not about putting) and so do the
    joining words, because the search is a word-AND: every extra word can only lose the match
    we are looking for."""
    words = [w.strip(".,;:!?()[]'\"").lower() for w in str(title or "").split()]
    words = [w for w in words if w and w not in SEARCH_STOPWORDS]
    if len(words) > 1 and words[0] in LEADING_VERBS:
        words = words[1:]
    return words


def is_open(issue: dict[str, Any]) -> bool:
    """Whether an issue is still live work.

    An issue whose state type we do not know counts as open. That is the cautious direction:
    a candidate kept can only make the "exactly one match" test harder to pass, while a
    candidate wrongly dropped could leave one match standing and point an update at the wrong
    ticket."""
    return str(issue.get("state_type") or "").strip().lower() not in CLOSED_STATES


async def resolve_target(
    item: dict[str, Any], team_id: str, linear: IssueSearch
) -> tuple[str, str]:
    """The issue an update must have meant, when the tracker names exactly one.

    The title is searched whole first, then with its trailing words dropped one at a time —
    titles put their subject early and their qualifiers late, so "invoice CSV export behind
    feature flag" narrows to "invoice CSV export", which is the phrase the ticket was filed
    under. The first search that matches anything decides: one open issue is an answer, several
    is an ambiguity we must not guess at, and narrowing further would only add more.

    Returns (identifier, note); both empty when nothing can be resolved safely, including when
    the tracker is down — an outage is not evidence that no issue exists."""
    words = search_words(str(item.get("title") or ""))
    for keep in range(len(words), MIN_SEARCH_WORDS - 1, -1):
        try:
            hits = [i for i in await linear.search_issues(team_id, " ".join(words[:keep]))
                    if is_open(i)]
        except SourceUnavailable:
            return "", ""
        if len(hits) == 1:
            found = str(hits[0].get("identifier") or "")
            return found, f"matched to {found} by title"
        if hits:
            return "", ""
    return "", ""


async def resolve_missing_targets(
    items: list[dict[str, Any]], team_id: str, linear: IssueSearch | None
) -> tuple[list[dict[str, Any]], list[str]]:
    """Give every update that named no issue a target where the tracker makes it unambiguous.

    Returns the items and the titles still without one. A model that says "update" and then
    names nothing has described work with nowhere to go, and the harness can often find the
    where itself rather than letting the commitment fall on the floor."""
    resolved: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for item in items:
        if item.get("disposition") not in NEEDS_TARGET or str(
            item.get("target_issue") or ""
        ).strip():
            resolved.append(item)
            continue
        found, note = await resolve_target(item, team_id, linear) if linear else ("", "")
        if found:
            resolved.append({**item, "target_issue": found, "match_note": note})
        else:
            unresolved.append(str(item.get("title") or "?"))
            resolved.append(item)
    return resolved, unresolved


def _target_feedback(titles: list[str]) -> str:
    return (
        "These items say \"update\" or \"duplicate_of\" but name no issue to update: "
        f"{'; '.join(titles)}. Give each one a target_issue you have opened with the tools, or "
        "make it \"new\"."
    )


def downgrade_unresolved(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Turn an update with nowhere to go into a clearly-labelled new issue.

    Somebody committed to this on a call. Filing it as a possible duplicate leaves the team a
    ticket to merge in one click; dropping it leaves them nothing, and nobody finds out until
    the work does not happen. The label is the honesty: the description says up front that this
    may already exist."""
    kept: list[dict[str, Any]] = []
    downgraded: list[str] = []
    for item in items:
        if item.get("disposition") in NEEDS_TARGET and not str(
            item.get("target_issue") or ""
        ).strip():
            body = str(item.get("description") or "").strip()
            kept.append({**item, "disposition": "new", "target_issue": None,
                         "description": f"{DOWNGRADE_PREFIX} {body}".strip()})
            downgraded.append(str(item.get("title") or "?"))
        else:
            kept.append(item)
    return kept, downgraded


async def _verify(
    items: list[dict[str, Any]], ids: IdGate
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    """Split items into verified and unverified. The third value says whether a source outage
    was the reason, which is what makes a retry worth scheduling."""
    verified: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    outage = False
    for item in items:
        try:
            missing = await ids.missing_refs(item_refs(item))
        except SourceUnavailable as exc:
            outage = True
            unverified.append({**item, "gate_reason": f"{exc.source} unavailable"})
            continue
        if missing:
            unverified.append({
                **item, "gate_reason": f"unknown identifier(s): {', '.join(missing)}"
            })
        else:
            verified.append(item)
    return verified, unverified, outage


def _feedback(unverified: list[dict[str, Any]], homeless: list[str] | None = None) -> str:
    """The one thing the model is told before its single retry: exactly what was wrong."""
    parts: list[str] = []
    if unverified:
        lines = "; ".join(
            f"{u.get('title', '?')} — {u.get('gate_reason', '')}" for u in unverified
        )
        parts.append(
            "These items were rejected because they name things that could not be confirmed: "
            f"{lines}. Re-check each identifier with the tools before citing it. Never write a "
            "reference you did not open; omit the citation and say what you could not verify."
        )
    if homeless:
        parts.append(_target_feedback(homeless))
    return " ".join(parts)


async def run(task: Doc, deps: Deps) -> StageResult:
    event = await deps.events.get(task["payload"]["event_id"])
    if event is None:
        raise PmError(f"event {task['payload']['event_id']} not found")
    project = await deps.projects.get(task["project_id"])
    if project is None:
        raise PmError(f"project {task['project_id']} not found")
    if deps.reconciler is None or deps.ids is None:
        raise PmError("reconcile needs a reconciler and an id gate")
    ids = deps.ids

    extract_task = await deps.db.get("tasks", task["payload"]["extract_task_id"])
    if extract_task is None or not extract_task.get("result"):
        raise PmError("the extract result this reconcile depends on is missing")
    extracted: dict[str, Any] = extract_task["result"]
    action_items: list[dict[str, Any]] = extracted.get("action_items") or []

    meeting = parse_meeting(event["payload"])
    decisions = [
        d for d in [await deps.db.get("decisions", i) for i in extracted.get("decision_ids") or []]
        if d is not None
    ]
    payload: dict[str, Any] = {
        "action_items": action_items,
        "decisions": [
            {"statement": d["statement"], "quote": d.get("quote", ""), "source": d.get("source")}
            for d in decisions
        ],
        "meeting": {"id": meeting["meeting_id"], "title": meeting["title"], "url": meeting["url"]},
        "roster": [{"name": m["name"], "role": m.get("role")} for m in project.get("roster", [])],
        "brain": (await deps.wiki.for_prompt(task["project_id"], _situation(action_items))
                  if deps.wiki is not None else []),
        "today": iso(deps.clock.now())[:10],
        "feedback": None,
    }

    parsed = ReconcileResult.model_validate(await deps.reconciler.run(payload)).model_dump()
    # The self-citation is added before verification, not after, so there is exactly one place
    # that decides whether a reference is real. If the event is not in the store the item comes
    # back unverified like any other, bounces once, and is held back honestly.
    team_id = str(project.get("linear_team_id") or "")
    items, uncitable = with_call_citation(
        parsed.get("items") or [], meeting["meeting_id"], action_items
    )
    items = with_investigation_refs(items)
    # An "update" that names no issue has nowhere to go. Resolve what the tracker makes
    # unambiguous before verification, so a recovered target is checked like any other.
    items, homeless = await resolve_missing_targets(items, team_id, deps.linear)
    matched = [i["match_note"] for i in items if i.get("match_note")]
    verified, unverified, outage = await _verify(items, ids)

    bounced = False
    downgraded: list[str] = []
    if unverified or homeless:
        bounced = True
        rescued = ReconcileResult.model_validate(
            await deps.reconciler.run(
                {**payload, "feedback": _feedback(unverified, homeless)}
            )
        ).model_dump()
        items, uncitable = with_call_citation(
            rescued.get("items") or [], meeting["meeting_id"], action_items
        )
        items = with_investigation_refs(items)
        items, homeless = await resolve_missing_targets(items, team_id, deps.linear)
        matched = [i["match_note"] for i in items if i.get("match_note")]
        # The bounce was its chance to say which issue it meant. Anything still pointing
        # nowhere is filed as a labelled possible duplicate rather than lost.
        if homeless:
            items, downgraded = downgrade_unresolved(items)
        verified, unverified, outage = await _verify(items, ids)
        parsed = rescued

    for item in verified:
        index = int(item.get("index", -1))
        item["quotes"] = quotes_for(index, action_items)
        item["moments"] = moments_for(index, action_items, meeting["meeting_id"])

    # Durable facts go into the brain, but only the ones whose source survived the identifier
    # gate: a fact nobody can re-open is exactly the kind of thing that should not become
    # something the agent repeats back to the team next week.
    learned = await _remember_facts(verified, deps, task["project_id"])

    result: dict[str, Any] = {
        "learned": learned,
        "meeting": payload["meeting"],
        "items": verified,
        "unverified": unverified,
        "decision_conflicts": parsed.get("decision_conflicts") or [],
        "decision_ids": extracted.get("decision_ids") or [],
        "bounced": bounced,
        "notes": [
            *([
                f"{count_of(len(uncitable), 'item')} could not be given the moment in the call "
                f"they came from — no timestamp on their evidence: {', '.join(uncitable)}"
            ] if uncitable else []),
            *matched,
            *([
                f"{count_of(len(downgraded), 'item')} said \"update\" but named no issue even "
                f"after being asked, so {'it was' if len(downgraded) == 1 else 'they were'} "
                f"filed as possible duplicates for a human to merge: {', '.join(downgraded)}"
            ] if downgraded else []),
        ],
    }

    children: list[dict[str, Any]] = [{
        "kind": "act",
        "payload": {"event_id": event["id"], "reconcile_task_id": task["id"]},
        "reason": (
            f"file {len(verified)} verified item(s) from '{meeting['title']}'"
            if verified else f"report on '{meeting['title']}': nothing survived verification"
        ),
    }]

    # An outage is the one failure worth retrying: the items were probably fine, the source was
    # not. Retry once, only for the items that were held back.
    if outage and not task["payload"].get("retry"):
        children.append({
            "kind": "reconcile",
            "payload": {**task["payload"], "retry": 1},
            "due_at": iso(deps.clock.now() + timedelta(minutes=RETRY_MINUTES)),
            "reason": f"retry {len(unverified)} item(s) whose sources were unavailable",
        })

    return StageResult(result=result, children=children)

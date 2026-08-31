"""act: the only stage that changes anything outside this system.

No model runs here. Everything the reconciler proposed has already been verified; this stage
decides what policy allows, performs the writes, and records how to undo each one.

The order matters and is deliberate:

    roster → priority → dates → caps → idempotency → write → record

An owner who is not on the project is dropped before a priority is considered, because assigning
urgency to a phantom is worse than either mistake alone. Caps come last of the gates so that an
item held back by a cap is otherwise fully decided and can simply be replayed tomorrow.

Every write is recorded as `pending` before it happens, with a deterministic idempotency key
also stamped into the issue body. A crash between the write and the record is therefore
recoverable: the next attempt finds its own earlier work instead of duplicating it."""

from __future__ import annotations

from typing import Any

from app.harness.connectors.slack_blocks import call_summary_blocks, what_happened
from app.harness.core.errors import PmError, SourceUnavailable
from app.harness.core.keys import idempotency_key
from app.harness.core.redact import redact
from app.harness.core.voice import first_name
from app.harness.deps import Deps
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc
from app.harness.verify.caps import check_caps
from app.harness.verify.dates import resolve_due
from app.harness.verify.priority import check_priority
from app.harness.verify.roster import resolve_owner

SAID_HEADING = "**What was said**"
DESCRIPTION_CAP = 1800

# The ladder the body is cut down by when it runs long, in order. The investigation goes first
# because it is the one section an engineer can rebuild for themselves — the files stay behind
# in **Checked:** either way — and the note is the longest thing in it. Then the quotes after
# the first, then the free prose down to a paragraph each. The acceptance criteria are never on
# this ladder: a ticket that arrives without them is the thing this was all built to stop.
FULL, NO_NOTE, NO_INVESTIGATION, ONE_QUOTE, SHORT_PROSE = range(5)
PROSE_CEILING = 240


def _clip(text: str, room: int) -> str:
    """The last resort: cut at a word boundary and say so with an ellipsis."""
    if room <= 1:
        return ""
    if len(text) <= room:
        return text
    cut = text[: room - 1].rstrip()
    return (cut[: cut.rfind(" ")].rstrip() if " " in cut else cut) + "…"


def _code_path(ref: str) -> str:
    """`code:acme/reminders/scheduler.py:19` as `acme/reminders/scheduler.py:19`.

    The typed reference is what the identifier gate re-checks and it sits in **Checked:** a few
    lines further down; what belongs in a sentence an engineer reads is the line they open."""
    text = str(ref or "").strip()
    return text[5:] if text.lower().startswith("code:") else text


def _said_lines(item: dict[str, Any], meeting: dict[str, Any], keep: int | None) -> list[str]:
    """The words somebody actually said, each with the moment in the call they said them.

    `moments` holds one fathom reference per quote, built by the reconcile stage from the same
    evidence entries `quotes` came from, in the same order — so the pairing is the extractor's
    work, not a guess made here. An item filed before that field existed renders its quotes
    without the moments rather than mispairing them."""
    quotes = [str(q) for q in item.get("quotes") or []]
    moments = [str(m) for m in item.get("moments") or []]
    speakers = [str(s) for s in item.get("speakers") or []]
    said = [
        (quote.strip(),
         moments[i] if i < len(moments) else "",
         speakers[i].strip() if i < len(speakers) else "")
        for i, quote in enumerate(quotes)
        if quote.strip()
    ]
    if not said:
        return []
    if keep is not None:
        said = said[:keep]
    where = " · ".join(part for part in [
        str(meeting.get("title") or "").strip(),
        f"[recording]({meeting['url']})" if meeting.get("url") else "",
    ] if part)
    lines = [f"{SAID_HEADING} — {where}" if where else SAID_HEADING]
    lines += [_said_line(quote, ref, who) for quote, ref, who in said]
    return [*lines, ""]


def _said_line(quote: str, ref: str, who: str) -> str:
    """`> Two of them said they'd leave — Tom, 01:58`. The machine reference behind the moment
    stays in **Checked:**; a sentence a human reads gets a name and a clock, not a URI."""
    stamp = ref.rsplit("@", 1)[-1] if "@" in ref else ""
    stamp = stamp[3:] if len(stamp) == 8 and stamp.startswith("00:") else stamp
    name = first_name(who) if who else ""
    trail = ", ".join(part for part in (name, stamp) if part)
    return f"> {quote} — {trail}" if trail else f"> {quote}"


def _acceptance_lines(item: dict[str, Any]) -> list[str]:
    """What "done" means, as boxes a reviewer can tick. Nobody has to guess whether the thing
    they built is the thing that was asked for."""
    criteria = [str(c).strip() for c in item.get("acceptance") or [] if str(c).strip()]
    if not criteria:
        return []
    return ["**Acceptance criteria**", *(f"- [ ] {c}" for c in criteria), ""]


def _investigation_lines(item: dict[str, Any], *, with_note: bool) -> list[str]:
    """Where the behaviour lives, for a bug. Confidence is stated because "possible" and
    "likely" send an engineer to different places, and "unknown" tells them to start fresh."""
    investigation = item.get("investigation") or {}
    note = str(investigation.get("note") or "").strip() if with_note else ""
    files = [path for path in (_code_path(f) for f in investigation.get("files") or []) if path]
    if not note and not files:
        return []
    confidence = str(investigation.get("confidence") or "").strip()
    lines = [f"**Investigation** ({confidence})" if confidence else "**Investigation**"]
    if note:
        lines.append(note)
    if files:
        lines.append("· " + " · ".join(files))
    return [*lines, ""]


def _head_lines(item: dict[str, Any], meeting: dict[str, Any], trim: int) -> list[str]:
    """The part of the body that describes the work: why, what was said, what done means, and
    what the code says. Assembled here and nowhere else, so no model decides its shape."""
    room = PROSE_CEILING if trim >= SHORT_PROSE else DESCRIPTION_CAP
    lines: list[str] = []
    lead = _clip(str(item.get("description") or "").strip(), room)
    if lead:
        lines += [lead, ""]
    why = _clip(str(item.get("context") or "").strip(), room)
    if why:
        lines += ["**Why**", why, ""]
    lines += _said_lines(item, meeting, keep=1 if trim >= ONE_QUOTE else None)
    lines += _acceptance_lines(item)
    if trim < NO_INVESTIGATION:
        lines += _investigation_lines(item, with_note=trim < NO_NOTE)
    return lines


def _tail_lines(item: dict[str, Any], notes: list[str]) -> list[str]:
    """What the gates produced: the disagreements, the references that were re-fetched, every
    place the proposal was not taken at face value. None of it is ever trimmed — a note about
    why the owner is missing is the most useful line in the ticket. (Idempotency lives in the
    actions store, not here: the footer is provenance for a reader, nothing parses it.)"""
    lines: list[str] = []
    for conflict in item.get("conflicts") or []:
        sides = " · ".join(
            f"{s.get('claim', '')} (`{s.get('source', '')}`)" for s in conflict.get("sides") or []
        )
        lines += [f"**Sources disagree** on {conflict.get('about', '')}: {sides}", ""]

    citations = [c for c in item.get("citations") or []]
    if citations:
        lines += ["**Checked:** " + " · ".join(f"`{c}`" for c in citations), ""]

    for note in notes:
        lines.append(f"_{note}_")

    lines += ["", "— filed by pm-agent"]
    return lines


def build_description(
    item: dict[str, Any], meeting: dict[str, Any], key: str, notes: list[str]
) -> str:
    """What a human reads in Linear. Every claim carries where it came from, so the issue can be
    audited in ten seconds without opening this system.

    Nothing here is model prose: the sections are assembled in a fixed order from typed fields,
    empty ones are left out rather than filled with a heading and nothing under it, and the
    whole thing goes through redact() before it leaves. A body over the cap is cut down the
    ladder above and never past the footer."""
    tail = redact("\n".join(_tail_lines(item, notes)))
    head = ""
    for trim in (FULL, NO_NOTE, NO_INVESTIGATION, ONE_QUOTE, SHORT_PROSE):
        head = redact("\n".join(_head_lines(item, meeting, trim))).strip()
        body = f"{head}\n\n{tail}".strip() if head else tail.strip()
        if len(body) <= DESCRIPTION_CAP:
            return body
    head = _clip(head, DESCRIPTION_CAP - len(tail) - 2)
    return f"{head}\n\n{tail}".strip() if head else tail.strip()


def dedupe_conflicts(conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One entry per disagreement, keyed by what it is about and which sources disagree —
    not by `kind`, since the same pair can be labelled differently on two passes."""
    seen: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    for conflict in conflicts:
        sources = tuple(sorted(s.get("source", "") for s in conflict.get("sides") or []))
        key = ((conflict.get("about") or "").strip().lower(), sources)
        seen.setdefault(key, conflict)
    return list(seen.values())


def decide(item: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
    """Apply the roster, priority and date gates. Returns what will be written plus the notes
    explaining every place the proposal was not taken at face value."""
    policy = project.get("policy") or {}
    roster = project.get("roster") or []
    quotes = item.get("quotes") or []
    notes: list[str] = []
    passed: list[str] = []

    owner = resolve_owner(item.get("owner"), roster)
    passed.append("roster")
    if item.get("owner") and owner is None:
        notes.append(f"{item['owner']} isn't on this project, so I left it unassigned")

    verdict = check_priority(item.get("priority"), quotes, policy)
    passed.append("priority")
    if verdict.note:
        notes.append(verdict.note)

    due = resolve_due(item.get("due"), item.get("due_hint"), quotes)
    passed.append("dates")
    if item.get("due") and due is None:
        notes.append(
            f"no due date — '{item.get('due_hint') or item['due']}' wasn't actually said"
        )

    return {
        "owner": owner,
        "priority": verdict.priority,
        "due": due,
        "notes": notes,
        "checks_passed": passed,
    }


async def _perform(
    item: dict[str, Any],
    decided: dict[str, Any],
    *,
    index: int,
    task: Doc,
    project: dict[str, Any],
    meeting: dict[str, Any],
    deps: Deps,
) -> dict[str, Any]:
    """One item, one write. Returns a record of what happened for the summary."""
    assert deps.actions is not None and deps.linear is not None
    kind = "linear.create_issue" if item["disposition"] == "new" else "linear.comment"
    key = idempotency_key(str(task.get("root_event_id") or task["id"]), index, kind)

    earlier = await deps.actions.find_by_key(key)
    if earlier is not None and earlier.get("status") == "done":
        # A replay after a crash. Report what actually exists — not what this attempt would
        # have done — so the summary of a retried run is still true.
        return {
            "outcome": "created" if earlier["kind"] == "linear.create_issue" else "updated",
            "identifier": earlier["target_ids"].get("identifier"),
            "url": earlier["target_ids"].get("url", ""), "action_id": earlier["id"],
            "title": item["title"], "owner": (decided["owner"] or {}).get("name"),
            "note": "already filed by an earlier attempt",
        }

    body = build_description(item, meeting, key, decided["notes"])
    action_id = await deps.actions.begin(
        task_id=task["id"], project_id=task["project_id"], kind=kind, idempotency_key=key,
        inputs={"title": item["title"], "disposition": item["disposition"],
                "target_issue": item.get("target_issue"),
                "owner": (decided["owner"] or {}).get("name"),
                "priority": decided["priority"], "due": decided["due"]},
        citations=list(item.get("citations") or []),
        checks_passed=list(decided["checks_passed"]),
    )

    try:
        if item["disposition"] == "new":
            created = await deps.linear.create_issue(
                team_id=project.get("linear_team_id", ""),
                project_id=project.get("linear_project_id") or None,
                title=item["title"], description=body,
                assignee_id=(decided["owner"] or {}).get("linear_user_id") or None,
                priority=decided["priority"], due_date=decided["due"],
            )
            await deps.actions.finish(
                action_id, target_ids={"identifier": created["identifier"], "url": created["url"]},
                revert={"op": "archive", "issue": created["identifier"]},
            )
            return {"outcome": "created", "identifier": created["identifier"],
                    "url": created["url"], "action_id": action_id, "title": item["title"],
                    "owner": (decided["owner"] or {}).get("name"),
                    # Both already decided above; carried so the summary can say where the date
                    # came from without anybody having to go and look.
                    "due": decided["due"], "due_hint": item.get("due_hint"),
                    "note": "; ".join(decided["notes"])}

        target = item["target_issue"]
        comment_id = await deps.linear.comment(target, body)
        await deps.actions.finish(
            action_id, target_ids={"identifier": target, "comment_id": comment_id},
            revert={"op": "delete_comment", "issue": target, "comment_id": comment_id},
        )
        return {"outcome": "updated", "identifier": target, "url": "", "action_id": action_id,
                "title": item["title"],
                "note": "raised again in this call" if item["disposition"] == "update"
                        else "already covered by this issue"}
    except SourceUnavailable as exc:
        await deps.actions.fail(action_id, redact(str(exc)))
        return {"outcome": "failed", "identifier": None, "url": "", "action_id": action_id,
                "title": item["title"], "note": redact(str(exc))}


async def run(task: Doc, deps: Deps) -> StageResult:
    if deps.actions is None or deps.linear is None:
        raise PmError("act needs an action log and a tracker")
    project = await deps.projects.get(task["project_id"])
    if project is None:
        raise PmError(f"project {task['project_id']} not found")
    source = await deps.db.get("tasks", task["payload"]["reconcile_task_id"])
    if source is None or not source.get("result"):
        raise PmError("the reconcile result this act depends on is missing")

    reconciled: dict[str, Any] = source["result"]
    meeting: dict[str, Any] = reconciled.get("meeting") or {}
    policy = project.get("policy") or {}
    counts = await deps.actions.counts_today(task["project_id"])

    created: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = [
        {"title": u.get("title", "?"), "reason": u.get("gate_reason", "unverified")}
        for u in reconciled.get("unverified") or []
    ]
    performed: list[dict[str, Any]] = []

    for index, item in enumerate(reconciled.get("items") or []):
        allowed = check_caps("write", counts, deps.clock.now(), policy)
        if not allowed.ok:
            skipped.append({"title": item["title"], "reason": allowed.reason})
            continue
        decided = decide(item, project)
        record = await _perform(item, decided, index=index, task=task, project=project,
                                meeting=meeting, deps=deps)
        if record["outcome"] == "failed":
            skipped.append({"title": record["title"], "reason": record["note"]})
            continue
        counts["write"] += 1
        performed.append({"id": record["action_id"], "label": record["identifier"] or "action"})
        (created if record["outcome"] == "created" else updated).append(record)

    # The same disagreement often arrives twice — once against the item, once against the
    # decision that produced it. The team should hear about it once.
    conflicts = dedupe_conflicts(
        [c for item in reconciled.get("items") or [] for c in item.get("conflicts") or []]
        + (reconciled.get("decision_conflicts") or [])
    )

    summary_action = await _post_summary(
        task, project, meeting, created, updated, skipped, conflicts, performed, counts, deps
    )

    result: dict[str, Any] = {
        "created": [{"identifier": c["identifier"], "title": c["title"], "url": c.get("url", ""),
                     "owner": c.get("owner"), "due": None} for c in created],
        "updated": [{"identifier": u["identifier"], "title": u["title"]} for u in updated],
        "skipped": skipped,
        "conflicts": conflicts,
        "action_ids": [p["id"] for p in performed],
        "summary_action_id": summary_action,
    }

    children: list[dict[str, Any]] = []
    if created or updated:
        children.append({
            "kind": "plan",
            "payload": {"act_task_id": task["id"]},
            "context": {
                "created": result["created"], "updated": result["updated"],
                "decision_ids": reconciled.get("decision_ids") or [],
                "meeting": meeting,
                "items": [
                    {"identifier": c["identifier"], "owner": c.get("owner"),
                     "due": next((i.get("due") for i in reconciled.get("items") or []
                                  if i["title"] == c["title"]), None)}
                    for c in created
                ],
            },
            "reason": f"plan the follow-through for {len(created) + len(updated)} issue(s)",
        })
    return StageResult(result=result, children=children)


async def _post_summary(
    task: Doc,
    project: dict[str, Any],
    meeting: dict[str, Any],
    created: list[dict[str, Any]],
    updated: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    performed: list[dict[str, Any]],
    counts: dict[str, int],
    deps: Deps,
) -> str | None:
    """One message per call. Decoration is best-effort: a Slack outage must not undo the work
    that already landed in the tracker.

    Where the webhook left a "reading the call…" message, this edits that message in place
    rather than posting a second one. Slack notifies nobody for a chat.update, which is the
    point: the team already got one notification when the call ended, and watching the message
    fill itself in is calm in a way a second post is not. The plan announcement that follows is
    deliberately a fresh post — that one is new information, arriving after the work is done,
    and it should ping."""
    assert deps.actions is not None
    channel = project.get("slack_channel_id")
    if deps.slack is None or not channel:
        return None

    key = idempotency_key(str(task.get("root_event_id") or task["id"]), 0, "slack.post")
    earlier = await deps.actions.find_by_key(key)
    if earlier is not None and earlier.get("status") == "done":
        return str(earlier["id"])

    status = await _status_message(task, deps)
    target = status["channel"] if status else channel
    action_id = await deps.actions.begin(
        task_id=task["id"], project_id=task["project_id"], kind="slack.post",
        idempotency_key=key,
        inputs={"channel": target, "meeting": meeting.get("title", ""),
                "edited": status is not None},
    )
    blocks = call_summary_blocks(
        meeting, created, updated, skipped, conflicts, performed, post_ref=action_id,
        now=deps.clock.now(),
    )
    # The notification line is the message's own first sentence, said once — Slack shows the
    # preview or the message, never both, so a second header would only ever be a duplicate.
    text = (f"{meeting.get('title', 'call')} — "
            f"{what_happened(created, updated, skipped, conflicts)}.")
    try:
        if status is not None:
            await deps.slack.update(status["channel"], status["ts"], text, blocks)
            ts = status["ts"]
        else:
            ts = await deps.slack.post(channel, text, blocks)
    except SourceUnavailable as exc:
        await deps.actions.fail(action_id, redact(str(exc)))
        return None
    await deps.actions.finish(
        action_id, target_ids={"channel": target, "ts": ts},
        revert={"op": "edit_message", "channel": target, "ts": ts},
    )
    counts["ping"] += 1
    return action_id


async def _status_message(task: Doc, deps: Deps) -> dict[str, str] | None:
    """The "reading the call…" message the webhook posted for this call, if there is one.

    A replayed root carries a `#retryN` suffix (scripts and operators use it to rerun a call
    with fresh idempotency), so the event id is everything before the `#`. A mention-triggered
    flow has no status message at all, and neither does a call whose Slack post failed — both
    simply post fresh."""
    root = str(task.get("root_event_id") or "")
    if not root:
        return None
    event = await deps.events.get(root.split("#")[0])
    status = (event or {}).get("status_message") or {}
    if not status.get("channel") or not status.get("ts"):
        return None
    return {"channel": str(status["channel"]), "ts": str(status["ts"])}

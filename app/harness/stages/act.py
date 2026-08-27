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

from app.harness.connectors.slack_blocks import call_summary_blocks
from app.harness.core.errors import PmError, SourceUnavailable
from app.harness.core.keys import idempotency_key
from app.harness.core.redact import redact
from app.harness.deps import Deps
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc
from app.harness.verify.caps import check_caps
from app.harness.verify.dates import resolve_due
from app.harness.verify.priority import check_priority
from app.harness.verify.roster import resolve_owner

FOOTER = "<!-- pm-agent:{key} -->"


def build_description(
    item: dict[str, Any], meeting: dict[str, Any], key: str, notes: list[str]
) -> str:
    """What a human reads in Linear. Every claim carries where it came from, so the issue can be
    audited in ten seconds without opening this system."""
    lines: list[str] = []
    if item.get("description"):
        lines += [item["description"], ""]

    quotes = item.get("quotes") or []
    if quotes:
        link = f" · [recording]({meeting['url']})" if meeting.get("url") else ""
        lines += [f"**From the call:** {meeting.get('title', '')}{link}", f"> {quotes[0]}", ""]

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

    lines += ["", f"— filed by pm-agent {FOOTER.format(key=key)}"]
    return "\n".join(lines).strip()


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
        notes.append(f"owner named in the call: '{item['owner']}' — not on this project's roster")

    verdict = check_priority(item.get("priority"), quotes, policy)
    passed.append("priority")
    if verdict.note:
        notes.append(verdict.note)

    due = resolve_due(item.get("due"), item.get("due_hint"), quotes)
    passed.append("dates")
    if item.get("due") and due is None:
        notes.append(f"no due date set: '{item.get('due_hint') or item['due']}' was not spoken")

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

    conflicts = [c for item in reconciled.get("items") or [] for c in item.get("conflicts") or []]
    conflicts += reconciled.get("decision_conflicts") or []

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
    that already landed in the tracker."""
    assert deps.actions is not None
    channel = project.get("slack_channel_id")
    if deps.slack is None or not channel:
        return None

    key = idempotency_key(str(task.get("root_event_id") or task["id"]), 0, "slack.post")
    earlier = await deps.actions.find_by_key(key)
    if earlier is not None and earlier.get("status") == "done":
        return str(earlier["id"])

    action_id = await deps.actions.begin(
        task_id=task["id"], project_id=task["project_id"], kind="slack.post",
        idempotency_key=key, inputs={"channel": channel, "meeting": meeting.get("title", "")},
    )
    blocks = call_summary_blocks(
        meeting, created, updated, skipped, conflicts, performed, post_ref=action_id
    )
    text = (f"{meeting.get('title', 'call')}: {len(created)} filed, {len(updated)} updated, "
            f"{len(skipped)} skipped, {len(conflicts)} conflict(s)")
    try:
        ts = await deps.slack.post(channel, text, blocks)
    except SourceUnavailable as exc:
        await deps.actions.fail(action_id, redact(str(exc)))
        return None
    await deps.actions.finish(
        action_id, target_ids={"channel": channel, "ts": ts},
        revert={"op": "edit_message", "channel": channel, "ts": ts},
    )
    counts["ping"] += 1
    return action_id

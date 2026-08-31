"""intake: somebody asked the agent for something, and the agent answers.

Everything else in this system is triggered by an event — a call ended, an issue changed, the
clock struck nine. This is the one stage a person starts, which changes what is owed. A request
gets exactly one of two replies, in the thread it was made in:

- a commitment: dated checks the requester can hold the agent to, each carrying who asked so the
  answer comes back to them rather than to whoever happens to own the ticket; or
- a refusal in one sentence, naming what the agent cannot do.

Silence is not an option, and neither is an agreeable yes the agent cannot keep — the plan gate
runs on the steward's proposal exactly as it runs on the planner's, so nothing is promised that
could not be scheduled."""

from __future__ import annotations

from typing import Any

from app.agents.base.schemas import Plan
from app.harness.connectors.slack import react_quietly
from app.harness.connectors.slack_blocks import commitment_blocks
from app.harness.core.clock import iso
from app.harness.core.errors import PmError, SourceUnavailable
from app.harness.core.keys import idempotency_key
from app.harness.core.redact import redact
from app.harness.core.voice import first_name
from app.harness.deps import Deps
from app.harness.kinds.registry import KINDS, catalog_for_prompt
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc
from app.harness.store.tasks import OPEN_STATUSES
from app.harness.verify.plan import check_plan, nothing_exists
from app.harness.verify.roster import resolve_owner

CHECK_KINDS = tuple(kind for kind in KINDS if kind.startswith("check_"))


def commissioned_by(task: Doc) -> dict[str, str]:
    """Who asked, and where they asked it. Carried into every task the request produces so the
    answer goes back to the person waiting for it."""
    payload = task.get("payload") or {}
    return {
        "requester_slack_id": str(payload.get("requester") or ""),
        "request_channel": str(payload.get("channel") or ""),
        "request_ts": str(payload.get("thread_ts") or ""),
    }


def commission(tasks: list[dict[str, Any]], task: Doc) -> list[dict[str, Any]]:
    """Stamp the requester onto accepted work, and default a check nobody chose an action for to
    answering the person who asked. A check somebody commissioned that reports to nobody is the
    one outcome worse than refusing outright."""
    who = commissioned_by(task)
    return [
        {
            **accepted,
            "payload": {},
            "on_unmet": "ping_requester"
            if accepted["on_unmet"] == "none" and accepted["kind"] in CHECK_KINDS
            else accepted["on_unmet"],
            "context": {**accepted.get("context", {}), **who},
        }
        for accepted in tasks
    ]


def interpretation(request: str, children: list[dict[str, Any]]) -> str:
    """When the ask named no ticket and the agent picked one, say which — in the same breath.

    Somebody who wrote "keep an eye on the export" needs to know I read that as INV-26, because
    if I read it wrong the whole commitment is about the wrong thing and the only moment they
    can cheaply tell me is now."""
    named = [
        issue for issue in dict.fromkeys(
            str((child.get("params") or {}).get("issue") or "") for child in children
        ) if issue and issue not in request
    ]
    if not named:
        return ""
    asked = _short(request, 48)
    return f"Taking \"{asked}\" to mean {', '.join(named)}."


def _short(text: str, limit: int) -> str:
    words = " ".join(str(text).split())
    return words if len(words) <= limit else words[: limit - 1] + "…"


async def _requester_name(task: Doc, deps: Deps) -> str:
    """Their display name, or "you". Best-effort: a Slack outage costs the prompt a name, and
    the steward writes to "you" instead."""
    slack_id = commissioned_by(task)["requester_slack_id"]
    if deps.slack is None or not slack_id:
        return "you"
    try:
        person = await deps.slack.user_info(slack_id)
    except SourceUnavailable:
        return "you"
    return str((person or {}).get("name") or "you")


async def _lessons(deps: Deps, project_id: str) -> list[str]:
    """What the agent learned about its own planning. Advisory, and never a reason to promise
    something the gate would refuse."""
    if deps.lessons is None:
        return []
    return [str(row.get("text") or "") for row in await deps.lessons.for_project(project_id)]


async def _cancel(task: Doc, identifier: str, deps: Deps) -> StageResult:
    """Stop the checks this person asked for on this issue — and only theirs. Somebody else's
    follow-through, and the agent's own, are not theirs to cancel."""
    who = commissioned_by(task)["requester_slack_id"]
    mine = [
        row for row in await deps.db.query(
            "tasks", [("project_id", "==", task["project_id"]),
                      ("status", "in", list(OPEN_STATUSES))], limit=200,
        )
        if (row.get("params") or {}).get("issue") == identifier
        and (row.get("context") or {}).get("requester_slack_id") == who
    ]
    cancelled: list[str] = []
    for row in mine:
        cancelled.extend(await deps.queue.cancel(row["id"], "the requester asked me to stop"))

    said = (
        f"Done — I've stopped watching {identifier}."
        if cancelled
        else f"I'm not watching anything on {identifier} for you — nothing to stop."
    )
    posted = await _reply(task, said, [], deps)
    return StageResult(result={
        "cancelled": cancelled, "identifier": identifier, "replied": posted,
    })


def _noted(remembered: dict[str, Any] | None) -> str:
    """What the agent says back when it has been told something.

    Said in the words a colleague would use, and said once — a rule repeated back as a
    confirmation dialogue is how a helpful bot becomes an annoying one."""
    if not remembered:
        return ""
    kind, text = str(remembered.get("kind")), str(remembered.get("text") or "")
    person = str(remembered.get("person") or "")
    if kind == "ownership" and person:
        # The subject is a list of words from one phrase ("frontend bugs"), not a list of
        # items — joined with spaces so the reply reads like the sentence the person typed.
        subject = " ".join(str(w) for w in remembered.get("subject") or []) or "that work"
        return f"Noted — {subject} go to {first_name({'name': person})} from now on."
    # People type rules without a full stop; the agent still writes sentences.
    said = text if text.endswith((".", "!", "?")) else f"{text}."
    if kind == "fact":
        return f"Noted, I'll remember that: {said}"
    return f"Noted — from now on: {said}"


async def _remember(
    memory: dict[str, Any] | None, task: Doc, project: Doc, deps: Deps
) -> tuple[dict[str, Any] | None, str]:
    """File an instruction in the brain. Returns (what was remembered, what to say instead).

    An owner who is not on the roster is the one thing this refuses: a name the agent invented
    would be handed back to the team for weeks as though they had chosen it."""
    if not memory or deps.wiki is None:
        return None, ""
    text = redact(str(memory.get("text") or "")).strip()
    if not text:
        return None, ""

    person = str(memory.get("person") or "").strip()
    if person:
        found = resolve_owner(person, list(project.get("roster") or []))
        if found is None:
            return None, (f"I don't know a {person} on this project — who did you mean?")
        person = str(found.get("name") or person)

    payload = task.get("payload") or {}
    source = f"slack:{payload.get('channel', '')}:{payload.get('thread_ts', task['id'])}"
    where = await deps.wiki.add_entry(task["project_id"], str(memory.get("kind")), {
        "text": text,
        "subject": list(memory.get("subject") or []),
        "person": person or None,
        "source": source,
        "said_by": await _requester_name(task, deps),
    })
    if where is None:
        return None, ""
    return {**memory, "text": text, "person": person or None,
            "ref": f"wiki:{where[0]}#{where[1]}"}, ""


async def run(task: Doc, deps: Deps) -> StageResult:
    project = await deps.projects.get(task["project_id"])
    if project is None:
        raise PmError(f"project {task['project_id']} not found")

    params = task.get("params") or {}
    if params.get("cancel"):
        return await _cancel(task, str(params["cancel"]), deps)

    request = str(params.get("text") or "").strip()
    if not request:
        raise PmError("intake needs either a request or an identifier to stop watching")
    if deps.steward is None:
        raise PmError("intake needs a steward")

    policy = project.get("policy") or {}
    now = deps.clock.now()
    open_tasks = [
        {"id": row["id"], "kind": row["kind"], "params": row.get("params") or {},
         "due_at": row.get("due_at"), "reason": row.get("reason")}
        for row in await deps.db.query(
            "tasks", [("project_id", "==", task["project_id"]),
                      ("status", "in", ["queued", "blocked", "deferred"])], limit=50,
        )
        if row["kind"] in KINDS
    ]
    open_ids = {row["id"] for row in open_tasks}

    payload: dict[str, Any] = {
        "request": request,
        "requester_name": await _requester_name(task, deps),
        "today": iso(now)[:10],
        "open_tasks": open_tasks,
        "catalog": catalog_for_prompt(),
        "policy": {k: policy.get(k) for k in ("plan_horizon_days", "max_plan_size")},
        "lessons": await _lessons(deps, task["project_id"]),
        "brain": (await deps.wiki.for_prompt(task["project_id"], request)
                  if deps.wiki is not None else []),
        "feedback": None,
    }

    async def propose(sent: dict[str, Any]) -> tuple[dict[str, Any], Any]:
        assert deps.steward is not None
        parsed = Plan.model_validate(await deps.steward.run(sent)).model_dump()
        verdict = await check_plan(
            parsed, now=now, policy=policy,
            open_tasks=await deps.queue.open_count(task["project_id"]),
            existing_ids=lambda tid: tid in open_ids,
            id_exists=deps.ids.exists if deps.ids is not None else nothing_exists,
        )
        return parsed, verdict

    proposal, verdict = await propose(payload)
    bounced = False
    if verdict.rejected or verdict.reasons:
        bounced = True
        problems = "; ".join(
            [f"{r['key']}: {r['reason']}" for r in verdict.rejected] + verdict.reasons
        )
        proposal, verdict = await propose({
            **payload,
            "feedback": f"Some of what you proposed could not be scheduled — {problems}. "
                        "Fix those, keep the rest, and do not promise anything you had to drop.",
        })

    # An instruction is answered with a memory, not a plan. The roster gate applies here for
    # the same reason it applies to a filed ticket: an owner the agent invented is worse than
    # no owner, and this one would be repeated back for weeks.
    remembered, refused = await _remember(proposal.get("memory"), task, project, deps)

    children = commission(verdict.tasks, task)
    notes = " ".join(x for x in (interpretation(request, children),
                                 str(proposal.get("notes") or "")) if x)
    if remembered or refused:
        notes = refused or _noted(remembered)
    posted = await _reply(task, notes if (remembered or refused)
                          else _fallback_text(children, notes), children, deps, notes=notes)
    if posted and children:
        await react_quietly(
            deps.slack, task["payload"].get("channel"), task["payload"].get("thread_ts"),
            "handshake",
        )

    return StageResult(
        result={
            "accepted": [t["key"] for t in children],
            "rejected": verdict.rejected,
            "reasons": verdict.reasons,
            "notes": notes,
            "bounced": bounced,
            "replied": posted,
            "remembered": remembered,
        },
        children=children,
    )


def _fallback_text(children: list[dict[str, Any]], notes: str) -> str:
    """The notification line: the first sentence of the reply, said once."""
    if not children:
        return notes or "I couldn't turn that into anything I know how to watch."
    issues = [str((c.get("params") or {}).get("issue") or "") for c in children]
    named = [i for i in dict.fromkeys(issues) if i]
    return (f"Got it — I'll watch {named[0]} for you." if len(named) == 1
            else "Got it — here's what I'll keep an eye on.")


async def _reply(
    task: Doc, text: str, children: list[dict[str, Any]], deps: Deps, *, notes: str = ""
) -> bool:
    """Answer in the thread the request was made in. Recorded as an action — unlike the status
    message, this one is the agent speaking to a person who is waiting, so it belongs in the
    audit log and carries a revert."""
    channel = task["payload"].get("channel")
    if deps.slack is None or deps.actions is None or not channel:
        return False

    key = idempotency_key(str(task.get("root_event_id") or task["id"]), 0, "slack.intake")
    earlier = await deps.actions.find_by_key(key)
    if earlier is not None and earlier.get("status") == "done":
        return True

    action_id = await deps.actions.begin(
        task_id=task["id"], project_id=task["project_id"], kind="slack.post",
        idempotency_key=key, inputs={"channel": channel, "committed": len(children)},
    )
    try:
        ts = await deps.slack.post(
            channel, text, commitment_blocks(children, notes, now=deps.clock.now()),
            thread_ts=task["payload"].get("thread_ts"),
        )
    except SourceUnavailable as exc:
        await deps.actions.fail(action_id, redact(str(exc)))
        return False
    await deps.actions.finish(
        action_id, target_ids={"channel": channel, "ts": ts},
        revert={"op": "edit_message", "channel": channel, "ts": ts},
    )
    return True

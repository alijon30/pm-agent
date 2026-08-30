"""The console: one read-only page that explains what the agent has been doing, to a person.

The centrepiece is the decision journal — a reverse-chronological, plain-English feed of what the
agent decided and why. It is rendered entirely from records the harness already writes for other
reasons (task reasons and results, the action log's citations and checks_passed), because a
narrative maintained separately from the work is a narrative that drifts from it. Everything on
this page is derived; nothing here is a second source of truth.

Three rules hold for this module:

1. **Read-only.** No route here writes anything, and the import-linter contract keeps it away
   from the stages so it cannot start.
2. **Nothing raw reaches the page.** `esc()` redacts credential-shaped substrings and then
   HTML-escapes, and it is the only way a string gets into the output. Event payloads — the one
   place a transcript's raw words live — are never read at all.
3. **It renders on an empty database.** The first thing a judge sees is this page, possibly
   before anything has run.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.harness.core.clock import human_date, human_delta, human_due, iso, readable
from app.harness.core.dedupe import collapse
from app.harness.core.redact import redact
from app.harness.core.refs import ref_chip
from app.harness.core.voice import (
    count_in_words,
    first_name,
    issue_phrase,
    sentence_list,
)
from app.harness.core.words import count_of
from app.harness.deps import Deps
from app.harness.http.graph_assets import GRAPH_SCRIPT, GRAPH_STYLE
from app.harness.kinds.phrasing import UNMET_CONSEQUENCES, human_check, human_working
from app.harness.store.db import Doc
from app.harness.store.tasks import OPEN_STATUSES

router = APIRouter()

# The console reads whole collections for one project. That is honest at the scale the caps gate
# permits (tens of writes a day) and the limit keeps a runaway queue from timing out the page.
SCAN_LIMIT = 500
JOURNAL_LIMIT = 60
AUDIT_LIMIT = 30
GRAPH_LIMIT = 40
# A force layout stops being readable long before it stops being fast. The cap is about the eye.
GRAPH_NODES = 250
ISSUE_ACTIONS = ("linear.create_issue", "linear.comment")
# The order a story is told in when several things share a timestamp — which they do constantly,
# because one call produces a decision, an issue and a check inside the same second.
GRAPH_ORDER = {"meeting": 0, "decision": 1, "issue": 2, "person": 3, "check": 4, "lesson": 5}
STORY_LINES = 12
NOW_LINES = 5
# Firestore documents and one HTTP response: the page fetches this once, so it has to stay
# something a browser downloads without thinking about it.
GRAPH_BYTES = 300_000
STORY_TRIMS = (12, 6, 3, 1, 0)
DONE_ISH = ("done", "completed", "merged", "closed")
HEADLINE_FIELDS = (
    ("accuracy_pct", "factual accuracy"),
    ("fabricated_identifiers", "fabricated identifiers"),
    ("citation_coverage_pct", "citation coverage"),
    ("invalid_plans_materialised", "invalid plans materialised"),
    ("corrections_recurred", "corrections recurred"),
)


def esc(value: object) -> str:
    """The only way a string enters the page: redact anything credential-shaped (a stored error
    may quote a token), then HTML-escape it."""
    return html.escape(redact(str(value)))


# --- the decision journal ---------------------------------------------------------------------


def _ts_of(doc: Doc) -> str:
    return str(doc.get("finished_at") or doc.get("created_at") or "")


def _entry(ts: str, category: str, text: str, refs: list[str] | None = None) -> dict[str, Any]:
    """One line of the journal, plus the documents it was derived from.

    `refs` exists so another view can attribute an entry without re-deriving its phrasing: the
    graph asks "which of these lines are about this node?" and the answer is a set membership
    test rather than a second copy of every sentence in this file."""
    return {"ts": ts, "category": category, "text": text, "refs": refs or []}


def _short(text: str, limit: int = 90) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _issues_of(tasks: list[Doc]) -> list[str]:
    """The distinct issue identifiers a group of tasks is about, in first-seen order."""
    seen: list[str] = []
    for task in tasks:
        identifier = str((task.get("params") or {}).get("issue") or "")
        if identifier and identifier not in seen:
            seen.append(identifier)
    return seen


def _named(identifiers: list[str], noun: str) -> str:
    """Up to four things are named; more than that and the count is the useful part."""
    kept = [i for i in identifiers if i]
    if not kept:
        return ""
    return sentence_list(kept) if len(kept) <= 4 else count_in_words(len(kept), noun)


def _who(name_or_id: str, roster: list[dict[str, Any]]) -> str:
    """A first name, from a roster name or a Slack id. Falls back to whatever it was given —
    a journal that says "U-maya" is still better than one that says nothing."""
    for member in roster or []:
        known = (str(member.get("name") or ""), str(member.get("slack_id") or ""))
        if name_or_id and name_or_id in known:
            return first_name(member)
    return first_name(name_or_id) if name_or_id else ""


def _plan_line(task: Doc, children: list[Doc]) -> tuple[str, str]:
    if not children:
        return "planned", "nothing needed watching, so I scheduled nothing"
    dates = sorted({str(c.get("due_at") or "")[:10] for c in children if c.get("due_at")})
    about = _named(_issues_of(children), "ticket") or "this project"
    when = f" ({', '.join(human_date(d) for d in dates)})" if dates else ""
    return "planned", f"lined up {count_in_words(len(children), 'check')} on {about}{when}"


def _check_line(task: Doc, result: dict[str, Any], roster: list[dict[str, Any]]) -> tuple[str, str]:
    observed = result.get("observed") or {}
    identifier = str(observed.get("issue") or (task.get("params") or {}).get("issue") or "an issue")
    state = str(observed.get("state") or "")
    if result.get("early"):
        due = human_date(str(task.get("due_at") or ""))
        return "early", (
            f"{identifier} moved ahead of schedule — the check due {due or 'later'} "
            "answered itself"
        )
    if result.get("met"):
        return "checked", f"{identifier} is where it should be{f' — {state}' if state else ''}"
    if result.get("acted"):
        who = _who(str(observed.get("assignee") or ""), roster)
        return "nudged", f"{identifier} hadn't moved — said so once{f', to {who}' if who else ''}"
    reason = str(observed.get("reason") or observed.get("status") or "nothing worth saying")
    return "checked", f"{identifier} hadn't moved — stayed quiet ({reason})"


def _act_line(result: dict[str, Any]) -> tuple[str, str]:
    """What one call actually produced. A line that reports three zeroes has said nothing, so
    only the parts that happened get named — and when nothing did, it says that outright."""
    created = _named([str(c.get("identifier") or "") for c in result.get("created") or []],
                     "ticket")
    updated = _named([str(u.get("identifier") or "") for u in result.get("updated") or []],
                     "issue")
    skipped, conflicts = len(result.get("skipped") or []), len(result.get("conflicts") or [])
    parts: list[str] = []
    if created:
        parts.append(f"filed {created}")
    if updated:
        parts.append(f"updated {updated}")
    if skipped:
        parts.append(f"left {count_in_words(skipped, 'item')} out on purpose")
    if conflicts:
        parts.append(f"flagged {count_in_words(conflicts, 'disagreement')} for a human")
    if not parts:
        return "filed", "read the call and found nothing new to file"
    return "filed", sentence_list(parts)


def _done_line(
    task: Doc, children: list[Doc], roster: list[dict[str, Any]]
) -> tuple[str, str]:
    """One sentence for a finished task, in the words a person would use — and never a zero."""
    result: dict[str, Any] = task.get("result") or {}
    kind = str(task["kind"])

    if kind == "extract":
        title = str((result.get("meeting") or {}).get("title") or "a call")
        parts = []
        if result.get("action_items"):
            parts.append(count_in_words(len(result["action_items"]), "action item"))
        if result.get("decision_ids"):
            parts.append(count_in_words(len(result["decision_ids"]), "decision"))
        if result.get("dropped"):
            parts.append(f"dropped {count_in_words(len(result['dropped']), 'item')} "
                         "with no verbatim quote")
        return "extracted", f"read '{title}' — {sentence_list(parts) or 'nothing new'}"
    if kind == "reconcile":
        items, held = len(result.get("items") or []), len(result.get("unverified") or [])
        if not items and not held:
            return "reconciled", "checked the call against the tracker and found nothing to file"
        parts = []
        if items:
            parts.append(f"checked {count_in_words(items, 'item')} against the tracker, the "
                         "spec and the code")
        if held:
            parts.append(f"held {count_in_words(held, 'item')} back as unverified")
        return "reconciled", sentence_list(parts)
    if kind == "act":
        return _act_line(result)
    if kind == "plan":
        return _plan_line(task, children)
    if kind == "report":
        report = result.get("report") or {}
        removed = len(result.get("removed") or [])
        claims = sum(len(s.get("claims") or []) for s in report.get("sections") or [])
        tail = (f"; dropped {count_in_words(removed, 'claim')} it couldn't cite" if removed else "")
        return "reported", (
            f"wrote the status report — {count_in_words(claims, 'cited claim')}: "
            f"\"{_short(str(report.get('headline') or ''), 70)}\"{tail}"
        )
    if kind == "intake":
        if result.get("identifier"):
            stopped = len(result.get("cancelled") or [])
            return "cancelled", (
                f"stopped watching {result['identifier']} — the person who asked said so"
                if stopped else
                f"asked to stop watching {result['identifier']}, but nothing was running"
            )
        accepted = result.get("accepted") or []
        if accepted:
            return "planned", (
                f"a teammate asked for something and I took on "
                f"{count_in_words(len(accepted), 'check')}"
            )
        return "checked", (
            f"a teammate asked for something I can't do — "
            f"{_short(str(result.get('notes') or 'and I said so'), 70)}"
        )
    if kind == "daily_review":
        parts = []
        if result.get("checked"):
            parts.append(f"{count_in_words(int(result['checked']), 'check')} ran")
        if result.get("nudged"):
            parts.append(f"{count_in_words(int(result['nudged']), 'message')} went out")
        if result.get("learned"):
            parts.append(f"learned {count_in_words(len(result['learned']), 'thing')}")
        return "extracted", (
            f"reviewed yesterday — {sentence_list(parts) or 'a quiet day, nothing to learn from'}"
        )
    if kind.startswith("check_"):
        return _check_line(task, result, roster)
    if kind == "nudge":
        if result.get("sent"):
            return "nudged", f"sent one nudge about {(task.get('params') or {}).get('about', '')}"
        return "checked", f"stayed quiet — {result.get('reason', 'nothing to send')}"
    return "done", f"finished {kind}"


def task_refs(task: Doc, children: list[Doc]) -> list[str]:
    """The nodes a task's line is about: itself, the issue in its params, and — for a plan —
    the issues of everything it scheduled."""
    refs = [f"task:{task['id']}"]
    issue = str((task.get("params") or {}).get("issue") or "")
    if issue:
        refs.append(f"issue:{issue}")
    for child in children:
        child_issue = str((child.get("params") or {}).get("issue") or "")
        if child_issue and f"issue:{child_issue}" not in refs:
            refs.append(f"issue:{child_issue}")
    return refs


def action_refs(action: Doc) -> list[str]:
    """The nodes an action's line is about: the task that performed it, the issue it touched,
    and the person it was assigned to."""
    inputs: dict[str, Any] = action.get("inputs") or {}
    targets: dict[str, Any] = action.get("target_ids") or {}
    refs = [f"action:{action['id']}"]
    if action.get("task_id"):
        refs.append(f"task:{action['task_id']}")
    identifier = str(targets.get("identifier") or inputs.get("target_issue") or "")
    if identifier:
        refs.append(f"issue:{identifier}")
    if inputs.get("owner"):
        refs.append(f"person:{inputs['owner']}")
    return refs


def _task_entries(
    task: Doc, children: list[Doc], roster: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    ts, kind, status = _ts_of(task), str(task["kind"]), str(task["status"])
    refs = task_refs(task, children)
    entries: list[dict[str, Any]] = []

    if status == "done":
        category, text = _done_line(task, children, roster)
        entries.append(_entry(ts, category, text, refs))
    elif status == "deferred":
        entries.append(_entry(ts, "deferred", (
            f"held {kind} until {str(task.get('due_at') or '')[11:16]} — "
            f"{task.get('defer_reason') or 'not now'}"
        ), refs))
    elif status == "failed":
        entries.append(
            _entry(ts, "failed", f"{kind} failed — {_short(str(task.get('error')))}", refs))
    elif status == "cancelled":
        entries.append(
            _entry(ts, "cancelled", f"{kind} — {_short(str(task.get('error')))}", refs))
    elif status == "skipped":
        entries.append(
            _entry(ts, "cancelled", f"skipped {kind} — a dependency did not hold", refs))

    # A refused enqueue is the lineage gate saying no. It is the agent declining to give itself
    # more work, which is exactly the kind of decision this journal exists to show.
    for refusal in task.get("refused_enqueues") or []:
        entries.append(_entry(ts, "refused", (
            f"refused to schedule {refusal.get('kind', '?')} — {refusal.get('reason', '')}"
        ), refs))
    return entries


def _slack_line(
    action: Doc, task: Doc | None, children: list[Doc], roster: list[dict[str, Any]]
) -> tuple[str, str]:
    """What one Slack post was, said as what it did rather than which template it used."""
    inputs: dict[str, Any] = action.get("inputs") or {}
    observed = ((task or {}).get("result") or {}).get("observed") or {}

    if inputs.get("tasks"):
        dates = sorted({str(c.get("due_at") or "")[:10] for c in children if c.get("due_at")})
        when = f" ({', '.join(human_date(d) for d in dates)})" if dates else ""
        return "posted", f"posted the follow-through plan{when}"
    template = str(inputs.get("template") or "")
    if template == "standup":
        return "posted", "posted the morning standup"
    if template == "first_look":
        issue = str(observed.get("issue") or "it")
        return "posted", f"told whoever asked that the first check on {issue} looked fine"
    if template == "blocked":
        return "failed", "told whoever asked that I was stuck"
    if template:
        who = _who(str(observed.get("assignee") or ""), roster)
        about = str(observed.get("issue") or (task or {}).get("params", {}).get("issue") or "")
        return "nudged", (
            f"nudged {who or 'the channel'}{f' about {about}' if about else ''}"
        )
    if inputs.get("sprint"):
        return "posted", f"posted the {inputs['sprint']} report"
    meeting = inputs.get("meeting")
    subject = f" of '{meeting}'" if meeting else ""
    # The summary usually replaces the "reading the call…" message rather than arriving as a new
    # one, and the journal should say which happened — an edit notified nobody.
    verb = "filled in the summary" if inputs.get("edited") else "posted the summary"
    return "posted", f"{verb}{subject}, with a revert button on every action"


def _action_entries(
    action: Doc, task: Doc | None, children: list[Doc], roster: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    kind, status = str(action.get("kind")), str(action.get("status"))
    refs = action_refs(action)
    targets: dict[str, Any] = action.get("target_ids") or {}
    identifier = str(targets.get("identifier") or "")
    inputs: dict[str, Any] = action.get("inputs") or {}

    if status == "reverted":
        who = _who(str(action.get("reverted_by") or ""), roster) or "someone"
        return [_entry(str(action.get("reverted_at") or _ts_of(action)), "reverted",
                       f"{who} reverted {identifier or kind}", refs)]
    if status == "failed":
        return [_entry(_ts_of(action), "failed",
                       f"couldn't {kind} — {_short(str(action.get('error')))}", refs)]
    if status == "pending":
        return [_entry(_ts_of(action), "pending",
                       f"started {kind} — recorded before doing it, not yet confirmed", refs)]

    ts = _ts_of(action)
    if kind == "linear.create_issue":
        # A citation is shown as a person reads it; an issue with none says nothing about it,
        # because a line that announces an absence on every ticket stops being information.
        cited = [ref_chip(str(c)) for c in (action.get("citations") or [])][:2]
        owner = _who(str(inputs.get("owner") or ""), roster)
        clauses = [
            f"filed {issue_phrase(identifier or 'an issue', str(inputs.get('title') or ''))}",
            *( [f"assigned to {owner}"] if owner else [] ),
            *( [f"cited {' · '.join(cited)}"] if cited else [] ),
        ]
        return [_entry(ts, "filed", sentence_list(clauses), refs)]
    if kind == "linear.comment":
        return [_entry(ts, "filed", (
            f"commented on {identifier or 'an issue'} — "
            f"{_short(str(inputs.get('title') or 'raised again in a call'), 60)}"
        ), refs)]
    if kind.startswith("slack."):
        category, text = _slack_line(action, task, children, roster)
        return [_entry(ts, category, text, refs)]
    return [_entry(ts, "done", f"{kind} completed", refs)]


def journal_entries(
    tasks: list[Doc], actions: list[Doc], roster: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """The agent's decisions, newest first, as plain sentences.

    Pure: documents in, a list of {ts, category, text, refs} out. `category` is both the badge a
    reader sees and the CSS class, so a new kind of entry needs no template change. The roster is
    optional and only ever used to turn a name or a Slack id into a first name."""
    people = roster or []
    children: dict[str, list[Doc]] = {}
    for task in tasks:
        parent = str(task.get("parent_task_id") or "")
        if parent:
            children.setdefault(parent, []).append(task)
    by_id = {str(t["id"]): t for t in tasks}

    entries: list[dict[str, Any]] = []
    for task in tasks:
        entries.extend(_task_entries(task, children.get(str(task["id"]), []), people))
    for action in actions:
        owner = by_id.get(str(action.get("task_id") or ""))
        entries.extend(_action_entries(
            action, owner, children.get(str(action.get("task_id") or ""), []), people
        ))
    return sorted(entries, key=lambda e: e["ts"], reverse=True)


# --- the task graph ---------------------------------------------------------------------------


def plan_groups(tasks: list[Doc]) -> list[dict[str, Any]]:
    """Tasks grouped by the plan that created them, each group ordered so a task appears after
    whatever it waits on, with `depth` = how far down that chain it sits. Depth is what the page
    indents by, which is a dependency edge drawn in text instead of in SVG.

    Only the planner's own plans get a group. Every stage's children carry a plan_id — it is the
    queue's transaction id, not a statement that a model planned anything — so the spine of a
    call (extract → reconcile → act → plan) stays one list rather than looking like four plans."""
    planned_by = {str(t["id"]) for t in tasks if t["kind"] == "plan"}
    groups: dict[str, list[Doc]] = {}
    for task in tasks:
        from_planner = str(task.get("parent_task_id") or "") in planned_by
        groups.setdefault(str(task.get("plan_id") or "") if from_planner else "", []).append(task)

    out: list[dict[str, Any]] = []
    for plan_id, rows in groups.items():
        inside = {str(r["id"]) for r in rows}
        depth = {str(r["id"]): 0 for r in rows}
        # Relax until stable rather than recurse: the plan gate rejects cycles, but the console
        # must render whatever is in the database, including something a cycle survived into.
        for _ in range(len(rows)):
            changed = False
            for row in rows:
                deps_in = [d for d in row.get("depends_on") or [] if d in inside]
                want = max((depth[d] + 1 for d in deps_in), default=0)
                if want > depth[str(row["id"])]:
                    depth[str(row["id"])] = want
                    changed = True
            if not changed:
                break
        ordered = sorted(rows, key=lambda r: (depth[str(r["id"])], str(r.get("due_at") or "")))
        out.append({
            "plan_id": plan_id,
            "created_at": max((str(r.get("created_at") or "") for r in rows), default=""),
            "tasks": [{**r, "depth": depth[str(r["id"])]} for r in ordered],
        })
    return sorted(out, key=lambda g: str(g["created_at"]), reverse=True)


# --- the graph --------------------------------------------------------------------------------


def _node(node_id: str, kind: str, label: str, ts: str, **extra: Any) -> dict[str, Any]:
    return {"id": node_id, "type": kind, "label": redact(_short(label, 60)), "ts": ts, **extra}


def _issue_nodes(actions: list[Doc]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """One node per issue the agent touched, however many times it touched it, plus the root
    event each one came from — which is how a decision gets connected to the ticket it caused."""
    issues: dict[str, dict[str, Any]] = {}
    for action in actions:
        if action.get("kind") not in ISSUE_ACTIONS or action.get("status") != "done":
            continue
        targets = action.get("target_ids") or {}
        identifier = str(targets.get("identifier") or "")
        if not identifier:
            continue
        inputs = action.get("inputs") or {}
        existing = issues.get(identifier)
        # A create carries the title and the link; a later comment on the same issue does not,
        # so the first good value wins rather than the last write.
        issues[identifier] = {
            "id": f"issue:{identifier}",
            "type": "issue",
            "label": redact(_short(str(inputs.get("title") or identifier), 60)),
            "ts": str((existing or {}).get("ts") or action.get("created_at") or ""),
            "url": str((existing or {}).get("url") or targets.get("url") or ""),
            "owner": str((existing or {}).get("owner") or inputs.get("owner") or ""),
        }
    owners = {i["id"]: i["owner"] for i in issues.values() if i["owner"]}
    return [{k: v for k, v in i.items() if k != "owner"} for i in issues.values()], owners


def _cap(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The newest GRAPH_NODES, except that people are always kept: a roster is small, and a
    graph of work with the people removed is a graph of the wrong thing."""
    people = [n for n in nodes if n["type"] == "person"]
    rest = sorted((n for n in nodes if n["type"] != "person"), key=lambda n: str(n["ts"]))
    room = max(0, GRAPH_NODES - len(people))
    return [*people, *rest[-room:]]


def attribute(
    entries: list[dict[str, Any]], node_ids: set[str], expand: dict[str, list[str]]
) -> dict[str, list[dict[str, Any]]]:
    """Which lines of the journal belong to which node.

    Attribution is set membership on the refs each line already carries, plus `expand` for the
    two relationships a ref cannot state on its own: a task belongs to the call it came from,
    and a decision owns the issues it led to. Nothing here re-derives a sentence."""
    story: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        owners: set[str] = set()
        for ref in entry.get("refs") or []:
            if ref in node_ids:
                owners.add(ref)
            owners.update(target for target in expand.get(ref, []) if target in node_ids)
        # The page redacts as it renders; JSON has no render step, so a line is cleaned here or
        # it ships as it is. A stored error can quote a token, and this is the one road out.
        line = {"ts": entry["ts"], "category": entry["category"],
                "text": redact(str(entry["text"]))}
        for owner in owners:
            story.setdefault(owner, []).append(dict(line))
    return {node_id: lines[:STORY_LINES] for node_id, lines in story.items()}


def _observations(tasks: list[Doc]) -> dict[str, dict[str, Any]]:
    """The newest thing each check saw about each issue. This page never calls the tracker — it
    shows what the agent recorded, which is also what lets it render with the network down."""
    seen: dict[str, dict[str, Any]] = {}
    for task in sorted(tasks, key=lambda t: str(t.get("finished_at") or "")):
        observed = (task.get("result") or {}).get("observed") or {}
        identifier = str(observed.get("issue") or "")
        if identifier and observed.get("status") == "ok":
            seen[identifier] = observed
    return seen


def issue_facts(node: dict[str, Any], created: Doc | None, observed: dict[str, Any],
                from_call: bool) -> dict[str, Any]:
    inputs: dict[str, Any] = (created or {}).get("inputs") or {}
    return {
        "state": redact(str(observed.get("state") or "")) or "unknown",
        "assignee": redact(str(observed.get("assignee") or inputs.get("owner") or "")) or "nobody",
        "priority": inputs.get("priority"),
        "due": human_date(str(observed.get("due") or inputs.get("due") or "")),
        "filed_from_call": from_call,
    }


def check_facts(task: Doc) -> dict[str, Any]:
    result: dict[str, Any] = task.get("result") or {}
    observed: dict[str, Any] = result.get("observed") or {}
    summary = observed.get("state") or observed.get("reason") or (
        "a pull request" if observed.get("prs") else "")
    return {
        "reason": redact(str(task.get("reason") or "")),
        "due": human_due(str(task.get("due_at") or "")),
        "status": str(task.get("status") or ""),
        "on_unmet": UNMET_CONSEQUENCES.get(str(task.get("on_unmet") or ""), ""),
        "observed": redact(str(summary)) if summary else "nothing yet",
        "early": bool(result.get("early")),
    }


def _capped(items: list[dict[str, Any]]) -> dict[str, Any]:
    """A short list plus how much it is hiding. Five lines is what a glance holds; the count is
    what stops five from reading like all of it."""
    return {"items": items[:NOW_LINES], "more": max(0, len(items) - NOW_LINES)}


def _waiting_on(task: Doc, by_id: dict[str, Doc]) -> str:
    """What a blocked task is waiting for, named rather than pointed at. This is the plan made
    visible: the graph shows the dependency, this says it out loud."""
    named: list[str] = []
    for dependency in task.get("depends_on") or []:
        found = by_id.get(str(dependency))
        named.append(
            redact(human_check(found)) if found else "something that has not finished"
        )
    return " and ".join(named[:2]) or "an earlier step"


def now_view(
    tasks: list[Doc], events: list[Doc], now: datetime, lease_minutes: int
) -> dict[str, Any]:
    """What the agent is doing this second, what it will do next, and what it is waiting for.

    Assembled from the same task documents the graph is drawn from — the present and the past
    are one read, so the two halves of the page can never disagree about the state of the queue.
    """
    by_id = {str(t["id"]): t for t in tasks}

    working: list[dict[str, Any]] = []
    for task in tasks:
        if task.get("status") != "leased":
            continue
        # A lease is stamped as "now + the lease window", so the moment work started is the only
        # thing the document does not say outright — and is exactly one subtraction away.
        until = readable(str(task.get("lease_until") or ""))
        working.append({
            "id": str(task["id"]), "kind": str(task["kind"]),
            "phrase": redact(human_working(task)),
            "issue": str((task.get("params") or {}).get("issue") or ""),
            "since": iso(until - timedelta(minutes=lease_minutes)) if until
                     else str(task.get("created_at") or ""),
        })

    upcoming = sorted(
        (t for t in tasks if t.get("status") in ("queued", "deferred") and t.get("due_at")),
        key=lambda t: str(t["due_at"]),
    )
    up_next = [{
        "kind": str(t["kind"]), "phrase": redact(human_check(t)),
        "issue": str((t.get("params") or {}).get("issue") or ""),
        "due_at": str(t["due_at"]), "due_human": human_delta(str(t["due_at"]), now),
    } for t in upcoming]

    waiting = [
        {"phrase": redact(human_check(t)), "on": _waiting_on(t, by_id)}
        for t in tasks if t.get("status") == "blocked"
    ]

    moved = [str(t.get("finished_at") or "") for t in tasks]
    moved += [str(e.get("received_at") or "") for e in events]
    open_tasks = [t for t in tasks if str(t.get("status")) in OPEN_STATUSES]

    return {
        "working": _capped(working),
        "up_next": _capped(up_next),
        "waiting": _capped(waiting),
        "last_tick": max((m for m in moved if m), default=""),
        "open": len(open_tasks),
        "watching": sum(1 for t in open_tasks if str(t["kind"]).startswith("check_")),
    }


def _facts_for(
    node: dict[str, Any],
    project: Doc,
    decisions: list[Doc],
    observed: dict[str, dict[str, Any]],
    created_by_issue: dict[str, Doc],
    issue_event: dict[str, str],
    tasks_by_id: dict[str, Doc],
    owners: dict[str, str],
    nudged: dict[str, int],
) -> dict[str, Any]:
    """What this thing is, in the terms its own kind is described in. Every value comes from a
    document this project already wrote — the panel is a reading of the record, not a lookup."""
    kind, node_id = str(node["type"]), str(node["id"])
    identifier = node_id.partition(":")[2]

    if kind == "issue":
        return issue_facts(node, created_by_issue.get(node_id),
                           observed.get(identifier, {}), bool(issue_event.get(node_id)))
    if kind == "check":
        task = tasks_by_id.get(identifier)
        return check_facts(task) if task else {}
    if kind == "decision":
        found = next((d for d in decisions if str(d["id"]) == identifier), {})
        return {
            "statement": redact(str(found.get("statement") or "")),
            "quote": redact(str(found.get("quote") or "")),
            "source": ref_chip(str(found.get("source") or "")),
        }
    if kind == "person":
        member: dict[str, Any] = next(
            (m for m in project.get("roster") or [] if str(m.get("name")) == identifier), {}
        )
        return {
            "role": redact(str(member.get("role") or "")) or "on the team",
            "owns": sorted(
                issue_id.partition(":")[2] for issue_id, who in owners.items()
                if who == identifier
            ),
            "pings_received": nudged.get(identifier, 0),
        }
    if kind == "meeting":
        event_id = identifier
        return {
            "title": node["label"],
            "when": human_due(str(node.get("ts") or "")),
            "produced": {
                "decisions": sum(
                    1 for d in decisions if str(d.get("event_id") or "") == event_id
                ),
                "issues": sum(1 for root in issue_event.values() if root == event_id),
            },
        }
    return {}


def lesson_chips(node: dict[str, Any], evidence: list[str], labels: dict[str, str]) -> list[str]:
    """A lesson's evidence, said in the words of what it points at. "task:8da1…" tells a reader
    nothing; "check that INV-26 is underway" tells them why the agent believes this."""
    chips: list[str] = []
    for ref in evidence:
        chip = labels.get(str(ref)) or ref_chip(str(ref))
        if chip and chip not in chips:
            chips.append(_short(chip, 48))
    return chips


def _within_budget(graph: dict[str, Any]) -> dict[str, Any]:
    """One response has to stay downloadable. Stories are trimmed before anything else — the
    shape of the graph is the point of the page, and a shorter story is still a true one."""
    for limit in STORY_TRIMS:
        for node in graph["nodes"]:
            node["story"] = node.get("story", [])[:limit]
        graph["truncated"] = limit < STORY_LINES
        if len(json.dumps(graph, ensure_ascii=False)) <= GRAPH_BYTES:
            return graph
    return graph


async def graph_data(project: Doc, deps: Deps) -> dict[str, Any]:
    """The agent's world as a graph: what it was told, what it decided, what it filed, who owns
    it, what it is watching, and what it learned. Assembled from the same documents the rest of
    the console reads — nothing here is a second record."""
    project_id = str(project["id"])
    filters = [("project_id", "==", project_id)]
    tasks = await deps.db.query("tasks", filters, order_by="created_at", limit=SCAN_LIMIT)
    actions = await deps.db.query("actions", filters, order_by="created_at", limit=SCAN_LIMIT)
    # Collapsed on the way in: production holds near-duplicates from before the ledger guarded
    # against them, and a graph with the same decision twice is a graph nobody trusts.
    decisions = collapse(
        await deps.db.query("decisions", filters, order_by="created_at", limit=SCAN_LIMIT),
        lambda row: str(row.get("statement") or ""),
    )
    events = await deps.db.query("events", filters, order_by="received_at", limit=SCAN_LIMIT)
    lessons = await deps.lessons.for_project(project_id) if deps.lessons is not None else []

    nodes: list[dict[str, Any]] = []
    # The only thing this page ever takes from an event payload is the call's title. The
    # transcript inside it is exactly what the console must never render.
    for event in events:
        if event.get("provider") != "fathom":
            continue
        title = str((event.get("payload") or {}).get("title") or "Call")
        nodes.append(_node(f"meeting:{event['id']}", "meeting", title,
                           str(event.get("received_at") or "")))
    for decision in decisions:
        nodes.append(_node(f"decision:{decision['id']}", "decision",
                           str(decision.get("statement") or ""),
                           str(decision.get("created_at") or "")))
    issue_nodes, owners = _issue_nodes(actions)
    nodes.extend(issue_nodes)
    for member in project.get("roster") or []:
        name = str(member.get("name") or "")
        if name:
            nodes.append(_node(f"person:{name}", "person", name, ""))
    for task in tasks:
        if not str(task["kind"]).startswith("check_"):
            continue
        nodes.append(_node(
            f"task:{task['id']}", "check", human_check(task),
            str(task.get("created_at") or ""), status=str(task.get("status") or ""),
            early=bool((task.get("result") or {}).get("early")),
        ))
    for lesson in lessons:
        nodes.append(_node(f"lesson:{lesson['id']}", "lesson", str(lesson.get("text") or ""),
                           str(lesson.get("created_at") or "")))

    kept = _cap(nodes)
    known = {n["id"] for n in kept}

    # Which call each issue came from, routed through the task that filed it. A decision and an
    # issue that share a root event came out of the same conversation.
    task_root = {str(t["id"]): str(t.get("root_event_id") or "") for t in tasks}
    tasks_by_id = {str(t["id"]): t for t in tasks}
    issue_event: dict[str, str] = {}
    for action in actions:
        if action.get("kind") not in ISSUE_ACTIONS or action.get("status") != "done":
            continue
        identifier = str((action.get("target_ids") or {}).get("identifier") or "")
        root = task_root.get(str(action.get("task_id") or ""), "")
        if identifier and root:
            issue_event.setdefault(f"issue:{identifier}", root)

    edges: list[dict[str, Any]] = []

    def link(source: str, target: str, rel: str, ts: str) -> None:
        if source in known and target in known and source != target:
            edges.append({"source": source, "target": target, "rel": rel, "ts": ts})

    for decision in decisions:
        node_id = f"decision:{decision['id']}"
        event_id = str(decision.get("event_id") or "")
        created = str(decision.get("created_at") or "")
        link(f"meeting:{event_id}", node_id, "decided", created)
        linked = [str(i) for i in decision.get("linked_issue_ids") or []]
        if linked:
            for identifier in linked:
                link(node_id, f"issue:{identifier}", "led to", created)
        else:
            # Nothing recorded the link explicitly, so fall back to the call they share. Skipped
            # entirely when the issue's origin is unknown — a guessed edge is worse than none.
            for issue_id, root in issue_event.items():
                if root and root == event_id:
                    link(node_id, issue_id, "led to", created)

    for issue_id, owner in owners.items():
        link(issue_id, f"person:{owner}", "owned by", "")

    for task in tasks:
        if not str(task["kind"]).startswith("check_"):
            continue
        node_id = f"task:{task['id']}"
        created = str(task.get("created_at") or "")
        issue = str((task.get("params") or {}).get("issue") or "")
        if issue:
            link(node_id, f"issue:{issue}", "watches", created)
        for dependency in task.get("depends_on") or []:
            link(node_id, f"task:{dependency}", "waits on", created)

    for lesson in lessons:
        node_id = f"lesson:{lesson['id']}"
        for ref in lesson.get("evidence") or []:
            if str(ref).startswith("task:"):
                link(node_id, str(ref), "learned from", str(lesson.get("created_at") or ""))

    # What each node is, and what the agent did about it. The journal is generated once and
    # attributed, so the panel and the console's feed can never tell different stories.
    expand = {f"task:{tid}": [f"meeting:{root}"] for tid, root in task_root.items() if root}
    for decision in decisions:
        linked = [f"issue:{i}" for i in decision.get("linked_issue_ids") or []] or [
            issue_id for issue_id, root in issue_event.items()
            if root and root == str(decision.get("event_id") or "")
        ]
        for issue_id in linked:
            expand.setdefault(issue_id, []).append(f"decision:{decision['id']}")
    story = attribute(
        journal_entries(tasks, actions, project.get("roster") or []), known, expand
    )

    observed = _observations(tasks)
    created_by_issue = {
        f"issue:{(a.get('target_ids') or {}).get('identifier')}": a
        for a in actions if a.get("kind") == "linear.create_issue"
    }
    nudged: dict[str, int] = {}
    for action in actions:
        if not (action.get("inputs") or {}).get("template"):
            continue
        who = str((((tasks_by_id.get(str(action.get("task_id") or "")) or {}).get("result") or {})
                   .get("observed") or {}).get("assignee") or "")
        if who:
            nudged[who] = nudged.get(who, 0) + 1

    labels = {str(n["id"]): str(n["label"]) for n in kept}
    evidence = {f"lesson:{row['id']}": [str(r) for r in row.get("evidence") or []]
                for row in lessons}
    for node in kept:
        node["story"] = story.get(str(node["id"]), [])
        if node["type"] == "lesson":
            node["facts"] = {
                "evidence": lesson_chips(node, evidence.get(str(node["id"]), []), labels)
            }
            continue
        node["facts"] = _facts_for(node, project, decisions, observed, created_by_issue,
                                   issue_event, tasks_by_id, owners, nudged)

    # Emitted in the order the replay should reveal them. The client walks the array rather than
    # the clock: a burst of activity inside one second is the normal case, and a cursor moving
    # over milliseconds would show all of it in a single frame and then sit still all night.
    kept.sort(key=lambda n: (str(n["ts"]), GRAPH_ORDER.get(str(n["type"]), 9), str(n["id"])))
    graph = {"nodes": kept, "edges": edges, "truncated": False,
             "now": now_view(tasks, events, deps.clock.now(), deps.settings.lease_minutes),
             "generated_at": iso_now(deps), "project": str(project.get("name") or project_id)}
    return _within_budget(graph)


def iso_now(deps: Deps) -> str:
    return deps.clock.now().isoformat()


# The legend is the key to the glyphs, so it has to carry them. Kept beside the page rather
# than in the script because it is markup, and the script's copy of these colours is the one the
# nodes are drawn with — a mismatch here would be visible immediately.
GRAPH_LEGEND = (
    ("call", "#b48ead", "☎"),
    ("decision", "#ebcb8b", "◆"),
    ("issue", "#5e81ac", "▣"),
    # Drawn by the page from the same silhouette the node uses, so the key cannot drift from
    # the thing it is a key to.
    ("person", "#a3be8c", ""),
    ("check", "#4c566a", "○"),
    ("lesson", "#d08770", "✦"),
)


def graph_page(project_name: str) -> str:
    """One self-contained document: no script src, no stylesheet link, no font, no CDN. It
    fetches its own data from /console/graph.json and draws everything itself — the glows, the
    arrowheads and the glyphs are all defined by the page at load."""
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{esc(project_name)} — the agent's world</title>"
        f"<style>{GRAPH_STYLE}</style></head><body>"
        "<div id='stage'><svg id='canvas'><defs id='defs'></defs>"
        "<g id='edges'></g><g id='nodes'></g></svg></div>"
        f"<header><h1>{esc(project_name)}</h1>"
        "<p>the agent's world, as it learned it · <a href='/console'>← console</a></p></header>"
        "<div id='rail'>"
        "<div id='now'><div id='now-head'><span id='pulse'></span>"
        "<span id='now-line'>waking up…</span><span class='caret'>▾</span></div>"
        "<div id='now-body'></div>"
        "<div id='now-hint' class='now-past-hint' style='display:none'>"
        "viewing the past — scrub to the end for now</div></div></div>"
        # The legend anchors the bottom-left corner on its own: a colour key is furniture, and
        # it should not sit above the fold pretending to be status.
        "<div id='legend'>"
        + "".join(
            f"<span><i id='legend-{esc(name)}' style='background:{colour}'>{esc(glyph)}</i>"
            f"{esc(name)}</span>"
            for name, colour, glyph in GRAPH_LEGEND
        )
        + "</div>"
        "<div id='tooltip'></div>"
        "<aside id='panel'><button id='panel-close' title='Close'>✕</button>"
        "<div id='panel-body'></div></aside>"
        "<div id='empty' style='display:none'>Nothing has happened yet.</div>"
        "<div id='controls'>"
        "<button id='play'>▶ Replay</button>"
        "<input type='range' id='scrubber' min='0' max='1' value='1'>"
        "<span id='clock'>—</span><span id='mode'>LIVE</span>"
        "<span id='count'>0 / 0</span>"
        "</div>"
        f"<script>{GRAPH_SCRIPT}</script></body></html>"
    )


# --- rendering --------------------------------------------------------------------------------

STYLE = """
/* The console and the graph are one surface seen two ways, so they share a palette, a material
   and a typeface. Tokens, gradient and glass are lifted from GRAPH_STYLE deliberately: a judge
   clicking between the two pages should never feel they left the product. */
:root { --bg:#06080d; --fg:#e8ecf4; --muted:#7e899c; --line:rgba(148,163,184,.14);
        --panel:rgba(15,19,29,.78); --accent:#7dd3e0; --good:#a3be8c; --warm:#ebcb8b;
        --warn:#bf616a; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin:0; padding:30px 20px 72px; color:var(--fg); min-height:100%;
  font:14.5px/1.6 ui-sans-serif,-apple-system,"SF Pro Text","Segoe UI",Roboto,sans-serif;
  background:
    radial-gradient(ellipse 110% 60% at 50% 0%, rgba(56,78,118,.20) 0%, rgba(10,14,22,0) 62%),
    radial-gradient(circle at 50% 20%, #0c111d 0%, #080b12 55%, #05070b 100%);
  background-attachment:fixed; }
/* The same faint dot grid the graph hangs its void on, fading out before the fold. */
body::before { content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:radial-gradient(circle, rgba(148,163,184,.06) 1px, transparent 1.4px);
  background-size:26px 26px;
  -webkit-mask-image:linear-gradient(#000 0%, transparent 70%);
  mask-image:linear-gradient(#000 0%, transparent 70%); }
main { max-width:960px; margin:0 auto; position:relative; z-index:1; }

h1 { font-size:22px; margin:0 0 3px; font-weight:700; letter-spacing:-.015em;
  background:linear-gradient(135deg, #f2f5fa 30%, #9fb2cc);
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }
h2 { font-size:9.5px; text-transform:uppercase; letter-spacing:.14em; color:var(--muted);
  margin:38px 0 12px; font-weight:600; }
.sub { color:var(--muted); margin:0 0 20px; font-size:12.5px; letter-spacing:.01em; }

/* Every panel is the same glass as the graph's floating chrome. */
.card, .j li, table { background:var(--panel);
  -webkit-backdrop-filter:blur(18px) saturate(1.4); backdrop-filter:blur(18px) saturate(1.4); }
.cards { display:flex; flex-wrap:wrap; gap:11px; }
.card { border:1px solid var(--line); border-radius:14px; padding:12px 16px; min-width:112px;
  box-shadow:0 14px 40px rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.05); }
.card b { display:block; font-size:22px; font-weight:700; letter-spacing:-.02em;
  font-variant-numeric:tabular-nums; }
.card span { color:var(--muted); font-size:11.5px; }

.j { list-style:none; margin:0; padding:0; border:1px solid var(--line); border-radius:14px;
  overflow:hidden; box-shadow:0 14px 40px rgba(0,0,0,.42); }
.j li { display:flex; gap:11px; padding:9px 15px; align-items:baseline; line-height:1.5;
  border-bottom:1px solid var(--line); }
.j li:last-child { border-bottom:none; }
.j time { color:var(--muted); font-variant-numeric:tabular-nums; font-size:11.5px;
  white-space:nowrap; flex:none; min-width:78px; }

/* Category chips carry the graph's tints, so "filed" is the same green in both places. */
.tag { font-size:10px; letter-spacing:.1em; text-transform:uppercase; padding:2px 9px;
  border-radius:999px; white-space:nowrap; font-weight:600; flex:none; min-width:74px;
  text-align:center; color:#8892a4; border:1px solid rgba(136,146,164,.3);
  background:rgba(136,146,164,.1); }
.tag.filed, .tag.reported, .tag.early { color:#a3be8c; border-color:rgba(163,190,140,.34);
  background:rgba(163,190,140,.11); }
.tag.planned, .tag.posted { color:#88c0d0; border-color:rgba(136,192,208,.34);
  background:rgba(136,192,208,.11); }
.tag.nudged { color:#ebcb8b; border-color:rgba(235,203,139,.34);
  background:rgba(235,203,139,.11); }
.tag.extracted, .tag.reconciled { color:#b48ead; border-color:rgba(180,142,173,.34);
  background:rgba(180,142,173,.11); }
.tag.deferred, .tag.reverted { color:#d08770; border-color:rgba(208,135,112,.34);
  background:rgba(208,135,112,.11); }
.tag.refused, .tag.failed, .tag.cancelled { color:#bf616a; border-color:rgba(191,97,106,.34);
  background:rgba(191,97,106,.11); }

table { width:100%; border-collapse:separate; border-spacing:0; font-size:13px;
  border:1px solid var(--line); border-radius:14px; overflow:hidden;
  box-shadow:0 14px 40px rgba(0,0,0,.42); }
th { text-align:left; color:var(--muted); font-weight:600; font-size:9.5px;
  text-transform:uppercase; letter-spacing:.12em; padding:10px 14px;
  border-bottom:1px solid var(--line); background:rgba(148,163,184,.05); }
td { padding:9px 14px; border-bottom:1px solid var(--line); vertical-align:top;
  color:#c6cede; }
tr:last-child td { border-bottom:none; }
code { font:11.5px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--accent);
  background:rgba(125,211,224,.09); border:1px solid rgba(125,211,224,.18);
  border-radius:5px; padding:1px 6px; }
.empty { color:var(--muted); font-style:italic; font-size:13px; }
.dep { color:var(--muted); }
a { color:inherit; text-decoration:none; border-bottom:1px solid var(--line);
  transition:border-color 140ms ease, color 140ms ease; }
a:hover { color:var(--accent); border-color:var(--accent); }
"""


def _cards(pairs: list[tuple[str, str]]) -> str:
    if not pairs:
        return "<p class='empty'>Nothing yet.</p>"
    cells = "".join(
        f"<div class='card'><b>{esc(value)}</b><span>{esc(label)}</span></div>"
        for label, value in pairs
    )
    return f"<div class='cards'>{cells}</div>"


def _table(headers: list[str], rows: list[list[str]], empty: str) -> str:
    """Rows arrive already escaped — every caller builds cells with esc() so a cell may carry
    markup we chose (a <code> wrapper), never markup a document carried in."""
    if not rows:
        return f"<p class='empty'>{esc(empty)}</p>"
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _journal_html(entries: list[dict[str, str]]) -> str:
    if not entries:
        return "<p class='empty'>The agent has not done anything yet.</p>"
    items = "".join(
        f"<li><time>{esc(e['ts'][5:16].replace('T', ' '))}</time>"
        f"<span class='tag {esc(e['category'])}'>{esc(e['category'])}</span>"
        f"<span>{esc(e['text'])}</span></li>"
        for e in entries
    )
    return f"<ul class='j'>{items}</ul>"


def _graph_html(groups: list[dict[str, Any]]) -> str:
    if not groups:
        return "<p class='empty'>No tasks yet.</p>"
    blocks: list[str] = []
    for group in groups:
        label = (
            f"follow-ups the planner scheduled · plan {group['plan_id'][:8]}"
            if group["plan_id"] else "the call, end to end"
        )
        rows: list[list[str]] = []
        for task in group["tasks"]:
            indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * int(task["depth"])
            arrow = "<span class='dep'>└─ </span>" if task["depth"] else ""
            rows.append([
                f"{indent}{arrow}<code>{esc(task['kind'])}</code>",
                esc(task["status"]),
                esc(str(task.get("due_at") or "")[:16].replace("T", " ")),
                esc(_short(str(task.get("reason") or ""), 70)),
            ])
        blocks.append(
            f"<p class='sub'>{esc(label)} · {count_of(len(group['tasks']), 'task')}</p>"
            + _table(["task", "status", "due", "why"], rows, "empty plan")
        )
    return "".join(blocks)


def _audit_html(actions: list[Doc]) -> str:
    rows: list[list[str]] = []
    for action in actions:
        targets: dict[str, Any] = action.get("target_ids") or {}
        cited = list(action.get("citations") or [])
        rows.append([
            f"<code>{esc(action.get('kind'))}</code>",
            esc(action.get("status")),
            esc(targets.get("identifier") or targets.get("channel") or ""),
            f"<code>{esc(' · '.join(cited[:2])) or '—'}</code>",
            esc(", ".join(action.get("checks_passed") or []) or "—"),
        ])
    return _table(["action", "status", "target", "cited", "gates"], rows, "No actions yet.")


def _conflicts_html(conflicts: list[dict[str, Any]]) -> str:
    if not conflicts:
        return "<p class='empty'>No unresolved disagreements on record.</p>"
    rows = [
        [esc(c.get("about", "")),
         esc(c.get("kind", "")),
         "<br>".join(
             f"{esc(s.get('claim', ''))} <code>{esc(s.get('source', ''))}</code>"
             for s in c.get("sides") or []
         )]
        for c in conflicts
    ]
    return _table(["about", "kind", "what each source says"], rows, "none")


def _lessons_html(lessons: list[Doc]) -> str:
    """What the agent worked out about its own behaviour, with what it worked it out from. The
    evidence is shown because a lesson nobody can trace back is a lesson nobody should trust."""
    if not lessons:
        return "<p class='empty'>The agent has not drawn any lessons from its own runs yet.</p>"
    items = "".join(
        f"<li><time>{esc(str(row.get('created_at') or '')[5:10])}</time>"
        f"<span>{esc(row.get('text'))}</span>"
        + "".join(
            f"<span class='tag'>{esc(ref)}</span>" for ref in (row.get("evidence") or [])[:4]
        )
        + "</li>"
        for row in lessons
    )
    return f"<ul class='j'>{items}</ul>"


def _corrections_html(corrections: list[Doc]) -> str:
    rows = [
        [esc(c.get("wrong", "")), esc(c.get("right", "")), esc(c.get("scope", "")),
         esc(c.get("stage", ""))]
        for c in corrections
    ]
    return _table(["what was wrong", "what is right", "scope", "stage"], rows,
                  "Nobody has corrected the agent yet.")


def _evals_html(doc: Doc | None) -> str:
    if doc is None:
        return "<p class='empty'>No eval run recorded yet (evals/run_evals.py writes one).</p>"
    headline: dict[str, Any] = doc.get("headline") or {}
    pairs = [(label, str(headline.get(key, "n/a"))) for key, label in HEADLINE_FIELDS]
    when = esc(str(doc.get("created_at") or "")[:16].replace("T", " "))
    passed, total = doc.get("passed", "?"), doc.get("total", "?")
    return (
        f"<p class='sub'>{esc(passed)}/{esc(total)} questions · run {when}</p>" + _cards(pairs)
    )


def render(
    project: Doc | None,
    tasks: list[Doc],
    actions: list[Doc],
    corrections: list[Doc],
    lessons: list[Doc],
    evals: Doc | None,
    today: str,
) -> str:
    """The whole page, as a string. Pure, so what a judge sees is unit-testable."""
    if project is None:
        return _page(
            "pm-agent", "<h1>pm-agent</h1><p class='sub'>No project is seeded yet — run "
                        "scripts/seed_project.py. Everything else is up.</p>"
        )

    policy: dict[str, Any] = project.get("policy") or {}
    sprint: dict[str, Any] = project.get("sprint") or {}
    statuses: dict[str, int] = {}
    for task in tasks:
        key = str(task["status"])
        statuses[key] = statuses.get(key, 0) + 1
    today_actions = [a for a in actions if a.get("day") == today and a.get("status") != "failed"]
    writes = sum(1 for a in today_actions if a.get("cap_kind") != "ping")
    pings = len(today_actions) - writes

    latest_act = max(
        (t for t in tasks if t["kind"] == "act" and t["status"] == "done"),
        key=lambda t: str(t.get("created_at") or ""), default=None,
    )
    conflicts = ((latest_act or {}).get("result") or {}).get("conflicts") or []

    newest_first = sorted(actions, key=lambda a: str(a.get("created_at") or ""), reverse=True)
    window = (
        f"{sprint.get('name', '')} · {sprint.get('start', '')} → {sprint.get('end', '')}"
        if sprint else "no sprint configured"
    )
    counts = [(status, str(n)) for status, n in sorted(statuses.items())] + [
        ("writes today", f"{writes}/{policy.get('daily_write_cap', 40)}"),
        ("pings today", f"{pings}/{policy.get('daily_ping_cap', 10)}"),
    ]

    body = (
        f"<h1>{esc(project.get('name') or project.get('slug') or 'project')}</h1>"
        f"<p class='sub'>{esc(window)} · read-only console · "
        "<a href='/console/graph'>◉ Graph</a></p>"
        + _cards(counts)
        + "<h2>Decision journal</h2>"
        + _journal_html(
            journal_entries(tasks, actions, project.get("roster") or [])[:JOURNAL_LIMIT]
        )
        + "<h2>Task graph</h2>"
        + _graph_html(plan_groups(sorted(
            tasks, key=lambda t: str(t.get("created_at") or ""), reverse=True)[:GRAPH_LIMIT]))
        + "<h2>Audit log</h2>"
        + _audit_html(newest_first[:AUDIT_LIMIT])
        + "<h2>Open conflicts</h2>"
        + _conflicts_html(conflicts)
        + "<h2>Lessons</h2>"
        + _lessons_html(lessons)
        + "<h2>Corrections</h2>"
        + _corrections_html(corrections)
        + "<h2>Evals</h2>"
        + _evals_html(evals)
    )
    return _page(str(project.get("name") or "pm-agent"), body)


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{esc(title)} — pm-agent</title><style>{STYLE}</style></head>"
        f"<body><main>{body}</main></body></html>"
    )


@router.get("/console", response_class=HTMLResponse)
async def console(request: Request) -> HTMLResponse:
    """The whole state of the agent on one page. Reads only; writes nothing, ever."""
    deps: Deps = request.app.state.deps
    slug = deps.settings.default_project_slug
    project = await deps.projects.get(slug)
    if project is None:
        return HTMLResponse(render(None, [], [], [], [], None, ""))

    filters = [("project_id", "==", project["id"])]
    tasks = await deps.db.query("tasks", filters, order_by="created_at", limit=SCAN_LIMIT)
    actions = await deps.db.query("actions", filters, order_by="created_at", limit=SCAN_LIMIT)
    corrections = await deps.db.query("corrections", [], order_by="created_at", limit=50)
    lessons = (
        await deps.lessons.for_project(project["id"]) if deps.lessons is not None else []
    )
    runs = await deps.db.query("evals", [], order_by="created_at", limit=50)
    today = deps.clock.now().date().isoformat()
    return HTMLResponse(
        render(project, tasks, actions, corrections, lessons, runs[-1] if runs else None, today)
    )


@router.get("/console/graph.json")
async def graph_json(request: Request) -> dict[str, Any]:
    """The graph as data, so the page can draw it and anyone can read it. Read-only, like the
    rest of the console."""
    deps: Deps = request.app.state.deps
    project = await deps.projects.get(deps.settings.default_project_slug)
    if project is None:
        return {"nodes": [], "edges": [], "truncated": False, "project": "",
                "now": now_view([], [], deps.clock.now(), deps.settings.lease_minutes),
                "generated_at": iso_now(deps)}
    return await graph_data(project, deps)


@router.get("/console/graph", response_class=HTMLResponse)
async def graph_view(request: Request) -> HTMLResponse:
    """The knowledge graph, with a scrubber that replays how it was built."""
    deps: Deps = request.app.state.deps
    project = await deps.projects.get(deps.settings.default_project_slug)
    return HTMLResponse(graph_page(str((project or {}).get("name") or "pm-agent")))

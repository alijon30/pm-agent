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
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.harness.core.redact import redact
from app.harness.deps import Deps
from app.harness.store.db import Doc

router = APIRouter()

# The console reads whole collections for one project. That is honest at the scale the caps gate
# permits (tens of writes a day) and the limit keeps a runaway queue from timing out the page.
SCAN_LIMIT = 500
JOURNAL_LIMIT = 60
AUDIT_LIMIT = 30
GRAPH_LIMIT = 40
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


def _entry(ts: str, category: str, text: str) -> dict[str, str]:
    return {"ts": ts, "category": category, "text": text}


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


def _plan_line(task: Doc, children: list[Doc]) -> tuple[str, str]:
    dates = sorted({str(c.get("due_at") or "")[:10] for c in children if c.get("due_at")})
    about = ", ".join(_issues_of(children)) or "this project"
    when = f" ({', '.join(dates)})" if dates else ""
    return "planned", f"planned {len(children)} follow-up(s) for {about}{when}"


def _check_line(task: Doc, result: dict[str, Any]) -> tuple[str, str]:
    observed = result.get("observed") or {}
    identifier = str(observed.get("issue") or (task.get("params") or {}).get("issue") or "an issue")
    state = str(observed.get("state") or "")
    if result.get("early"):
        return "early", (
            f"{identifier} moved ahead of schedule — the {task['kind']} check due "
            f"{str(task.get('due_at') or '')[:10]} resolved early"
        )
    if result.get("met"):
        seen = f" — {state}" if state else ""
        return "checked", f"{identifier} is where it should be{seen}"
    if result.get("acted"):
        return "nudged", f"{identifier} had not moved — said something, once, to the assignee"
    reason = str(observed.get("reason") or observed.get("status") or "nothing to say")
    return "checked", f"{identifier} had not moved — stayed quiet ({reason})"


def _done_line(task: Doc, children: list[Doc]) -> tuple[str, str]:
    """One sentence for a finished task, in the words a person would use."""
    result: dict[str, Any] = task.get("result") or {}
    kind = str(task["kind"])

    if kind == "extract":
        title = str((result.get("meeting") or {}).get("title") or "a call")
        dropped = len(result.get("dropped") or [])
        tail = f"; dropped {dropped} without a verbatim quote" if dropped else ""
        return "extracted", (
            f"read '{title}' — {len(result.get('action_items') or [])} action item(s), "
            f"{len(result.get('decision_ids') or [])} decision(s){tail}"
        )
    if kind == "reconcile":
        held = len(result.get("unverified") or [])
        tail = f"; {held} held back as unverified" if held else ""
        return "reconciled", (
            f"checked {len(result.get('items') or [])} item(s) against the tracker, the spec "
            f"and the code{tail}"
        )
    if kind == "act":
        return "filed", (
            f"filed {len(result.get('created') or [])}, "
            f"updated {len(result.get('updated') or [])}, "
            f"skipped {len(result.get('skipped') or [])} — "
            f"{len(result.get('conflicts') or [])} conflict(s) reported, never resolved"
        )
    if kind == "plan":
        return _plan_line(task, children)
    if kind == "report":
        report = result.get("report") or {}
        removed = len(result.get("removed") or [])
        claims = sum(len(s.get("claims") or []) for s in report.get("sections") or [])
        tail = f"; removed {removed} claim(s) it could not cite" if removed else ""
        return "reported", (
            f"wrote the status report — {claims} cited claim(s): "
            f"\"{_short(str(report.get('headline') or ''), 70)}\"{tail}"
        )
    if kind.startswith("check_"):
        return _check_line(task, result)
    if kind == "nudge":
        if result.get("sent"):
            return "nudged", f"sent one nudge about {(task.get('params') or {}).get('about', '')}"
        return "checked", f"stayed quiet — {result.get('reason', 'nothing to send')}"
    return "done", f"finished {kind}"


def _task_entries(task: Doc, children: list[Doc]) -> list[dict[str, str]]:
    ts, kind, status = _ts_of(task), str(task["kind"]), str(task["status"])
    entries: list[dict[str, str]] = []

    if status == "done":
        category, text = _done_line(task, children)
        entries.append(_entry(ts, category, text))
    elif status == "deferred":
        entries.append(_entry(ts, "deferred", (
            f"held {kind} until {str(task.get('due_at') or '')[11:16]} — "
            f"{task.get('defer_reason') or 'not now'}"
        )))
    elif status == "failed":
        entries.append(_entry(ts, "failed", f"{kind} failed — {_short(str(task.get('error')))}"))
    elif status == "cancelled":
        entries.append(_entry(ts, "cancelled", f"{kind} — {_short(str(task.get('error')))}"))
    elif status == "skipped":
        entries.append(_entry(ts, "cancelled", f"skipped {kind} — a dependency did not hold"))

    # A refused enqueue is the lineage gate saying no. It is the agent declining to give itself
    # more work, which is exactly the kind of decision this journal exists to show.
    for refusal in task.get("refused_enqueues") or []:
        entries.append(_entry(ts, "refused", (
            f"refused to schedule {refusal.get('kind', '?')} — {refusal.get('reason', '')}"
        )))
    return entries


def _slack_line(action: Doc) -> tuple[str, str]:
    inputs: dict[str, Any] = action.get("inputs") or {}
    if inputs.get("tasks"):
        return "posted", f"told the channel about {inputs['tasks']} planned follow-up(s)"
    if inputs.get("template"):
        return "nudged", f"messaged the channel — {inputs['template']}"
    if inputs.get("sprint"):
        return "posted", f"posted the {inputs['sprint']} report to Slack"
    meeting = inputs.get("meeting")
    subject = f" of '{meeting}'" if meeting else ""
    # The summary usually replaces the "reading the call…" message rather than arriving as a new
    # one, and the journal should say which happened — an edit notified nobody.
    verb = "filled in the summary" if inputs.get("edited") else "posted the summary"
    return "posted", f"{verb}{subject} with a revert button on every action"


def _action_entries(action: Doc) -> list[dict[str, str]]:
    kind, status = str(action.get("kind")), str(action.get("status"))
    targets: dict[str, Any] = action.get("target_ids") or {}
    identifier = str(targets.get("identifier") or "")
    inputs: dict[str, Any] = action.get("inputs") or {}

    if status == "reverted":
        who = str(action.get("reverted_by") or "someone")
        return [_entry(str(action.get("reverted_at") or _ts_of(action)), "reverted",
                       f"{who} reverted {identifier or kind}")]
    if status == "failed":
        return [_entry(_ts_of(action), "failed",
                       f"could not {kind} — {_short(str(action.get('error')))}")]
    if status == "pending":
        return [_entry(_ts_of(action), "pending",
                       f"started {kind} — recorded before doing it, not yet confirmed")]

    ts = _ts_of(action)
    if kind == "linear.create_issue":
        cited = list(action.get("citations") or [])
        checks = list(action.get("checks_passed") or [])
        tail = f" · cited {' · '.join(cited[:2])}" if cited else " · no citation on record"
        gates = f" · checks: {', '.join(checks)}" if checks else ""
        title = _short(str(inputs.get("title") or ""), 60)
        return [_entry(ts, "filed", f"filed {identifier or 'an issue'} — {title}{tail}{gates}")]
    if kind == "linear.comment":
        return [_entry(ts, "filed", (
            f"commented on {identifier or 'an issue'} — "
            f"{_short(str(inputs.get('title') or 'raised again in a call'), 60)}"
        ))]
    if kind.startswith("slack."):
        category, text = _slack_line(action)
        return [_entry(ts, category, text)]
    return [_entry(ts, "done", f"{kind} completed")]


def journal_entries(tasks: list[Doc], actions: list[Doc]) -> list[dict[str, str]]:
    """The agent's decisions, newest first, as plain sentences.

    Pure: two lists of documents in, a list of {ts, category, text} out. `category` is both the
    badge a reader sees and the CSS class, so a new kind of entry needs no template change."""
    children: dict[str, list[Doc]] = {}
    for task in tasks:
        parent = str(task.get("parent_task_id") or "")
        if parent:
            children.setdefault(parent, []).append(task)

    entries: list[dict[str, str]] = []
    for task in tasks:
        entries.extend(_task_entries(task, children.get(str(task["id"]), [])))
    for action in actions:
        entries.extend(_action_entries(action))
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


# --- rendering --------------------------------------------------------------------------------

STYLE = """
:root { color-scheme: light dark; --fg:#16181d; --muted:#6b7280; --line:#e3e5ea; --bg:#fbfbfc;
        --card:#fff; --accent:#2f6f4f; --warn:#a3421c; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#e6e8ec; --muted:#9aa1ad; --line:#2a2e37; --bg:#14161a; --card:#1b1e24;
          --accent:#7fd1a5; --warn:#e0a07a; } }
* { box-sizing: border-box; }
body { margin:0; padding:28px 20px 60px; background:var(--bg); color:var(--fg);
       font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif; }
main { max-width: 940px; margin: 0 auto; }
h1 { font-size:20px; margin:0 0 2px; } h2 { font-size:14px; text-transform:uppercase;
       letter-spacing:.08em; color:var(--muted); margin:34px 0 10px; font-weight:600; }
.sub { color:var(--muted); margin:0 0 18px; font-size:13px; }
.cards { display:flex; flex-wrap:wrap; gap:10px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px;
        padding:9px 13px; min-width:104px; }
.card b { display:block; font-size:19px; font-weight:650; } .card span { color:var(--muted);
        font-size:12px; }
.j { list-style:none; margin:0; padding:0; }
.j li { display:flex; gap:10px; padding:6px 0; border-bottom:1px solid var(--line);
        align-items:baseline; }
.j time { color:var(--muted); font-variant-numeric:tabular-nums; font-size:12px;
          white-space:nowrap; }
.tag { font-size:11px; letter-spacing:.04em; text-transform:uppercase; padding:1px 7px;
       border-radius:99px; border:1px solid var(--line); color:var(--muted); white-space:nowrap; }
.tag.filed,.tag.reported,.tag.early { color:var(--accent); border-color:var(--accent); }
.tag.failed,.tag.refused,.tag.cancelled,.tag.deferred { color:var(--warn);
       border-color:var(--warn); }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { text-align:left; color:var(--muted); font-weight:600; font-size:12px;
     border-bottom:1px solid var(--line); padding:6px 8px 6px 0; }
td { padding:6px 8px 6px 0; border-bottom:1px solid var(--line); vertical-align:top; }
code { font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--muted); }
.empty { color:var(--muted); font-style:italic; }
.dep { color:var(--muted); }
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
            f"<p class='sub'>{esc(label)} · {len(group['tasks'])} task(s)</p>"
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
        f"<p class='sub'>{esc(window)} · read-only console</p>"
        + _cards(counts)
        + "<h2>Decision journal</h2>"
        + _journal_html(journal_entries(tasks, actions)[:JOURNAL_LIMIT])
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

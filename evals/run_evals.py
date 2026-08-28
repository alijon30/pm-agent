"""Run the whole pipeline against the fixture company and score it against known answers.

Two things make this reproducible for someone who is not us:

- **The world is fake, the agent is real.** Linear, Notion, GitHub and Slack are the same
  in-memory fakes the test suite uses, seeded from `fixtures/`, so anyone can run this without a
  workspace, an API key for any of them, or permission to write to a real tracker. The stages,
  the gates and the queue are the production ones, imported from `app/`.
- **The clock is fixed.** Due dates, plan horizons and quiet hours all read the clock, so a
  moving clock would make "the expected answer" a function of when you ran it. `EVAL_NOW` is a
  weekday mid-afternoon in UTC: outside quiet hours, so the run exercises the posting path.

The one thing that is genuinely live is Gemini. Everything runs on the fast tier — the free
tier allows 15 requests a minute against it and 5 against the strong tier, and one reconcile is
several tool round-trips — and `sdk_runner.retrying` waits out the 429s.

    uv run --env-file .env python evals/run_evals.py
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.agents.base.tools import make_read_tools
from app.agents.extractor import GeminiExtractor
from app.agents.planner import GeminiPlanner
from app.agents.reconciler import GeminiReconciler
from app.agents.reporter import GeminiReporter
from app.agents.triage import PassthroughTriage
from app.config import Settings
from app.harness.connectors.code import CodeSearch
from app.harness.connectors.fathom import parse_meeting, transcript_plain
from app.harness.core.clock import iso
from app.harness.deps import Deps
from app.harness.kinds.registry import KINDS, validate_params
from app.harness.stages.runner import STAGES, run_task
from app.harness.store.actions import ActionStore
from app.harness.store.corrections import CorrectionStore
from app.harness.store.decisions import DecisionStore
from app.harness.store.events import EventStore
from app.harness.store.projects import ProjectStore
from app.harness.store.tasks import TaskQueue
from app.harness.verify.ids import IdGate
from app.harness.verify.plan import check_plan
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_db import FakeDb
from tests.fakes.fake_github import FakeGitHub
from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_notion import FakeNotion
from tests.fakes.fake_slack import FakeSlack

from evals.scorers import SCORERS, Score, fabricated_identifiers

ROOT = Path(__file__).parents[1]
QUESTIONS = Path(__file__).parent / "questions.jsonl"
RESULTS = Path(__file__).parent / "results"
TRANSCRIPT = ROOT / "fixtures" / "transcripts" / "01-q3-planning.md"

# Mid-afternoon UTC on a weekday: inside the write cap, outside quiet hours, so nothing is
# deferred for a reason that has nothing to do with the agent's judgment.
EVAL_NOW = datetime(2026, 8, 28, 16, 0, tzinfo=UTC)
MEETING_ID = "8841201"

# The two spec pages the call disagrees with. Kept here rather than in Notion so the conflict
# the eval asks about is part of the fixture, not part of someone's workspace.
NOTION_PAGES = {
    "page-prd": {
        "title": "Reminders PRD",
        "url": "https://notion.so/page-prd",
        "markdown": "# Reminders\n\nThe first payment reminder is sent **5 days** after the "
                    "invoice due date. Subsequent reminders repeat weekly.",
    },
    "page-export": {
        "title": "Invoice CSV export spec",
        "url": "https://notion.so/page-export",
        "markdown": "# Invoice CSV export\n\nThe export includes one row per invoice **and the "
                    "payments applied to it**, so finance can reconcile without a second file.",
    },
}


@dataclass(frozen=True)
class Agents:
    extractor: Any
    reconciler: Any
    planner: Any
    reporter: Any


AgentsFactory = Callable[[dict[str, Any], dict[str, Any]], Agents]


# --- the fixture world ------------------------------------------------------------------------


def seed_rows() -> list[tuple[str, str, str, int | None, bool]]:
    """The seeded backlog, read from the same list that seeds the real Linear team, so the eval
    fixture and the demo workspace cannot drift apart. `fixtures/` is data rather than a package,
    so it is loaded by path instead of imported."""
    spec = importlib.util.spec_from_file_location("linear_seed", ROOT / "fixtures" /
                                                  "linear_seed.py")
    if spec is None or spec.loader is None:  # pragma: no cover — the file is in the repo
        raise RuntimeError("fixtures/linear_seed.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows: list[tuple[str, str, str, int | None, bool]] = list(module.SEED)
    return rows


def seed_issues() -> list[dict[str, Any]]:
    """The backlog as the tracker would hold it, numbered from INV-101 in seed order."""
    issues: list[dict[str, Any]] = []
    for number, (title, description, state, priority, _in_project) in enumerate(
        seed_rows(), start=101
    ):
        identifier = f"INV-{number}"
        issues.append({
            "id": f"uuid-{number}", "identifier": identifier, "title": title,
            "description": description, "state": state, "priority": priority, "assignee": None,
            "due_date": None, "url": f"https://linear.app/acme/issue/{identifier}",
            "updated_at": "2026-06-01T09:00:00+00:00",
        })
    return issues


def project_document() -> dict[str, Any]:
    project: dict[str, Any] = json.loads((ROOT / "fixtures" / "projects" / "acme.json").read_text())
    roster: list[dict[str, Any]] = json.loads((ROOT / "fixtures" / "roster.json").read_text())
    # The demo workspace's real Linear user ids are not in the repo; synthetic ones let the
    # assignment path run exactly as it does in production.
    project["roster"] = [
        {**m, "linear_user_id": f"u-{str(m['name']).split()[0].lower()}"} for m in roster
    ]
    return project


def fathom_payload() -> dict[str, Any]:
    """The rehearsal script as a Fathom webhook body — the same '**Name:** text' parse the live
    extractor test uses, so the transcript the eval scores is the one we demo."""
    segments: list[dict[str, Any]] = []
    for i, line in enumerate(TRANSCRIPT.read_text().splitlines()):
        if line.startswith("**") and ":**" in line:
            name, text = line[2:].split(":**", 1)
            segments.append({
                "speaker": {"display_name": name.strip()},
                "text": text.strip(),
                "timestamp": f"00:{i // 60:02d}:{i % 60:02d}",
            })
    return {
        "recording_id": MEETING_ID,
        "title": "Q3 Billing planning",
        "share_url": "https://fathom.video/share/eval-q3-planning",
        "recording_start_time": "2026-08-28T15:00:00+00:00",
        "transcript": segments,
        "calendar_invitees": [],
        "default_summary": {"markdown_formatted": ""},
        "action_items": [],
    }


def connectors(project: dict[str, Any]) -> dict[str, Any]:
    members = [
        {"id": m["linear_user_id"], "name": m["name"], "email": m.get("email", "")}
        for m in project["roster"]
    ]
    return {
        "linear": FakeLinear(issues=seed_issues(), members=members),
        "notion": FakeNotion(NOTION_PAGES),
        "code": CodeSearch(ROOT / "fixtures" / "acme-invoicing"),
        "github": FakeGitHub([]),
        "slack": FakeSlack(),
    }


def gemini_agents(conns: dict[str, Any], project: dict[str, Any]) -> Agents:
    """Every agent on the fast tier: the free tier's per-minute budget is the binding constraint
    on a run this size, and the retry in sdk_runner absorbs what is left."""
    settings = Settings()
    tools = make_read_tools(
        linear=conns["linear"], team_id=str(project.get("linear_team_id") or ""),
        notion=conns["notion"], code=conns["code"], roster=project["roster"],
    )
    model = settings.model_fast
    return Agents(
        extractor=GeminiExtractor(model),
        reconciler=GeminiReconciler(model, tools),
        planner=GeminiPlanner(model, tools),
        reporter=GeminiReporter(model, tools),
    )


async def build_deps(agents: Agents, conns: dict[str, Any], project: dict[str, Any]) -> Deps:
    db = FakeDb()
    clock = FakeClock(EVAL_NOW)
    projects = ProjectStore(db, default_slug="acme")
    await projects.upsert("acme", project)

    async def known_meeting(meeting_id: str) -> bool:
        rows = await db.query("events", [("provider", "==", "fathom")], limit=50)
        return any(str((r.get("payload") or {}).get("recording_id")) == meeting_id for r in rows)

    return Deps(
        settings=Settings.for_tests(default_project_slug="acme"),
        db=db, clock=clock,
        queue=TaskQueue(db, clock),
        events=EventStore(db, clock),
        projects=projects,
        decisions=DecisionStore(db, clock),
        extractor=agents.extractor,
        triage=PassthroughTriage(),
        actions=ActionStore(db, clock),
        corrections=CorrectionStore(db, clock),
        ids=IdGate(linear=conns["linear"], notion=conns["notion"], code=conns["code"],
                   roster=project["roster"], db=db, known_meeting=known_meeting),
        reconciler=agents.reconciler,
        planner=agents.planner,
        reporter=agents.reporter,
        linear=conns["linear"], notion=conns["notion"], code=conns["code"],
        slack=conns["slack"], github=conns["github"],
    )


# --- running the pipeline ---------------------------------------------------------------------


async def drain(deps: Deps, *, rounds: int = 20) -> None:
    """Run every due task until nothing is due. Checks the planner scheduled for the future stay
    where they are — this measures what one call produces, not what next week produces."""
    for _ in range(rounds):
        due = await deps.queue.due(list(STAGES), 20)
        if not due:
            return
        for task in due:
            await run_task(task, deps)


async def probe_gates(deps: Deps, project: dict[str, Any], known: str) -> dict[str, Any]:
    """Two plans the pipeline would never produce, put straight to the gate. A suite that only
    scores what the model happened to do never learns whether the refusals still work."""
    policy = project.get("policy") or {}
    assert deps.ids is not None
    common = {
        "now": EVAL_NOW, "policy": policy, "open_tasks": 0,
        "existing_ids": lambda _tid: False, "id_exists": deps.ids.exists,
    }

    def task(key: str, issue: str, depends_on: list[str]) -> dict[str, Any]:
        return {
            "key": key, "kind": "check_issue_state",
            "params": {"issue": issue, "expect": ["Done"]},
            "due": "2026-09-04T16:00:00+00:00", "reason": "probe", "depends_on": depends_on,
            "on_unmet": "none", "on_dep_failed": "skip", "context": {},
        }

    unknown = await check_plan({"tasks": [task("ghost", "INV-999", [])]}, **common)  # type: ignore[arg-type]
    cycle = await check_plan(
        {"tasks": [task("a", known, ["b"]), task("b", known, ["a"])]}, **common  # type: ignore[arg-type]
    )
    return {
        "unknown_issue": {"ok": unknown.ok, "tasks": unknown.tasks, "rejected": unknown.rejected,
                          "reasons": unknown.reasons},
        "cycle": {"ok": cycle.ok, "tasks": cycle.tasks, "rejected": cycle.rejected,
                  "reasons": cycle.reasons},
    }


async def execute(deps: Deps, project: dict[str, Any]) -> dict[str, Any]:
    """One call, end to end, then a status report — and everything the run produced, as the flat
    JSON bundle the scorers read."""
    payload = fathom_payload()
    event_id = await deps.events.record(
        provider="fathom", provider_event_id="eval-run", payload=payload, project_id="acme"
    )
    assert event_id is not None
    extract_id = await deps.queue.enqueue(
        kind="extract", project_id="acme", payload={"event_id": event_id},
        reason="Fathom call 'Q3 Billing planning' finished", root_event_id=event_id,
        policy=project.get("policy"),
    )
    assert extract_id is not None
    await drain(deps)

    await deps.queue.enqueue(
        kind="report", project_id="acme", payload={},
        params={"project": "acme", "window": "sprint"},
        reason="status report for the eval run", root_event_id=event_id,
        policy=project.get("policy"),
    )
    await drain(deps)

    tasks = await deps.db.query("tasks", [("project_id", "==", "acme")], order_by="created_at")

    def result_of(kind: str) -> dict[str, Any]:
        for task in tasks:
            if task["kind"] == kind and task["status"] == "done" and task.get("result"):
                return dict(task["result"])
        return {}

    seeded = [i["identifier"] for i in seed_issues()]
    filed = [
        str((a.get("target_ids") or {}).get("identifier"))
        for a in await deps.db.query("actions", [("project_id", "==", "acme")])
        if a.get("kind") == "linear.create_issue" and (a.get("target_ids") or {}).get("identifier")
    ]
    issues = [
        issue for issue in
        [await deps.linear.get_issue(i) for i in dict.fromkeys([*seeded, *filed])]
        if issue is not None
    ]

    return {
        "now": iso(EVAL_NOW),
        "meeting_id": MEETING_ID,
        "transcript": transcript_plain(parse_meeting(payload)),
        "policy": project.get("policy") or {},
        "roster": [m["name"] for m in project["roster"]],
        "extract": result_of("extract"),
        "reconcile": result_of("reconcile"),
        "act": result_of("act"),
        "plan": result_of("plan"),
        "report": result_of("report"),
        "decisions": await deps.db.query("decisions", [("project_id", "==", "acme")]),
        "actions": await deps.db.query("actions", [("project_id", "==", "acme")],
                                       order_by="created_at"),
        "tasks": tasks,
        # What the plan gate let through into the queue — children of a plan task, whatever
        # their kind. Every stage's children carry a plan_id, so parentage is the honest filter.
        "scheduled": [
            t for t in tasks
            if t.get("parent_task_id") in {p["id"] for p in tasks if p["kind"] == "plan"}
        ],
        "issues": issues,
        "seeded_identifiers": seeded,
        "gate": await probe_gates(deps, project, seeded[0]),
        "errors": [
            {"kind": t["kind"], "error": str(t.get("error"))}
            for t in tasks if t.get("error")
        ],
    }


# --- scoring ----------------------------------------------------------------------------------


def load_questions(path: Path = QUESTIONS) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text().splitlines() if line.strip()
    ]


def invalid_plans_materialised(run: dict[str, Any]) -> int:
    """Scheduled work the plan gate should never have let through: an unknown kind, params that
    do not validate, or a check pointed at an issue the tracker does not have."""
    known = {str(i.get("identifier")) for i in run.get("issues") or []}
    invalid = 0
    for task in run.get("scheduled") or []:
        kind = str(task.get("kind"))
        clean, error = validate_params(kind, dict(task.get("params") or {}))
        issue = str((task.get("params") or {}).get("issue") or "")
        if kind not in KINDS or error is not None or clean is None or (issue and issue not in known):
            invalid += 1
    return invalid


def headline_numbers(rows: list[dict[str, Any]], run: dict[str, Any]) -> dict[str, Any]:
    """The five numbers that go in the README, and nothing else."""
    passed = sum(1 for r in rows if r["passed"])
    claims = [
        claim
        for section in ((run.get("report") or {}).get("report") or {}).get("sections") or []
        for claim in section.get("claims") or []
    ]
    cited = sum(1 for c in claims if c.get("refs"))
    return {
        "accuracy_pct": round(100 * passed / len(rows), 1) if rows else 0.0,
        "fabricated_identifiers": len(fabricated_identifiers(run)),
        "citation_coverage_pct": round(100 * cited / len(claims), 1) if claims else 0.0,
        "invalid_plans_materialised": invalid_plans_materialised(run),
        # The correction loop needs a human pressing "wrong" on a post; one automated run cannot
        # exercise it, and reporting 0 for something never tested would be a lie.
        "corrections_recurred": "n/a",
    }


def score_all(questions: list[dict[str, Any]], run: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for question in questions:
        scorer = SCORERS.get(str(question["check"]))
        outcome = (
            scorer(question, run) if scorer is not None
            else Score(False, f"no scorer named {question['check']!r}")
        )
        rows.append({
            "id": question["id"], "kind": question["kind"], "check": question["check"],
            "question": question["input"], "passed": outcome.passed, "detail": outcome.detail,
        })
    return rows


async def run_suite(
    make_agents: AgentsFactory, questions: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """The whole suite: build the fixture world, run the pipeline through it, score it. Agents
    arrive through a factory so the tests can run this end to end without a model."""
    project = project_document()
    conns = connectors(project)
    deps = await build_deps(make_agents(conns, project), conns, project)
    run = await execute(deps, project)
    rows = score_all(questions if questions is not None else load_questions(), run)
    return {
        "created_at": iso(datetime.now(UTC)),
        "eval_now": run["now"],
        "total": len(rows),
        "passed": sum(1 for r in rows if r["passed"]),
        "headline": headline_numbers(rows, run),
        "report_claims": sum(
            len(s.get("claims") or [])
            for s in ((run.get("report") or {}).get("report") or {}).get("sections") or []
        ),
        "report_claims_removed": len((run.get("report") or {}).get("removed") or []),
        "stage_errors": run["errors"],
        "questions": rows,
    }


# --- output -----------------------------------------------------------------------------------


def render_table(outcome: dict[str, Any]) -> str:
    lines = [
        f"{'':<5} {'kind':<10} {'check':<28} {'':<4} detail",
        "-" * 100,
    ]
    for row in outcome["questions"]:
        mark = "pass" if row["passed"] else "FAIL"
        lines.append(
            f"{row['id']:<5} {row['kind']:<10} {row['check']:<28} {mark:<4} {row['detail'][:44]}"
        )
    lines.append("-" * 100)
    lines.append(f"{outcome['passed']}/{outcome['total']} questions passed")
    lines.append("")
    for key, value in outcome["headline"].items():
        lines.append(f"  {key.replace('_', ' '):<28} {value}")
    if outcome["stage_errors"]:
        lines.append("")
        lines.append("stage errors (the pipeline did not finish cleanly):")
        lines.extend(f"  {e['kind']}: {e['error'][:80]}" for e in outcome["stage_errors"])
    return "\n".join(lines)


def write_results(outcome: dict[str, Any]) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{outcome['created_at'][:10]}.json"
    path.write_text(json.dumps(outcome, indent=2, ensure_ascii=False) + "\n")
    return path


async def publish(outcome: dict[str, Any]) -> str | None:
    """Put the run where the console can read it. Only when a GCP project is configured — the
    suite must be runnable by a judge with no cloud account at all."""
    settings = Settings()
    if not settings.gcp_project:
        return None
    from app.harness.store.firestore import FirestoreDb

    db = FirestoreDb(settings.gcp_project, settings.firestore_database)
    doc_id = f"run-{outcome['created_at'][:19]}"
    await db.set("evals", doc_id, outcome)
    return doc_id


async def main() -> int:
    outcome = await run_suite(gemini_agents)
    print(render_table(outcome))
    print(f"\nwrote {write_results(outcome)}")
    published = await publish(outcome)
    print(f"published evals/{published}" if published else
          "not published: PM_GCP_PROJECT is unset, so the console keeps its previous run")
    return 0 if outcome["passed"] == outcome["total"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

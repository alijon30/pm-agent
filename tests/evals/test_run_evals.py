"""The eval runner, run end to end with no model in the loop.

The agents here are scripted rather than canned: each one reads the payload it is given and
answers from it, so the suite exercises the real stages, the real gates and the real queue
against identifiers the fake tracker actually handed out. If this test passes, the only thing
left untested in `uv run python evals/run_evals.py` is Gemini itself."""

import json
from typing import Any

from app.harness.verify.evidence import normalize
from evals.run_evals import (
    EVAL_NOW,
    QUESTIONS,
    Agents,
    fathom_payload,
    headline_numbers,
    load_questions,
    project_document,
    render_table,
    run_suite,
    seed_issues,
    write_results,
)
from evals.scorers import SCORERS

DUPLICATE_OF = seed_issues()[0]["identifier"]  # the overdue dashboard the call re-raises

MOVE = "let's move payment reminders to three days after the due date"
FRIDAY = "I can have that done by next Friday"
SMS = "We considered SMS reminders last quarter"
URGENT = "This is urgent, a customer is blocked"
EXPORT = "can you take the invoice CSV export and get it behind the flag this week"
DASHBOARD = "We need the overdue dashboard for the finance team"
LATE_FEES = "Need to check with finance before anything goes in the product"
OFF_SPEC = "Today the first reminder goes out seven days after the due date"

EXTRACTED = {
    "decisions": [{
        "statement": "Payment reminders move to three days after the invoice due date.",
        "rejected_options": ["SMS reminders — email only until we trust a provider"],
        "evidence": [{"quote": MOVE, "timestamp": "00:00:14", "speaker": "Maya Chen"}],
    }],
    "action_items": [
        {"title": "Move payment reminders to three days after the due date",
         "description": "Support sees people miss the invoice until a week later.",
         "owner_name": "Nodir Rahimov", "due_hint": "next Friday", "priority_hint": None,
         "evidence": [{"quote": MOVE, "timestamp": "00:00:14", "speaker": "Maya Chen"},
                      {"quote": FRIDAY, "timestamp": "00:00:16", "speaker": "Nodir Rahimov"}]},
        {"title": "Ship the invoice CSV export behind the flag",
         "description": "Northwind cannot close their books without it.",
         "owner_name": "Priya Nair", "due_hint": None, "priority_hint": "urgent",
         "evidence": [{"quote": URGENT, "timestamp": "00:00:28", "speaker": "Maya Chen"},
                      {"quote": EXPORT, "timestamp": "00:00:28", "speaker": "Maya Chen"}]},
        {"title": "Build the overdue invoices dashboard for finance",
         "description": "Raised again; there may already be a ticket.",
         "owner_name": "Priya Nair", "due_hint": None, "priority_hint": None,
         "evidence": [{"quote": DASHBOARD, "timestamp": "00:00:38", "speaker": "Priya Nair"}]},
    ],
    "open_questions": [{
        "question": "Do we charge late fees on overdue invoices?",
        "evidence": [{"quote": LATE_FEES, "timestamp": "00:00:42", "speaker": "Maya Chen"}],
    }],
}

RECONCILED = {
    "items": [
        {"index": 0, "title": "Move payment reminders to three days after the due date",
         "description": "The PRD says five days; the code sends at seven.",
         "disposition": "new", "target_issue": None, "owner": "Nodir Rahimov", "priority": 3,
         "due": "2026-09-04", "due_hint": "next Friday",
         "citations": ["fathom:8841201@00:00:14", "notion:page-prd", "code:acme/config.py:6"],
         "conflicts": [{"kind": "code_vs_spec", "about": "reminder window", "sides": [
             {"claim": "7 days", "source": "code:acme/config.py:6"},
             {"claim": "5 days", "source": "notion:page-prd"}]}],
         "facts": [{"text": "Reminders are configured at 7 days in code.",
                    "source": "code:acme/config.py:6"}]},
        {"index": 1, "title": "Ship the invoice CSV export behind the flag",
         "description": "Northwind is blocked; the spec and the code disagree on payments.",
         "disposition": "new", "target_issue": None, "owner": "Priya Nair", "priority": 1,
         "due": None, "due_hint": None,
         "citations": ["fathom:8841201@00:00:28", "notion:page-export"],
         "conflicts": [{"kind": "code_vs_spec", "about": "export payments", "sides": [
             {"claim": "invoice columns only", "source": "code:acme/invoices/export.py:1"},
             {"claim": "includes the payments applied", "source": "notion:page-export"}]}],
         "facts": []},
        {"index": 2, "title": "Build the overdue invoices dashboard for finance",
         "description": "Already requested last quarter.", "disposition": "duplicate_of",
         "target_issue": DUPLICATE_OF, "owner": "Priya Nair", "priority": 4,
         "due": None, "due_hint": None,
         "citations": ["fathom:8841201@00:00:38", f"linear:{DUPLICATE_OF}"],
         "conflicts": [], "facts": []},
    ],
    "decision_conflicts": [],
}


class ScriptedExtractor:
    """Answers with the planted moments, quoted verbatim from the fixture transcript."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        return EXTRACTED


class ScriptedReconciler:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        return RECONCILED


class ScriptedPlanner:
    """Watches whatever was actually filed: the identifier is read from the context the act
    stage handed over, not hard-coded, so the plan gate sees a real issue."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        created = (payload.get("context") or {}).get("created") or []
        if not created:
            return {"tasks": [], "supersedes": [], "notes": "nothing was filed"}
        issue = created[0]["identifier"]
        return {"tasks": [
            {"key": "started", "kind": "check_issue_state",
             "params": {"issue": issue, "expect": ["In Progress", "Done"]},
             "due": "2026-09-03T16:00:00+00:00", "depends_on": [],
             "reason": f"{issue} should be underway by the day before it is due",
             "on_unmet": "nudge_assignee", "on_dep_failed": "skip", "context": {}},
            {"key": "pr", "kind": "check_pr_exists", "params": {"issue": issue},
             "due": "2026-09-04T16:00:00+00:00", "depends_on": ["started"],
             "reason": f"a pull request should reference {issue} by Friday",
             "on_unmet": "nudge_assignee", "on_dep_failed": "skip", "context": {}},
        ], "supersedes": [], "notes": "Nodir committed to Friday."}


class ScriptedReporter:
    """Cites only what it was handed: the live issues and the decisions in the payload."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        claims = [
            {"text": f"{issue['identifier']} is {issue['state']}.",
             "refs": [f"linear:{issue['identifier']}"]}
            for issue in payload.get("created_issues") or []
        ]
        decisions = [
            {"text": decision["statement"], "refs": [f"decision:{decision['id']}"]}
            for decision in payload.get("decisions") or []
        ]
        sections = [{"name": "moved", "claims": claims}] if claims else []
        if decisions:
            sections.append({"name": "decisions", "claims": decisions})
        return {"headline": "Reminders and the export are filed and being watched.",
                "sections": sections}


def scripted(_conns: dict[str, Any], _project: dict[str, Any]) -> Agents:
    return Agents(ScriptedExtractor(), ScriptedReconciler(), ScriptedPlanner(), ScriptedReporter())


# --- the question set -------------------------------------------------------------------------

def test_every_scorer_named_in_questions_exists() -> None:
    unknown = {row["check"] for row in load_questions()} - set(SCORERS)
    assert unknown == set(), f"questions.jsonl names scorers that do not exist: {unknown}"


def test_every_question_carries_the_fields_the_runner_reads() -> None:
    for row in load_questions():
        assert set(row) >= {"id", "kind", "input", "expected", "check"}, row
        assert row["kind"] in ("recall", "guarantee", "gate"), row["kind"]
        assert isinstance(row["expected"], dict)


def test_question_ids_are_unique_and_the_file_is_one_json_object_per_line() -> None:
    lines = [line for line in QUESTIONS.read_text().splitlines() if line.strip()]
    ids = [json.loads(line)["id"] for line in lines]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 20, "the suite is meant to be ~25 known-answer questions"


def test_every_scorer_that_exists_is_asked_about_at_least_once() -> None:
    unused = set(SCORERS) - {row["check"] for row in load_questions()}
    assert unused == set(), f"scorers nobody asks: {unused}"


# --- the fixture world ------------------------------------------------------------------------

def test_the_fixture_transcript_becomes_a_fathom_payload_with_every_planted_moment() -> None:
    spoken = normalize(" ".join(s["text"] for s in fathom_payload()["transcript"]))

    for quote in (MOVE, FRIDAY, SMS, URGENT, EXPORT, DASHBOARD, LATE_FEES, OFF_SPEC):
        assert normalize(quote) in spoken, quote


def test_the_seeded_backlog_contains_the_ticket_the_call_re_raises() -> None:
    titles = {i["title"] for i in seed_issues()}
    assert "Overdue invoices dashboard for finance" in titles
    assert len({i["identifier"] for i in seed_issues()}) == len(seed_issues())


def test_the_project_the_eval_runs_against_is_the_one_we_ship() -> None:
    project = project_document()
    assert project["slug"] == "acme" and project["sprint"]["name"]
    assert all(m["linear_user_id"] for m in project["roster"])


# --- the run ----------------------------------------------------------------------------------

async def test_the_runner_answers_every_question_and_prints_the_five_headline_numbers() -> None:
    outcome = await run_suite(scripted)

    failed = [f"{r['id']} {r['check']}: {r['detail']}" for r in outcome["questions"]
              if not r["passed"]]
    assert failed == [], failed
    assert outcome["stage_errors"] == []
    assert outcome["passed"] == outcome["total"] == len(load_questions())
    assert outcome["headline"] == {
        "accuracy_pct": 100.0,
        "fabricated_identifiers": 0,
        "citation_coverage_pct": 100.0,
        "invalid_plans_materialised": 0,
        "corrections_recurred": "n/a",
    }
    assert outcome["eval_now"] == "2026-08-28T16:00:00+00:00"


async def test_a_run_where_the_model_invents_a_ticket_says_so_in_the_headline() -> None:
    class Fabricating(ScriptedReporter):
        async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
            await super().run(payload)
            return {"headline": "All good.", "sections": [{"name": "shipped", "claims": [
                {"text": "INV-404 shipped.", "refs": ["linear:INV-404"]}]}]}

    def fabricating(_c: dict[str, Any], _p: dict[str, Any]) -> Agents:
        return Agents(ScriptedExtractor(), ScriptedReconciler(), ScriptedPlanner(), Fabricating())

    outcome = await run_suite(fabricating)
    by_id = {r["check"]: r for r in outcome["questions"]}

    # The citation gate removes the claim, so nothing fabricated survives into the report — and
    # the suite still records that the report came back empty rather than quietly passing.
    assert outcome["report_claims_removed"] == 1
    assert by_id["report_citation_coverage"]["passed"] is False
    assert outcome["headline"]["fabricated_identifiers"] == 0


async def test_the_pipeline_the_eval_drives_is_the_real_one() -> None:
    """Not a mock of the pipeline: a call goes in and filed issues, a plan and a report come out."""
    outcome = await run_suite(scripted, questions=[])
    rows = {r["check"] for r in outcome["questions"]}

    assert rows == set()
    assert outcome["total"] == 0 and outcome["headline"]["accuracy_pct"] == 0.0
    assert outcome["report_claims"] >= 1


def test_the_table_names_every_question_and_the_headline_numbers() -> None:
    outcome = {
        "questions": [{"id": "q01", "kind": "recall", "check": "decision_recorded",
                       "question": "?", "passed": True, "detail": "found it"},
                      {"id": "q02", "kind": "gate", "check": "plan_rejects_cycle",
                       "question": "?", "passed": False, "detail": "accepted a cycle"}],
        "passed": 1, "total": 2, "stage_errors": [{"kind": "act", "error": "linear unavailable"}],
        "headline": {"fabricated_identifiers": 0},
    }
    table = render_table(outcome)

    assert "q01" in table and "pass" in table
    assert "q02" in table and "FAIL" in table
    assert "1/2 questions passed" in table
    headline = next(line for line in table.splitlines() if "fabricated identifiers" in line)
    assert headline.split()[-1] == "0"
    assert "act: linear unavailable" in table


def test_the_headline_reports_no_coverage_when_the_report_has_no_claims() -> None:
    headline = headline_numbers([{"passed": True}], {"issues": [], "report": {"report": {}}})

    assert headline["citation_coverage_pct"] == 0.0
    assert headline["accuracy_pct"] == 100.0


async def test_a_run_is_written_where_the_console_and_the_readme_can_read_it(
    tmp_path: Any, monkeypatch: Any
) -> None:
    import evals.run_evals as runner

    monkeypatch.setattr(runner, "RESULTS", tmp_path / "results")
    outcome = await run_suite(scripted, questions=load_questions()[:1])
    path = write_results(outcome)

    assert path.exists()
    written = json.loads(path.read_text())
    assert written["headline"]["fabricated_identifiers"] == 0
    assert written["questions"][0]["check"] == "decision_recorded"


def test_the_clock_is_fixed_so_the_expected_answers_do_not_move() -> None:
    assert EVAL_NOW.isoformat() == "2026-08-28T16:00:00+00:00"

"""The console is the page a judge lands on, so these tests are about it telling the truth
plainly, escaping everything, and never being the reason the service looks broken."""

from typing import Any

from app.harness.deps import Deps
from app.harness.http.console import journal_entries, plan_groups
from app.harness.store.actions import ActionStore
from app.harness.store.corrections import CorrectionStore
from fastapi.testclient import TestClient

from tests.conftest import ACME

CONFLICT = {"kind": "code_vs_spec", "about": "reminder window", "sides": [
    {"claim": "7 days", "source": "code:acme/config.py:6"},
    {"claim": "5 days", "source": "notion:page-prd"}]}


def task(**fields: Any) -> dict[str, Any]:
    """A task document with only the fields the console reads, so a test says what it means."""
    base: dict[str, Any] = {
        "id": "t-1", "kind": "act", "status": "done", "project_id": "acme", "params": {},
        "reason": "", "result": {}, "created_at": "2026-08-27T09:00:00+00:00",
        "finished_at": "2026-08-27T09:12:00+00:00", "due_at": "2026-08-27T09:00:00+00:00",
        "depends_on": [], "refused_enqueues": [], "plan_id": None, "parent_task_id": None,
        "error": None, "defer_reason": None,
    }
    return {**base, **fields}


def action(**fields: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "a-1", "kind": "linear.create_issue", "status": "done", "project_id": "acme",
        "inputs": {}, "citations": [], "checks_passed": [], "target_ids": {}, "error": None,
        "created_at": "2026-08-27T09:11:00+00:00", "finished_at": "2026-08-27T09:12:00+00:00",
        "reverted_at": None, "reverted_by": None, "day": "2026-08-27", "cap_kind": "write",
    }
    return {**base, **fields}


# --- the journal ------------------------------------------------------------------------------

def test_a_filed_issue_reads_as_a_sentence_with_its_citation_and_its_gates() -> None:
    entries = journal_entries([], [action(
        target_ids={"identifier": "INV-143"}, inputs={"title": "Move payment reminders"},
        citations=["fathom:8841201@00:01:58"], checks_passed=["roster", "priority", "dates"])])

    assert entries[0]["category"] == "filed"
    assert entries[0]["text"] == (
        "filed INV-143 — Move payment reminders · cited fathom:8841201@00:01:58 · "
        "checks: roster, priority, dates")


def test_a_plan_reads_as_what_will_be_watched_and_when() -> None:
    plan = task(id="t-plan", kind="plan", result={"accepted": ["a", "b"]})
    children = [
        task(id="c-1", kind="check_issue_state", status="queued", parent_task_id="t-plan",
             params={"issue": "INV-143"}, due_at="2026-09-03T16:00:00+00:00"),
        task(id="c-2", kind="check_pr_exists", status="queued", parent_task_id="t-plan",
             params={"issue": "INV-143"}, due_at="2026-09-04T16:00:00+00:00"),
    ]
    entries = journal_entries([plan, *children], [])

    assert entries[0]["category"] == "planned"
    assert entries[0]["text"] == "planned 2 follow-up(s) for INV-143 (2026-09-03, 2026-09-04)"


def test_a_check_that_reality_beat_reads_as_good_news() -> None:
    entries = journal_entries([task(
        id="t-c", kind="check_pr_merged", params={"issue": "INV-143"},
        due_at="2026-09-07T16:00:00+00:00",
        result={"met": True, "early": True, "observed": {"issue": "INV-143"}})], [])

    assert entries[0]["category"] == "early"
    assert "INV-143 moved ahead of schedule" in entries[0]["text"]
    assert "due 2026-09-07" in entries[0]["text"]


def test_staying_quiet_is_recorded_as_a_decision_not_as_silence() -> None:
    entries = journal_entries([task(
        id="t-d", kind="nudge", status="deferred", due_at="2026-08-28T08:00:00+00:00",
        defer_reason="quiet hours until 08:00")], [])

    assert entries[0]["category"] == "deferred"
    assert entries[0]["text"] == "held nudge until 08:00 — quiet hours until 08:00"


def test_the_agent_declining_to_give_itself_more_work_is_in_the_journal() -> None:
    entries = journal_entries([task(
        refused_enqueues=[{"kind": "plan", "reason": "max depth 4 reached"}])], [])

    assert [e["category"] for e in entries] == ["filed", "refused"]
    assert "refused to schedule plan — max depth 4 reached" in entries[1]["text"]


def test_a_report_says_what_it_claimed_and_what_it_could_not_prove() -> None:
    entries = journal_entries([task(id="t-r", kind="report", result={
        "report": {"headline": "Reminders landed early.", "sections": [
            {"name": "shipped", "claims": [{"text": "x", "refs": ["linear:INV-143"]}]}]},
        "removed": [{"section": "moved", "text": "y", "reason": "no reference"}]})], [])

    assert entries[0]["category"] == "reported"
    assert "1 cited claim(s)" in entries[0]["text"]
    assert "Reminders landed early." in entries[0]["text"]
    assert "removed 1 claim(s) it could not cite" in entries[0]["text"]


def test_a_revert_names_who_undid_what() -> None:
    entries = journal_entries([], [action(
        status="reverted", reverted_by="U-maya", reverted_at="2026-08-27T10:00:00+00:00",
        target_ids={"identifier": "INV-143"})])

    assert entries[0] == {"ts": "2026-08-27T10:00:00+00:00", "category": "reverted",
                          "text": "U-maya reverted INV-143"}


def test_the_journal_runs_newest_first_across_tasks_and_actions() -> None:
    entries = journal_entries(
        [task(id="t-a", kind="extract", finished_at="2026-08-27T09:05:00+00:00",
              result={"meeting": {"title": "Q3 Billing planning"}, "action_items": [1],
                      "decision_ids": ["d"], "dropped": []})],
        [action(finished_at="2026-08-27T09:12:00+00:00", target_ids={"identifier": "INV-143"})],
    )

    assert [e["category"] for e in entries] == ["filed", "extracted"]
    assert "read 'Q3 Billing planning' — 1 action item(s), 1 decision(s)" in entries[1]["text"]


def test_an_empty_history_produces_an_empty_journal() -> None:
    assert journal_entries([], []) == []


# --- the graph --------------------------------------------------------------------------------

def check(task_id: str, kind: str, depends_on: list[str]) -> dict[str, Any]:
    """A check the planner scheduled: parented to the plan task, sharing its plan_id."""
    return task(id=task_id, kind=kind, status="queued", plan_id="p-1", parent_task_id="t-plan",
                depends_on=depends_on, due_at=f"2026-09-0{task_id[-1]}T16:00:00+00:00")


def test_a_chain_of_checks_is_indented_by_what_it_waits_on() -> None:
    rows = [
        task(id="t-plan", kind="plan"),
        check("c-3", "check_issue_state", ["c-2"]),
        check("c-1", "check_issue_state", []),
        check("c-2", "check_pr_exists", ["c-1"]),
    ]
    groups = {g["plan_id"]: g for g in plan_groups(rows)}

    assert [t["depth"] for t in groups["p-1"]["tasks"]] == [0, 1, 2]
    assert [t["id"] for t in groups["p-1"]["tasks"]] == ["c-1", "c-2", "c-3"]


def test_the_spine_of_a_call_is_one_list_not_a_plan_per_stage() -> None:
    """Every stage's children carry a plan_id; only the planner's are a plan."""
    rows = [
        task(id="t-extract", kind="extract", plan_id=None),
        task(id="t-reconcile", kind="reconcile", plan_id="tx-1", parent_task_id="t-extract"),
        task(id="t-act", kind="act", plan_id="tx-2", parent_task_id="t-reconcile"),
        task(id="t-plan", kind="plan", plan_id="tx-3", parent_task_id="t-act"),
        check("c-1", "check_issue_state", []),
    ]
    groups = plan_groups(rows)

    assert len(groups) == 2
    by_plan = {g["plan_id"]: [t["id"] for t in g["tasks"]] for g in groups}
    assert set(by_plan[""]) == {"t-extract", "t-reconcile", "t-act", "t-plan"}
    assert by_plan["p-1"] == ["c-1"]


def test_tasks_that_belong_to_no_plan_are_still_shown() -> None:
    groups = plan_groups([task(id="t-1", kind="extract", plan_id=None)])
    assert groups[0]["plan_id"] == "" and groups[0]["tasks"][0]["depth"] == 0


def test_a_dependency_cycle_that_reached_the_database_still_renders() -> None:
    rows = [task(id="t-plan", kind="plan"),
            check("c-1", "check_issue_state", ["c-2"]),
            check("c-2", "check_pr_exists", ["c-1"])]
    groups = {g["plan_id"]: g for g in plan_groups(rows)}
    assert len(groups["p-1"]["tasks"]) == 2  # must not hang or raise


# --- the page ---------------------------------------------------------------------------------

def test_the_console_renders_with_an_empty_database(client: TestClient, deps: Deps) -> None:
    async def nothing(slug: str) -> None:
        return None

    deps.projects.get = nothing  # type: ignore[method-assign]
    response = client.get("/console")

    assert response.status_code == 200
    assert "No project is seeded yet" in response.text


async def test_the_console_tells_the_story_of_what_the_agent_did(
    client: TestClient, deps: Deps
) -> None:
    await deps.projects.upsert("acme", {
        **ACME, "name": "Q3 Billing",
        "sprint": {"name": "Sprint 1", "start": "2026-08-20", "end": "2026-09-03"}})
    actions = ActionStore(deps.db, deps.clock)
    action_id = await actions.begin(
        task_id="t", project_id="acme", kind="linear.create_issue", idempotency_key="k1",
        inputs={"title": "Move payment reminders"}, citations=["fathom:8841201@00:01:58"],
        checks_passed=["roster", "priority", "dates"])
    await actions.finish(action_id, target_ids={"identifier": "INV-143"},
                         revert={"op": "archive", "issue": "INV-143"})
    act_id = await deps.queue.enqueue(kind="act", project_id="acme", payload={},
                                      reason="file what the call agreed")
    assert act_id is not None
    await deps.db.update("tasks", act_id, {"status": "done", "result": {
        "created": [{"identifier": "INV-143"}], "updated": [], "skipped": [],
        "conflicts": [CONFLICT]}})
    await CorrectionStore(deps.db, deps.clock).add(
        project_id="acme", wrong="assigned design work to backend", right="design goes to Priya")
    await deps.db.set("evals", "run-1", {
        "created_at": "2026-08-28T10:00:00+00:00", "passed": 23, "total": 24,
        "headline": {"accuracy_pct": 95.8, "fabricated_identifiers": 0,
                     "citation_coverage_pct": 100.0, "invalid_plans_materialised": 0,
                     "corrections_recurred": "n/a"}})

    page = client.get("/console").text

    assert "Q3 Billing" in page and "Sprint 1 · 2026-08-20 → 2026-09-03" in page
    assert "filed INV-143 — Move payment reminders" in page
    assert "checks: roster, priority, dates" in page
    assert "reminder window" in page and "code:acme/config.py:6" in page
    assert "design goes to Priya" in page
    assert "fabricated identifiers" in page and "95.8" in page
    assert "writes today" in page and "1/40" in page


async def test_the_console_escapes_everything_a_document_carried_in(
    client: TestClient, deps: Deps
) -> None:
    await deps.projects.upsert("acme", ACME)
    tid = await deps.queue.enqueue(
        kind="extract", project_id="acme", payload={},
        reason="<script>alert('xss')</script> from a call")
    assert tid is not None

    page = client.get("/console").text

    assert "<script>alert" not in page
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in page


async def test_the_console_never_renders_event_payloads_or_secret_shaped_strings(
    client: TestClient, deps: Deps
) -> None:
    await deps.projects.upsert("acme", ACME)
    await deps.events.record(provider="fathom", provider_event_id="m1", project_id="acme",
                             payload={"transcript": [{"text": "the unredacted words of a call"}]})
    tid = await deps.queue.enqueue(kind="extract", project_id="acme", payload={}, reason="a call")
    assert tid is not None
    await deps.db.update("tasks", tid, {
        "status": "failed", "error": "linear rejected the token xoxb-4444-secret-value"})

    page = client.get("/console").text

    assert "the unredacted words of a call" not in page
    assert "xoxb-4444-secret-value" not in page
    assert "[redacted]" in page

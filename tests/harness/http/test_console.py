"""The console is the page a judge lands on, so these tests are about it telling the truth
plainly, escaping everything, and never being the reason the service looks broken."""

import re
from typing import Any

from app.harness.deps import Deps
from app.harness.http.console import STYLE, journal_entries, plan_groups
from app.harness.http.graph_assets import GRAPH_SCRIPT, GRAPH_STYLE
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

def test_a_filed_issue_reads_as_a_sentence_with_its_owner_and_its_citation() -> None:
    entries = journal_entries([], [action(
        target_ids={"identifier": "INV-143"},
        inputs={"title": "Move payment reminders", "owner": "Nodir Rahimov"},
        citations=["fathom:8841201@00:01:58"], checks_passed=["roster", "priority", "dates"])],
        [{"name": "Nodir Rahimov", "slack_id": "U-nodir"}])

    assert entries[0]["category"] == "filed"
    assert entries[0]["text"] == (
        "filed INV-143 (the payment reminders), assigned to Nodir, and cited call @ 01:58")
    assert "fathom:" not in entries[0]["text"], "a citation is shown the way a person reads it"


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
    assert entries[0]["text"] == "lined up two checks on INV-143 (Sep 3, Sep 4)"


def test_a_check_that_reality_beat_reads_as_good_news() -> None:
    entries = journal_entries([task(
        id="t-c", kind="check_pr_merged", params={"issue": "INV-143"},
        due_at="2026-09-07T16:00:00+00:00",
        result={"met": True, "early": True, "observed": {"issue": "INV-143"}})], [])

    assert entries[0]["category"] == "early"
    assert "INV-143 moved ahead of schedule" in entries[0]["text"]
    assert "due Sep 7" in entries[0]["text"]


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
    assert "one cited claim" in entries[0]["text"]
    assert "Reminders landed early." in entries[0]["text"]
    assert "dropped one claim it couldn't cite" in entries[0]["text"]


def test_the_journal_says_whether_the_summary_was_posted_or_filled_in() -> None:
    edited = journal_entries([], [action(
        kind="slack.post", inputs={"meeting": "Q3 Billing planning", "edited": True})])
    fresh = journal_entries([], [action(
        kind="slack.post", inputs={"meeting": "Q3 Billing planning", "edited": False})])

    assert edited[0]["text"].startswith("filled in the call summary for 'Q3 Billing planning'")
    assert fresh[0]["text"].startswith("posted the call summary for 'Q3 Billing planning'")


def test_a_revert_names_who_undid_what() -> None:
    entries = journal_entries([], [action(
        status="reverted", reverted_by="U-maya", reverted_at="2026-08-27T10:00:00+00:00",
        target_ids={"identifier": "INV-143"})])

    assert entries[0]["ts"] == "2026-08-27T10:00:00+00:00"
    assert entries[0]["category"] == "reverted"
    assert entries[0]["text"] == "U-maya reverted INV-143"
    assert "issue:INV-143" in entries[0]["refs"], "the graph attributes this line by its refs"


def test_the_journal_runs_newest_first_across_tasks_and_actions() -> None:
    entries = journal_entries(
        [task(id="t-a", kind="extract", finished_at="2026-08-27T09:05:00+00:00",
              result={"meeting": {"title": "Q3 Billing planning"}, "action_items": [1],
                      "decision_ids": ["d"], "dropped": []})],
        [action(finished_at="2026-08-27T09:12:00+00:00", target_ids={"identifier": "INV-143"})],
    )

    assert [e["category"] for e in entries] == ["filed", "extracted"]
    assert "read 'Q3 Billing planning' — one action item and one decision" in entries[1]["text"]


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

    assert "Q3 Billing" in page and "of Sprint 1" in page
    assert "filed INV-143 (the payment reminders)" in page
    assert "cited call @ 01:58" in page
    assert "reminder window" in page and "code:acme/config.py:6" in page
    assert "design goes to Priya" in page
    assert "fabricated identifiers" in page and "95.8" in page
    assert "Writes today" in page and "1 / 40" in page


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


async def test_the_console_shows_what_the_agent_learned_and_what_from(
    client: TestClient, deps: Deps
) -> None:
    from app.harness.store.lessons import LessonStore

    await deps.projects.upsert("acme", ACME)
    deps.lessons = LessonStore(deps.db, deps.clock)
    await deps.lessons.add(
        project_id="acme", text="Give a pull request a full working day before asking about it.",
        evidence=["task:t-abc", "action:a-def"], source_task_id="review-1")

    page = client.get("/console").text

    assert "Lessons" in page
    assert "Give a pull request a full working day before asking about it." in page
    assert "task:t-abc" in page and "action:a-def" in page


def test_a_console_with_no_lesson_store_still_renders(client: TestClient, deps: Deps) -> None:
    page = client.get("/console").text
    assert "has not drawn any lessons" in page


async def test_a_lesson_containing_markup_is_escaped_like_everything_else(
    client: TestClient, deps: Deps
) -> None:
    from app.harness.store.lessons import LessonStore

    await deps.projects.upsert("acme", ACME)
    deps.lessons = LessonStore(deps.db, deps.clock)
    await deps.lessons.add(project_id="acme", text="<img onerror=alert(1)>", evidence=["task:1"])

    page = client.get("/console").text
    assert "<img onerror" not in page and "&lt;img onerror" in page


def test_every_journal_line_says_which_documents_it_came_from() -> None:
    """The graph attributes a line to a node by set membership rather than by re-deriving the
    sentence, so a line with no refs would be a line no node could ever claim."""
    entries = journal_entries(
        [task(id="t-1", kind="check_pr_exists", params={"issue": "INV-143"},
              result={"met": False, "observed": {"issue": "INV-143"}})],
        [action(target_ids={"identifier": "INV-143"}, task_id="t-1",
                inputs={"title": "Move reminders", "owner": "Nodir Rahimov"})],
    )

    assert all(e["refs"] for e in entries)
    filed = next(e for e in entries if e["category"] == "filed")
    assert set(filed["refs"]) >= {"issue:INV-143", "person:Nodir Rahimov", "task:t-1"}
    checked = next(e for e in entries if e["category"] == "checked")
    assert set(checked["refs"]) == {"task:t-1", "issue:INV-143"}


def test_a_plan_line_belongs_to_the_issues_it_scheduled_work_about() -> None:
    plan = task(id="t-plan", kind="plan")
    child = task(id="c-1", kind="check_issue_state", status="queued", parent_task_id="t-plan",
                 params={"issue": "INV-143"}, due_at="2026-09-03T16:00:00+00:00")
    entries = journal_entries([plan, child], [])

    planned = next(e for e in entries if e["category"] == "planned")
    assert "issue:INV-143" in planned["refs"]


# --- the console and the graph are one surface -------------------------------------------------

# Which family each status belongs to. The console tints a chip's background at 15% and
# lightens the text for contrast, so the two pages share the meaning rather than the hex.
FAMILIES = {
    "5e6ad2": "indigo", "8b95e8": "indigo",
    "4cb782": "green", "f2c94c": "yellow", "eb5757": "red", "8a8f98": "grey",
}
# The console reaches its colours through tokens and tints, so a family has several spellings.
SPELLINGS = {
    "indigo": ("5e6ad2", "8b95e8", "94,106,210", "--accent", "--done"),
    "green": ("4cb782", "76,183,130", "--spark"),
    "yellow": ("f2c94c", "242,201,76", "--progress"),
    "red": ("eb5757", "235,87,87", "--failed"),
    "grey": ("8a8f98", "138,143,152", "--muted"),
}


def _graph_tints() -> dict[str, str]:
    """CATEGORY_TINT as the graph's script declares it, resolved to a colour family."""
    block = re.search(r"const CATEGORY_TINT = \{(.+?)\};", GRAPH_SCRIPT, re.S)
    assert block is not None
    names = {"DONE": "#5e6ad2", "SPARK": "#4cb782", "PROGRESS": "#f2c94c",
             "FAILED": "#eb5757", "MUTED": "#8a8f98"}
    found: dict[str, str] = {}
    for key, value in re.findall(r"(\w+):\s*(\"#[0-9a-f]{6}\"|[A-Z]+)", block.group(1)):
        found[key] = FAMILIES[names.get(value, value.strip('"')).lstrip("#")]
    return found


def _console_family(category: str) -> str:
    rule = re.search(rf"\.tag\.{category}\b[^{{]*\{{([^}}]+)\}}", STYLE)
    used = rule.group(1) if rule else STYLE[STYLE.index(".tag {"):]
    for family, spellings in SPELLINGS.items():
        if any(word in used for word in spellings):
            return family
    return "grey"


def test_a_category_means_the_same_thing_on_the_console_as_on_the_graph() -> None:
    """The two pages show the same journal. A judge clicking between them must not have to
    relearn what green means — and on this palette green means exactly one thing."""
    for category, family in _graph_tints().items():
        assert _console_family(category) == family, (
            f"{category} is {family} on the graph and {_console_family(category)} here"
        )


def test_every_category_the_journal_emits_has_a_chip_colour() -> None:
    for category in _graph_tints():
        assert f".tag.{category}" in STYLE, f"no chip style for {category}"


def test_green_means_one_thing_across_the_product() -> None:
    """Done is indigo, like Linear's. Green is reserved for work that came back early, so a
    reviewer who sees green anywhere knows what it is without a legend."""
    assert _console_family("early") == "green"
    assert _console_family("filed") == "indigo"
    assert _graph_tints()["early"] == "green"
    assert _graph_tints()["filed"] == "indigo"


def test_the_console_wears_the_same_palette_as_the_graph() -> None:
    """Clicking between the two pages should feel like two views of one tracker."""
    for token in ("--bg:#08090a", "--surface:#141516", "--border:#1f2023", "--text:#f7f8f8",
                  "--muted:#8a8f98", "--accent:#5e6ad2", "--faint:#5c5f66"):
        assert token in STYLE, f"the console is missing {token}"
        assert token in GRAPH_STYLE, f"the graph is missing {token}"


def test_the_console_page_still_asks_the_network_for_nothing(client: TestClient) -> None:
    body = client.get("/console").text

    assert "http://" not in body.replace("http://www.w3.org", "")
    assert "<script src" not in body, "inline is fine; fetching is not"
    assert "@import" not in body


# --- the dashboard ------------------------------------------------------------------------------

def test_the_console_wears_the_graphs_toolbar(client: TestClient) -> None:
    """One product, two views. The bar, the status line and the avatars are the same."""
    page = client.get("/console").text

    for element_id in ("top", "title", "nav", "status", "tools", "avatars"):
        assert f"id='{element_id}'" in page
    assert "class='on'" in page, "the current view is marked in the segmented control"
    assert ">Graph</a>" in page and ">Console</a>" in page


def test_the_dashboard_groups_its_numbers_under_what_they_answer(client: TestClient) -> None:
    page = client.get("/console").text

    for header in ("This sprint", "How it works", "Trust"):
        assert f">{header}</h2>" in page
    for piece in (".tiles", ".tile", ".t-label", ".t-value", ".t-note"):
        assert piece in page, f"the dashboard needs {piece}"


def test_a_dashboard_tile_may_say_zero(client: TestClient) -> None:
    """The journal must never print a zero; a tile reporting no calls this sprint is simply
    telling the truth."""
    page = client.get("/console").text

    assert "Calls heard" in page
    assert "Citation coverage" in page and "References verified" in page


def test_the_console_page_asks_the_network_for_nothing_still(client: TestClient) -> None:
    body = client.get("/console").text

    assert "<script src" not in body, "inline is fine; fetching is not"
    assert "@import" not in body
    assert "http://" not in body.replace("http://www.w3.org", "")


def test_the_journal_writes_a_time_the_team_recognises() -> None:
    """A standup posted at 9am in California read as 16:00 while this wrote UTC, which makes
    a correctly-timed agent look mistimed."""
    from zoneinfo import ZoneInfo

    from app.harness.core.clock import stamp_local

    assert stamp_local("2026-08-29T16:00:00+00:00", ZoneInfo("America/Los_Angeles")) == (
        "Aug 29 09:00")
    from app.harness.http.console import _journal_html

    row = _journal_html(
        [{"ts": "2026-08-29T16:00:00+00:00", "category": "posted",
          "text": "posted the morning standup"}],
        ZoneInfo("America/Los_Angeles"),
    )

    assert ">Aug 29 09:00</time>" in row
    assert "title='2026-08-29T16:00:00+00:00'" in row, "the exact moment is one hover away"


def test_the_act_summary_does_not_repeat_the_lines_beneath_it() -> None:
    """Every ticket gets its own line directly underneath; naming them twice reads like a
    stutter."""
    from app.harness.http.console import _act_line

    assert _act_line({"created": [{"identifier": "INV-32"}]}, "PDF incident huddle") == (
        "filed", "filed one ticket from 'PDF incident huddle'")
    assert _act_line(
        {"created": [{}] * 5, "updated": [{}]}, "Sprint 1 kickoff sync",
    ) == ("filed", "filed five tickets and updated one issue from 'Sprint 1 kickoff sync'")
    assert _act_line({}, "PDF incident huddle") == (
        "filed", "read 'PDF incident huddle' and found nothing new to file")
    assert "INV-" not in _act_line({"created": [{"identifier": "INV-32"}]}, "a call")[1]
    # The call is named against what was filed. Tacked onto the end it says the wrong thing:
    # "flagged two disagreements for a human from 'Q3 planning'".
    assert _act_line({"created": [{}], "conflicts": [{}, {}]}, "Q3 planning")[1] == (
        "filed one ticket from 'Q3 planning' and flagged two disagreements for a human")


# --- the company brain --------------------------------------------------------------------------

def test_the_brain_is_a_section_a_reviewer_can_read(client: TestClient) -> None:
    page = client.get("/console").text

    assert ">Brain</h2>" in page
    assert "tell the agent something in Slack" in page, "and says how to fill it"


def test_a_retired_rule_stays_on_the_page_struck_through() -> None:
    """The useful question about an ownership rule is often "since when", and a page that
    silently rewrites itself cannot answer it."""
    from zoneinfo import ZoneInfo

    from app.harness.http.console import _brain_html

    html = _brain_html([{
        "slug": "ownership", "kind": "ownership", "title": "Ownership", "entries": [
            {"id": "a", "text": "Billing goes to Nodir", "person": "Nodir Rahimov",
             "said_by": "Maya Chen", "source": "slack:C1:1",
             "created_at": "2026-08-28T17:00:00+00:00",
             "retired_at": "2026-08-30T17:00:00+00:00"},
            {"id": "b", "text": "Billing goes to Priya", "person": "Priya Nair",
             "said_by": "Maya Chen", "source": "slack:C1:2",
             "created_at": "2026-08-30T17:00:00+00:00", "retired_at": None},
        ]}], ZoneInfo("America/Los_Angeles"))

    assert "class='retired'" in html
    assert "Billing goes to Nodir" in html, "history is kept"
    assert html.index("Billing goes to Priya") < html.index("Billing goes to Nodir")

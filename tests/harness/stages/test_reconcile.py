"""reconcile turns a call's action items into verified proposals — or into honest gaps."""

import json
from pathlib import Path
from typing import Any

from app.harness.connectors.code import CodeSearch
from app.harness.core.errors import SourceUnavailable
from app.harness.deps import Deps
from app.harness.stages.reconcile import (
    call_citation,
    is_open,
    item_refs,
    run,
    search_words,
    with_call_citation,
)
from app.harness.store.wiki import WikiStore
from app.harness.verify.ids import IdGate

from tests.conftest import ACME
from tests.fakes.fake_agents import FakeReconciler
from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_notion import FakeNotion

REPO = Path(__file__).parents[3] / "fixtures" / "acme-invoicing"
SAMPLE = json.loads(
    (Path(__file__).parents[2] / "fixtures" / "fathom_webhook_sample.json").read_text()
)

EXTRACTED = {
    "meeting": {"id": "8841201", "title": "Q3 Billing planning", "url": "https://f.video/abc"},
    "action_items": [
        {"title": "Move payment reminders to 3 days", "owner_name": "Nodir Rahimov",
         "due_hint": "next Friday",
         "evidence": [{"quote": "I can have that done by next Friday", "timestamp": "00:01:58",
                       "speaker": "Nodir Rahimov"}]},
    ],
    "open_questions": [],
    "decision_ids": [],
    "dropped": [],
    "bounced": False,
}

GOOD_ITEM = {
    "index": 0,
    "title": "Move payment reminders to 3 days",
    "description": "Decided in the Q3 planning call.",
    "disposition": "new",
    "target_issue": None,
    "owner": "Nodir Rahimov",
    "priority": 3,
    "due": "2026-09-04",
    "due_hint": "next Friday",
    "citations": ["fathom:8841201@00:01:58", "code:acme/config.py:6"],
    "conflicts": [{"kind": "code_vs_spec", "about": "reminder window", "sides": [
        {"claim": "7 days", "source": "code:acme/config.py:6"},
        {"claim": "5 days", "source": "notion:page-prd"}]}],
    "facts": [{"text": "Reminders are sent 7 days after due.", "source": "code:acme/config.py:6"}],
}
FABRICATED_ITEM = {**GOOD_ITEM, "citations": ["linear:INV-999"], "conflicts": [], "facts": []}
GOOD = {"items": [GOOD_ITEM], "decision_conflicts": []}
FABRICATED = {"items": [FABRICATED_ITEM], "decision_conflicts": []}


def make_ids(**overrides: Any) -> IdGate:
    kwargs: dict[str, Any] = {
        "linear": FakeLinear(issues=[
            {"id": "u-104", "identifier": "INV-104", "title": "Overdue dashboard",
             "description": "", "state": "Backlog", "priority": 4, "assignee": None,
             "due_date": None, "url": "", "updated_at": ""},
        ]),
        "notion": FakeNotion({"page-prd": {"title": "Reminders PRD", "url": "", "markdown": "5"}}),
        "code": CodeSearch(REPO),
        "roster": [{"name": "Nodir Rahimov", "aliases": ["Nodir"]}],
        "known_meeting": _known_meeting,
    }
    kwargs.update(overrides)
    return IdGate(**kwargs)


async def _known_meeting(meeting_id: str) -> bool:
    return meeting_id == "8841201"


async def seed(deps: Deps, extracted: dict[str, Any] | None = None) -> dict[str, Any]:
    """A finished extract task plus the reconcile task that follows it, already claimed."""
    event_id = await deps.events.record(provider="fathom", provider_event_id="msg_1",
                                        payload=SAMPLE, project_id="acme")
    assert event_id is not None
    extract_id = await deps.queue.enqueue(kind="extract", project_id="acme",
                                          payload={"event_id": event_id}, reason="t",
                                          root_event_id=event_id)
    assert extract_id is not None
    await deps.db.update("tasks", extract_id,
                         {"status": "done", "result": extracted or EXTRACTED})
    tid = await deps.queue.enqueue(
        kind="reconcile", project_id="acme",
        payload={"event_id": event_id, "extract_task_id": extract_id}, reason="t",
        root_event_id=event_id)
    assert tid is not None
    task = await deps.queue.claim(tid)
    assert task is not None
    return task


# --- what an item asserts ---------------------------------------------------------------------

def test_every_reference_an_item_makes_is_collected_for_checking() -> None:
    refs = item_refs({**GOOD_ITEM, "disposition": "update", "target_issue": "INV-104"})
    assert set(refs) == {
        "fathom:8841201@00:01:58", "code:acme/config.py:6", "notion:page-prd", "linear:INV-104",
    }


def test_a_new_item_does_not_claim_an_issue_it_is_not_updating() -> None:
    assert "linear:INV-104" not in item_refs({**GOOD_ITEM, "target_issue": "INV-104"})


# --- the stage --------------------------------------------------------------------------------

async def test_a_fully_cited_item_is_verified_and_flows_to_act(deps: Deps) -> None:
    fake = FakeReconciler([GOOD])
    deps.reconciler, deps.ids = fake, make_ids()
    task = await seed(deps)
    out = await run(task, deps)

    assert [i["title"] for i in out.result["items"]] == ["Move payment reminders to 3 days"]
    assert out.result["unverified"] == [] and out.result["bounced"] is False
    assert out.result["items"][0]["quotes"] == ["I can have that done by next Friday"]
    assert [c["kind"] for c in out.children] == ["act"]
    assert "file 1 verified item(s)" in out.children[0]["reason"]

    sent = fake.calls[0]
    assert sent["today"] == "2026-08-27"
    assert {"name": "Nodir Rahimov", "role": "backend"} in sent["roster"]
    assert [p["name"] for p in sent["roster"]] == [m["name"] for m in ACME["roster"]]
    assert sent["meeting"]["title"] == "Q3 Billing planning"
    assert sent["feedback"] is None


async def test_an_item_citing_an_issue_that_does_not_exist_is_bounced_once_then_held_back(
    deps: Deps,
) -> None:
    fake = FakeReconciler([FABRICATED, FABRICATED])
    deps.reconciler, deps.ids = fake, make_ids()
    task = await seed(deps)
    out = await run(task, deps)

    assert out.result["items"] == [] and out.result["bounced"] is True
    assert "linear:INV-999" in out.result["unverified"][0]["gate_reason"]
    assert len(fake.calls) == 2
    assert "linear:INV-999" in (fake.calls[1]["feedback"] or "")
    assert [c["kind"] for c in out.children] == ["act"]
    assert "nothing survived verification" in out.children[0]["reason"]


async def test_the_bounce_rescues_an_item_when_the_model_corrects_its_citation(
    deps: Deps,
) -> None:
    deps.reconciler, deps.ids = FakeReconciler([FABRICATED, GOOD]), make_ids()
    task = await seed(deps)
    out = await run(task, deps)
    assert out.result["bounced"] is True and out.result["unverified"] == []
    assert len(out.result["items"]) == 1


async def test_a_source_outage_holds_items_back_and_schedules_exactly_one_retry(
    deps: Deps,
) -> None:
    class DownLinear:
        async def get_issue(self, identifier: str) -> dict[str, Any] | None:
            raise SourceUnavailable("linear", "HTTP 503")

    updating = {**GOOD_ITEM, "disposition": "update", "target_issue": "INV-104"}
    deps.reconciler = FakeReconciler([{"items": [updating], "decision_conflicts": []}] * 2)
    deps.ids = make_ids(linear=DownLinear())
    task = await seed(deps)
    out = await run(task, deps)

    assert out.result["items"] == []
    assert "linear unavailable" in out.result["unverified"][0]["gate_reason"]
    kinds = [c["kind"] for c in out.children]
    assert kinds == ["act", "reconcile"]
    retry = out.children[1]
    assert retry["payload"]["retry"] == 1
    assert retry["due_at"] == "2026-08-27T09:30:00+00:00"


async def test_a_retry_that_still_cannot_reach_the_source_does_not_retry_again(
    deps: Deps,
) -> None:
    class DownLinear:
        async def get_issue(self, identifier: str) -> dict[str, Any] | None:
            raise SourceUnavailable("linear", "HTTP 503")

    updating = {**GOOD_ITEM, "disposition": "update", "target_issue": "INV-104"}
    deps.reconciler = FakeReconciler([{"items": [updating], "decision_conflicts": []}] * 2)
    deps.ids = make_ids(linear=DownLinear())
    task = await seed(deps)
    task["payload"]["retry"] = 1
    out = await run(task, deps)
    assert [c["kind"] for c in out.children] == ["act"]


async def test_conflicts_are_carried_through_untouched_never_resolved(deps: Deps) -> None:
    deps.reconciler, deps.ids = FakeReconciler([GOOD]), make_ids()
    task = await seed(deps)
    out = await run(task, deps)
    conflict = out.result["items"][0]["conflicts"][0]
    assert conflict["kind"] == "code_vs_spec"
    assert [s["claim"] for s in conflict["sides"]] == ["7 days", "5 days"]


# --- the call is always citable -------------------------------------------------------------------

UNCITED_ITEM = {**GOOD_ITEM, "citations": [], "conflicts": [], "facts": []}
CALL_REF = "fathom:8841201@00:01:58"


def test_an_item_that_cited_nothing_gains_the_moment_it_came_from() -> None:
    """A smaller model reliably skips citation assembly. The harness knows the answer already —
    the item's index points at the action item, which carries the evidence it was taken from."""
    cited, uncitable = with_call_citation([UNCITED_ITEM], "8841201", EXTRACTED["action_items"])

    assert cited[0]["citations"] == [CALL_REF]
    assert uncitable == []


def test_an_item_that_already_cited_the_call_is_not_cited_twice() -> None:
    cited, _ = with_call_citation([GOOD_ITEM], "8841201", EXTRACTED["action_items"])

    assert cited[0]["citations"] == [CALL_REF, "code:acme/config.py:6"]
    assert cited[0]["citations"].count(CALL_REF) == 1


def test_everything_the_model_did_cite_survives_alongside() -> None:
    """A backstop adds; it never replaces. The model's own work is the better answer."""
    theirs = {**UNCITED_ITEM, "citations": ["linear:INV-104", "notion:page-prd"]}
    cited, _ = with_call_citation([theirs], "8841201", EXTRACTED["action_items"])

    assert cited[0]["citations"] == ["linear:INV-104", "notion:page-prd", CALL_REF]


def test_evidence_with_no_timestamp_gets_no_invented_one() -> None:
    """A fabricated timestamp would be worse than no citation: it would pass the gate, because
    the gate only checks the meeting, and then point a reader at a moment that never happened."""
    untimed = {**EXTRACTED, "action_items": [
        {**EXTRACTED["action_items"][0], "evidence": [{"quote": "something said", "speaker": "x"}]}
    ]}
    cited, uncitable = with_call_citation([UNCITED_ITEM], "8841201", untimed["action_items"])

    assert cited[0]["citations"] == []
    assert uncitable == ["Move payment reminders to 3 days"]


def test_an_item_pointing_at_no_action_item_gets_nothing() -> None:
    assert call_citation({"index": 9}, "8841201", EXTRACTED["action_items"]) == ""
    assert call_citation({"index": 0}, "", EXTRACTED["action_items"]) == ""
    assert call_citation({}, "8841201", EXTRACTED["action_items"]) == ""


async def test_the_stage_files_an_uncited_item_with_the_call_attached(deps: Deps) -> None:
    deps.reconciler = FakeReconciler([{"items": [UNCITED_ITEM], "decision_conflicts": []}])
    deps.ids = make_ids()
    task = await seed(deps)

    out = await run(task, deps)

    assert out.result["unverified"] == []
    assert out.result["items"][0]["citations"] == [CALL_REF]
    assert out.result["bounced"] is False
    assert out.result["notes"] == []


async def test_a_harness_written_citation_is_checked_like_any_other(deps: Deps) -> None:
    """The gate does not care who wrote a reference. With the call absent from the store, the
    item it belongs to is held back exactly as a fabricated ticket id would be."""
    async def no_meetings(meeting_id: str) -> bool:
        return False

    deps.reconciler = FakeReconciler([
        {"items": [UNCITED_ITEM], "decision_conflicts": []},
        {"items": [UNCITED_ITEM], "decision_conflicts": []},
    ])
    deps.ids = make_ids(known_meeting=no_meetings)
    task = await seed(deps)

    out = await run(task, deps)

    assert out.result["items"] == []
    assert out.result["bounced"] is True
    assert CALL_REF in out.result["unverified"][0]["gate_reason"]


async def test_an_item_with_no_timestamp_is_filed_and_the_gap_is_recorded(deps: Deps) -> None:
    """Not a failure — the work is real and still ships. The task result says what it could not
    give the reader, which is the whole difference between a gap and a lie."""
    untimed = {**EXTRACTED, "action_items": [
        {**EXTRACTED["action_items"][0], "evidence": [{"quote": "I can have that done by next "
                                                                "Friday", "speaker": "Nodir"}]}
    ]}
    deps.reconciler = FakeReconciler([{"items": [UNCITED_ITEM], "decision_conflicts": []}])
    deps.ids = make_ids()
    task = await seed(deps, extracted=untimed)

    out = await run(task, deps)

    assert out.result["items"][0]["citations"] == []
    assert out.result["unverified"] == []  # nothing false was written, so nothing is held back
    assert "no timestamp on their evidence" in out.result["notes"][0]
    assert "Move payment reminders to 3 days" in out.result["notes"][0]


# --- an "update" that names no issue ------------------------------------------------------------

TRACKED = [
    {"id": "u-25", "identifier": "INV-25", "title": "Add invoice CSV export",
     "description": "Finance asked for it", "state": "Backlog", "state_type": "backlog",
     "priority": 4, "assignee": None, "due_date": None, "url": "", "updated_at": ""},
]
HOMELESS_ITEM = {
    **GOOD_ITEM, "index": 0, "title": "Put the invoice CSV export behind a feature flag",
    "description": "Raised again in the kickoff.", "disposition": "update", "target_issue": None,
    "citations": ["fathom:8841201@00:01:58"], "conflicts": [], "facts": [],
}
HOMELESS = {"items": [HOMELESS_ITEM], "decision_conflicts": []}


def linear_with(*issues: dict[str, Any]) -> FakeLinear:
    return FakeLinear(issues=list(issues))


# --- picking the words to search on -------------------------------------------------------------

def test_a_title_is_searched_on_the_words_that_identify_the_work() -> None:
    assert search_words("Put the invoice CSV export behind a feature flag") == [
        "invoice", "csv", "export", "feature", "flag"]
    assert search_words("Build the overdue invoices dashboard for finance") == [
        "overdue", "invoices", "dashboard", "finance"]


def test_an_issue_of_unknown_state_counts_as_open() -> None:
    """Keeping a candidate can only make "exactly one match" harder to reach. Dropping one
    could leave a single wrong match standing."""
    assert is_open({"identifier": "INV-1"})
    assert is_open({"state_type": "started"})
    assert not is_open({"state_type": "completed"})
    assert not is_open({"state_type": "canceled"})


# --- resolving it ourselves ---------------------------------------------------------------------

async def test_an_update_naming_no_issue_is_matched_to_the_one_the_tracker_holds(
    deps: Deps,
) -> None:
    """The reconciler said "update" and named nothing. Exactly one open issue answers to the
    title, so the harness supplies what the model left out instead of losing the commitment."""
    deps.reconciler = FakeReconciler([HOMELESS])
    deps.ids = make_ids(linear=linear_with(*TRACKED))
    deps.linear = linear_with(*TRACKED)

    out = await run(await seed(deps), deps)

    assert [i["target_issue"] for i in out.result["items"]] == ["INV-25"]
    assert [i["disposition"] for i in out.result["items"]] == ["update"]
    assert "matched to INV-25 by title" in out.result["notes"]


async def test_a_matched_target_is_verified_like_one_the_model_wrote(deps: Deps) -> None:
    """A recovered identifier is still an identifier: if it does not resolve it is held back."""
    deps.reconciler = FakeReconciler([HOMELESS, HOMELESS])
    deps.ids = make_ids(linear=linear_with())
    deps.linear = linear_with(*TRACKED)

    out = await run(await seed(deps), deps)

    assert out.result["items"] == []
    assert "INV-25" in out.result["unverified"][0]["gate_reason"]


async def test_an_update_that_already_names_its_issue_is_left_alone(deps: Deps) -> None:
    named = {**HOMELESS_ITEM, "target_issue": "INV-104"}
    deps.reconciler, deps.ids = FakeReconciler([{"items": [named], "decision_conflicts": []}]), (
        make_ids())
    deps.linear = linear_with(*TRACKED)

    out = await run(await seed(deps), deps)

    assert [i["target_issue"] for i in out.result["items"]] == ["INV-104"]
    assert out.result["notes"] == []
    assert not out.result["bounced"]


async def test_a_new_item_is_never_matched_to_an_existing_issue(deps: Deps) -> None:
    deps.reconciler, deps.ids = FakeReconciler([GOOD]), make_ids()
    deps.linear = linear_with(*TRACKED)

    out = await run(await seed(deps), deps)

    assert out.result["items"][0]["target_issue"] is None
    assert out.result["items"][0]["disposition"] == "new"


# --- when it cannot be resolved -----------------------------------------------------------------

async def test_several_matches_are_never_guessed_between(deps: Deps) -> None:
    """Two issues answer to the title. Picking one would be a coin flip against a team's
    tracker, so the model is asked and the item is downgraded when it still will not say."""
    twin = {**TRACKED[0], "id": "u-26", "identifier": "INV-26",
            "title": "Rework invoice CSV export"}
    deps.reconciler, deps.ids = FakeReconciler([HOMELESS, HOMELESS]), make_ids()
    deps.linear = linear_with(TRACKED[0], twin)

    out = await run(await seed(deps), deps)

    assert [i["disposition"] for i in out.result["items"]] == ["new"]
    assert out.result["items"][0]["description"].startswith(
        "Possibly duplicates existing work —")


async def test_no_match_at_all_takes_the_same_road(deps: Deps) -> None:
    deps.reconciler, deps.ids = FakeReconciler([HOMELESS, HOMELESS]), make_ids()
    deps.linear = linear_with()

    out = await run(await seed(deps), deps)

    assert [i["disposition"] for i in out.result["items"]] == ["new"]
    assert out.result["items"][0]["target_issue"] is None


async def test_the_model_is_told_exactly_what_it_left_out_before_anything_is_downgraded(
    deps: Deps,
) -> None:
    fake = FakeReconciler([HOMELESS, HOMELESS])
    deps.reconciler, deps.ids = fake, make_ids()
    deps.linear = linear_with()

    out = await run(await seed(deps), deps)

    assert out.result["bounced"]
    feedback = fake.calls[1]["feedback"]
    assert "names no issue" in feedback or "name no issue" in feedback
    assert "Put the invoice CSV export behind a feature flag" in feedback


async def test_the_model_correcting_itself_is_believed_and_nothing_is_downgraded(
    deps: Deps,
) -> None:
    corrected = {**HOMELESS_ITEM, "target_issue": "INV-104"}
    deps.reconciler = FakeReconciler([HOMELESS, {"items": [corrected],
                                                 "decision_conflicts": []}])
    deps.ids = make_ids()
    deps.linear = linear_with()

    out = await run(await seed(deps), deps)

    assert [i["disposition"] for i in out.result["items"]] == ["update"]
    assert out.result["items"][0]["target_issue"] == "INV-104"


async def test_a_downgrade_is_written_down_where_a_human_will_read_it(deps: Deps) -> None:
    deps.reconciler, deps.ids = FakeReconciler([HOMELESS, HOMELESS]), make_ids()
    deps.linear = linear_with()

    out = await run(await seed(deps), deps)

    note = " ".join(out.result["notes"])
    assert "named no issue" in note
    assert "Put the invoice CSV export behind a feature flag" in note


async def test_the_original_description_survives_the_downgrade(deps: Deps) -> None:
    deps.reconciler, deps.ids = FakeReconciler([HOMELESS, HOMELESS]), make_ids()
    deps.linear = linear_with()

    out = await run(await seed(deps), deps)

    assert "Raised again in the kickoff." in out.result["items"][0]["description"]


async def test_a_tracker_outage_never_looks_like_no_such_issue(deps: Deps) -> None:
    """An outage is not evidence the issue does not exist, so nothing is matched on it — and
    the item takes the honest road rather than a wrong one."""
    class Down(FakeLinear):
        async def search_issues(
            self, team_id: str, text: str, *, limit: int = 8
        ) -> list[dict[str, Any]]:
            raise SourceUnavailable("linear", "502")

    deps.reconciler, deps.ids = FakeReconciler([HOMELESS, HOMELESS]), make_ids()
    deps.linear = Down(issues=list(TRACKED))

    out = await run(await seed(deps), deps)

    assert [i["disposition"] for i in out.result["items"]] == ["new"]


# --- what the company has already told it -------------------------------------------------------

FACT_ITEM = {
    **GOOD_ITEM, "conflicts": [],
    "facts": [{"text": "Line-item rates allow six decimal places",
               "source": "code:acme/config.py:6"}],
}
# The second fact points at an issue that does not exist, so the item never survives the gate.
UNVERIFIED_FACT = {
    **GOOD_ITEM, "conflicts": [],
    "facts": [{"text": "Statements are generated nightly", "source": "linear:INV-999"}],
}


async def brain(deps: Deps) -> WikiStore:
    deps.wiki = WikiStore(deps.db, deps.clock)
    return deps.wiki


async def test_the_reconciler_is_shown_what_this_company_has_said(deps: Deps) -> None:
    """"assign billing to Nodir" has to reach the step that decides owners, or it was never
    worth storing."""
    wiki = await brain(deps)
    await wiki.add_entry("acme", "ownership", {
        "text": "Billing and statements go to Nodir", "subject": ["billing", "statements"],
        "person": "Nodir Rahimov", "source": "slack:C1:1", "said_by": "Maya Chen"})
    fake = FakeReconciler([GOOD])
    deps.reconciler, deps.ids = fake, make_ids()
    extracted = {**EXTRACTED, "action_items": [
        {**EXTRACTED["action_items"][0], "title": "Fix the billing statements page"}]}

    await run(await seed(deps, extracted), deps)

    handed = fake.calls[0]["brain"]
    assert [e["text"] for e in handed] == ["Billing and statements go to Nodir"]
    assert handed[0]["person"] == "Nodir Rahimov"
    assert handed[0]["ref"].startswith("wiki:ownership#")
    assert handed[0]["said_by"] == "Maya Chen"
    assert handed[0]["when"], "and when they said it"


async def test_a_call_about_something_else_does_not_carry_the_whole_brain(deps: Deps) -> None:
    wiki = await brain(deps)
    await wiki.add_entry("acme", "ownership", {
        "text": "Onboarding emails go to Priya", "subject": ["onboarding", "emails"],
        "person": "Priya Nair", "source": "slack:C1:1"})
    fake = FakeReconciler([GOOD])
    deps.reconciler, deps.ids = fake, make_ids()

    await run(await seed(deps), deps)

    assert fake.calls[0]["brain"] == []


async def test_a_verified_fact_from_the_call_becomes_something_it_remembers(deps: Deps) -> None:
    wiki = await brain(deps)
    deps.reconciler = FakeReconciler([{"items": [FACT_ITEM], "decision_conflicts": []}])
    deps.ids = make_ids()

    out = await run(await seed(deps), deps)

    remembered = [e["text"] for p in await wiki.pages("acme") for e in p["entries"]]
    assert "Line-item rates allow six decimal places" in remembered
    assert out.result["learned"], "and the journal can say so"


async def test_a_fact_whose_source_did_not_survive_the_gate_is_not_remembered(
    deps: Deps,
) -> None:
    """A fact nobody can re-open is exactly the kind of thing that should not be repeated back
    to the team next week."""
    wiki = await brain(deps)
    deps.reconciler = FakeReconciler([
        {"items": [UNVERIFIED_FACT], "decision_conflicts": []},
        {"items": [UNVERIFIED_FACT], "decision_conflicts": []}])
    deps.ids = make_ids()

    await run(await seed(deps), deps)

    remembered = [e["text"] for p in await wiki.pages("acme") for e in p["entries"]]
    assert "Statements are generated nightly" not in remembered, "INV-999 does not exist"


async def test_the_same_fact_from_a_replayed_call_is_remembered_once(deps: Deps) -> None:
    wiki = await brain(deps)
    deps.reconciler = FakeReconciler([{"items": [FACT_ITEM], "decision_conflicts": []}])
    deps.ids = make_ids()
    first = await seed(deps)
    await run(first, deps)

    # The same call reconciled again, as a replay would do it.
    again = await deps.queue.enqueue(
        kind="reconcile", project_id="acme", payload=first["payload"], reason="replay",
        root_event_id=first.get("root_event_id"))
    assert again is not None
    claimed = await deps.queue.claim(again)
    assert claimed is not None
    deps.reconciler = FakeReconciler([{"items": [FACT_ITEM], "decision_conflicts": []}])
    await run(claimed, deps)

    entries = [e for p in await wiki.pages("acme") for e in p["entries"]]
    assert len(entries) == 1, "one memory, however many times the call is processed"

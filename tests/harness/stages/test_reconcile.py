"""reconcile turns a call's action items into verified proposals — or into honest gaps."""

import json
from pathlib import Path
from typing import Any

from app.harness.connectors.code import CodeSearch
from app.harness.core.errors import SourceUnavailable
from app.harness.deps import Deps
from app.harness.stages.reconcile import (
    call_citation,
    item_refs,
    run,
    with_call_citation,
)
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

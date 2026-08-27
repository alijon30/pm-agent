import json
from pathlib import Path
from typing import Any

from app.harness.deps import Deps
from app.harness.stages.extract import run, select_with_context

from tests.fakes.fake_agents import FakeExtractor

SAMPLE = json.loads(
    (Path(__file__).parents[2] / "fixtures" / "fathom_webhook_sample.json").read_text()
)

GOOD = {
    "decisions": [{"statement": "Payment reminders move to three days after due date",
                   "rejected_options": [],
                   "evidence": [{"quote": "move payment reminders to three days after the due date",
                                 "timestamp": "00:01:42", "speaker": "Maya Chen"}]}],
    "action_items": [{"title": "Move payment reminders to 3 days", "owner_name": "Nodir Rahimov",
                      "due_hint": "next Friday",
                      "evidence": [{"quote": "I can have that done by next Friday",
                                    "timestamp": "00:01:58", "speaker": "Nodir Rahimov"}]}],
    "open_questions": [],
}
HALLUCINATED = {
    "decisions": [],
    "action_items": [{"title": "Ship SMS reminders",
                      "evidence": [{"quote": "we will ship SMS in Q4"}]}],
    "open_questions": [],
}


async def seed_event_and_task(deps: Deps) -> dict[str, Any]:
    event_id = await deps.events.record(provider="fathom", provider_event_id="msg_1",
                                        payload=SAMPLE, project_id="acme")
    assert event_id is not None
    tid = await deps.queue.enqueue(kind="extract", project_id="acme",
                                   payload={"event_id": event_id}, reason="test",
                                   root_event_id=event_id)
    assert tid is not None
    task = await deps.queue.claim(tid)
    assert task is not None
    return task


def test_select_with_context_keeps_flagged_segments_plus_neighbours_in_order() -> None:
    segs = [{"text": str(i)} for i in range(8)]
    flags = [False, False, False, True, False, False, False, False]
    assert [s["text"] for s in select_with_context(segs, flags, window=2)] == ["1", "2", "3", "4", "5"]
    assert select_with_context(segs, [False] * 8) == []


async def test_extract_persists_decisions_and_enqueues_reconcile(deps: Deps) -> None:
    fake = FakeExtractor([GOOD])
    deps.extractor = fake
    task = await seed_event_and_task(deps)
    out = await run(task, deps)
    assert out.result["meeting"]["title"] == "Q3 Billing planning"
    assert [a["title"] for a in out.result["action_items"]] == ["Move payment reminders to 3 days"]
    assert len(out.result["decision_ids"]) == 1
    assert out.result["dropped"] == [] and out.result["bounced"] is False
    assert out.children == [{"kind": "reconcile",
                             "payload": {"event_id": "fathom:msg_1", "extract_task_id": task["id"]},
                             "reason": "reconcile 1 action item(s) and 1 decision(s) from "
                                       "'Q3 Billing planning' against Linear, Notion and code"}]
    payload = fake.calls[0]
    assert "[00:01:42] Maya Chen:" in payload["transcript"]
    assert "Nodir Rahimov" in payload["roster_names"] and payload["feedback"] is None
    assert await deps.db.count("decisions", []) == 1


async def test_an_item_without_a_verbatim_quote_is_bounced_once_then_dropped_not_guessed(
    deps: Deps,
) -> None:
    fake = FakeExtractor([HALLUCINATED, HALLUCINATED])
    deps.extractor = fake
    task = await seed_event_and_task(deps)
    out = await run(task, deps)
    assert out.result["action_items"] == []
    assert out.result["bounced"] is True
    assert out.result["dropped"][0]["title"] == "Ship SMS reminders"
    assert out.result["dropped"][0]["gate_reason"] == "no verbatim quote found in transcript"
    assert len(fake.calls) == 2
    assert "Ship SMS reminders" in (fake.calls[1]["feedback"] or "")
    assert out.children == []  # nothing survived, nothing to reconcile


async def test_the_bounce_can_rescue_an_item_when_the_model_supplies_a_real_quote(
    deps: Deps,
) -> None:
    deps.extractor = FakeExtractor([HALLUCINATED, GOOD])
    task = await seed_event_and_task(deps)
    out = await run(task, deps)
    assert out.result["bounced"] is True and out.result["dropped"] == []
    assert len(out.result["action_items"]) == 1

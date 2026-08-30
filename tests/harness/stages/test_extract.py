import json
from pathlib import Path
from typing import Any

from app.harness.deps import Deps
from app.harness.stages.extract import (
    commitment_cues,
    covered,
    recall_feedback,
    run,
    select_with_context,
    thin_recall,
)

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


# --- the recall backstop -------------------------------------------------------------------------
#
# The evidence gate stops the model inventing. Nothing stopped it being quiet: on a live standup
# it returned two action items where a person finds six, and every miss was an ordinary sentence.

STANDUP = [
    {"timestamp": "00:00:12", "speaker": "Omar", "text": "Morning — can you see my screen?"},
    {"timestamp": "00:00:30", "speaker": "Lena",
     "text": "Can you add a comment on the credit-notes ticket with the doc link?"},
    {"timestamp": "00:01:05", "speaker": "Omar",
     "text": "I'll run the payment-terms migration by today."},
    {"timestamp": "00:02:10", "speaker": "Lena",
     "text": "Let's remove the six-decimals feature flag and verify with Lena."},
    {"timestamp": "00:03:00", "speaker": "Priya",
     "text": "The weather has been unbelievable this week."},
    {"timestamp": "00:04:20", "speaker": "Omar",
     "text": "Please tag Omar on the PATCH-versus-POST thread."},
]


def cue_at(stamp: str) -> dict[str, Any]:
    return next(c for c in commitment_cues(STANDUP) if c["timestamp"] == stamp)


def test_a_line_that_hands_work_to_somebody_is_a_cue() -> None:
    found = {c["timestamp"] for c in commitment_cues(STANDUP)}

    assert found == {"00:00:30", "00:01:05", "00:02:10", "00:04:20"}
    assert cue_at("00:00:30")["speaker"] == "Lena"


def test_can_you_see_my_screen_is_not_a_commitment() -> None:
    """Every call opens with one, and counting it would make the alarm cry wolf."""
    assert commitment_cues([STANDUP[0]]) == []
    assert commitment_cues([{"text": "Can you hear me now?"}]) == []
    assert commitment_cues([{"text": "Can you share your screen?"}]) == []


def test_small_talk_is_not_a_commitment() -> None:
    assert commitment_cues([STANDUP[4]]) == []
    assert commitment_cues([{"text": "Sounds good, thanks everyone."}]) == []


def test_a_cue_is_covered_when_an_item_cites_its_moment() -> None:
    item = {"evidence": [{"quote": "anything", "timestamp": "00:01:05"}]}

    assert covered(cue_at("00:01:05"), [item])
    assert not covered(cue_at("00:02:10"), [item])


def test_a_cue_is_covered_when_an_item_quotes_words_the_line_contains() -> None:
    item = {"evidence": [{"quote": "run the payment-terms migration"}]}

    assert covered(cue_at("00:01:05"), [item])


def test_a_quiet_pass_over_a_talkative_standup_asks_once() -> None:
    cues = commitment_cues(STANDUP)
    one_item = [{"evidence": [{"timestamp": "00:01:05"}]}]

    assert thin_recall(cues, one_item), "three of four commitments went nowhere"


def test_one_miss_is_not_worth_a_second_call() -> None:
    """Below the threshold a bounce costs a call and a delay to argue about one sentence
    somebody may well have meant rhetorically."""
    cues = commitment_cues(STANDUP)
    almost = [{"evidence": [{"timestamp": t}]}
              for t in ("00:00:30", "00:01:05", "00:02:10")]

    assert not thin_recall(cues, almost)


def test_a_transcript_with_no_commitments_never_bounces() -> None:
    assert not thin_recall([], [])
    assert not thin_recall(commitment_cues([STANDUP[4]]), [])


def test_the_feedback_names_the_lines_verbatim() -> None:
    text = recall_feedback(commitment_cues(STANDUP)[:2])

    assert "[00:00:30] Lena: Can you add a comment on the credit-notes ticket" in text
    assert "either add an item with this line as its evidence" in text
    assert "say in `dropped` why it is not" in text


# --- through the stage ---------------------------------------------------------------------------

def standup_payload() -> dict[str, Any]:
    return {**SAMPLE, "transcript": [
        {"speaker": {"display_name": s["speaker"]}, "text": s["text"],
         "timestamp": s["timestamp"]}
        for s in STANDUP
    ]}


def item(title: str, quote: str, stamp: str) -> dict[str, Any]:
    return {"title": title, "owner_name": "Omar",
            "evidence": [{"quote": quote, "timestamp": stamp, "speaker": "Omar"}]}


QUIET = {"decisions": [], "open_questions": [], "action_items": [
    item("Run the payment-terms migration", "I'll run the payment-terms migration by today",
         "00:01:05")]}
FULLER = {"decisions": [], "open_questions": [], "action_items": [
    item("Run the payment-terms migration", "I'll run the payment-terms migration by today",
         "00:01:05"),
    item("Comment on the credit-notes ticket",
         "Can you add a comment on the credit-notes ticket with the doc link?", "00:00:30"),
    item("Remove the six-decimals feature flag",
         "Let's remove the six-decimals feature flag and verify with Lena", "00:02:10"),
    item("Tag Omar on the PATCH-versus-POST thread",
         "Please tag Omar on the PATCH-versus-POST thread", "00:04:20"),
]}


async def seed_standup(deps: Deps) -> dict[str, Any]:
    event_id = await deps.events.record(provider="fathom", provider_event_id="standup",
                                        payload=standup_payload(), project_id="acme")
    assert event_id is not None
    tid = await deps.queue.enqueue(kind="extract", project_id="acme",
                                   payload={"event_id": event_id}, reason="test",
                                   root_event_id=event_id)
    assert tid is not None
    task = await deps.queue.claim(tid)
    assert task is not None
    return task


async def test_a_quiet_first_pass_is_asked_again_and_the_items_come_back(deps: Deps) -> None:
    deps.extractor = FakeExtractor([QUIET, FULLER])

    out = await run(await seed_standup(deps), deps)

    assert len(out.result["action_items"]) == 4
    assert out.result["recall"] == {"cues": 4, "covered_first": 1, "covered_final": 4,
                                    "bounced": True}


async def test_a_second_pass_that_found_less_is_not_a_newer_answer(deps: Deps) -> None:
    """A retry can only ever add cited items; one that came back with fewer is worse, and the
    first answer stands."""
    thinner = {"decisions": [], "open_questions": [], "action_items": []}
    deps.extractor = FakeExtractor([QUIET, thinner])

    out = await run(await seed_standup(deps), deps)

    assert len(out.result["action_items"]) == 1, "the first pass survives"
    assert out.result["recall"]["covered_final"] == 1


async def test_a_pass_that_already_heard_everything_is_not_asked_again(deps: Deps) -> None:
    fake = FakeExtractor([FULLER])
    deps.extractor = fake

    out = await run(await seed_standup(deps), deps)

    assert out.result["recall"] == {"cues": 4, "covered_first": 4, "covered_final": 4,
                                    "bounced": False}
    assert len(fake.calls) == 1, "no second call"


def test_the_top_and_tail_of_a_call_are_not_commitments() -> None:
    """Every standup opens and closes the same way, and counting the ritual would drown the
    real thing."""
    assert commitment_cues([{"text": "All right, thank you. I'll talk to you later."}]) == []
    assert commitment_cues([{"text": "Have a good one, everyone."}]) == []


def test_a_line_saying_something_is_impossible_is_not_handing_out_work() -> None:
    assert commitment_cues([{"text": "We can't run migrations during business hours."}]) == []
    assert commitment_cues([{"text": "We cannot do it for one customer."}]) == []

import pytest
from app.agents.base.schemas import ExtractResult, Investigation, ReconcileItem, Report
from pydantic import ValidationError


def test_extract_result_validates_the_documented_shape() -> None:
    raw = {
        "decisions": [{"statement": "Reminders move to 3 days", "rejected_options": ["SMS"],
                       "evidence": [{"quote": "move payment reminders to three days",
                                     "timestamp": "00:01:42", "speaker": "Maya Chen"}]}],
        "action_items": [{"title": "Move reminders to 3 days", "owner_name": "Nodir Rahimov",
                          "due_hint": "next Friday",
                          "evidence": [{"quote": "I can have that done by next Friday"}]}],
        "open_questions": [],
    }
    result = ExtractResult.model_validate(raw)
    assert result.decisions[0].rejected_options == ["SMS"]
    assert result.action_items[0].description == ""
    assert result.action_items[0].priority_hint is None


def test_an_item_without_an_evidence_list_is_invalid() -> None:
    with pytest.raises(ValidationError):
        ExtractResult.model_validate({"decisions": [{"statement": "x"}]})


def test_empty_sections_default_to_empty_lists() -> None:
    assert ExtractResult.model_validate({}).model_dump() == {
        "decisions": [], "action_items": [], "open_questions": []}


def test_a_report_section_must_be_one_the_gate_and_the_renderer_know() -> None:
    with pytest.raises(ValidationError):
        Report.model_validate({"headline": "h", "sections": [{"name": "vibes", "claims": []}]})


def test_a_report_with_nothing_to_say_is_still_a_valid_report() -> None:
    assert Report.model_validate({"headline": "A quiet sprint."}).model_dump() == {
        "headline": "A quiet sprint.", "sections": []}


def test_a_reconcile_item_carries_the_why_the_criteria_and_the_investigation() -> None:
    raw = {
        "index": 0,
        "title": "Fix duplicate reminder emails",
        "description": "Raised by support in the Q3 planning call.",
        "context": "Two customers were billed twice in June and one threatened to cancel.",
        "acceptance": ["A customer gets at most one reminder per invoice per day"],
        "disposition": "new",
        "citations": ["fathom:8841201@00:01:58"],
        "investigation": {
            "files": ["code:acme/reminders/scheduler.py:19"],
            "note": "The repeat window is enforced in due_for_reminder.",
            "confidence": "likely",
        },
    }
    item = ReconcileItem.model_validate(raw)

    assert item.acceptance == ["A customer gets at most one reminder per invoice per day"]
    assert item.investigation is not None
    assert item.investigation.files == ["code:acme/reminders/scheduler.py:19"]
    assert item.investigation.confidence == "likely"
    assert ReconcileItem.model_validate(item.model_dump()) == item


def test_an_item_nobody_investigated_defaults_to_saying_nothing() -> None:
    """Empty is a real answer: not every action item is about behaviour that already exists."""
    item = ReconcileItem.model_validate(
        {"index": 0, "title": "Draft the Q4 roadmap", "disposition": "new"})

    assert item.context == "" and item.acceptance == [] and item.investigation is None


def test_an_investigation_that_found_nothing_is_unknown_by_default() -> None:
    found_nothing = Investigation.model_validate(
        {"note": "couldn't locate this in the code"})

    assert found_nothing.confidence == "unknown" and found_nothing.files == []


def test_a_confidence_nobody_can_read_is_refused() -> None:
    """"pretty sure" sends an engineer somewhere on a feeling. Three words, or none."""
    with pytest.raises(ValidationError):
        Investigation.model_validate({"note": "somewhere in billing", "confidence": "pretty sure"})

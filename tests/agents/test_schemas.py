import pytest
from app.agents.schemas import ExtractResult
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

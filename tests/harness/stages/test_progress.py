"""The status checklist is decoration with rules: it always shows the whole plan, it never
invents a count, and it never gets to break a stage."""

from app.harness.stages.progress import check_note, checklist, read_note


def test_the_first_post_is_the_whole_plan_with_the_first_step_current() -> None:
    text = checklist("Related articles huddle", doing=0)
    assert text.splitlines() == [
        "✻ *Related articles huddle* — on it. The plan:",
        "🟠 read the call",
        "○ check it against Linear, the docs and the code",
        "○ file what was agreed",
        "○ set up the follow-through",
    ]


def test_a_finished_step_is_ticked_and_carries_its_note() -> None:
    text = checklist(
        "Related articles huddle", doing=2,
        notes={0: "two action items, one decision", 1: "one item checked out"},
    )
    assert "✓ read the call — two action items, one decision" in text
    assert "✓ checked it against Linear, the docs and the code — one item checked out" in text
    assert "🟠 file what was agreed" in text
    assert "○ set up the follow-through" in text


def test_notes_speak_like_a_person() -> None:
    assert read_note(2, 1) == "two action items, one decision"
    assert read_note(1, 0) == "one action item"
    assert read_note(0, 0) == "nothing that needs filing"
    assert check_note(1) == "one item checked out"
    assert check_note(0) == "nothing survived verification"

"""The rules in a prompt that a gate downstream depends on.

Most prompt wording is taste and does not belong in a test. These lines are different: each one
is the only thing standing between a gate and an item that will fail it. A live run against the
second fixture call produced `citations: []` on every item and `priority: null` despite a spoken
"this is a blocker", and both were prompt failures rather than gate failures — the gates worked
exactly as designed on input that never carried what they check for."""

from app.agents.extractor import EXTRACTOR_INSTRUCTION
from app.agents.reconciler import RECONCILER_INSTRUCTION
from app.harness.verify.priority import has_escalation

ESCALATION_PHRASES = ("urgent", "blocker", "blocked", "p0", "asap")


def test_the_reconciler_is_told_an_item_can_always_cite_the_call() -> None:
    """Empty citations are never correct: the item exists because somebody said it out loud."""
    assert "citations: never empty" in RECONCILER_INSTRUCTION
    assert "An item with empty citations is a bug" in RECONCILER_INSTRUCTION
    assert "the call is always citable" in RECONCILER_INSTRUCTION


def test_the_reconciler_is_told_where_the_meeting_id_comes_from() -> None:
    """`fathom:<meeting_id>@<mm:ss>` is only actionable if the model knows which field holds the
    id — and the id it must use is the one the identifier gate re-checks."""
    assert "fathom:<meeting.id>@<timestamp>" in RECONCILER_INSTRUCTION
    assert 'meeting.id is the id in the "meeting" object' in RECONCILER_INSTRUCTION
    assert "The id is what a fathom: reference is built from." in RECONCILER_INSTRUCTION


def test_the_priority_rule_tells_the_model_what_to_do_not_only_what_to_avoid() -> None:
    """"Only use 1 when…" reads as discouragement and produced null every time."""
    assert "you MUST set 1 for a" in RECONCILER_INSTRUCTION
    assert "Do not soften a stated emergency into null" in RECONCILER_INSTRUCTION
    assert "Only use\n  1 when someone actually used escalation language" not in (
        RECONCILER_INSTRUCTION
    )


def test_every_phrase_the_gate_looks_for_is_named_in_both_prompts() -> None:
    """A phrase the gate unlocks on but no prompt mentions is a capability nobody can reach."""
    for phrase in ESCALATION_PHRASES:
        assert phrase in RECONCILER_INSTRUCTION, f"reconciler never mentions {phrase!r}"
        assert phrase in EXTRACTOR_INSTRUCTION, f"extractor never mentions {phrase!r}"


def test_the_extractor_is_told_to_carry_the_urgency_to_the_item_it_is_about() -> None:
    """The priority gate reads the item's own evidence quotes. Urgency spoken in a different
    line reaches it only if the extractor attaches that line to the item."""
    assert "attach\n  THAT line as evidence on the item too" in EXTRACTOR_INSTRUCTION
    assert "The urgency has to travel with the item it is about" in EXTRACTOR_INSTRUCTION


def test_the_phrases_the_prompts_name_are_the_phrases_the_gate_unlocks_on() -> None:
    """Not a wording test: proof that saying these words in a quote actually opens the band."""
    for phrase in ESCALATION_PHRASES:
        assert has_escalation([f"honestly this is {phrase}, it cannot wait"],
                              ESCALATION_PHRASES) is True
    assert has_escalation(["we should probably look at this sometime"],
                          ESCALATION_PHRASES) is False

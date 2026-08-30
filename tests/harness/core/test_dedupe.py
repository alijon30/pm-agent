"""The rule that decides two sentences are one decision.

The restated pairs below are real: they came out of the first production call, where a model
faithfully extracted the same decision from two moments a minute apart. The pairs that must stay
apart are the reason the rule is not similarity alone — the sentences that share the most words
are often the ones that disagree."""

from app.harness.core.dedupe import (
    collapse,
    duplicate_of,
    near_duplicate,
    overlap,
    tokens,
    values,
)

RESTATED = (
    "Move payment reminders to three days after the due date.",
    "Move payment reminders to three days after due.",
)
SMS = (
    "Keep SMS reminders off for now.",
    "Keep SMS reminders off for now, email only.",
)


def test_the_same_decision_said_twice_in_one_call_is_one_decision() -> None:
    assert near_duplicate(*RESTATED)
    assert near_duplicate(*SMS)
    assert near_duplicate(
        "Ship the invoice CSV export behind a flag.", "Ship the invoice CSV export behind the flag"
    )


def test_a_different_number_is_a_different_decision_however_alike_the_words() -> None:
    """This pair scores higher than either real restatement above. Similarity alone would merge
    it and the ledger would lose whichever the team actually chose."""
    three, five = RESTATED[0], "Move payment reminders to five days after the due date."

    assert overlap(three, five) > overlap(*RESTATED)
    assert not near_duplicate(three, five)
    assert not near_duplicate("Charge a late fee of 2%.", "Charge a late fee of 5%.")


def test_a_different_name_is_a_different_decision_however_alike_the_words() -> None:
    priya = "Assign the overdue invoices dashboard for finance to Priya by Friday."
    nodir = "Assign the overdue invoices dashboard for finance to Nodir by Friday."

    assert overlap(priya, nodir) > 0.8
    assert not near_duplicate(priya, nodir)
    assert not near_duplicate(
        "File INV-27 for the reminders bug.", "File INV-28 for the reminders bug."
    )


def test_the_same_number_spelled_either_way_is_the_same_decision() -> None:
    assert values("Move reminders to three days.") == values("Move reminders to 3 days.")
    assert near_duplicate("Move reminders to three days after due.",
                          "Move reminders to 3 days after due.")


def test_word_order_and_punctuation_do_not_make_a_new_decision() -> None:
    assert near_duplicate("Reminders move to three days.", "reminders move to three days!!")
    assert tokens("Three days, after due.") == tokens("after due three days")


def test_an_opposite_decision_about_the_same_subject_stays_separate() -> None:
    assert not near_duplicate("Keep SMS reminders off for now.", "Turn SMS reminders on for now.")
    assert not near_duplicate("Ship the CSV export this week.", "Ship the CSV export next month.")


def test_an_empty_statement_matches_nothing_real() -> None:
    assert overlap("", "Move the reminders") == 0.0
    assert overlap("", "") == 1.0


def test_collapsing_keeps_the_earliest_of_each_cluster() -> None:
    """Earliest, because that is the id other documents already point at."""
    rows = [
        {"id": "d1", "statement": RESTATED[0]},
        {"id": "d2", "statement": RESTATED[1]},
        {"id": "d3", "statement": "Ship the CSV export behind a flag."},
        {"id": "d4", "statement": SMS[0]},
        {"id": "d5", "statement": SMS[1]},
    ]

    kept = collapse(rows, lambda r: str(r["statement"]))

    assert [r["id"] for r in kept] == ["d1", "d3", "d4"]


def test_finding_what_a_sentence_restates() -> None:
    rows = [{"id": "d1", "statement": RESTATED[0]}]

    assert (duplicate_of(RESTATED[1], rows) or {}).get("id") == "d1"
    assert duplicate_of("Ship the CSV export.", rows) is None

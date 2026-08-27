from app.harness.verify.evidence import check_evidence, normalize, quote_in_transcript

TRANSCRIPT = (
    "Let's move payment reminders to three days after the due date. Nodir, can you own that? "
    "Sure, I can have that done by next Friday. We considered SMS reminders — decided no for now."
)


def test_normalize_folds_case_whitespace_and_smart_punctuation() -> None:
    assert normalize("Let’s  MOVE “payment”\nreminders") == "let's move \"payment\" reminders"


def test_an_exact_quote_matches() -> None:
    assert quote_in_transcript("move payment reminders to three days", normalize(TRANSCRIPT))


def test_a_quote_with_different_casing_and_curly_quotes_still_matches() -> None:
    assert quote_in_transcript("Let’s move Payment Reminders", normalize(TRANSCRIPT))


def test_a_quote_spanning_two_speakers_matches_because_words_are_what_count() -> None:
    assert quote_in_transcript("can you own that? Sure, I can have", normalize(TRANSCRIPT))


def test_a_paraphrase_does_not_match() -> None:
    assert not quote_in_transcript("reminders will be sent after 3 days", normalize(TRANSCRIPT))


def test_a_trivially_short_quote_never_counts_as_evidence() -> None:
    assert not quote_in_transcript("Sure,", normalize(TRANSCRIPT))


def test_check_evidence_keeps_items_with_a_real_quote_and_drops_the_rest_with_a_reason() -> None:
    items = [
        {"title": "ok", "evidence": [{"quote": "I can have that done by next Friday"},
                                     {"quote": "this was never said in the call"}]},
        {"title": "hallucinated", "evidence": [{"quote": "we will ship SMS reminders in Q4"}]},
    ]
    verdict = check_evidence(items, TRANSCRIPT)
    assert [i["title"] for i in verdict.kept] == ["ok"]
    assert verdict.kept[0]["evidence"] == [{"quote": "I can have that done by next Friday"}]
    assert verdict.dropped[0]["title"] == "hallucinated"
    assert verdict.dropped[0]["gate_reason"] == "no verbatim quote found in transcript"

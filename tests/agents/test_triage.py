"""Triage is the one place a model failure is routine rather than exceptional, so almost all of
this is about what happens when the answer comes back wrong or not at all."""

from typing import Any

import pytest
from app.agents.triage import (
    INTENTS,
    SEGMENT_WINDOW,
    GemmaTriage,
    PassthroughTriage,
    parse_flags,
    parse_intent,
)


class FakeGemma:
    """A genai client stand-in: answers from a script, and records what it was asked."""

    def __init__(self, answers: list[str] | None = None, *, explode: bool = False) -> None:
        self.answers = list(answers or [])
        self.prompts: list[str] = []
        self.explode = explode
        outer = self

        class Models:
            async def generate_content(
                self, *, model: str, contents: str, config: dict[str, Any]
            ) -> Any:
                outer.prompts.append(contents)
                if outer.explode:
                    raise RuntimeError("503 from the model")
                answer = outer.answers.pop(0) if outer.answers else ""
                return type("Response", (), {"text": answer})()

        self.aio = type("Aio", (), {"models": Models()})()


def gemma(answers: list[str] | None = None, *, explode: bool = False) -> GemmaTriage:
    return GemmaTriage("gemma-4-31b-it", FakeGemma(answers, explode=explode))


def segments(count: int) -> list[dict[str, Any]]:
    return [{"speaker": "Maya Chen", "text": f"line {i}"} for i in range(count)]


# --- parsing what a model without structured output hands back -----------------------------------

def test_the_array_gemma_was_asked_for_is_read() -> None:
    assert parse_flags("[1,0,1]", 3) == [True, False, True]
    assert parse_flags("Here you go: [0, 1]  \n", 2) == [False, True]
    assert parse_flags("```json\n[1,1,1]\n```", 3) == [True, True, True]


def test_anything_that_is_not_that_array_is_refused_rather_than_guessed() -> None:
    assert parse_flags("", 3) is None
    assert parse_flags("I cannot help with that.", 3) is None
    assert parse_flags("[1,0]", 3) is None, "the wrong length is not a partial answer"
    assert parse_flags("[1,0,maybe]", 3) is None
    assert parse_flags("[[1],[0]]", 2) is None


def test_an_intent_is_read_leniently_from_whatever_wraps_it() -> None:
    assert parse_intent("report") == "report"
    assert parse_intent("  REPORT\n") == "report"
    assert parse_intent("The intent is: cancel.") == "cancel"
    assert parse_intent("This looks like noise to me") == "noise"


def test_the_first_intent_mentioned_is_the_answer() -> None:
    assert parse_intent("cancel the report") == "cancel"
    assert parse_intent("report, not a cancel") == "report"


def test_an_answer_naming_no_intent_defaults_to_helping() -> None:
    assert parse_intent("") == "request"
    assert parse_intent("I'm not sure what you mean.") == "request"


# --- keeping every segment -----------------------------------------------------------------------

async def test_segments_are_classified_in_windows() -> None:
    triage = gemma(["[1,0,1,1,0,1,0,1]", "[0,1]"])
    flags = await triage.decision_bearing(segments(10))

    assert flags == [True, False, True, True, False, True, False, True, False, True]
    assert len(triage._api().prompts) == 2  # noqa: SLF001 — asserting the batching, not the API


async def test_a_window_the_model_refused_is_kept_in_full() -> None:
    triage = gemma(["I cannot classify meeting transcripts.", "[0,0]"])
    flags = await triage.decision_bearing(segments(10))

    assert flags[:8] == [True] * 8, "a refusal must never drop a decision"
    assert flags[8:] == [False, False]


async def test_an_outage_keeps_everything_rather_than_losing_a_decision() -> None:
    triage = gemma(explode=True)
    assert await triage.decision_bearing(segments(5)) == [True] * 5


async def test_the_window_prompt_asks_for_exactly_as_many_answers_as_it_sends() -> None:
    triage = gemma(["[1,1,1]"])
    await triage.decision_bearing(segments(3))

    prompt = triage._api().prompts[0]  # noqa: SLF001
    assert "3 numbered lines" in prompt and "array of 3 integers" in prompt
    assert "When in doubt, answer 1" in prompt


def test_the_window_is_small_enough_that_one_failure_is_cheap() -> None:
    assert SEGMENT_WINDOW == 8


# --- what a mention wants --------------------------------------------------------------------------

async def test_an_intent_comes_back_as_one_of_the_words_the_router_knows() -> None:
    assert await gemma(["report"]).classify_intent("how are we doing?") in INTENTS


async def test_a_classifier_outage_still_tries_to_help() -> None:
    assert await gemma(explode=True).classify_intent("watch INV-26") == "request"


# --- the passthrough --------------------------------------------------------------------------------

async def test_the_passthrough_keeps_everything_and_claims_no_opinion() -> None:
    triage = PassthroughTriage()

    assert await triage.decision_bearing(segments(4)) == [True] * 4
    assert await triage.classify_intent("anything at all") == ""


def test_the_passthrough_and_gemma_answer_the_same_protocol() -> None:
    for name in ("decision_bearing", "classify_intent"):
        assert hasattr(PassthroughTriage(), name) and hasattr(gemma(), name)


@pytest.mark.live
async def test_the_real_gemma_finds_the_decisions_in_the_fixture_call() -> None:
    import os
    from pathlib import Path

    if not os.environ.get("GOOGLE_API_KEY"):
        pytest.skip("no GOOGLE_API_KEY")

    from app.config import Settings

    script = Path(__file__).parents[2] / "fixtures" / "transcripts" / "01-q3-planning.md"
    lines = [
        {"speaker": line[2:].split(":**", 1)[0], "text": line[2:].split(":**", 1)[1].strip()}
        for line in script.read_text().splitlines()
        if line.startswith("**") and ":**" in line
    ]
    flags = await GemmaTriage(Settings().model_triage).decision_bearing(lines)

    assert len(flags) == len(lines)
    kept = " ".join(s["text"] for s, keep in zip(lines, flags, strict=True) if keep).lower()
    assert "three days" in kept, "the planted decision must survive triage"
    assert sum(flags) < len(flags), "keeping literally everything means it did not filter"


def test_gemma_stays_on_the_gemini_api_when_the_agents_move_to_vertex(monkeypatch) -> None:
    """GOOGLE_GENAI_USE_VERTEXAI routes bare clients to Vertex, where Gemma does not live."""
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    triage = GemmaTriage()
    client = triage._api()
    assert client.vertexai is False

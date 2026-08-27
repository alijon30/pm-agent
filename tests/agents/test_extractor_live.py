"""Hits Gemini. Skipped unless GOOGLE_API_KEY is set. This is the one place we check that the
real model, the schema and the evidence gate agree on a real transcript."""

import os
from pathlib import Path

import pytest
from app.agents.base.schemas import ExtractResult
from app.agents.extractor import GeminiExtractor
from app.config import Settings
from app.harness.verify.evidence import check_evidence, normalize, quote_in_transcript

pytestmark = pytest.mark.live
live = pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="no GOOGLE_API_KEY")
SCRIPT = Path(__file__).parents[2] / "fixtures" / "transcripts" / "01-q3-planning.md"


def script_as_transcript() -> tuple[str, str]:
    """The rehearsal script doubles as a transcript: '**Name:** text' lines → segments."""
    rendered, plain = [], []
    for i, line in enumerate(SCRIPT.read_text().splitlines()):
        if line.startswith("**") and ":**" in line:
            name, text = line[2:].split(":**", 1)
            ts = f"00:{i // 60:02d}:{i % 60:02d}"
            rendered.append(f"[{ts}] {name.strip()}: {text.strip()}")
            plain.append(text.strip())
    return "\n".join(rendered), " ".join(plain)


@live
async def test_the_real_extractor_returns_schema_valid_items_with_verbatim_quotes() -> None:
    transcript, plain = script_as_transcript()
    extractor = GeminiExtractor(Settings.for_tests().model_fast)
    raw = await extractor.run({
        "transcript": transcript,
        "roster_names": ["Maya Chen", "Nodir Rahimov", "Priya Nair", "Tom Alvarez"],
        "feedback": None,
    })
    result = ExtractResult.model_validate(raw).model_dump()
    assert result["decisions"], "expected at least one decision from the planning call"
    assert result["action_items"], "expected at least one action item"
    verdict = check_evidence(result["action_items"], plain)
    assert len(verdict.kept) >= len(result["action_items"]) // 2, verdict.dropped
    assert any(
        quote_in_transcript(e["quote"], normalize(plain))
        for d in result["decisions"]
        for e in d["evidence"]
    )

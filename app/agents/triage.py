"""Triage: the cheap model that decides what is worth the expensive model's attention.

Two jobs, both classification, neither worth an agent loop. Gemma is called directly through the
GenAI SDK rather than through ADK: there are no tools to offer, no session to keep and no
structured output to enforce, so a runner would be scaffolding around a single request.

The failure posture is the interesting part, and it is deliberately different for each job:

- **Segment triage never loses content.** A window the model could not classify — a refusal, a
  malformed answer, a timeout — is kept in full. Dropping a segment silently loses a decision
  the team made; keeping one costs the extractor a few tokens.
- **Intent classification defaults to helping.** An unreadable answer becomes "request", because
  the worst outcome of guessing "request" is that the steward politely says it cannot help,
  while the worst outcome of guessing "noise" is ignoring a colleague."""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.base.sdk_runner import retrying

# Verified against scripts/list_models.py: this key serves gemma-4-26b-a4b-it and gemma-4-31b-it.
# The 31b is the one used — it is the larger dense model of the two this key can actually reach,
# and a classifier is the one place where being slightly slower and more literal is a virtue.
DEFAULT_TRIAGE_MODEL = "gemma-4-31b-it"

INTENTS = ("report", "request", "cancel", "noise")
SEGMENT_WINDOW = 8

SEGMENT_PROMPT = """You are filtering a meeting transcript so a slower model only reads the
parts that matter.

A line is WORTH KEEPING (1) if it contains, or is needed to understand, any of:
a decision, a commitment to do something, an owner being named, a date or deadline, a
disagreement, an open question, or a request.

A line is CHATTER (0) if it is greetings, scheduling small talk, thanks, or filler.

When in doubt, answer 1. Losing a decision is far worse than keeping a dull line.

Here are {count} numbered lines:

{lines}

Answer with ONLY a JSON array of {count} integers, each 0 or 1, in order. No prose, no code
fence. Example for 3 lines: [1,0,1]"""

INTENT_PROMPT = """Classify what this Slack message is asking a product-manager bot to do.

Answer with exactly ONE of these words and nothing else:

report  - they want a status report or summary of the project
cancel  - they want the bot to stop watching or drop something it is tracking
request - they are asking the bot to do, watch, or check something
noise   - thanks, greetings, jokes, or a message not addressed to the bot at all

Message: {text}

One word:"""


def parse_flags(text: str, count: int) -> list[bool] | None:
    """The JSON array Gemma was asked for, or None if what came back was not that.

    Gemma offers no structured-output guarantee, so this assumes nothing: it finds the first
    bracketed run, refuses anything that is not exactly `count` numbers, and hands the caller a
    None it knows how to fall back from."""
    match = re.search(r"\[[^\[\]]*\]", text or "")
    if match is None:
        return None
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, list) or len(raw) != count:
        return None
    try:
        return [bool(int(value)) for value in raw]
    except (TypeError, ValueError):
        return None


def parse_intent(text: str) -> str:
    """The first intent word the answer mentions. Lenient on purpose: "intent: report" and
    "This is a report request." both mean report, and an answer naming none of them means the
    model did not understand the question, which is not the sender's fault."""
    lowered = (text or "").strip().lower()
    found = [(lowered.find(intent), intent) for intent in INTENTS if intent in lowered]
    return min(found)[1] if found else "request"


class PassthroughTriage:
    """Keeps every segment and has no opinion about intent.

    The empty intent is not a classification, it is an abstention: the Slack route reads it as
    "nobody classified this" and falls back to matching keywords itself."""

    async def decision_bearing(self, segments: list[dict[str, Any]]) -> list[bool]:
        return [True] * len(segments)

    async def classify_intent(self, text: str) -> str:
        return ""


class GemmaTriage:
    """Implements the Triage protocol against a Gemma model on the Gemini API."""

    def __init__(self, model: str = DEFAULT_TRIAGE_MODEL, client: Any | None = None) -> None:
        self._model = model
        self._client = client

    def _api(self) -> Any:
        """Built on first use, not in __init__: constructing a client reads the environment, and
        wiring should not fail at import time on a machine with no key."""
        if self._client is None:
            from google import genai

            self._client = genai.Client()
        return self._client

    async def _ask(self, prompt: str, *, max_output_tokens: int) -> str:
        response = await self._api().aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config={"temperature": 0.0, "max_output_tokens": max_output_tokens},
        )
        return str(getattr(response, "text", "") or "")

    async def decision_bearing(self, segments: list[dict[str, Any]]) -> list[bool]:
        """One call per window of eight lines. Windows are independent, so a failure costs the
        filter one window's worth of precision and nothing else."""
        flags: list[bool] = []
        for start in range(0, len(segments), SEGMENT_WINDOW):
            flags.extend(await self._window(segments[start:start + SEGMENT_WINDOW]))
        return flags

    async def _window(self, window: list[dict[str, Any]]) -> list[bool]:
        lines = "\n".join(
            f"{i}. {segment.get('speaker', '?')}: {segment.get('text', '')}"
            for i, segment in enumerate(window)
        )
        prompt = SEGMENT_PROMPT.format(count=len(window), lines=lines)
        try:
            # Rate limits are worth waiting out here: this runs inside a stage, where a slow
            # answer costs nothing anyone is watching.
            answer = await retrying(lambda: self._ask(prompt, max_output_tokens=64))
        except Exception:  # noqa: BLE001 — every failure has the same safe answer
            return [True] * len(window)
        return parse_flags(answer, len(window)) or [True] * len(window)

    async def classify_intent(self, text: str) -> str:
        """What one Slack message wants. Deliberately not retried: this is on the path that owes
        Slack a response in three seconds, and a wrong-but-instant guess beats a right-but-late
        one when the fallback is a keyword match that was good enough yesterday."""
        try:
            answer = await self._ask(INTENT_PROMPT.format(text=text), max_output_tokens=8)
        except Exception:  # noqa: BLE001 — a classifier outage must not swallow a request
            return "request"
        return parse_intent(answer)

"""The extractor agent: reads a transcript, returns ExtractResult. No tools — it only reads."""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents import LlmAgent
from google.genai import types

from app.agents.base.schemas import ExtractResult
from app.agents.base.sdk_runner import run_agent_once

EXTRACTOR_INSTRUCTION = """You are the extraction step of an autonomous product-manager agent.

You receive JSON with:
- "transcript": lines formatted "[HH:MM:SS] Speaker: words"
- "roster_names": the people on this project
- "feedback": null, or a note about items that were rejected on a previous attempt

Extract three kinds of items and return ONLY the JSON schema you were given:
1. decisions — things the group settled on. Include options that were explicitly considered and
   rejected in rejected_options.
2. action_items — concrete work someone should do. title is imperative and under 80 characters.
   owner_name must be EXACTLY one of roster_names, or null if the person named is not on the
   roster or nobody was named. due_hint and priority_hint repeat the speaker's words verbatim
   (e.g. "by next Friday", "this is urgent"); null when nothing was said.
3. open_questions — questions raised and left unanswered.

EVIDENCE RULES (these are checked mechanically; items that fail are discarded):
- Every item MUST include at least one evidence entry.
- evidence.quote MUST be copied verbatim from the transcript: same words, same order, at least
  12 characters. Do not paraphrase, do not fix grammar, do not merge two sentences.
- Fill timestamp and speaker from the line the quote came from.
- When someone calls an item urgent — "urgent", "a blocker", "blocked", "p0", "asap" — attach
  THAT line as evidence on the item too, alongside the line that commits to the work. The two
  are usually said by different people a minute apart: one person says it is on fire, another
  says who will fix it. The urgency has to travel with the item it is about, because what is
  checked later is the item's own quotes, and a priority nobody can point at is dropped to an
  ordinary one.

Do not invent names, dates or identifiers. If the transcript contains no decisions or action
items, return empty lists. Prefer fewer, well-supported items over many weak ones."""


class GeminiExtractor:
    def __init__(self, model: str) -> None:
        self._agent = LlmAgent(
            name="extractor",
            model=model,
            instruction=EXTRACTOR_INSTRUCTION,
            output_schema=ExtractResult,
            include_contents="none",
            generate_content_config=types.GenerateContentConfig(
                temperature=0.1, max_output_tokens=8192
            ),
        )

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = await run_agent_once(self._agent, json.dumps(payload, ensure_ascii=False))
        parsed: dict[str, Any] = json.loads(text)
        return parsed

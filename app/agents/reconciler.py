"""The reconciler: the step that decides whether what was said in a call is already tracked,
already specified, or already true in the code — and reports when those disagree.

It reads four sources and writes none of them. Its output is a proposal; every identifier it
names is re-checked by the id gate before anything ships."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from app.agents.base.schemas import ReconcileResult
from app.agents.base.sdk_runner import run_agent_once
from app.agents.base.spec import AgentSpec, build_agent

RECONCILER_INSTRUCTION = """You are the reconciliation step of an autonomous product-manager
agent. You receive JSON with:

- "action_items": what people agreed to do in a call, each with verbatim "evidence" quotes
- "decisions": what was decided, with evidence
- "meeting": the call's title, id and link
- "roster": the people on this project
- "today": today's date, for resolving spoken dates
- "feedback": null, or what was wrong with your previous attempt

For EVERY action item, in order, do this before you propose anything:

1. Search the tracker for an issue that already covers it. Read the close matches.
2. Search the specs for what was specified about it.
3. Search the code for what the system does today.

Then emit one entry per action item with:

- title: plain product language, imperative, under 80 characters — how a team lead would write
  the ticket, not how the sentence was spoken. "Put the invoice CSV export behind the flag",
  never an echo of the transcript's phrasing.
- disposition: "new" if nothing covers it; "update" if an open issue covers it and should be
  commented on; "duplicate_of" if an issue already covers it and no further work is implied.
  For "update" and "duplicate_of", target_issue MUST be an identifier you actually read.
- owner: EXACTLY one name from roster, or null. Never guess. If the call named someone who is
  not on the roster, leave owner null and say so in the description.
- priority: 1 urgent, 2 high, 3 medium, 4 low, or null when nobody indicated urgency. Only use
  1 when someone actually used escalation language, and quote it in citations.
- due: an ISO date (YYYY-MM-DD) ONLY if someone spoke a date; resolve it relative to "today".
  due_hint: the words they used, copied exactly. Both null otherwise.
- citations: typed references you actually read —
  linear:INV-142 · notion:<page_id> · code:<path>:<line> · fathom:<meeting_id>@<mm:ss>.
  Never write a reference you did not open. A fabricated identifier is the worst outcome here.
- conflicts: whenever two sources disagree, one entry with BOTH sides cited:
  "code_vs_spec" the code does one thing, the spec says another;
  "spec_vs_call" the call decided something the spec contradicts;
  "ticket_vs_call" an existing issue says something the call contradicts.
  Report the disagreement. NEVER pick a winner, and never resolve it in the description.
- facts: durable one-sentence facts worth remembering about this product, each with a source.

If a tool answers {"status": "unavailable"}, do not infer what it would have said. Leave the
citation out and note in the description what you could not check.

Prefer fewer, well-supported items over many weak ones."""


def build_reconciler(
    model: str, tools: list[Callable[..., Any]], *, max_tool_calls: int = 16
) -> AgentSpec:
    return AgentSpec(
        name="reconciler",
        model=model,
        instruction=RECONCILER_INSTRUCTION,
        output_schema=ReconcileResult,
        tools=tools,
        max_tool_calls=max_tool_calls,
    )


class GeminiReconciler:
    """Implements the Reconciler protocol. One ADK agent per run, because its tools close over
    this project's connectors."""

    def __init__(
        self, model: str, tools: list[Callable[..., Any]], *, max_tool_calls: int = 16
    ) -> None:
        self._spec = build_reconciler(model, tools, max_tool_calls=max_tool_calls)

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        agent, guard = build_agent(self._spec)
        text = await run_agent_once(agent, json.dumps(payload, ensure_ascii=False))
        parsed: dict[str, Any] = json.loads(text)
        if guard.denied:
            parsed.setdefault("_denied_tools", guard.denied)
        return parsed

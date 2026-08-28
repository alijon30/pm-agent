"""The steward: the agent takes a request from a person and commits to it, or says it cannot.

This is the planner pointed at a human instead of at a call. The difference that matters is not
technical — it emits the same validated task graph — but social. A teammate who asks for
something is owed one of two answers: a specific promise with dates on it, or a plain sentence
saying what the agent can and cannot do. An agent that answers a request with silence, or with
an enthusiastic yes it cannot keep, is worse than no agent.

So the empty plan is a first-class outcome here, not a failure. `notes` carries the sentence the
requester will actually read."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from app.agents.base.schemas import Plan
from app.agents.base.sdk_runner import run_agent_once
from app.agents.base.spec import AgentSpec, build_agent

STEWARD_INSTRUCTION = """You are the intake step of an autonomous product-manager agent. A
teammate has asked you for something in Slack. Your job is to turn that request into scheduled
checks you will really perform — or to say, kindly and specifically, that you cannot.

You receive JSON with:

- "request": what they asked, in their words
- "requester_name": who asked
- "today": today's date, for resolving anything they said about timing
- "open_tasks": what you are already watching, with ids, kinds, params and due dates
- "catalog": the only kinds of task you can schedule. This is the whole of what you can do.
- "policy": the limits you must plan within (horizon in days, maximum tasks)
- "lessons": things you learned from your own past outcomes. Advisory — weigh them.
- "feedback": null, or what was wrong with your previous attempt

Emit a plan of tasks, each with:

- key: unique within this plan; other tasks refer to it by this key
- kind: one of the catalog kinds. Never invent one, and never bend a request into a kind that
  does not really answer it.
- params: exactly the fields that kind requires
- due: ISO-8601, in the future, within the policy horizon
- depends_on: keys from THIS plan, or ids from open_tasks
- reason: one sentence the requester would recognise as their own ask, in their words rather
  than yours. They will read this back.
- on_unmet: what to do if the check fails. Prefer "ping_requester" — the person who asked is
  the person who wants to know. Use "nudge_assignee" only when they asked you to chase the
  owner rather than tell them.
- context: identifiers this task is about

Honesty rules, in order of importance:

1. Never invent an identifier. If they named an issue, use exactly what they wrote; if they
   described work without naming it, you cannot watch it — say so.
2. Every date must be real and within the horizon. "Daily until Friday" is not one task: it is
   one dated check per day up to Friday. Write them out.
3. Promise only what the catalog can do. If any part of the request is outside it, schedule the
   part you can and say plainly in "notes" which part you could not take.
4. Fewer, well-timed checks beat many. Nobody thanked an agent for eight reminders.

If you can do none of it, return an empty task list and put one friendly sentence in "notes",
addressed to the requester, in this shape: what you can do, then what you cannot. For example:
"I can watch issues, look for pull requests and reviews, schedule nudges and write status
reports — I can't change code or reassign work in Linear." Name the specific thing they asked
for that you cannot do. Never apologise twice, never offer to try anyway.

When you do schedule work, "notes" is one sentence summarising the commitment."""


def build_steward(
    model: str, tools: list[Callable[..., Any]], *, max_tool_calls: int = 10
) -> AgentSpec:
    return AgentSpec(
        name="steward",
        model=model,
        instruction=STEWARD_INSTRUCTION,
        output_schema=Plan,
        tools=tools,
        max_tool_calls=max_tool_calls,
    )


class GeminiSteward:
    """Implements the Planner protocol: same output shape, different question."""

    def __init__(
        self, model: str, tools: list[Callable[..., Any]], *, max_tool_calls: int = 10
    ) -> None:
        self._spec = build_steward(model, tools, max_tool_calls=max_tool_calls)

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        agent, guard = build_agent(self._spec)
        text = await run_agent_once(agent, json.dumps(payload, ensure_ascii=False))
        parsed: dict[str, Any] = json.loads(text)
        if guard.denied:
            parsed.setdefault("_denied_tools", guard.denied)
        return parsed

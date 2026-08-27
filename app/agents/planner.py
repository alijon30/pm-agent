"""The planner: the agent decides what it will check, and when.

This is the closest the system comes to letting a model drive, so the boundary is worth stating
plainly. The planner never enqueues anything. It emits a task graph as structured output; the
plan gate decides which of those tasks are real; the queue materialises the survivors in one
transaction. The model gets the judgment — what to watch, in what order, how long to wait — and
none of the authority."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from app.agents.base.schemas import Plan
from app.agents.base.sdk_runner import run_agent_once
from app.agents.base.spec import AgentSpec, build_agent

PLANNER_INSTRUCTION = """You are the planning step of an autonomous product-manager agent. Your
job is to decide what this agent should check later, and in what order, so that work agreed in a
call actually happens.

You receive JSON with:

- "context": what was just filed or updated — issues, owners, due dates — or, for a daily
  review, the current state of the project
- "open_tasks": checks already scheduled, with their ids, kinds, params and due dates
- "recent_results": what recent checks observed, including anything that came back unmet
- "policy": the limits you must plan within (horizon in days, maximum tasks, default offsets)
- "now": the current time, ISO-8601
- "feedback": null, or what was wrong with your previous plan

Emit a plan of tasks. Each task has:

- key: unique within this plan; other tasks refer to it by this key
- kind: one of the catalog kinds you were given. Never invent one.
- params: exactly the fields that kind requires
- due: ISO-8601, in the future, within the policy horizon
- depends_on: keys from THIS plan, or ids from open_tasks. A check that only makes sense after
  another has passed MUST depend on it — do not check for a pull request before the issue is in
  progress, and do not check for a review before a pull request exists.
- reason: one sentence a human would accept as an explanation
- on_unmet: what to do if the check fails — only a value that kind allows
- context: identifiers this task is about

Principles:

- Plan backwards from the commitment. If someone said "by Friday", the last check is on Friday,
  and the earlier ones are spaced so there is still time to react.
- Do not schedule two checks that would observe the same thing at the same time.
- If an open task already covers something, leave it alone. If reality has moved past an open
  task, list its id in "supersedes" — it will be cancelled.
- Fewer, well-timed checks beat many. A person who gets nudged about everything stops reading.
- Use "notes" to say what you observed in one or two sentences.

If nothing needs checking, return an empty task list. That is a valid plan."""


def build_planner(
    model: str, tools: list[Callable[..., Any]], *, max_tool_calls: int = 10
) -> AgentSpec:
    return AgentSpec(
        name="planner",
        model=model,
        instruction=PLANNER_INSTRUCTION,
        output_schema=Plan,
        tools=tools,
        max_tool_calls=max_tool_calls,
    )


class GeminiPlanner:
    """Implements the Planner protocol."""

    def __init__(
        self, model: str, tools: list[Callable[..., Any]], *, max_tool_calls: int = 10
    ) -> None:
        self._spec = build_planner(model, tools, max_tool_calls=max_tool_calls)

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        agent, guard = build_agent(self._spec)
        text = await run_agent_once(agent, json.dumps(payload, ensure_ascii=False))
        parsed: dict[str, Any] = json.loads(text)
        if guard.denied:
            parsed.setdefault("_denied_tools", guard.denied)
        return parsed

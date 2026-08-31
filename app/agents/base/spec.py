"""How an agent is declared, and the one place a tool allow-list is enforced.

Every agent is a name, a model, an instruction, a set of read-only tools and a fixed output
schema — plus budgets, so a confused run costs a bounded amount. `build_agent` attaches a
`before_tool_callback` that refuses any tool outside the spec: the tool list already omits
writers, and this refuses them again in code the prompt cannot reach."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from google.adk.agents import LlmAgent
from google.genai import types
from pydantic import BaseModel

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentSpec:
    name: str
    model: str
    instruction: str | Callable[[Any], str]
    output_schema: type[BaseModel]
    tools: list[Callable[..., Any]] = field(default_factory=list)
    max_tool_calls: int = 12
    max_output_tokens: int = 8192
    temperature: float = 0.1


# ADK delivers structured output by calling a synthetic tool of its own when an agent has both
# an output_schema and real tools. It is the framework talking to itself, not the model reaching
# for something, so the guard must let it through — denying it silently empties the response.
ADK_INTERNAL_TOOLS = frozenset({"set_model_response", "transfer_to_agent", "exit_loop"})


class ToolGuard:
    """Denies tools outside the allow-list and stops a run that will not stop calling them.

    Returning a dict from before_tool_callback skips the tool and hands the model that dict as
    the result, so a denied call becomes a visible refusal in the transcript rather than a
    crash — the run continues and usually recovers."""

    def __init__(self, allowed: set[str], max_calls: int) -> None:
        self._allowed = allowed
        self._max_calls = max_calls
        self.calls = 0
        self.denied: list[str] = []

    def __call__(self, tool: Any, args: dict[str, Any], tool_context: Any) -> dict[str, Any] | None:
        name = getattr(tool, "name", "") or getattr(tool, "__name__", "")
        if name in ADK_INTERNAL_TOOLS:
            return None
        if name not in self._allowed:
            self.denied.append(name)
            log.warning("tool %r denied: not in the agent's allow-list", name)
            return {"status": "denied", "error": f"tool {name!r} is not available to this agent"}
        self.calls += 1
        if self.calls > self._max_calls:
            self.denied.append(name)
            return {
                "status": "denied",
                "error": f"tool call budget of {self._max_calls} exhausted; answer with what "
                         "you have and say what you could not verify",
            }
        return None


def _content_config(spec: AgentSpec) -> types.GenerateContentConfig:
    """One environment switch turns reasoning on for every agent at once.

    PM_THINKING_BUDGET is a token budget for the model's own deliberation (0 = off). It lives
    in the environment rather than on each spec because it is a deployment posture, not an
    agent trait: off on the free tier where every token is rationed, on in production where
    judgment is worth more than latency."""
    budget = int(os.environ.get("PM_THINKING_BUDGET", "0") or "0")
    thinking = types.ThinkingConfig(thinking_budget=budget) if budget > 0 else None
    return types.GenerateContentConfig(
        temperature=spec.temperature, max_output_tokens=spec.max_output_tokens,
        thinking_config=thinking,
    )


def build_agent(spec: AgentSpec) -> tuple[LlmAgent, ToolGuard]:
    """The agent and the guard that is watching it. The guard is returned so a caller can see
    what was denied after the run."""
    guard = ToolGuard({getattr(t, "__name__", "") for t in spec.tools}, spec.max_tool_calls)
    agent = LlmAgent(
        name=spec.name,
        model=spec.model,
        instruction=spec.instruction,
        tools=list(spec.tools),
        output_schema=spec.output_schema,
        include_contents="none",
        before_tool_callback=guard,
        generate_content_config=_content_config(spec),
    )
    return agent, guard

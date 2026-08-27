"""One-shot ADK execution: fresh in-memory session per call, return the final text. Firestore
is the source of truth for everything durable; ADK session state is scratch."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

APP_NAME = "pm-agent"
USER_ID = "harness"


async def run_agent_once(
    agent: LlmAgent, message: str, *, state: dict[str, Any] | None = None
) -> str:
    sessions = InMemorySessionService()
    session = await sessions.create_session(app_name=APP_NAME, user_id=USER_ID, state=state or {})
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=sessions)
    content = types.Content(role="user", parts=[types.Part(text=message)])
    final = ""
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session.id, new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final = "".join(part.text or "" for part in event.content.parts)
    return final

"""One-shot ADK execution: fresh in-memory session per call, return the final text."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

log = logging.getLogger(__name__)

APP_NAME = "pm-agent"
USER_ID = "harness"

# The free tier's per-minute window resets quickly; the last delay covers a full window.
RATE_LIMIT_DELAYS: tuple[float, ...] = (10.0, 30.0, 65.0)


def is_rate_limited(exc: BaseException) -> bool:
    """Walk the exception chain looking for a 429. ADK wraps the genai ClientError, so the
    match is on the chain's text rather than any one exception type."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        text = f"{type(current).__name__}: {current}"
        if "429" in text or "RESOURCE_EXHAUSTED" in text.upper():
            return True
        current = current.__cause__ or current.__context__
    return False


async def retrying[T](
    attempt: Callable[[], Awaitable[T]],
    *,
    delays: Sequence[float] = RATE_LIMIT_DELAYS,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Run `attempt`, waiting out rate limits. Any other failure propagates immediately, and so
    does a rate limit that outlasts every delay — the queue's backoff takes over from there."""
    for delay in delays:
        try:
            return await attempt()
        except Exception as exc:  # noqa: BLE001 — is_rate_limited decides what is retryable
            if not is_rate_limited(exc):
                raise
            log.warning("rate limited; retrying in %.0fs", delay)
            await sleep(delay)
    return await attempt()


async def run_agent_once(
    agent: LlmAgent, message: str, *, state: dict[str, Any] | None = None
) -> str:
    async def attempt() -> str:
        sessions = InMemorySessionService()
        session = await sessions.create_session(
            app_name=APP_NAME, user_id=USER_ID, state=state or {}
        )
        runner = Runner(agent=agent, app_name=APP_NAME, session_service=sessions)
        content = types.Content(role="user", parts=[types.Part(text=message)])
        final = ""
        async for event in runner.run_async(
            user_id=USER_ID, session_id=session.id, new_message=content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final = "".join(part.text or "" for part in event.content.parts)
        return final

    return await retrying(attempt)

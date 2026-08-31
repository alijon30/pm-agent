"""Ask this same instance to run a tick right now, instead of waiting for the scheduler.

The once-a-minute tick is the guarantee; this is only an accelerator, so a poke that never
lands costs nothing but the wait it would have saved."""

from __future__ import annotations

import asyncio
import logging
import os

import httpx

log = logging.getLogger(__name__)


def poke_tick(token: str) -> None:
    """Fire-and-forget loopback POST /tick, so freshly queued work starts in seconds."""
    if not token:
        return

    async def _post() -> None:
        url = f"http://127.0.0.1:{os.environ.get('PORT', '8080')}/tick"
        try:
            async with httpx.AsyncClient(timeout=70) as client:
                await client.post(url, headers={"x-tick-token": token})
        except Exception as exc:  # noqa: BLE001 — an accelerator never gets to break anything
            log.info("tick poke did not land: %s", exc)

    try:
        asyncio.get_running_loop().create_task(_post())
    except RuntimeError:
        pass

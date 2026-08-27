"""In-memory Slack. Records what was posted, edited and opened so tests assert on the exact
message the team would see."""

from __future__ import annotations

import copy
from typing import Any


class FakeSlack:
    def __init__(self, users: dict[str, dict[str, Any]] | None = None) -> None:
        self.posts: list[dict[str, Any]] = []
        self.updates: list[dict[str, Any]] = []
        self.modals: list[dict[str, Any]] = []
        self._users = copy.deepcopy(users or {})
        self._ts = 1_787_821_200

    async def post(
        self,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        *,
        thread_ts: str | None = None,
    ) -> str:
        self._ts += 1
        ts = f"{self._ts}.000100"
        self.posts.append({"channel": channel, "text": text, "blocks": blocks or [],
                           "thread_ts": thread_ts, "ts": ts})
        return ts

    async def update(
        self, channel: str, ts: str, text: str, blocks: list[dict[str, Any]] | None = None
    ) -> None:
        self.updates.append({"channel": channel, "ts": ts, "text": text, "blocks": blocks})

    async def open_modal(self, trigger_id: str, view: dict[str, Any]) -> None:
        self.modals.append({"trigger_id": trigger_id, "view": view})

    async def user_info(self, user_id: str) -> dict[str, Any] | None:
        user = self._users.get(user_id)
        return copy.deepcopy(user) if user is not None else None

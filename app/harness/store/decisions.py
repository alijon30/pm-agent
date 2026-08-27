"""Decision ledger. Full implementation in Task 10."""

from __future__ import annotations

from typing import Any

from app.harness.core.clock import Clock
from app.harness.store.db import Db


class DecisionStore:
    def __init__(self, db: Db, clock: Clock) -> None:
        self._db = db
        self._clock = clock

    async def add_many(
        self, project_id: str, event_id: str, decisions: list[dict[str, Any]], meeting: dict[str, Any]
    ) -> list[str]:
        raise NotImplementedError

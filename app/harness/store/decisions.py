"""Decision ledger: every decision a call produced, with the exact moment it was said. Started
in v0 so it is queryable later; nothing reads it yet except the report stage (Plan 4)."""

from __future__ import annotations

from typing import Any

from app.harness.core.clock import Clock, iso
from app.harness.core.keys import new_id
from app.harness.store.db import Db


class DecisionStore:
    def __init__(self, db: Db, clock: Clock) -> None:
        self._db = db
        self._clock = clock

    async def add_many(
        self,
        project_id: str,
        event_id: str,
        decisions: list[dict[str, Any]],
        meeting: dict[str, Any],
    ) -> list[str]:
        ids: list[str] = []
        now = iso(self._clock.now())
        for d in decisions:
            first = (d.get("evidence") or [{}])[0]
            doc_id = new_id()
            await self._db.create("decisions", doc_id, {
                "statement": d["statement"],
                "rejected_options": list(d.get("rejected_options") or []),
                "source": f"fathom:{meeting['meeting_id']}@{first.get('timestamp', '')}",
                "quote": first.get("quote", ""),
                "meeting_title": meeting.get("title", ""),
                "meeting_url": meeting.get("url", ""),
                "linked_issue_ids": [],
                "project_id": project_id,
                "event_id": event_id,
                "created_at": now,
            })
            ids.append(doc_id)
        return ids

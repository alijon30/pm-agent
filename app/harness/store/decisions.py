"""Decision ledger: every decision a call produced, with the exact moment it was said."""

from __future__ import annotations

from typing import Any

from app.harness.core.clock import Clock, iso
from app.harness.core.dedupe import duplicate_of
from app.harness.core.keys import new_id
from app.harness.store.db import Db, Doc


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
        # Read once: each new statement is checked against everything the project holds.
        existing = await self._db.query("decisions", [("project_id", "==", project_id)])
        for d in decisions:
            first = (d.get("evidence") or [{}])[0]
            source = f"fathom:{meeting['meeting_id']}@{first.get('timestamp', '')}"

            said_before = duplicate_of(str(d["statement"]), existing)
            if said_before is not None:
                # Said again: the earlier entry keeps its id and gains the second moment.
                ids.append(str(said_before["id"]))
                await self._also_quoted(said_before, first.get("quote", ""), source)
                continue

            doc_id = new_id()
            await self._db.create("decisions", doc_id, {
                "statement": d["statement"],
                "rejected_options": list(d.get("rejected_options") or []),
                "source": source,
                "quote": first.get("quote", ""),
                "also_quoted": [],
                "meeting_title": meeting.get("title", ""),
                "meeting_url": meeting.get("url", ""),
                "linked_issue_ids": [],
                "project_id": project_id,
                "event_id": event_id,
                "created_at": now,
            })
            ids.append(doc_id)
            existing.append({"id": doc_id, "statement": d["statement"], "also_quoted": []})
        return ids

    async def _also_quoted(self, decision: Doc, quote: str, source: str) -> None:
        """A second moment the same decision was made, kept beside the first. Nothing is
        overwritten: the ledger only ever gains evidence."""
        if not quote:
            return
        already = list(decision.get("also_quoted") or [])
        if any(str(e.get("source")) == source for e in already):
            return
        already.append({"quote": quote, "source": source})
        await self._db.update("decisions", str(decision["id"]), {"also_quoted": already})

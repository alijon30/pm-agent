"""Inbound events. The doc id is provider:provider_event_id, so create() failing IS the dedupe."""

from __future__ import annotations

from typing import Any

from app.harness.core.clock import Clock, iso
from app.harness.core.keys import event_doc_id
from app.harness.store.db import Db, Doc


class EventStore:
    def __init__(self, db: Db, clock: Clock) -> None:
        self._db = db
        self._clock = clock

    async def record(
        self, *, provider: str, provider_event_id: str, payload: dict[str, Any], project_id: str
    ) -> str | None:
        """The event id if this is the first delivery; None if we have seen it before."""
        doc_id = event_doc_id(provider, provider_event_id)
        created = await self._db.create("events", doc_id, {
            "provider": provider,
            "provider_event_id": provider_event_id,
            "payload": payload,
            "project_id": project_id,
            "received_at": iso(self._clock.now()),
            "notes": [],
        })
        return doc_id if created else None

    async def get(self, event_id: str) -> Doc | None:
        return await self._db.get("events", event_id)

    async def note(self, event_id: str, note: str) -> None:
        current = await self._db.get("events", event_id)
        notes = list((current or {}).get("notes") or [])
        notes.append(note)
        await self._db.update("events", event_id, {"notes": notes})

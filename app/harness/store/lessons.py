"""What the agent learned about its own behaviour, from watching what its behaviour caused."""

from __future__ import annotations

from app.harness.core.clock import Clock, iso
from app.harness.core.keys import new_id
from app.harness.store.db import Db, Doc

MAX_LESSONS = 12


class LessonStore:
    def __init__(self, db: Db, clock: Clock) -> None:
        self._db = db
        self._clock = clock

    async def add(
        self,
        *,
        project_id: str,
        text: str,
        evidence: list[str],
        source_task_id: str = "",
    ) -> str:
        """File one lesson and drop the oldest beyond the cap. Returns the new lesson's id."""
        existing = await self._all(project_id)
        # created_at has second precision; seq is the tiebreak and only ever goes up.
        sequence = max((int(row.get("seq", 0)) for row in existing), default=-1) + 1
        lesson_id = new_id()
        await self._db.create("lessons", lesson_id, {
            "text": text,
            "evidence": list(evidence),
            "project_id": project_id,
            "source_task_id": source_task_id,
            "seq": sequence,
            "created_at": iso(self._clock.now()),
        })
        for stale in (await self._all(project_id))[:-MAX_LESSONS]:
            await self.delete(stale["id"])
        return lesson_id

    async def for_project(self, project_id: str) -> list[Doc]:
        """Newest first — the order a prompt should read them in."""
        return list(reversed(await self._all(project_id)))

    async def delete(self, lesson_id: str) -> None:
        await self._db.delete("lessons", lesson_id)

    async def _all(self, project_id: str) -> list[Doc]:
        """Oldest first, sorted here rather than by the database."""
        rows = await self._db.query("lessons", [("project_id", "==", project_id)])
        return sorted(rows, key=lambda row: (str(row.get("created_at") or ""),
                                             int(row.get("seq", 0))))

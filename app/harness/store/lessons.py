"""What the agent learned about its own behaviour, from watching what its behaviour caused.

A lesson is not a fact about the product — that would be the brain's job — and it is not a rule.
It is one sentence about how this agent should plan and interrupt people, derived from outcomes
it can point at: a nudge that moved something, a check that fired at the wrong hour, a plan that
was superseded the next morning. Every lesson cites the tasks and actions it came from, and the
review stage refuses to store one whose citations it cannot find in the evidence it gathered.

The cap is deliberate and small. Twelve sentences is roughly what fits in a prompt without
crowding out the actual question, and an agent carrying a hundred accumulated opinions about
itself is one nobody can predict. The oldest fall off; nothing is edited in place."""

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
        # created_at has second precision, so a review that files three lessons at once needs a
        # tiebreak that is not chance. The sequence only ever goes up, including after deletes.
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
        """Oldest first. Sorted here rather than by the database: `seq` is what makes the order
        total, and no index needs to exist for a collection this small."""
        rows = await self._db.query("lessons", [("project_id", "==", project_id)])
        return sorted(rows, key=lambda row: (str(row.get("created_at") or ""),
                                             int(row.get("seq", 0))))

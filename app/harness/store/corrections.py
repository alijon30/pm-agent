"""Corrections: what a human told the agent it got wrong.

A correction is not a rule the model may reinterpret — it is stored with the situation it
applies to, and later runs receive only the corrections whose matcher fits. The important part
is that a correction, once given, does not have to be given again."""

from __future__ import annotations

from app.harness.core.clock import Clock, iso
from app.harness.core.keys import new_id
from app.harness.store.db import Db, Doc

STAGES = ("extract", "reconcile", "plan", "report", "any")


def matcher_for(wrong: str, right: str) -> list[str]:
    """The words that decide whether this correction is relevant later. Crude on purpose: a
    correction that fires slightly too often is a smaller problem than one that never fires."""
    words = {
        w.strip(".,;:!?\"'").lower()
        for w in f"{wrong} {right}".split()
        if len(w.strip(".,;:!?\"'")) > 4
    }
    return sorted(words)[:12]


class CorrectionStore:
    def __init__(self, db: Db, clock: Clock) -> None:
        self._db = db
        self._clock = clock

    async def add(
        self,
        *,
        project_id: str,
        wrong: str,
        right: str,
        scope: str = "project",
        stage: str = "any",
        source_action_id: str | None = None,
        author: str = "",
    ) -> str:
        correction_id = new_id()
        await self._db.create("corrections", correction_id, {
            "project_id": project_id,
            "scope": scope if scope in ("project", "global") else "project",
            "stage": stage if stage in STAGES else "any",
            "wrong": wrong,
            "right": right,
            "matcher": matcher_for(wrong, right),
            "source_action_id": source_action_id,
            "author_slack_id": author,
            "created_at": iso(self._clock.now()),
        })
        return correction_id

    async def for_stage(self, project_id: str, stage: str) -> list[Doc]:
        """Everything that could apply to this stage of this project, newest last so a later
        correction wins when two disagree."""
        rows = await self._db.query("corrections", [], order_by="created_at")
        return [
            r for r in rows
            if (r.get("scope") == "global" or r.get("project_id") == project_id)
            and r.get("stage") in (stage, "any")
        ]

"""Project configuration: roster, policy, and the ids of the external workspaces."""

from __future__ import annotations

from typing import Any

from app.harness.core.errors import PmError
from app.harness.store.db import Db, Doc


class ProjectStore:
    def __init__(self, db: Db, default_slug: str) -> None:
        self._db = db
        self._default_slug = default_slug

    async def get(self, slug: str) -> Doc | None:
        return await self._db.get("projects", slug)

    async def default(self) -> Doc:
        """Fails closed: with no configured project there is no roster and no policy, and
        nothing may run without those."""
        doc = await self.get(self._default_slug)
        if doc is None:
            raise PmError(f"default project {self._default_slug!r} is not seeded")
        return doc

    async def upsert(self, slug: str, data: dict[str, Any]) -> None:
        await self._db.set("projects", slug, {**data, "slug": slug})

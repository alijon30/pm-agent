"""In-memory Notion. Pages keyed by id; each is {"title", "url", "markdown", "children": [ids]}."""

from __future__ import annotations

import copy
from typing import Any


class FakeNotion:
    def __init__(self, pages: dict[str, dict[str, Any]] | None = None) -> None:
        self._pages = copy.deepcopy(pages or {})

    async def search(self, text: str, *, limit: int = 5) -> list[dict[str, Any]]:
        needle = text.lower()
        hits = [
            {"id": pid, "title": page.get("title", ""), "url": page.get("url", "")}
            for pid, page in self._pages.items()
            if needle in page.get("title", "").lower()
            or needle in page.get("markdown", "").lower()
        ]
        return hits[:limit]

    async def get_page_text(self, page_id: str) -> dict[str, Any] | None:
        page = self._pages.get(page_id)
        if page is None:
            return None
        return {
            "id": page_id,
            "title": page.get("title", ""),
            "url": page.get("url", ""),
            "markdown": page.get("markdown", ""),
        }

    async def list_children(self, page_id: str) -> list[dict[str, Any]]:
        page = self._pages.get(page_id)
        if page is None:
            return []
        return [
            {"id": child, "title": self._pages.get(child, {}).get("title", "")}
            for child in page.get("children", [])
        ]

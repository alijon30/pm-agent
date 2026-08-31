"""Notion over the REST API."""

from __future__ import annotations

from typing import Any

import httpx

from app.harness.core.errors import SourceUnavailable
from app.harness.core.redact import redact

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"

# block type -> markdown prefix. Types absent here contribute their plain text only.
_PREFIX = {
    "heading_1": "# ",
    "heading_2": "## ",
    "heading_3": "### ",
    "bulleted_list_item": "- ",
    "numbered_list_item": "1. ",
    "to_do": "- [ ] ",
    "quote": "> ",
    "code": "    ",
}


def rich_text(parts: list[dict[str, Any]] | None) -> str:
    """Notion returns text as a list of annotated runs; we keep the words, drop the styling."""
    return "".join(p.get("plain_text") or "" for p in parts or [])


def title_of(page: dict[str, Any]) -> str:
    """A page's title lives under a differently-named property per database, so find the one
    whose type is `title` rather than guessing the key."""
    for prop in (page.get("properties") or {}).values():
        if prop.get("type") == "title":
            return rich_text(prop.get("title"))
    return rich_text((page.get("title") or []) if isinstance(page.get("title"), list) else [])


def blocks_to_markdown(blocks: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for block in blocks:
        kind = block.get("type") or ""
        body = block.get(kind) or {}
        text = rich_text(body.get("rich_text"))
        if not text:
            continue
        lines.append(f"{_PREFIX.get(kind, '')}{text}")
    return "\n".join(lines)


class NotionClient:
    def __init__(self, token: str, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": VERSION,
            "Content-Type": "application/json",
        }
        self._transport = transport

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=20) as client:
                resp = await client.request(
                    method, f"{API}{path}", headers=self._headers, **kwargs
                )
        except httpx.HTTPError as exc:
            raise SourceUnavailable("notion", redact(str(exc))) from exc
        if resp.status_code == 404:
            raise _NotFound(path)
        if resp.status_code >= 400:
            raise SourceUnavailable("notion", f"HTTP {resp.status_code}")
        payload: dict[str, Any] = resp.json()
        return payload

    async def search(self, text: str, *, limit: int = 5) -> list[dict[str, Any]]:
        data = await self._request(
            "POST", "/search",
            json={"query": text, "page_size": limit,
                  "filter": {"property": "object", "value": "page"}},
        )
        return [
            {"id": r.get("id") or "", "title": title_of(r), "url": r.get("url") or ""}
            for r in data.get("results") or []
        ]

    async def get_page_text(self, page_id: str) -> dict[str, Any] | None:
        """Page metadata plus its top-level blocks as markdown. None when the page is gone."""
        try:
            page = await self._request("GET", f"/pages/{page_id}")
            blocks = await self._request(
                "GET", f"/blocks/{page_id}/children", params={"page_size": 100}
            )
        except _NotFound:
            return None
        return {
            "id": page.get("id") or page_id,
            "title": title_of(page),
            "url": page.get("url") or "",
            "markdown": blocks_to_markdown(blocks.get("results") or []),
        }

    async def list_children(self, page_id: str) -> list[dict[str, Any]]:
        """Child pages only."""
        try:
            data = await self._request(
                "GET", f"/blocks/{page_id}/children", params={"page_size": 100}
            )
        except _NotFound:
            return []
        return [
            {"id": b.get("id") or "", "title": rich_text((b.get("child_page") or {}).get("title"))
             if isinstance((b.get("child_page") or {}).get("title"), list)
             else ((b.get("child_page") or {}).get("title") or "")}
            for b in data.get("results") or []
            if b.get("type") == "child_page"
        ]


class _NotFound(Exception):
    """Internal: a 404 from Notion. Never escapes this module."""

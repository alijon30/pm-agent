"""The read-only tools an agent may call.

The tool docstrings below are model-facing: ADK sends them to the model as the tool
schema. They are API, not comments — do not trim them."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from app.harness.core.errors import SourceUnavailable

MAX_SNIPPET = 2000


class IssueSource(Protocol):
    async def get_issue(self, identifier: str) -> dict[str, Any] | None: ...
    async def search_issues(
        self, team_id: str, text: str, *, limit: int = 8
    ) -> list[dict[str, Any]]: ...


class PageSource(Protocol):
    async def search(self, text: str, *, limit: int = 5) -> list[dict[str, Any]]: ...
    async def get_page_text(self, page_id: str) -> dict[str, Any] | None: ...


class CodeSource(Protocol):
    def grep(
        self, pattern: str, *, glob: str = "**/*.py", max_hits: int = 20
    ) -> list[dict[str, Any]]: ...
    def read(self, path: str, start: int, end: int) -> str: ...


def make_read_tools(
    *,
    linear: IssueSource | None = None,
    team_id: str = "",
    notion: PageSource | None = None,
    code: CodeSource | None = None,
    roster: list[dict[str, Any]] | None = None,
) -> list[Callable[..., Any]]:
    """Build the tool set for one run. Tools close over the connectors, so the model never sees
    a credential, a project id, or anything it could point somewhere else."""
    members = list(roster or [])

    async def search_issues(text: str) -> dict[str, Any]:
        """Search this project's tracker for issues whose title or description mentions `text`.

        Use this before proposing a new issue, to find one that already covers the work.

        Args:
            text (str): Words to look for, e.g. "overdue dashboard".
        """
        if linear is None:
            return {"status": "unavailable", "error": "the tracker is not configured"}
        try:
            hits = await linear.search_issues(team_id, text, limit=8)
        except SourceUnavailable as exc:
            return {"status": "unavailable", "error": str(exc)}
        return {"status": "ok", "issues": [
            {"identifier": h["identifier"], "title": h["title"], "state": h["state"],
             "assignee": (h.get("assignee") or {}).get("name"), "url": h["url"]}
            for h in hits
        ]}

    async def get_issue(identifier: str) -> dict[str, Any]:
        """Fetch one issue by its identifier.

        Args:
            identifier (str): The issue key, e.g. "INV-142".
        """
        if linear is None:
            return {"status": "unavailable", "error": "the tracker is not configured"}
        try:
            issue = await linear.get_issue(identifier)
        except SourceUnavailable as exc:
            return {"status": "unavailable", "error": str(exc)}
        if issue is None:
            return {"status": "not_found", "identifier": identifier}
        return {"status": "ok", "issue": {
            "identifier": issue["identifier"], "title": issue["title"],
            "description": (issue.get("description") or "")[:MAX_SNIPPET],
            "state": issue["state"], "priority": issue.get("priority"),
            "assignee": (issue.get("assignee") or {}).get("name"),
            "due_date": issue.get("due_date"), "url": issue["url"],
        }}

    async def search_notion(text: str) -> dict[str, Any]:
        """Search the product specs for pages mentioning `text`.

        Use this to find what was specified, before claiming the product should behave a
        certain way.

        Args:
            text (str): Words to look for, e.g. "reminder cadence".
        """
        if notion is None:
            return {"status": "unavailable", "error": "the spec workspace is not configured"}
        try:
            hits = await notion.search(text, limit=5)
        except SourceUnavailable as exc:
            return {"status": "unavailable", "error": str(exc)}
        return {"status": "ok", "pages": hits}

    async def get_notion_page(page_id: str) -> dict[str, Any]:
        """Read one spec page as markdown.

        Args:
            page_id (str): The page id returned by search_notion.
        """
        if notion is None:
            return {"status": "unavailable", "error": "the spec workspace is not configured"}
        try:
            page = await notion.get_page_text(page_id)
        except SourceUnavailable as exc:
            return {"status": "unavailable", "error": str(exc)}
        if page is None:
            return {"status": "not_found", "page_id": page_id}
        return {"status": "ok", "page": {**page, "markdown": page["markdown"][:MAX_SNIPPET]}}

    def grep_code(pattern: str, glob: str = "**/*") -> dict[str, Any]:
        """Search the product's source for a regular expression. This is what the system
        actually does today — prefer it over assuming.

        Args:
            pattern (str): A regular expression, e.g. "REMINDER_DAYS" or "getRelatedNews".
            glob (str): Which files to search. The default searches every source file;
                narrow it like "**/*.py" or "src/**/*.ts" when the language is known.
        """
        if code is None:
            return {"status": "unavailable", "error": "the codebase is not configured"}
        return {"status": "ok", "hits": code.grep(pattern, glob=glob, max_hits=20)}

    def read_code(path: str, start: int, end: int) -> dict[str, Any]:
        """Read a line range from one file, to confirm what a grep hit means.

        Args:
            path (str): Repository-relative path, e.g. "acme/config.py".
            start (int): First line, 1-indexed.
            end (int): Last line, inclusive.
        """
        if code is None:
            return {"status": "unavailable", "error": "the codebase is not configured"}
        text = code.read(path, start, end)
        if not text:
            return {"status": "not_found", "path": path}
        return {"status": "ok", "path": path, "start": start, "text": text[:MAX_SNIPPET]}

    def list_roster() -> dict[str, Any]:
        """List the people on this project. An owner must be one of these names, exactly."""
        return {"status": "ok", "people": [
            {"name": m.get("name"), "role": m.get("role")} for m in members
        ]}

    tools: list[Callable[..., Any]] = [list_roster]
    if linear is not None:
        tools = [search_issues, get_issue, *tools]
    if notion is not None:
        tools = [*tools, search_notion, get_notion_page]
    if code is not None:
        tools = [*tools, grep_code, read_code]
    return tools

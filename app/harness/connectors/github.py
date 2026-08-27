"""GitHub pull requests, read-only. The agent never writes here — it only asks whether the work
it filed has become a PR, been reviewed, and merged.

Matching is by Linear identifier (INV-142) in the PR title, body or branch name, because that is
what a developer actually types and no other link exists between the two systems."""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.harness.core.errors import SourceUnavailable
from app.harness.core.redact import redact

API = "https://api.github.com"


def _norm_pr(raw: dict[str, Any], reviews: int = 0) -> dict[str, Any]:
    return {
        "number": raw.get("number"),
        "title": raw.get("title") or "",
        "state": raw.get("state") or "",
        "merged": bool(raw.get("merged_at")),
        "url": raw.get("html_url") or "",
        "branch": (raw.get("head") or {}).get("ref") or "",
        "updated_at": raw.get("updated_at") or "",
        "reviews": reviews,
    }


def mentions_issue(pr: dict[str, Any], identifier: str) -> bool:
    """Whole-word match, so INV-14 never matches INV-142."""
    pattern = re.compile(rf"\b{re.escape(identifier)}\b", re.IGNORECASE)
    haystack = " ".join([
        pr.get("title") or "",
        pr.get("body") or "",
        (pr.get("head") or {}).get("ref") or "",
    ])
    return bool(pattern.search(haystack))


class GitHubClient:
    def __init__(
        self, token: str, repo: str, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._repo = repo  # "owner/name"
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._transport = transport

    async def _get(self, path: str, **params: Any) -> Any:
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=20) as client:
                resp = await client.get(
                    f"{API}{path}", headers=self._headers, params=params or None
                )
        except httpx.HTTPError as exc:
            raise SourceUnavailable("github", redact(str(exc))) from exc
        if resp.status_code == 404:
            raise _NotFound(path)
        if resp.status_code >= 400:
            raise SourceUnavailable("github", f"HTTP {resp.status_code}")
        return resp.json()

    async def _review_count(self, number: int) -> int:
        """Distinct reviewers who submitted anything other than a bare comment."""
        try:
            reviews = await self._get(f"/repos/{self._repo}/pulls/{number}/reviews")
        except _NotFound:
            return 0
        reviewers = {
            (r.get("user") or {}).get("login")
            for r in reviews or []
            if (r.get("state") or "").upper() in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
        }
        return len(reviewers - {None})

    async def find_prs_for_issue(self, identifier: str) -> list[dict[str, Any]]:
        """Open and closed PRs mentioning the issue, newest first. [] when none match."""
        try:
            raw = await self._get(
                f"/repos/{self._repo}/pulls", state="all", per_page=50, sort="updated",
                direction="desc",
            )
        except _NotFound:
            raise SourceUnavailable("github", f"repo {self._repo} not found") from None
        matches = [pr for pr in raw or [] if mentions_issue(pr, identifier)]
        return [_norm_pr(pr, await self._review_count(int(pr["number"]))) for pr in matches]

    async def get_pr(self, number: int) -> dict[str, Any] | None:
        try:
            raw = await self._get(f"/repos/{self._repo}/pulls/{number}")
        except _NotFound:
            return None
        return _norm_pr(raw, await self._review_count(number))


class _NotFound(Exception):
    """Internal: a 404 from GitHub. Never escapes this module."""

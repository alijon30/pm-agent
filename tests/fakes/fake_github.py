"""In-memory GitHub. PRs are already in the normalised shape, plus a `mentions` list naming the
issue identifiers each PR refers to — the fake does not re-implement the matching regex."""

from __future__ import annotations

import copy
from typing import Any


class FakeGitHub:
    def __init__(self, prs: list[dict[str, Any]] | tuple[dict[str, Any], ...] = ()) -> None:
        self._prs = [copy.deepcopy(p) for p in prs]

    def _public(self, pr: dict[str, Any]) -> dict[str, Any]:
        out = copy.deepcopy(pr)
        out.pop("mentions", None)
        return out

    async def find_prs_for_issue(self, identifier: str) -> list[dict[str, Any]]:
        hits = [p for p in self._prs if identifier in (p.get("mentions") or [])]
        hits.sort(key=lambda p: p.get("updated_at") or "", reverse=True)
        return [self._public(p) for p in hits]

    async def get_pr(self, number: int) -> dict[str, Any] | None:
        pr = next((p for p in self._prs if p.get("number") == number), None)
        return self._public(pr) if pr is not None else None

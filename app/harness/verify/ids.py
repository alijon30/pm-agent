"""The identifier gate: nothing the agent writes may name something that does not exist.

Every citation is a typed reference and every reference is re-fetched from the system that owns
it before the claim carrying it may ship:

    linear:INV-142                 an issue
    notion:<page_id>               a page
    fathom:<meeting_id>@<mm:ss>    a moment in a call
    code:<path>:<line>             a line in the repo
    decision:<id>                  an entry in the decision ledger
    wiki:<slug>                    a page in the company brain

This is the single most important gate in the system: a plausible-looking ticket id in a Linear
comment is how an agent quietly destroys a team's trust."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Protocol

from app.harness.core.errors import SourceUnavailable
from app.harness.verify.roster import resolve_owner

REF = re.compile(r"^(linear|notion|fathom|code|decision|wiki):(.+)$", re.IGNORECASE)
ISSUE_IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")


class IssueLookup(Protocol):
    async def get_issue(self, identifier: str) -> dict[str, Any] | None: ...


class PageLookup(Protocol):
    async def get_page_text(self, page_id: str) -> dict[str, Any] | None: ...


class CodeLookup(Protocol):
    def exists(self, path: str, line: int | None = None) -> bool: ...


class DocLookup(Protocol):
    async def get(self, collection: str, doc_id: str) -> dict[str, Any] | None: ...


class IdGate:
    def __init__(
        self,
        *,
        linear: IssueLookup | None = None,
        notion: PageLookup | None = None,
        code: CodeLookup | None = None,
        roster: Sequence[dict[str, Any]] = (),
        db: DocLookup | None = None,
        known_meeting: Callable[[str], Awaitable[bool]] | None = None,
    ) -> None:
        self._linear = linear
        self._notion = notion
        self._code = code
        self._roster = list(roster)
        self._db = db
        self._known_meeting = known_meeting

    # --- individual kinds ---------------------------------------------------------------------

    async def issue_exists(self, identifier: str) -> bool:
        """False for an unknown issue. A source outage is not "does not exist" — it propagates,
        so the caller marks the item unverified instead of deleting a real citation."""
        if self._linear is None or not ISSUE_IDENTIFIER.match(identifier.strip().upper()):
            return False
        return await self._linear.get_issue(identifier.strip().upper()) is not None

    def person_exists(self, name: str) -> bool:
        return resolve_owner(name, self._roster) is not None

    async def page_exists(self, page_id: str) -> bool:
        if self._notion is None or not page_id.strip():
            return False
        return await self._notion.get_page_text(page_id.strip()) is not None

    def code_exists(self, target: str) -> bool:
        """`path:line` or a bare path."""
        if self._code is None:
            return False
        path, _, line = target.rpartition(":")
        if path and line.isdigit():
            return self._code.exists(path, int(line))
        return self._code.exists(target)

    async def doc_exists(self, collection: str, doc_id: str) -> bool:
        if self._db is None or not doc_id.strip():
            return False
        return await self._db.get(collection, doc_id.strip()) is not None

    async def meeting_exists(self, meeting_id: str) -> bool:
        if self._known_meeting is None:
            return False
        return await self._known_meeting(meeting_id)

    # --- references ---------------------------------------------------------------------------

    async def ref_exists(self, ref: str) -> bool:
        match = REF.match((ref or "").strip())
        if not match:
            return False
        kind, target = match.group(1).lower(), match.group(2).strip()
        if kind == "linear":
            return await self.issue_exists(target)
        if kind == "notion":
            return await self.page_exists(target)
        if kind == "code":
            return self.code_exists(target)
        if kind == "decision":
            return await self.doc_exists("decisions", target)
        if kind == "wiki":
            # A brain citation names a page and the entry on it: wiki:<slug>#<entry_id>. The
            # page is what can be re-fetched, so that is what is checked.
            slug, _, _entry = target.partition("#")
            return await self.doc_exists("wiki_pages", slug)
        if kind == "fathom":
            meeting_id, _, _timestamp = target.partition("@")
            return await self.meeting_exists(meeting_id)
        return False

    async def missing_refs(self, refs: Sequence[str]) -> list[str]:
        """Every reference that could not be confirmed. An outage propagates rather than
        reporting a real citation as missing."""
        missing: list[str] = []
        for ref in refs:
            if not await self.ref_exists(ref):
                missing.append(ref)
        return missing

    async def exists(self, token: str) -> bool:
        """For the plan gate, whose params carry bare identifiers rather than typed refs:
        anything shaped like an issue key is looked up as one, everything else as a person."""
        token = (token or "").strip()
        if not token:
            return False
        if ISSUE_IDENTIFIER.match(token.upper()):
            try:
                return await self.issue_exists(token)
            except SourceUnavailable:
                raise
        return self.person_exists(token)

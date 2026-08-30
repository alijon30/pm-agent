"""The company brain: what this team has told the agent, kept so it does not have to be said
twice.

Four kinds of thing live here, and the difference matters because each is used differently:

    ownership   who takes a kind of work — "billing and statements go to Nodir"
    preference  how to work — "never nudge before ten", "always cc the channel"
    fact        something durable about the product — "rates allow six decimals"
    correction  a mistake somebody pointed out, and what right looked like

Every entry carries where it came from. An entry with no source is a rumour, and this store
does not keep rumours: `source` is a typed ref that the identifier gate can re-check, so a
sentence in a Linear ticket that says "per the brain" can always be traced to the person who
said it and the moment they said it.

Nothing here reinterprets anything. Entries are matched to a situation by word overlap and
handed to the model as text; the gates that already govern owners, citations and evidence still
govern what comes back."""

from __future__ import annotations

import re
from typing import Any

from app.harness.core.clock import Clock, human_date, iso
from app.harness.core.keys import new_id
from app.harness.store.db import Db, Doc

KINDS = ("ownership", "preference", "fact", "correction")
PAGE_OF = {"ownership": "ownership", "preference": "preferences", "correction": "corrections"}
BRAIN_LIMIT = 8
WORD = re.compile(r"[a-z0-9][a-z0-9'-]*")
# Words too common to tell one situation from another. Kept short on purpose: a brain that
# fires slightly too often is a smaller problem than one that never fires.
NOISE = frozenset({
    "about", "after", "again", "always", "another", "because", "before", "being", "could",
    "every", "first", "never", "other", "should", "their", "there", "these",
    "thing", "things", "those", "through", "under", "where", "which", "while", "would",
    "please", "thanks", "going", "gonna", "really", "still", "there's",
})


def keywords(text: str, limit: int = 12) -> list[str]:
    """The words that decide whether something applies later.

    Crude on purpose, and the same rule everywhere: an entry that fires slightly too often is
    a smaller problem than one that never fires when it should."""
    found = {w for w in WORD.findall(str(text or "").lower()) if len(w) > 4 and w not in NOISE}
    return sorted(found)[:limit]


def topic_slug(text: str) -> str:
    """Which facts page a fact belongs on. Facts are per topic so a page stays readable."""
    words = keywords(text, limit=2)
    return "facts-" + ("-".join(words) if words else "general")


def overlap(entry: dict[str, Any], words: set[str]) -> int:
    return len(set(entry.get("subject") or []) & words)


class WikiStore:
    """The brain, as pages of entries. One store, not one per kind: a reader asking "what do
    you know about billing?" should not have to know which drawer it was filed in."""

    def __init__(self, db: Db, clock: Clock) -> None:
        self._db = db
        self._clock = clock

    def _slug(self, kind: str, text: str) -> str:
        return PAGE_OF.get(kind) or topic_slug(text)

    async def add_entry(
        self, project_id: str, kind: str, entry: dict[str, Any]
    ) -> tuple[str, str] | None:
        """Remember one thing. Returns (slug, entry_id), or None when it was already known.

        Idempotent by source: the same Slack message replayed, or the same fact extracted from
        the same call twice, must not become two memories."""
        if kind not in KINDS:
            return None
        text = str(entry.get("text") or "").strip()
        source = str(entry.get("source") or "").strip()
        if not text or not source:
            # No source, no memory. An entry nobody can trace is one nobody can argue with.
            return None

        slug = self._slug(kind, text)
        page = await self._page(project_id, slug, kind)
        entries: list[dict[str, Any]] = list(page.get("entries") or [])
        if any(str(e.get("source")) == source for e in entries):
            return None

        fresh = {
            "id": new_id(),
            "text": text,
            # An explicitly empty subject means "this applies to everything", which is not the
            # same as not having said what it is about.
            "subject": list(entry["subject"]) if "subject" in entry else keywords(text),
            "person": entry.get("person"),
            "source": source,
            "said_by": str(entry.get("said_by") or ""),
            "created_at": iso(self._clock.now()),
            "retired_at": None,
        }
        # A newer instruction about the same subject retires the older one rather than
        # deleting it: the page should be able to answer "since when, and what changed".
        for old in entries:
            if self._contradicts(old, fresh, kind):
                old["retired_at"] = fresh["created_at"]
        entries.append(fresh)
        await self._db.set("wiki_pages", f"{project_id}:{slug}", {
            **page, "entries": entries, "updated_at": fresh["created_at"],
        })
        return slug, str(fresh["id"])

    def _contradicts(self, old: dict[str, Any], fresh: dict[str, Any], kind: str) -> bool:
        """Whether a new entry replaces an older one.

        Only ownership can contradict: the same work cannot belong to two people, so naming a
        new owner retires the old claim. A second preference or fact about the same subject is
        additional, not contradictory — people hold several opinions about billing."""
        if kind != "ownership" or old.get("retired_at"):
            return False
        same = set(old.get("subject") or []) & set(fresh.get("subject") or [])
        return bool(same) and old.get("person") != fresh.get("person")

    async def _page(self, project_id: str, slug: str, kind: str) -> Doc:
        found = await self._db.get("wiki_pages", f"{project_id}:{slug}")
        if found is not None:
            return found
        return {
            "id": f"{project_id}:{slug}", "project_id": project_id, "slug": slug, "kind": kind,
            "title": slug.replace("-", " ").title(), "entries": [],
            "updated_at": iso(self._clock.now()),
        }

    async def pages(self, project_id: str) -> list[Doc]:
        rows = await self._db.query("wiki_pages", [("project_id", "==", project_id)])
        return sorted(rows, key=lambda p: str(p.get("slug") or ""))

    async def relevant(
        self, project_id: str, text: str, kinds: tuple[str, ...] | None = None,
        limit: int = BRAIN_LIMIT,
    ) -> list[dict[str, Any]]:
        """What this company has told the agent that bears on the situation in hand.

        Word overlap, newest first, retired entries left out. Capped because a prompt that
        carries the whole brain carries none of it — the model reads the top of a list."""
        words = set(keywords(text, limit=64))
        wanted = tuple(kinds or KINDS)
        scored: list[tuple[int, str, dict[str, Any]]] = []
        for page in await self.pages(project_id):
            if str(page.get("kind")) not in wanted:
                continue
            for entry in page.get("entries") or []:
                if entry.get("retired_at"):
                    continue
                hits = overlap(entry, words)
                # A global entry — one with nothing specific to match on — always applies.
                if hits or not entry.get("subject"):
                    scored.append((hits, str(entry.get("created_at") or ""),
                                   {**entry, "kind": page.get("kind"),
                                    "ref": f"wiki:{page.get('slug')}#{entry.get('id')}"}))
        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [entry for _, _, entry in scored[:limit]]

    async def for_prompt(
        self, project_id: str, text: str, kinds: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """What this company has said, phrased for a model rather than handed over as
        documents: the sentence, who said it, when, and the reference to cite if it is used."""
        return [
            {"kind": e.get("kind"), "text": e.get("text"), "person": e.get("person"),
             "said_by": e.get("said_by"), "when": human_date(str(e.get("created_at") or "")),
             "ref": e.get("ref")}
            for e in await self.relevant(project_id, text, kinds)
        ]

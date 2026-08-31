"""Give already-filed issues the call moment they came from.

    uv run --env-file .env python scripts/backfill_citations.py            # dry run, the default
    uv run --env-file .env python scripts/backfill_citations.py --apply    # write
"""

import argparse
import asyncio
from typing import Any

from app.config import Settings
from app.harness.stages.reconcile import call_citation
from app.harness.store.db import Db, Doc
from app.harness.store.firestore import FirestoreDb
from app.harness.verify.ids import IdGate

SCAN_LIMIT = 500
FILED = "linear.create_issue"


def matching_item(action: Doc, items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The reconciled item this action filed.

    By title, because that is what the act stage copied onto the action."""
    title = str((action.get("inputs") or {}).get("title") or "").strip()
    for item in items:
        if str(item.get("title") or "").strip() == title:
            return item
    return None


async def proposal(action: Doc, db: Db) -> tuple[str, str]:
    """The citation this action should carry, and why it does not have one yet.

    Returns (reference, reason); exactly one is ever non-empty."""
    act_task = await db.get("tasks", str(action.get("task_id") or ""))
    if act_task is None:
        return "", "its act task is gone"

    reconcile_id = str((act_task.get("payload") or {}).get("reconcile_task_id") or "")
    reconcile = await db.get("tasks", reconcile_id) if reconcile_id else None
    if reconcile is None or not reconcile.get("result"):
        return "", "no reconcile result behind it"
    result: dict[str, Any] = reconcile["result"]

    extract_id = str((reconcile.get("payload") or {}).get("extract_task_id") or "")
    extract = await db.get("tasks", extract_id) if extract_id else None
    if extract is None or not extract.get("result"):
        return "", "no extract result behind it"

    item = matching_item(action, list(result.get("items") or []))
    if item is None:
        return "", "no reconciled item matches its title"

    meeting_id = str((result.get("meeting") or {}).get("id") or "")
    reference = call_citation(item, meeting_id, list(extract["result"].get("action_items") or []))
    if not reference:
        return "", "its evidence carries no timestamp"
    return reference, ""


def gate_for(db: Db) -> IdGate:
    """The citation gate, with only the part a call reference needs.

    A `fathom:` reference resolves through `known_meeting` alone, so this is the production
    verification path."""
    async def known_meeting(meeting_id: str) -> bool:
        rows = await db.query("events", [("provider", "==", "fathom")], limit=50)
        return any(
            str((r.get("payload") or {}).get("recording_id")) == meeting_id for r in rows
        )

    return IdGate(db=db, known_meeting=known_meeting)


async def plan(db: Db) -> list[dict[str, str]]:
    """Every filed issue missing its citation, with what this would write against it."""
    gate = gate_for(db)
    rows = await db.query("actions", [("kind", "==", FILED)], limit=SCAN_LIMIT)
    rows = [r for r in rows if r.get("status") == "done" and not (r.get("citations") or [])]

    planned: list[dict[str, str]] = []
    for action in rows:
        reference, reason = await proposal(action, db)
        if reference and not await gate.ref_exists(reference):
            reference, reason = "", "the call it cites is not in the event store"
        planned.append({
            "id": str(action["id"]),
            "issue": str((action.get("target_ids") or {}).get("identifier") or "?"),
            "title": str((action.get("inputs") or {}).get("title") or "")[:44],
            "citation": reference,
            "reason": reason,
        })
    return planned


def table(planned: list[dict[str, str]]) -> str:
    if not planned:
        return "every filed issue already carries a citation — nothing to do"
    width = max(len(p["title"]) for p in planned)
    lines = [f"{'ISSUE':<8} {'TITLE':<{width}}  CITATION"]
    for p in planned:
        lines.append(
            f"{p['issue']:<8} {p['title']:<{width}}  "
            f"{p['citation'] or f'— skipped: {p['reason']}'}"
        )
    fillable = sum(1 for p in planned if p["citation"])
    lines.append("")
    lines.append(
        f"{fillable} of {len(planned)} uncited issues can be given the moment they came from"
    )
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="write the citations (default is a dry run)")
    args = parser.parse_args()

    settings = Settings()
    db = FirestoreDb(settings.gcp_project, settings.firestore_database)
    planned = await plan(db)
    print(table(planned))

    if not args.apply:
        print("\ndry run — nothing written. re-run with --apply to write these.")
        return

    written = 0
    for p in planned:
        if not p["citation"]:
            continue
        # Only this field. Everything else on the action is what it was when it happened.
        await db.update("actions", p["id"], {"citations": [p["citation"]]})
        written += 1
    print(f"\nwrote {written} citation(s)")


if __name__ == "__main__":
    asyncio.run(main())

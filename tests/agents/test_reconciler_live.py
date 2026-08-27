"""Hits Gemini. The question this answers is whether a fixed output schema and tools work in the
same request — the reconciler and the planner both depend on it."""

import os
from pathlib import Path
from typing import Any

import pytest
from app.agents.base.schemas import ReconcileResult
from app.agents.base.tools import make_read_tools
from app.agents.reconciler import GeminiReconciler
from app.config import Settings
from app.harness.connectors.code import CodeSearch

from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_notion import FakeNotion

pytestmark = pytest.mark.live
live = pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="no GOOGLE_API_KEY")
REPO = Path(__file__).parents[2] / "fixtures" / "acme-invoicing"

ROSTER = [{"name": "Maya Chen", "role": "pm"}, {"name": "Nodir Rahimov", "role": "backend"},
          {"name": "Priya Nair", "role": "frontend"}, {"name": "Tom Alvarez", "role": "support"}]
ISSUES = [
    {"id": "u-104", "identifier": "INV-104", "title": "Overdue invoices dashboard for finance",
     "description": "Finance asked for this last quarter", "state": "Backlog", "priority": 4,
     "assignee": None, "due_date": None, "url": "https://linear.app/acme/issue/INV-104",
     "updated_at": "2026-06-01T09:00:00Z"},
]
PAGES = {
    "page-prd": {"title": "Reminders PRD", "url": "https://notion.so/page-prd",
                 "markdown": "# Reminders\nThe first payment reminder is sent 5 days after the "
                             "invoice due date."},
}

ACTION_ITEMS = [
    {"title": "Move payment reminders to three days after due date", "owner_name": "Nodir Rahimov",
     "due_hint": "next Friday", "priority_hint": None,
     "evidence": [{"quote": "let's move payment reminders to three days after the due date",
                   "timestamp": "00:00:12", "speaker": "Maya Chen"}]},
    {"title": "Build the overdue invoices dashboard", "owner_name": "Priya Nair",
     "due_hint": None, "priority_hint": None,
     "evidence": [{"quote": "We need the overdue dashboard for the finance team",
                   "timestamp": "00:00:31", "speaker": "Priya Nair"}]},
]


def make_reconciler(model: str | None = None) -> GeminiReconciler:
    """Flash-Lite by default: the free tier allows 15 requests/minute against it and only 5
    against Flash, and one reconcile run is several tool round-trips."""
    tools = make_read_tools(
        linear=FakeLinear(issues=ISSUES), team_id="team-1", notion=FakeNotion(PAGES),
        code=CodeSearch(REPO), roster=ROSTER,
    )
    return GeminiReconciler(model or Settings().model_fast, tools)


@live
async def test_a_fixed_output_schema_and_tools_work_in_the_same_request() -> None:
    """The load-bearing question. If this fails, reconcile and plan need a two-call design."""
    raw = await make_reconciler().run({
        "action_items": ACTION_ITEMS[:1],
        "decisions": [],
        "meeting": {"id": "8841201", "title": "Q3 Billing planning", "url": "https://f.video/abc"},
        "roster": ROSTER,
        "today": "2026-08-27",
        "feedback": None,
    })
    result = ReconcileResult.model_validate(raw).model_dump()
    assert result["items"], "the reconciler returned no items"
    item = result["items"][0]
    assert item["disposition"] in ("new", "update", "duplicate_of")
    assert item["owner"] in (None, *[m["name"] for m in ROSTER])


@live
async def test_the_reconciler_finds_the_issue_that_already_covers_the_work() -> None:
    """It has to search the tracker rather than assume every item is new."""
    raw = await make_reconciler().run({
        "action_items": ACTION_ITEMS[1:],
        "decisions": [],
        "meeting": {"id": "8841201", "title": "Q3 Billing planning", "url": "https://f.video/abc"},
        "roster": ROSTER,
        "today": "2026-08-27",
        "feedback": None,
    })
    result = ReconcileResult.model_validate(raw).model_dump()
    item = result["items"][0]
    assert item["disposition"] in ("update", "duplicate_of"), (
        f"expected the existing INV-104 to be found, got {item['disposition']}"
    )
    assert item["target_issue"] == "INV-104"


@live
async def test_the_reconciler_reports_the_reminder_conflict_across_three_sources() -> None:
    """Code says 7 days, the spec says 5, the call decided 3. It must report, not resolve."""
    raw = await make_reconciler().run({
        "action_items": ACTION_ITEMS[:1],
        "decisions": [{"statement": "Payment reminders move to three days after the due date.",
                       "quote": "let's move payment reminders to three days after the due date",
                       "source": "fathom:8841201@00:00:12"}],
        "meeting": {"id": "8841201", "title": "Q3 Billing planning", "url": "https://f.video/abc"},
        "roster": ROSTER,
        "today": "2026-08-27",
        "feedback": None,
    })
    result = ReconcileResult.model_validate(raw).model_dump()
    conflicts: list[dict[str, Any]] = [
        c for item in result["items"] for c in item["conflicts"]
    ] + result["decision_conflicts"]
    assert conflicts, "expected the 7 / 5 / 3 disagreement to be reported"
    sources = " ".join(s["source"] for c in conflicts for s in c["sides"])
    assert "code:" in sources or "notion:" in sources, f"conflicts lacked citations: {conflicts}"

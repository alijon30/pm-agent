"""The read-only tools and the guard that decides which of them an agent may call."""

from pathlib import Path
from typing import Any

from app.agents.base.schemas import ReconcileResult
from app.agents.base.spec import AgentSpec, ToolGuard
from app.agents.base.tools import make_read_tools
from app.harness.connectors.code import CodeSearch
from app.harness.core.errors import SourceUnavailable

from tests.fakes.fake_linear import FakeLinear
from tests.fakes.fake_notion import FakeNotion

REPO = Path(__file__).parents[2] / "fixtures" / "acme-invoicing"
ROSTER = [{"name": "Maya Chen", "role": "pm"}, {"name": "Nodir Rahimov", "role": "backend"}]
ISSUE = {"id": "u-104", "identifier": "INV-104", "title": "Overdue invoices dashboard",
         "description": "Finance asked last quarter", "state": "Backlog", "priority": 4,
         "assignee": None, "due_date": None, "url": "https://linear.app/acme/issue/INV-104",
         "updated_at": ""}
PAGES = {"page-prd": {"title": "Reminders PRD", "url": "https://notion.so/page-prd",
                      "markdown": "The first reminder is sent 5 days after the due date."}}


def tools_by_name(**kw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "linear": FakeLinear(issues=[ISSUE]), "team_id": "team-1",
        "notion": FakeNotion(PAGES), "code": CodeSearch(REPO), "roster": ROSTER,
    }
    defaults.update(kw)
    return {t.__name__: t for t in make_read_tools(**defaults)}


# --- the tools --------------------------------------------------------------------------------

async def test_search_issues_returns_a_compact_summary_of_each_hit() -> None:
    result = await tools_by_name()["search_issues"]("overdue")
    assert result["status"] == "ok"
    assert result["issues"] == [{"identifier": "INV-104", "title": "Overdue invoices dashboard",
                                 "state": "Backlog", "assignee": None,
                                 "url": "https://linear.app/acme/issue/INV-104"}]


async def test_get_issue_says_not_found_rather_than_inventing_one() -> None:
    tools = tools_by_name()
    assert (await tools["get_issue"]("INV-104"))["issue"]["state"] == "Backlog"
    assert await tools["get_issue"]("INV-999") == {"status": "not_found", "identifier": "INV-999"}


async def test_a_source_outage_is_reported_to_the_model_not_raised_at_it() -> None:
    class DownLinear:
        async def get_issue(self, identifier: str) -> dict[str, Any] | None:
            raise SourceUnavailable("linear", "HTTP 503")

        async def search_issues(
            self, team_id: str, text: str, *, limit: int = 8
        ) -> list[dict[str, Any]]:
            raise SourceUnavailable("linear", "HTTP 503")

    tools = tools_by_name(linear=DownLinear())
    assert (await tools["get_issue"]("INV-104"))["status"] == "unavailable"
    assert (await tools["search_issues"]("x"))["status"] == "unavailable"


async def test_the_spec_tools_search_and_read_pages() -> None:
    tools = tools_by_name()
    hits = await tools["search_notion"]("reminder")
    assert hits["pages"][0]["id"] == "page-prd"
    page = await tools["get_notion_page"]("page-prd")
    assert "5 days" in page["page"]["markdown"]
    assert (await tools["get_notion_page"]("ghost"))["status"] == "not_found"


def test_grep_and_read_show_what_the_code_actually_does() -> None:
    tools = tools_by_name()
    hits = tools["grep_code"](r"REMINDER_DAYS\s*=")
    assert hits["status"] == "ok" and hits["hits"][0]["path"] == "acme/config.py"
    line = hits["hits"][0]["line"]
    window = tools["read_code"]("acme/config.py", line, line)
    assert "REMINDER_DAYS" in window["text"]
    assert tools["read_code"]("acme/ghost.py", 1, 2)["status"] == "not_found"


def test_the_roster_tool_lists_exactly_who_may_be_assigned() -> None:
    people = tools_by_name()["list_roster"]()["people"]
    assert [p["name"] for p in people] == ["Maya Chen", "Nodir Rahimov"]


def test_a_connector_that_is_not_configured_contributes_no_tools() -> None:
    names = set(tools_by_name(linear=None, notion=None, code=None))
    assert names == {"list_roster"}


# --- the guard --------------------------------------------------------------------------------

class NamedTool:
    def __init__(self, name: str) -> None:
        self.name = name


def test_a_tool_outside_the_allow_list_is_denied_and_the_run_continues() -> None:
    guard = ToolGuard({"search_issues"}, max_calls=5)
    assert guard(NamedTool("search_issues"), {}, None) is None
    denial = guard(NamedTool("create_issue"), {}, None)
    assert denial is not None and denial["status"] == "denied"
    assert "not available" in denial["error"]
    assert guard.denied == ["create_issue"]


def test_the_tool_call_budget_stops_a_run_that_will_not_stop_looking() -> None:
    guard = ToolGuard({"search_issues"}, max_calls=2)
    assert guard(NamedTool("search_issues"), {}, None) is None
    assert guard(NamedTool("search_issues"), {}, None) is None
    exhausted = guard(NamedTool("search_issues"), {}, None)
    assert exhausted is not None and "budget" in exhausted["error"]


def test_an_agent_spec_carries_its_tools_schema_and_budgets() -> None:
    tools = list(tools_by_name().values())
    spec = AgentSpec(name="reconciler", model="gemini-x", instruction="do the thing",
                     output_schema=ReconcileResult, tools=tools)
    assert spec.max_tool_calls == 12 and spec.max_output_tokens == 8192
    assert {t.__name__ for t in spec.tools} >= {"search_issues", "grep_code", "list_roster"}

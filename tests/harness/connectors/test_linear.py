import json
from typing import Any

import httpx
import pytest
from app.harness.connectors.linear import LinearClient
from app.harness.core.errors import SourceUnavailable

from tests.fakes.fake_linear import FakeLinear

ISSUES = [
    {"id": "uuid-142", "identifier": "INV-142", "title": "Move payment reminders to 3 days",
     "description": "From Q3 planning", "state": "Todo", "priority": 3,
     "assignee": {"id": "u-nodir", "name": "Nodir Rahimov"}, "due_date": None,
     "url": "https://linear.app/acme/issue/INV-142", "updated_at": "2026-08-27T09:00:00.000Z"},
    {"id": "uuid-104", "identifier": "INV-104", "title": "Overdue invoices dashboard for finance",
     "description": "Stale from last quarter", "state": "Backlog", "priority": 4,
     "assignee": None, "due_date": None,
     "url": "https://linear.app/acme/issue/INV-104", "updated_at": "2026-06-01T09:00:00.000Z"},
]
MEMBERS = [{"id": "u-nodir", "name": "Nodir Rahimov", "email": "nodir@acme-invoicing.test"}]
STATES = [{"id": "s-todo", "name": "Todo", "type": "unstarted"},
          {"id": "s-prog", "name": "In Progress", "type": "started"}]


def make_fake() -> FakeLinear:
    return FakeLinear(issues=ISSUES, members=MEMBERS, states=STATES)


# --- the fake defines the contract ------------------------------------------------------------

async def test_get_issue_returns_none_for_an_unknown_identifier() -> None:
    fake = make_fake()
    found = await fake.get_issue("INV-142")
    assert found is not None and found["title"].startswith("Move payment")
    assert await fake.get_issue("INV-999") is None


async def test_search_is_case_insensitive_over_title_and_description_and_respects_limit() -> None:
    fake = make_fake()
    hits = await fake.search_issues("team-1", "OVERDUE")
    assert [h["identifier"] for h in hits] == ["INV-104"]
    hits = await fake.search_issues("team-1", "q3 planning")
    assert [h["identifier"] for h in hits] == ["INV-142"]
    assert len(await fake.search_issues("team-1", "invoice", limit=1)) <= 1
    assert await fake.search_issues("team-1", "no such text") == []


async def test_create_issue_records_the_write_and_mints_the_next_identifier() -> None:
    fake = make_fake()
    created = await fake.create_issue(team_id="team-1", project_id="proj-1",
                                      title="Invoice CSV export",
                                      description="Northwind is blocked",
                                      assignee_id="u-nodir", priority=2, due_date=None)
    assert created["identifier"] == "INV-143"
    assert fake.writes[-1]["op"] == "create" and fake.writes[-1]["title"] == "Invoice CSV export"
    assert await fake.get_issue("INV-143") is not None


async def test_update_and_comment_record_writes_against_an_existing_issue_only() -> None:
    fake = make_fake()
    await fake.update_issue("INV-142", {"priority": 2})
    updated = await fake.get_issue("INV-142")
    assert updated is not None and updated["priority"] == 2
    comment_id = await fake.comment("INV-142", "From the call: [00:01:42]")
    assert comment_id and fake.writes[-1]["op"] == "comment"
    with pytest.raises(SourceUnavailable):
        await fake.update_issue("INV-999", {"priority": 2})
    with pytest.raises(SourceUnavailable):
        await fake.comment("INV-999", "x")


# --- the real client over a mock transport ----------------------------------------------------

def client_with(handler: httpx.MockTransport) -> LinearClient:
    return LinearClient("lin_api_TESTKEY", transport=handler)


async def test_the_real_client_parses_the_documented_issue_shape() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "lin_api_TESTKEY"
        return httpx.Response(200, json={"data": {"issue": {
            "id": "uuid-142", "identifier": "INV-142", "title": "Move payment reminders to 3 days",
            "description": "From Q3 planning", "url": "https://linear.app/acme/issue/INV-142",
            "priority": 3, "updatedAt": "2026-08-27T09:00:00.000Z", "dueDate": None,
            "state": {"name": "Todo"}, "assignee": {"id": "u-nodir", "name": "Nodir Rahimov"},
        }}})

    issue = await client_with(httpx.MockTransport(respond)).get_issue("INV-142")
    assert issue == {"id": "uuid-142", "identifier": "INV-142",
                     "title": "Move payment reminders to 3 days", "description": "From Q3 planning",
                     "state": "Todo", "priority": 3,
                     "assignee": {"id": "u-nodir", "name": "Nodir Rahimov"}, "due_date": None,
                     "url": "https://linear.app/acme/issue/INV-142",
                     "updated_at": "2026-08-27T09:00:00.000Z"}


async def test_an_entity_not_found_error_is_none_not_an_outage() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [{"message": "Entity not found: Issue"}]})

    assert await client_with(httpx.MockTransport(respond)).get_issue("INV-999") is None


async def test_a_graphql_error_becomes_source_unavailable_with_a_redacted_detail() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"errors": [{"message": "auth failed for lin_api_SECRET99"}]}
        )

    with pytest.raises(SourceUnavailable) as err:
        await client_with(httpx.MockTransport(respond)).get_issue("INV-142")
    assert "lin_api_SECRET99" not in str(err.value) and "linear" in str(err.value)


async def test_http_and_transport_failures_become_source_unavailable() -> None:
    def http500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(SourceUnavailable):
        await client_with(httpx.MockTransport(http500)).get_issue("INV-142")

    def explode(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns down")

    with pytest.raises(SourceUnavailable):
        await client_with(httpx.MockTransport(explode)).get_issue("INV-142")


async def test_create_issue_sends_the_input_and_returns_the_minted_identity() -> None:
    seen: dict[str, Any] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.update(body["variables"]["input"])
        return httpx.Response(200, json={"data": {"issueCreate": {"success": True, "issue": {
            "id": "uuid-new", "identifier": "INV-150",
            "url": "https://linear.app/acme/issue/INV-150"}}}})

    created = await client_with(httpx.MockTransport(respond)).create_issue(
        team_id="team-1", project_id="proj-1", title="T", description="D",
        assignee_id="u-nodir", priority=2, due_date="2026-09-04")
    assert created == {"id": "uuid-new", "identifier": "INV-150",
                       "url": "https://linear.app/acme/issue/INV-150"}
    assert seen["teamId"] == "team-1" and seen["assigneeId"] == "u-nodir"
    assert seen["priority"] == 2 and seen["dueDate"] == "2026-09-04"


async def test_optional_create_fields_are_omitted_when_absent() -> None:
    seen: dict[str, Any] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content)["variables"]["input"])
        return httpx.Response(200, json={"data": {"issueCreate": {"success": True, "issue": {
            "id": "u", "identifier": "INV-151", "url": "u"}}}})

    await client_with(httpx.MockTransport(respond)).create_issue(
        team_id="team-1", project_id=None, title="T", description="D",
        assignee_id=None, priority=None, due_date=None)
    assert set(seen) == {"teamId", "title", "description"}


async def test_search_words_may_span_the_title_and_description() -> None:
    fake = make_fake()
    # "overdue" is in INV-104's title, "quarter" in its description — a phrase search that a
    # contiguous-substring match would miss.
    hits = await fake.search_issues("team-1", "overdue quarter")
    assert [h["identifier"] for h in hits] == ["INV-104"]
    assert await fake.search_issues("team-1", "overdue reminders") == []


async def test_the_real_search_sends_a_word_and_filter() -> None:
    seen: dict[str, Any] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content)["variables"]["filter"])
        return httpx.Response(200, json={"data": {"issues": {"nodes": []}}})

    await client_with(httpx.MockTransport(respond)).search_issues("team-1", "overdue dashboard")
    assert seen["team"] == {"id": {"eq": "team-1"}}
    assert len(seen["and"]) == 2
    assert seen["and"][0]["or"][0] == {"title": {"containsIgnoreCase": "overdue"}}

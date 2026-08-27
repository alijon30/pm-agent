from typing import Any

import httpx
import pytest
from app.harness.connectors.notion import NotionClient, blocks_to_markdown, title_of
from app.harness.core.errors import SourceUnavailable

from tests.fakes.fake_notion import FakeNotion

PAGES = {
    "page-prd": {
        "title": "Reminders PRD",
        "url": "https://notion.so/page-prd",
        "markdown": "# Reminders\nThe first reminder is sent 5 days after the due date.",
        "children": ["page-cadence"],
    },
    "page-export": {
        "title": "Invoice Export spec",
        "url": "https://notion.so/page-export",
        "markdown": "The CSV export includes payments.",
        "children": [],
    },
    "page-cadence": {"title": "Cadence details", "url": "", "markdown": "", "children": []},
}


# --- the fake defines the contract ------------------------------------------------------------

async def test_search_matches_titles_and_body_case_insensitively() -> None:
    fake = FakeNotion(PAGES)
    assert [h["id"] for h in await fake.search("REMINDERS")] == ["page-prd"]
    assert [h["id"] for h in await fake.search("includes payments")] == ["page-export"]
    assert await fake.search("nothing here") == []


async def test_get_page_text_returns_none_for_an_unknown_page() -> None:
    fake = FakeNotion(PAGES)
    page = await fake.get_page_text("page-prd")
    assert page is not None and "5 days" in page["markdown"]
    assert await fake.get_page_text("page-ghost") is None


async def test_list_children_returns_child_pages() -> None:
    fake = FakeNotion(PAGES)
    assert await fake.list_children("page-prd") == [
        {"id": "page-cadence", "title": "Cadence details"}
    ]
    assert await fake.list_children("page-export") == []
    assert await fake.list_children("page-ghost") == []


# --- pure helpers -----------------------------------------------------------------------------

def test_title_of_finds_the_title_property_whatever_it_is_called() -> None:
    page = {"properties": {
        "Owner": {"type": "people", "people": []},
        "Doc name": {"type": "title", "title": [{"plain_text": "Reminders "},
                                                {"plain_text": "PRD"}]},
    }}
    assert title_of(page) == "Reminders PRD"
    assert title_of({"properties": {}}) == ""


def test_blocks_become_markdown_with_headings_and_bullets_and_skip_empty_blocks() -> None:
    blocks = [
        {"type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "Reminders"}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Sent 5 days after."}]}},
        {"type": "bulleted_list_item",
         "bulleted_list_item": {"rich_text": [{"plain_text": "Email only"}]}},
        {"type": "divider", "divider": {}},
        {"type": "to_do", "to_do": {"rich_text": [{"plain_text": "Confirm with finance"}]}},
    ]
    assert blocks_to_markdown(blocks) == (
        "# Reminders\nSent 5 days after.\n- Email only\n- [ ] Confirm with finance"
    )


# --- the real client over a mock transport ----------------------------------------------------

def client_with(handler: httpx.MockTransport) -> NotionClient:
    return NotionClient("ntn_TESTTOKEN", transport=handler)


async def test_the_real_client_sends_version_and_auth_headers_and_parses_search() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer ntn_TESTTOKEN"
        assert request.headers["Notion-Version"]
        return httpx.Response(200, json={"results": [{
            "id": "page-prd", "url": "https://notion.so/page-prd",
            "properties": {"Name": {"type": "title", "title": [{"plain_text": "Reminders PRD"}]}},
        }]})

    hits = await client_with(httpx.MockTransport(respond)).search("reminders")
    assert hits == [{"id": "page-prd", "title": "Reminders PRD",
                     "url": "https://notion.so/page-prd"}]


async def test_get_page_text_joins_page_metadata_with_its_blocks() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if "/blocks/" in str(request.url):
            return httpx.Response(200, json={"results": [
                {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "Cadence"}]}},
                {"type": "paragraph",
                 "paragraph": {"rich_text": [{"plain_text": "5 days after due."}]}},
            ]})
        return httpx.Response(200, json={
            "id": "page-prd", "url": "https://notion.so/page-prd",
            "properties": {"Name": {"type": "title", "title": [{"plain_text": "Reminders PRD"}]}},
        })

    page = await client_with(httpx.MockTransport(respond)).get_page_text("page-prd")
    assert page == {"id": "page-prd", "title": "Reminders PRD",
                    "url": "https://notion.so/page-prd",
                    "markdown": "## Cadence\n5 days after due."}


async def test_a_404_is_none_not_an_outage() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Could not find page"})

    assert await client_with(httpx.MockTransport(respond)).get_page_text("ghost") is None


async def test_http_and_transport_failures_become_source_unavailable() -> None:
    def http500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(SourceUnavailable):
        await client_with(httpx.MockTransport(http500)).search("x")

    def explode(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns down")

    with pytest.raises(SourceUnavailable):
        await client_with(httpx.MockTransport(explode)).search("x")


async def test_list_children_returns_only_child_pages() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [
            {"type": "child_page", "id": "kid-1", "child_page": {"title": "Cadence details"}},
            {"type": "paragraph", "id": "p-1", "paragraph": {"rich_text": []}},
        ]})

    kids: list[dict[str, Any]] = await client_with(
        httpx.MockTransport(respond)
    ).list_children("page-prd")
    assert kids == [{"id": "kid-1", "title": "Cadence details"}]

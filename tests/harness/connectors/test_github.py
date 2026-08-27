import httpx
import pytest
from app.harness.connectors.github import GitHubClient, mentions_issue
from app.harness.core.errors import SourceUnavailable

from tests.fakes.fake_github import FakeGitHub

PRS = [
    {"number": 7, "title": "Reminders to 3 days (INV-142)", "state": "open", "merged": False,
     "url": "https://github.com/acme/acme-invoicing/pull/7", "branch": "inv-142-reminders",
     "updated_at": "2026-08-29T10:00:00Z", "reviews": 0, "mentions": ["INV-142"]},
    {"number": 5, "title": "Earlier attempt", "state": "closed", "merged": True,
     "url": "https://github.com/acme/acme-invoicing/pull/5", "branch": "old",
     "updated_at": "2026-08-20T10:00:00Z", "reviews": 2, "mentions": ["INV-142", "INV-104"]},
]


# --- the fake defines the contract ------------------------------------------------------------

async def test_prs_for_an_issue_come_back_newest_first_and_without_internals() -> None:
    fake = FakeGitHub(PRS)
    hits = await fake.find_prs_for_issue("INV-142")
    assert [h["number"] for h in hits] == [7, 5]
    assert "mentions" not in hits[0]
    assert hits[0]["merged"] is False and hits[1]["merged"] is True


async def test_an_issue_with_no_pull_request_gets_an_empty_list() -> None:
    assert await FakeGitHub(PRS).find_prs_for_issue("INV-999") == []


async def test_get_pr_returns_none_for_an_unknown_number() -> None:
    fake = FakeGitHub(PRS)
    pr = await fake.get_pr(7)
    assert pr is not None and pr["branch"] == "inv-142-reminders"
    assert await fake.get_pr(999) is None


# --- the matching rule ------------------------------------------------------------------------

def test_an_identifier_matches_in_the_title_body_or_branch() -> None:
    assert mentions_issue({"title": "Fix INV-142 reminders", "body": "", "head": {}}, "INV-142")
    assert mentions_issue({"title": "", "body": "closes inv-142", "head": {}}, "INV-142")
    assert mentions_issue({"title": "", "body": "", "head": {"ref": "inv-142-x"}}, "INV-142")


def test_a_shorter_identifier_does_not_match_a_longer_one() -> None:
    assert not mentions_issue({"title": "INV-1420 work", "body": "", "head": {}}, "INV-142")
    assert not mentions_issue({"title": "INV-14 work", "body": "", "head": {}}, "INV-142")


# --- the real client over a mock transport ----------------------------------------------------

def client_with(handler: httpx.MockTransport) -> GitHubClient:
    return GitHubClient("ghp_TESTTOKEN", "acme/acme-invoicing", transport=handler)


async def test_the_real_client_filters_by_identifier_and_counts_distinct_reviewers() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/reviews"):
            return httpx.Response(200, json=[
                {"state": "APPROVED", "user": {"login": "maya"}},
                {"state": "COMMENTED", "user": {"login": "tom"}},
                {"state": "CHANGES_REQUESTED", "user": {"login": "maya"}},
            ])
        assert request.headers["Authorization"] == "Bearer ghp_TESTTOKEN"
        return httpx.Response(200, json=[
            {"number": 7, "title": "Reminders to 3 days (INV-142)", "state": "open",
             "body": "", "merged_at": None, "html_url": "https://github.com/x/y/pull/7",
             "head": {"ref": "inv-142-reminders"}, "updated_at": "2026-08-29T10:00:00Z"},
            {"number": 8, "title": "Unrelated cleanup", "state": "open", "body": "",
             "merged_at": None, "html_url": "https://github.com/x/y/pull/8",
             "head": {"ref": "cleanup"}, "updated_at": "2026-08-29T11:00:00Z"},
        ])

    hits = await client_with(httpx.MockTransport(respond)).find_prs_for_issue("INV-142")
    assert len(hits) == 1
    assert hits[0]["number"] == 7 and hits[0]["reviews"] == 1  # maya counted once, tom not at all
    assert hits[0]["merged"] is False and hits[0]["branch"] == "inv-142-reminders"


async def test_merged_is_true_only_when_the_pr_has_a_merge_timestamp() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/reviews"):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json={
            "number": 5, "title": "Earlier attempt", "state": "closed", "body": "INV-142",
            "merged_at": "2026-08-20T10:00:00Z", "html_url": "https://github.com/x/y/pull/5",
            "head": {"ref": "old"}, "updated_at": "2026-08-20T10:00:00Z",
        })

    pr = await client_with(httpx.MockTransport(respond)).get_pr(5)
    assert pr is not None and pr["merged"] is True and pr["state"] == "closed"


async def test_an_unknown_pr_is_none_but_an_unknown_repo_is_an_outage() -> None:
    def missing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    client = client_with(httpx.MockTransport(missing))
    assert await client.get_pr(999) is None
    with pytest.raises(SourceUnavailable):
        await client.find_prs_for_issue("INV-142")


async def test_http_and_transport_failures_become_source_unavailable() -> None:
    def http500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(SourceUnavailable):
        await client_with(httpx.MockTransport(http500)).find_prs_for_issue("INV-142")

    def explode(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns down")

    with pytest.raises(SourceUnavailable):
        await client_with(httpx.MockTransport(explode)).find_prs_for_issue("INV-142")

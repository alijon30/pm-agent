"""The one-off that gives already-filed issues the call moment they came from.

It runs against production, so what it must never do matters more than what it does: never
invent a moment, never write over anything, never touch a field it was not asked to."""

from typing import Any

from app.harness.deps import Deps
from scripts.backfill_citations import plan, proposal, table


async def a_filed_issue(
    deps: Deps, *, timestamp: str = "00:14", title: str = "Move payment reminders",
    citations: list[str] | None = None,
) -> str:
    """The chain a real filing leaves behind: a call, an extract, a reconcile, an act, an action.
    Returns the action id."""
    await deps.db.create("events", "ev-1", {
        "provider": "fathom", "payload": {"recording_id": "8841201"}})
    await deps.db.create("tasks", "t-extract", {
        "kind": "extract", "result": {"action_items": [
            {"title": title, "evidence": [{"quote": "three days after due",
                                           "timestamp": timestamp}]}]}})
    await deps.db.create("tasks", "t-reconcile", {
        "kind": "reconcile", "payload": {"extract_task_id": "t-extract"},
        "result": {"meeting": {"id": "8841201", "title": "Q3 Billing planning"},
                   "items": [{"title": title, "index": 0, "citations": []}]}})
    await deps.db.create("tasks", "t-act", {
        "kind": "act", "payload": {"reconcile_task_id": "t-reconcile"}})
    await deps.db.create("actions", "a-1", {
        "kind": "linear.create_issue", "status": "done", "task_id": "t-act",
        "inputs": {"title": title, "owner": "Nodir Rahimov", "priority": 2},
        "citations": list(citations or []), "checks_passed": ["evidence"],
        "target_ids": {"identifier": "INV-116"}, "revert": {"issue_id": "abc"}})
    return "a-1"


async def test_it_finds_the_moment_the_issue_came_from(deps: Deps) -> None:
    await a_filed_issue(deps)

    planned = await plan(deps.db)

    assert [p["citation"] for p in planned] == ["fathom:8841201@00:14"]
    assert planned[0]["issue"] == "INV-116"


async def test_it_never_invents_a_moment_that_was_not_recorded(deps: Deps) -> None:
    """The whole point of the backstop is that a missing timestamp stays missing."""
    await a_filed_issue(deps, timestamp="")

    planned = await plan(deps.db)

    assert planned[0]["citation"] == ""
    assert planned[0]["reason"] == "its evidence carries no timestamp"


async def test_it_refuses_a_citation_to_a_call_the_store_does_not_have(deps: Deps) -> None:
    """The same gate the live stage uses: a reference nobody can resolve is not written."""
    await a_filed_issue(deps)
    await deps.db.update("tasks", "t-reconcile", {
        "result": {"meeting": {"id": "9999999"},
                   "items": [{"title": "Move payment reminders", "index": 0}]}})

    planned = await plan(deps.db)

    assert planned[0]["citation"] == ""
    assert planned[0]["reason"] == "the call it cites is not in the event store"


async def test_an_issue_that_already_cites_its_call_is_left_alone(deps: Deps) -> None:
    await a_filed_issue(deps, citations=["fathom:8841201@00:02"])

    assert await plan(deps.db) == []


async def test_a_broken_chain_is_reported_rather_than_guessed_at(deps: Deps) -> None:
    await a_filed_issue(deps)
    await deps.db.delete("tasks", "t-extract")

    planned = await plan(deps.db)

    assert planned[0]["reason"] == "no extract result behind it"


async def test_an_action_whose_title_matches_nothing_is_skipped(deps: Deps) -> None:
    """Better an uncited issue than one citing the moment a different item came from."""
    await a_filed_issue(deps)
    await deps.db.update("actions", "a-1", {"inputs": {"title": "Something else entirely"}})

    reference, reason = await proposal(
        {**(await deps.db.get("actions", "a-1") or {})}, deps.db)

    assert reference == ""
    assert reason == "no reconciled item matches its title"


async def test_writing_touches_the_citations_field_and_nothing_else(deps: Deps) -> None:
    await a_filed_issue(deps)
    before: dict[str, Any] = dict(await deps.db.get("actions", "a-1") or {})
    planned = await plan(deps.db)

    await deps.db.update("actions", "a-1", {"citations": [planned[0]["citation"]]})

    after: dict[str, Any] = dict(await deps.db.get("actions", "a-1") or {})
    assert after["citations"] == ["fathom:8841201@00:14"]
    assert {k: v for k, v in after.items() if k != "citations"} == {
        k: v for k, v in before.items() if k != "citations"}


async def test_running_it_a_second_time_changes_nothing(deps: Deps) -> None:
    await a_filed_issue(deps)
    planned = await plan(deps.db)
    await deps.db.update("actions", "a-1", {"citations": [planned[0]["citation"]]})

    assert await plan(deps.db) == []


async def test_the_table_says_what_it_would_do_and_what_it_could_not(deps: Deps) -> None:
    await a_filed_issue(deps, timestamp="")

    rendered = table(await plan(deps.db))

    assert "INV-116" in rendered
    assert "skipped: its evidence carries no timestamp" in rendered
    assert "0 of 1 uncited issues" in rendered


def test_an_empty_plan_says_so() -> None:
    assert table([]) == "every filed issue already carries a citation — nothing to do"

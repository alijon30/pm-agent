import json
from pathlib import Path

from app.harness.deps import Deps
from fastapi.testclient import TestClient

from tests.fakes.fake_agents import FakeExtractor

SAMPLE = json.loads(
    (Path(__file__).parents[2] / "fixtures" / "fathom_webhook_sample.json").read_text()
)
GOOD = {
    "decisions": [],
    "open_questions": [],
    "action_items": [{"title": "t", "evidence": [{"quote": "I can have that done by next Friday"}]}],
}


def test_tick_without_the_token_is_rejected(client: TestClient) -> None:
    assert client.post("/tick").status_code == 401
    assert client.post("/tick", headers={"X-Tick-Token": "wrong"}).status_code == 401


async def test_tick_runs_due_tasks_and_reports_outcomes(client: TestClient, deps: Deps) -> None:
    deps.extractor = FakeExtractor([GOOD])
    event_id = await deps.events.record(provider="fathom", provider_event_id="m", payload=SAMPLE,
                                        project_id="acme")
    await deps.queue.enqueue(kind="extract", project_id="acme", payload={"event_id": event_id},
                             reason="t", root_event_id=event_id)
    r = client.post("/tick", headers={"X-Tick-Token": "tick-secret"})
    assert r.status_code == 200
    # One tick drains the chain: extract succeeds, and the reconcile it enqueued runs in the
    # same request — failing honestly (no reconciler configured) into a backoff retry.
    assert r.json() == {"processed": 2, "outcomes": ["done", "queued"], "daily_review": None}
    reconcile = (await deps.db.query("tasks", [("kind", "==", "reconcile")]))[0]
    assert "reconciler" in reconcile["error"]
    # The retry is on backoff, so an immediate second tick finds nothing due.
    r = client.post("/tick", headers={"X-Tick-Token": "tick-secret"})
    assert r.json() == {"processed": 0, "outcomes": [], "daily_review": None}


# --- the morning review --------------------------------------------------------------------------

async def test_the_review_header_starts_the_day_and_the_same_tick_runs_it(
    client: TestClient, deps: Deps
) -> None:
    response = client.post("/tick", headers={"X-Tick-Token": "tick-secret",
                                             "X-Tick-Kind": "daily_review"})

    assert response.status_code == 200
    body = response.json()
    assert body["daily_review"] is not None
    review = await deps.db.get("tasks", body["daily_review"])
    assert review is not None
    assert review["kind"] == "daily_review" and review["params"] == {"project": "acme"}
    # Queued and drained inside the same request, not left for the next minute — and the plan
    # it enqueues runs in the same tick, which is the loop closing.
    assert review["status"] == "done" and body["outcomes"] == ["done", "done"]
    plans = await deps.db.query("tasks", [("kind", "==", "plan")])
    assert len(plans) == 1 and plans[0]["parent_task_id"] == review["id"]


async def test_a_second_review_the_same_day_is_not_queued(
    client: TestClient, deps: Deps
) -> None:
    headers = {"X-Tick-Token": "tick-secret", "X-Tick-Kind": "daily_review"}
    first = client.post("/tick", headers=headers).json()
    second = client.post("/tick", headers=headers).json()

    assert first["daily_review"] is not None and second["daily_review"] is None
    assert await deps.db.count("tasks", [("kind", "==", "daily_review")]) == 1


async def test_tomorrow_gets_its_own_review(client: TestClient, deps: Deps) -> None:
    headers = {"X-Tick-Token": "tick-secret", "X-Tick-Kind": "daily_review"}
    client.post("/tick", headers=headers)
    deps.clock.advance(days=1)
    client.post("/tick", headers=headers)

    assert await deps.db.count("tasks", [("kind", "==", "daily_review")]) == 2


async def test_an_ordinary_tick_never_starts_a_review(client: TestClient, deps: Deps) -> None:
    body = client.post("/tick", headers={"X-Tick-Token": "tick-secret"}).json()

    assert body["daily_review"] is None
    assert await deps.db.count("tasks", [("kind", "==", "daily_review")]) == 0

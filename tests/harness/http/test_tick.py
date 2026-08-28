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
    assert r.json() == {"processed": 2, "outcomes": ["done", "queued"]}
    reconcile = (await deps.db.query("tasks", [("kind", "==", "reconcile")]))[0]
    assert "reconciler" in reconcile["error"]
    # The retry is on backoff, so an immediate second tick finds nothing due.
    r = client.post("/tick", headers={"X-Tick-Token": "tick-secret"})
    assert r.json() == {"processed": 0, "outcomes": []}

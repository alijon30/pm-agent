import asyncio
import json
from pathlib import Path
from typing import Any

from app.harness.deps import Deps
from app.harness.stages import runner
from app.harness.stages.base import StageResult
from app.harness.store.db import Doc

from tests.fakes.fake_agents import FakeExtractor

SAMPLE = json.loads(
    (Path(__file__).parents[2] / "fixtures" / "fathom_webhook_sample.json").read_text()
)
GOOD = {
    "decisions": [],
    "open_questions": [],
    "action_items": [{"title": "t", "evidence": [{"quote": "I can have that done by next Friday"}]}],
}


async def seed(deps: Deps, kind: str = "extract") -> str:
    event_id = await deps.events.record(provider="fathom", provider_event_id="m", payload=SAMPLE,
                                        project_id="acme")
    tid = await deps.queue.enqueue(kind=kind, project_id="acme", payload={"event_id": event_id},
                                   reason="t", root_event_id=event_id)
    assert tid is not None
    return tid


async def test_a_successful_stage_marks_the_task_done_and_enqueues_its_children(deps: Deps) -> None:
    deps.extractor = FakeExtractor([GOOD])
    tid = await seed(deps)
    task = (await deps.queue.due(["extract"], 10))[0]
    assert await runner.run_task(task, deps) == "done"
    done = await deps.db.get("tasks", tid)
    assert done is not None and done["status"] == "done"
    assert await deps.db.count("tasks", [("kind", "==", "reconcile")]) == 1


async def test_a_raising_stage_is_requeued_with_a_redacted_reason(deps: Deps) -> None:
    class Boom:
        async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError("linear token lin_api_SECRET123 rejected")

    deps.extractor = Boom()
    tid = await seed(deps)
    task = (await deps.queue.due(["extract"], 10))[0]
    assert await runner.run_task(task, deps) == "queued"
    doc = await deps.db.get("tasks", tid)
    assert doc is not None
    assert "lin_api_SECRET123" not in doc["error"] and "RuntimeError" in doc["error"]


async def test_a_stage_that_exceeds_the_timeout_is_treated_as_a_failure(deps: Deps) -> None:
    async def slow(task: Doc, d: Deps) -> StageResult:
        await asyncio.sleep(0.2)
        return StageResult({})

    runner.STAGES["slow"] = slow
    try:
        deps.settings.stage_timeout_seconds = 0
        tid = await seed(deps, kind="slow")
        task = (await deps.queue.due(["slow"], 10))[0]
        assert await runner.run_task(task, deps) == "queued"
        doc = await deps.db.get("tasks", tid)
        assert doc is not None and "TimeoutError" in doc["error"]
    finally:
        del runner.STAGES["slow"]


async def test_a_task_someone_else_claimed_is_skipped(deps: Deps) -> None:
    deps.extractor = FakeExtractor([GOOD])
    await seed(deps)
    task = (await deps.queue.due(["extract"], 10))[0]
    assert await deps.queue.claim(task["id"]) is not None
    assert await runner.run_task(task, deps) == "skipped"

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


# --- when work somebody asked for runs out of retries --------------------------------------------

COMMISSIONED = {"requester_slack_id": "U-maya", "request_channel": "C-random",
                "request_ts": "1787821201.000100"}


async def a_doomed_check(deps: Deps, *, context: dict[str, Any]) -> str:
    """A commissioned check whose executor always raises, already out of retries."""
    from app.harness.store.actions import ActionStore

    from tests.conftest import ACME
    from tests.fakes.fake_slack import FakeSlack

    await deps.projects.upsert("acme", {**ACME, "slack_channel_id": "C-product"})
    deps.actions = ActionStore(deps.db, deps.clock)
    deps.slack = FakeSlack()
    deps.github = None  # check_pr_exists reports "unavailable" rather than raising, so:

    async def explode(task: Doc, d: Deps) -> StageResult:
        raise RuntimeError("github token ghp_SECRET rejected")

    runner.STAGES["doomed"] = explode
    tid = await deps.queue.enqueue(
        kind="doomed", project_id="acme", payload={}, params={"issue": "INV-26"},
        reason="you asked me to watch INV-26", context=context)
    assert tid is not None
    await deps.db.update("tasks", tid, {"attempts": 3})
    return tid


async def test_a_requester_is_told_once_when_their_work_is_abandoned(deps: Deps) -> None:
    tid = await a_doomed_check(deps, context=COMMISSIONED)
    try:
        task = (await deps.queue.due(["doomed"], 10))[0]
        assert await runner.run_task(task, deps) == "failed"
    finally:
        del runner.STAGES["doomed"]

    assert len(deps.slack.posts) == 1
    told = deps.slack.posts[0]
    assert told["channel"] == "C-random" and told["thread_ts"] == "1787821201.000100"
    assert told["text"].startswith("<@U-maya>, I'm blocked on ")
    assert "I'll leave this with you." in told["text"]
    assert "ghp_SECRET" not in told["text"] and "[redacted]" in told["text"]
    assert (await deps.db.get("tasks", tid) or {})["status"] == "failed"


async def test_the_blocked_note_is_recorded_and_capped_like_any_interruption(
    deps: Deps,
) -> None:
    await a_doomed_check(deps, context=COMMISSIONED)
    try:
        task = (await deps.queue.due(["doomed"], 10))[0]
        await runner.run_task(task, deps)
    finally:
        del runner.STAGES["doomed"]

    posts = await deps.db.query("actions", [("kind", "==", "slack.post")])
    assert len(posts) == 1
    assert posts[0]["status"] == "done" and posts[0]["cap_kind"] == "ping"


async def test_a_retry_that_still_has_attempts_left_says_nothing_yet(deps: Deps) -> None:
    tid = await a_doomed_check(deps, context=COMMISSIONED)
    await deps.db.update("tasks", tid, {"attempts": 0})
    try:
        task = (await deps.queue.due(["doomed"], 10))[0]
        assert await runner.run_task(task, deps) == "queued"
    finally:
        del runner.STAGES["doomed"]

    assert deps.slack.posts == []  # it will try again; nobody needs telling


async def test_work_nobody_asked_for_fails_without_bothering_anyone(deps: Deps) -> None:
    await a_doomed_check(deps, context={})
    try:
        task = (await deps.queue.due(["doomed"], 10))[0]
        assert await runner.run_task(task, deps) == "failed"
    finally:
        del runner.STAGES["doomed"]

    assert deps.slack.posts == []

"""The lesson store keeps a small, bounded memory of the agent's own behaviour. These tests are
about the two properties that make that safe: the order is total, and the memory has a lid."""

from app.harness.deps import Deps
from app.harness.store.lessons import MAX_LESSONS, LessonStore


async def test_a_lesson_keeps_what_it_was_drawn_from(deps: Deps) -> None:
    store = LessonStore(deps.db, deps.clock)
    lesson_id = await store.add(
        project_id="acme", text="Wait a working day before checking for a pull request.",
        evidence=["task:t-1", "action:a-1"], source_task_id="review-1")

    stored = await deps.db.get("lessons", lesson_id)
    assert stored is not None
    assert stored["text"].startswith("Wait a working day")
    assert stored["evidence"] == ["task:t-1", "action:a-1"]
    assert stored["project_id"] == "acme" and stored["source_task_id"] == "review-1"
    assert stored["created_at"] == "2026-08-27T09:00:00+00:00"


async def test_lessons_come_back_newest_first_even_within_one_second(deps: Deps) -> None:
    """The clock has second precision, so several lessons from one review share a timestamp.
    Order still has to be certain, or "the newest twelve" is a coin toss."""
    store = LessonStore(deps.db, deps.clock)
    for n in range(3):
        await store.add(project_id="acme", text=f"lesson {n}", evidence=[f"task:{n}"])

    assert [row["text"] for row in await store.for_project("acme")] == [
        "lesson 2", "lesson 1", "lesson 0"]


async def test_the_memory_has_a_lid_and_the_oldest_falls_off(deps: Deps) -> None:
    store = LessonStore(deps.db, deps.clock)
    for n in range(MAX_LESSONS + 5):
        await store.add(project_id="acme", text=f"lesson {n}", evidence=[f"task:{n}"])

    kept = await store.for_project("acme")
    assert len(kept) == MAX_LESSONS
    assert kept[0]["text"] == f"lesson {MAX_LESSONS + 4}"
    assert kept[-1]["text"] == "lesson 5"  # 0 to 4 fell off


async def test_deleting_a_lesson_does_not_disturb_the_order_of_the_rest(deps: Deps) -> None:
    store = LessonStore(deps.db, deps.clock)
    first = await store.add(project_id="acme", text="one", evidence=["task:1"])
    await store.add(project_id="acme", text="two", evidence=["task:2"])
    await store.delete(first)
    await store.add(project_id="acme", text="three", evidence=["task:3"])

    assert [row["text"] for row in await store.for_project("acme")] == ["three", "two"]


async def test_one_project_never_reads_another_projects_lessons(deps: Deps) -> None:
    store = LessonStore(deps.db, deps.clock)
    await store.add(project_id="acme", text="ours", evidence=["task:1"])
    await store.add(project_id="other", text="theirs", evidence=["task:2"])

    assert [row["text"] for row in await store.for_project("acme")] == ["ours"]
    assert [row["text"] for row in await store.for_project("other")] == ["theirs"]


async def test_a_project_that_has_learned_nothing_yet_reads_as_empty(deps: Deps) -> None:
    assert await LessonStore(deps.db, deps.clock).for_project("acme") == []

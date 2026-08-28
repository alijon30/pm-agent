"""The plan gate: what the agent proposes to do to itself, checked before it can."""

from datetime import UTC, datetime
from typing import Any

from app.harness.kinds.registry import KINDS, get_kind, validate_params
from app.harness.verify.plan import check_plan

NOW = datetime(2026, 8, 27, 9, 0, tzinfo=UTC)
POLICY = {"plan_horizon_days": 30, "max_plan_size": 12, "max_open_tasks": 50}
KNOWN = {"INV-142", "INV-104", "Nodir Rahimov"}


async def known(token: str) -> bool:
    return token in KNOWN


def plan(*tasks: dict[str, Any], supersedes: list[str] | None = None) -> dict[str, Any]:
    return {"tasks": list(tasks), "supersedes": supersedes or [], "notes": ""}


def task(key: str, kind: str, params: dict[str, Any], due: str, **kw: Any) -> dict[str, Any]:
    return {"key": key, "kind": kind, "params": params, "due": due,
            "reason": kw.get("reason", f"{key} reason"),
            "depends_on": kw.get("depends_on", []), "on_unmet": kw.get("on_unmet", "none"),
            "on_dep_failed": kw.get("on_dep_failed", "skip"), "context": kw.get("context", {})}


async def check(p: dict[str, Any], open_tasks: int = 0) -> Any:
    return await check_plan(p, now=NOW, policy=POLICY, open_tasks=open_tasks,
                            existing_ids=lambda tid: tid.startswith("existing-"),
                            id_exists=known)


# --- the catalog ------------------------------------------------------------------------------

def test_the_catalog_lists_every_kind_the_agent_may_schedule() -> None:
    assert set(KINDS) == {
        "check_issue_state", "check_pr_exists", "check_pr_reviewed", "check_pr_merged",
        "nudge", "escalate", "reconcile_item", "daily_review", "report", "intake",
    }


def test_the_prompt_catalog_hides_the_kinds_no_model_may_schedule() -> None:
    from app.harness.kinds.registry import NOT_SCHEDULABLE, catalog_for_prompt

    offered = {row["kind"] for row in catalog_for_prompt()}
    assert offered == set(KINDS) - set(NOT_SCHEDULABLE)
    assert "intake" not in offered, "an agent that can schedule intakes can talk to itself"


def test_a_check_the_requester_commissioned_may_answer_the_requester() -> None:
    for kind in ("check_issue_state", "check_pr_exists", "check_pr_reviewed", "check_pr_merged"):
        assert "ping_requester" in KINDS[kind].unmet_actions
    assert "ping_requester" not in KINDS["nudge"].unmet_actions


def test_params_are_validated_against_the_kinds_schema() -> None:
    clean, error = validate_params("check_issue_state", {"issue": "INV-142", "expect": ["Done"]})
    assert error is None and clean == {"issue": "INV-142", "expect": ["Done"]}

    clean, error = validate_params("check_issue_state", {"issue": "INV-142"})
    assert clean is None and error is not None and "expect" in error

    clean, error = validate_params("check_pr_exists", {"issue": "INV-142", "bogus": 1})
    assert clean is None and error is not None and "bogus" in error


def test_a_kind_the_agent_invented_is_refused() -> None:
    assert get_kind("delete_everything") is None
    assert validate_params("delete_everything", {}) == (None, "unknown kind 'delete_everything'")


def test_each_kind_declares_which_unmet_actions_it_allows() -> None:
    assert "escalate_channel" in KINDS["check_issue_state"].unmet_actions
    assert KINDS["nudge"].unmet_actions == ()


# --- a good plan ------------------------------------------------------------------------------

async def test_a_dependency_chain_is_accepted_in_an_order_that_can_be_created() -> None:
    verdict = await check(plan(
        task("review", "check_pr_reviewed", {"issue": "INV-142"}, "2026-08-30T16:00:00Z",
             depends_on=["pr"], on_unmet="nudge_reviewer"),
        task("impl", "check_issue_state", {"issue": "INV-142", "expect": ["In Progress"]},
             "2026-08-28T16:00:00Z", on_unmet="nudge_assignee"),
        task("pr", "check_pr_exists", {"issue": "INV-142"}, "2026-08-29T16:00:00Z",
             depends_on=["impl"]),
    ))
    assert verdict.ok and verdict.rejected == [] and verdict.reasons == []
    assert [t["key"] for t in verdict.tasks] == ["impl", "pr", "review"]
    assert verdict.tasks[0]["due_at"] == "2026-08-28T16:00:00+00:00"
    assert verdict.tasks[1]["depends_on"] == ["impl"]


async def test_a_plan_may_wait_on_a_check_that_is_already_scheduled() -> None:
    verdict = await check(plan(task(
        "after", "nudge",
        {"person": "Nodir Rahimov", "about": "INV-142", "template": "still_open"},
        "2026-08-28T09:00:00Z", depends_on=["existing-123"])))
    assert verdict.ok and verdict.tasks[0]["depends_on"] == ["existing-123"]


async def test_an_empty_plan_is_a_valid_plan() -> None:
    verdict = await check(plan())
    assert verdict.ok and verdict.tasks == []


# --- what it refuses --------------------------------------------------------------------------

async def test_an_unknown_kind_or_bad_params_loses_that_task_alone() -> None:
    verdict = await check(plan(
        task("ok", "check_issue_state", {"issue": "INV-142", "expect": ["Done"]},
             "2026-08-28T09:00:00Z"),
        task("bad_kind", "launch_rockets", {}, "2026-08-28T09:00:00Z"),
        task("bad_params", "check_pr_exists", {"pull": 7}, "2026-08-28T09:00:00Z"),
    ))
    assert verdict.ok is False
    assert [t["key"] for t in verdict.tasks] == ["ok"]
    assert {r["key"] for r in verdict.rejected} == {"bad_kind", "bad_params"}


async def test_a_check_about_an_issue_that_does_not_exist_is_refused() -> None:
    verdict = await check(plan(task(
        "ghost", "check_issue_state", {"issue": "INV-999", "expect": ["Done"]},
        "2026-08-28T09:00:00Z")))
    assert verdict.tasks == [] and "INV-999" in verdict.rejected[0]["reason"]


async def test_a_nudge_to_someone_who_is_not_on_the_project_is_refused() -> None:
    verdict = await check(plan(task(
        "ping", "nudge", {"person": "Sam", "about": "INV-142", "template": "still_open"},
        "2026-08-28T09:00:00Z")))
    assert verdict.tasks == [] and "Sam" in verdict.rejected[0]["reason"]


async def test_a_due_in_the_past_or_beyond_the_horizon_is_refused() -> None:
    verdict = await check(plan(
        task("past", "check_issue_state", {"issue": "INV-142", "expect": ["Done"]},
             "2026-08-27T08:00:00Z"),
        task("far", "check_issue_state", {"issue": "INV-142", "expect": ["Done"]},
             "2026-10-15T09:00:00Z"),
        task("gibberish", "check_issue_state", {"issue": "INV-142", "expect": ["Done"]},
             "next Friday"),
    ))
    assert verdict.tasks == []
    reasons = " ".join(r["reason"] for r in verdict.rejected)
    assert "in the past" in reasons and "horizon" in reasons and "ISO-8601" in reasons


async def test_a_check_may_not_take_an_action_its_kind_does_not_allow() -> None:
    verdict = await check(plan(task(
        "x", "check_pr_exists", {"issue": "INV-142"}, "2026-08-28T09:00:00Z",
        on_unmet="escalate_channel")))
    assert verdict.tasks == [] and "on_unmet" in verdict.rejected[0]["reason"]


async def test_a_cycle_rejects_the_whole_plan_because_it_cannot_be_ordered() -> None:
    verdict = await check(plan(
        task("a", "check_issue_state", {"issue": "INV-142", "expect": ["Done"]},
             "2026-08-28T09:00:00Z", depends_on=["b"]),
        task("b", "check_pr_exists", {"issue": "INV-142"}, "2026-08-28T09:00:00Z",
             depends_on=["a"]),
    ))
    assert verdict.ok is False and verdict.tasks == []
    assert any("cycle" in r for r in verdict.reasons)


async def test_rejection_cascades_so_nothing_waits_on_something_that_will_never_run() -> None:
    verdict = await check(plan(
        task("bad", "launch_rockets", {}, "2026-08-28T09:00:00Z"),
        task("child", "check_pr_exists", {"issue": "INV-142"}, "2026-08-28T09:00:00Z",
             depends_on=["bad"]),
        task("orphan", "check_pr_exists", {"issue": "INV-142"}, "2026-08-28T09:00:00Z",
             depends_on=["nope"]),
    ))
    assert verdict.tasks == []
    assert {r["key"] for r in verdict.rejected} == {"bad", "child", "orphan"}


async def test_duplicate_keys_lose_the_later_one() -> None:
    verdict = await check(plan(
        task("dup", "check_pr_exists", {"issue": "INV-142"}, "2026-08-28T09:00:00Z"),
        task("dup", "check_pr_exists", {"issue": "INV-104"}, "2026-08-28T09:00:00Z"),
    ))
    assert len(verdict.tasks) == 1 and verdict.rejected[0]["reason"] == "duplicate key 'dup'"


async def test_a_plan_larger_than_the_project_allows_is_trimmed_and_says_so() -> None:
    many = [task(f"t{i}", "check_issue_state", {"issue": "INV-142", "expect": ["Done"]},
                 "2026-08-28T09:00:00Z") for i in range(14)]
    verdict = await check(plan(*many))
    assert len(verdict.tasks) == 12 and any("max_plan_size" in r for r in verdict.reasons)


async def test_a_project_already_full_of_open_work_accepts_only_what_fits() -> None:
    many = [task(f"t{i}", "check_issue_state", {"issue": "INV-142", "expect": ["Done"]},
                 "2026-08-28T09:00:00Z") for i in range(5)]
    verdict = await check(plan(*many), open_tasks=48)
    assert len(verdict.tasks) == 2 and any("max_open_tasks" in r for r in verdict.reasons)

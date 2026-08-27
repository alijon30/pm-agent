"""The plan gate: what the agent proposes to do to itself, checked before it can.

A plan is the one place the model reaches into the future, so this is where a bad idea is
cheapest to stop. Known kinds, valid params, unique keys, dependencies that resolve, no cycles,
due times inside the horizon, real identifiers, and a size the project can absorb.

Rejection is per-task where it can be — one bad check should not lose a good plan — but a cycle
rejects everything, because a graph that cannot be ordered cannot be partially trusted."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.harness.core.clock import iso, parse_iso
from app.harness.kinds.registry import KINDS, UNMET_ACTIONS, validate_params

ID_PARAM_FIELDS = ("issue", "person")
DEP_POLICIES = ("skip", "run_anyway", "cancel")
PAST_GRACE_MINUTES = 5


@dataclass(frozen=True)
class PlanVerdict:
    ok: bool
    tasks: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def _parse_due(raw: Any) -> datetime | None:
    try:
        return parse_iso(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


async def check_plan(
    plan: dict[str, Any],
    *,
    now: datetime,
    policy: dict[str, Any],
    open_tasks: int,
    existing_ids: Callable[[str], bool],
    id_exists: Callable[[str], Awaitable[bool]],
) -> PlanVerdict:
    horizon = now + timedelta(days=int(policy.get("plan_horizon_days", 30)))
    max_plan = int(policy.get("max_plan_size", 12))
    max_open = int(policy.get("max_open_tasks", 50))
    grace = now - timedelta(minutes=PAST_GRACE_MINUTES)

    accepted: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, str]] = []
    reasons: list[str] = []

    # 1. every task on its own terms
    for raw in plan.get("tasks") or []:
        key = str(raw.get("key") or "")
        if not key:
            rejected.append({"key": "", "reason": "missing key"})
            continue
        if key in accepted:
            rejected.append({"key": key, "reason": f"duplicate key {key!r}"})
            continue

        kind = str(raw.get("kind") or "")
        clean, error = validate_params(kind, raw.get("params") or {})
        if error is not None or clean is None:
            rejected.append({"key": key, "reason": error or "invalid params"})
            continue

        spec = KINDS[kind]
        on_unmet = str(raw.get("on_unmet") or "none")
        if on_unmet not in UNMET_ACTIONS or (
            on_unmet != "none" and on_unmet not in spec.unmet_actions
        ):
            rejected.append({"key": key, "reason": f"on_unmet {on_unmet!r} not allowed for {kind}"})
            continue

        on_dep_failed = str(raw.get("on_dep_failed") or "skip")
        if on_dep_failed not in DEP_POLICIES:
            rejected.append({"key": key, "reason": f"on_dep_failed {on_dep_failed!r} invalid"})
            continue

        due = _parse_due(raw.get("due"))
        if due is None:
            rejected.append({"key": key, "reason": "due is not an ISO-8601 timestamp"})
            continue
        if due < grace:
            rejected.append({"key": key, "reason": f"due {iso(due)} is in the past"})
            continue
        if due > horizon:
            rejected.append({"key": key, "reason": f"due {iso(due)} is beyond the plan horizon"})
            continue

        missing = [
            str(clean[f]) for f in ID_PARAM_FIELDS
            if clean.get(f) and not await id_exists(str(clean[f]))
        ]
        if missing:
            rejected.append({"key": key, "reason": f"unknown identifier(s): {', '.join(missing)}"})
            continue

        accepted[key] = {
            "key": key, "kind": kind, "params": clean, "due_at": iso(due),
            "reason": str(raw.get("reason") or ""),
            "depends_on": [str(d) for d in raw.get("depends_on") or []],
            "on_unmet": on_unmet, "on_dep_failed": on_dep_failed,
            "context": dict(raw.get("context") or {}),
        }

    # 2. a dependency must be an accepted key or a task that already exists. Rejection cascades:
    #    a check that waits on something that will never run must not run either.
    changed = True
    while changed:
        changed = False
        for key, task in list(accepted.items()):
            unknown = [d for d in task["depends_on"] if d not in accepted and not existing_ids(d)]
            if unknown:
                rejected.append({
                    "key": key, "reason": f"depends on unknown or rejected: {', '.join(unknown)}"
                })
                del accepted[key]
                changed = True

    # 3. cycles, and a topological order so children are created after what they wait on
    indegree = {k: sum(1 for d in t["depends_on"] if d in accepted) for k, t in accepted.items()}
    ready = sorted(k for k, n in indegree.items() if n == 0)
    ordered: list[str] = []
    while ready:
        key = ready.pop(0)
        ordered.append(key)
        for other, task in accepted.items():
            if key in task["depends_on"]:
                indegree[other] -= 1
                if indegree[other] == 0:
                    ready.append(other)
                    ready.sort()
    if len(ordered) != len(accepted):
        reasons.append("dependency cycle detected; the whole plan is rejected")
        return PlanVerdict(ok=False, tasks=[], rejected=rejected, reasons=reasons)

    # 4. size. Trim from the end of the order, so nothing kept loses what it depends on.
    tasks = [accepted[k] for k in ordered]
    if len(tasks) > max_plan:
        reasons.append(f"plan trimmed from {len(tasks)} to max_plan_size {max_plan}")
        tasks = tasks[:max_plan]
    room = max(0, max_open - open_tasks)
    if len(tasks) > room:
        reasons.append(f"plan trimmed from {len(tasks)} to {room} by max_open_tasks {max_open}")
        tasks = tasks[:room]

    kept = {t["key"] for t in tasks}
    tasks = [
        {**t, "depends_on": [d for d in t["depends_on"] if d in kept or existing_ids(d)]}
        for t in tasks
    ]
    return PlanVerdict(ok=not rejected and not reasons, tasks=tasks, rejected=rejected,
                       reasons=reasons)

"""The whitelist of things the agent may schedule for itself.

Everything the planner can put on the calendar is here and nowhere else. Adding a capability to
the agent is one entry plus one executor; the model cannot invent a kind, and a kind cannot do
more than its `unmet_actions` allow."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.harness.kinds.base import KindSpec, StrictParams

# "ping_requester" answers the person who commissioned a check, in the thread they asked in.
# It exists so a check somebody asked for reports back to them rather than to the assignee, who
# never agreed to anything.
UNMET_ACTIONS = (
    "none", "nudge_assignee", "nudge_reviewer", "escalate_channel", "ping_requester",
)

# Kinds the model may never schedule. `intake` is how a request enters the system; an agent that
# could schedule its own intakes could talk to itself.
NOT_SCHEDULABLE = ("intake",)


class IssueStateParams(StrictParams):
    issue: str
    expect: list[str]


class IssueParams(StrictParams):
    issue: str


class IssueOrPrParams(StrictParams):
    issue: str | None = None
    pr: int | None = None


class NudgeParams(StrictParams):
    person: str
    about: str
    template: str


class EscalateParams(StrictParams):
    about: str
    template: str


class ItemParams(StrictParams):
    item: dict[str, Any]


class ProjectParams(StrictParams):
    project: str


class IntakeParams(StrictParams):
    """A request in words, or an identifier to stop watching. The stage rejects a task carrying
    neither — the schema stays permissive because the router, not the model, fills this in."""

    text: str = ""
    cancel: str = ""


class ReportParams(StrictParams):
    project: str
    window: str = "7d"


KINDS: dict[str, KindSpec] = {
    spec.name: spec
    for spec in (
        KindSpec(name="check_issue_state", params_schema=IssueStateParams,
                 unmet_actions=("nudge_assignee", "escalate_channel", "ping_requester"),
                 description="Is the issue in one of the expected states?"),
        KindSpec(name="check_pr_exists", params_schema=IssueParams,
                 unmet_actions=("nudge_assignee", "ping_requester"),
                 description="Does a pull request reference the issue?"),
        KindSpec(name="check_pr_reviewed", params_schema=IssueOrPrParams,
                 unmet_actions=("nudge_reviewer", "ping_requester"),
                 description="Has the pull request received at least one review?"),
        KindSpec(name="check_pr_merged", params_schema=IssueOrPrParams,
                 unmet_actions=("nudge_assignee", "escalate_channel", "ping_requester"),
                 description="Is the pull request merged?"),
        KindSpec(name="nudge", params_schema=NudgeParams, unmet_actions=(),
                 description="Send one templated nudge to a person about something."),
        KindSpec(name="escalate", params_schema=EscalateParams, unmet_actions=(),
                 description="Post one templated escalation to the project channel."),
        KindSpec(name="reconcile_item", params_schema=ItemParams, unmet_actions=(),
                 description="Re-run reconciliation for one action item."),
        KindSpec(name="daily_review", params_schema=ProjectParams, unmet_actions=(),
                 description="Gather the project's state and plan the day."),
        KindSpec(name="report", params_schema=ReportParams, unmet_actions=(),
                 description="Write a status report for the project."),
        KindSpec(name="intake", params_schema=IntakeParams, unmet_actions=(),
                 description="Turn one teammate's request into scheduled work, or stop work "
                             "they asked to stop."),
    )
}


def catalog_for_prompt() -> list[dict[str, str]]:
    """The catalog as an agent is shown it: the kinds it may schedule, their parameters and what
    each one is allowed to do when the answer is no. This is the only description of the agent's
    capabilities any prompt gets, so a new capability reaches the model by being added to KINDS
    and by nothing else."""
    return [
        {"kind": spec.name, "params": ", ".join(spec.params_schema.model_fields),
         "unmet_actions": ", ".join(spec.unmet_actions) or "none",
         "description": spec.description}
        for spec in KINDS.values()
        if spec.name not in NOT_SCHEDULABLE
    ]


def get_kind(name: str) -> KindSpec | None:
    return KINDS.get(name)


def validate_params(kind: str, params: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """(clean params, None) or (None, a one-line error the planner can act on)."""
    spec = KINDS.get(kind)
    if spec is None:
        return None, f"unknown kind {kind!r}"
    try:
        return spec.params_schema.model_validate(params).model_dump(), None
    except ValidationError as exc:
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first.get("loc", ())) or "params"
        return None, f"{kind}: {loc}: {first.get('msg', 'invalid')}"

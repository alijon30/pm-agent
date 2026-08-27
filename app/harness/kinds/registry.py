"""The whitelist of things the agent may schedule for itself.

Everything the planner can put on the calendar is here and nowhere else. Adding a capability to
the agent is one entry plus one executor; the model cannot invent a kind, and a kind cannot do
more than its `unmet_actions` allow."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.harness.kinds.base import KindSpec, StrictParams

UNMET_ACTIONS = ("none", "nudge_assignee", "nudge_reviewer", "escalate_channel")


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


class ReportParams(StrictParams):
    project: str
    window: str = "7d"


KINDS: dict[str, KindSpec] = {
    spec.name: spec
    for spec in (
        KindSpec(name="check_issue_state", params_schema=IssueStateParams,
                 unmet_actions=("nudge_assignee", "escalate_channel"),
                 description="Is the issue in one of the expected states?"),
        KindSpec(name="check_pr_exists", params_schema=IssueParams,
                 unmet_actions=("nudge_assignee",),
                 description="Does a pull request reference the issue?"),
        KindSpec(name="check_pr_reviewed", params_schema=IssueOrPrParams,
                 unmet_actions=("nudge_reviewer",),
                 description="Has the pull request received at least one review?"),
        KindSpec(name="check_pr_merged", params_schema=IssueOrPrParams,
                 unmet_actions=("nudge_assignee", "escalate_channel"),
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
    )
}


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

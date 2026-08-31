
"""What each kind of scheduled work means, said the way the person waiting for it would say it.

This lives with the kinds rather than with Slack because it is a property of the catalog, not of
any one surface: the channel, the console and the graph all need to name a check in English, and
they must all name it the same way. Adding a kind without adding its sentence is caught by a
test, so a new capability can never reach a person as a bare slug."""

from __future__ import annotations

from typing import Any

DONE_STATES = ("done", "completed", "merged", "closed", "canceled", "cancelled")
"""Tracker states that mean the work is over. One tuple, because a check that nudges about
finished work and a review that lists it as overdue are the same mistake."""

# What happens if a check comes back unmet.
UNMET_CONSEQUENCES = {
    "nudge_assignee": "if not, I'll nudge the assignee",
    "nudge_reviewer": "if not, I'll ask for a reviewer",
    "escalate_channel": "if not, I'll raise it here",
    "ping_requester": "if not, I'll ping you",
}

CHECK_SENTENCES = {
    "check_issue_state": "check that {issue} is underway",
    "check_pr_exists": "look for a pull request on {issue}",
    "check_pr_reviewed": "make sure {issue}'s PR gets a review",
    "check_pr_merged": "confirm {issue} landed",
    "nudge": "remind {person} about {about}",
    "escalate": "raise {about} in the channel",
}


# The catalog in the present tense — two tables on purpose; inflection is a rule with exceptions.
WORKING_SENTENCES = {
    "check_issue_state": "checking whether {issue} is underway",
    "check_pr_exists": "looking for a pull request on {issue}",
    "check_pr_reviewed": "checking whether {issue}'s PR has a review",
    "check_pr_merged": "checking whether {issue} landed",
    "nudge": "reminding {person} about {about}",
    "escalate": "raising {about} in the channel",
    "extract": "reading the call",
    "reconcile": "checking what was said against the tracker, the spec and the code",
    "act": "filing what the call agreed",
    "plan": "planning the follow-through",
    "report": "writing the status report",
    "intake": "answering a teammate",
    "daily_review": "reading yesterday",
}


# The same work again, in a form that survives being put after "I can't".
INFINITIVE_SENTENCES = {
    "check_issue_state": "check whether {issue} has started",
    "check_pr_exists": "find {issue}'s pull request",
    "check_pr_reviewed": "check whether {issue}'s pull request has been reviewed",
    "check_pr_merged": "confirm {issue} landed",
    "nudge": "remind {person} about {about}",
    "escalate": "raise {about} here",
    "extract": "read the call",
    "reconcile": "check what was said against the tracker",
    "act": "file what the call agreed",
    "plan": "plan the follow-through",
    "report": "write the status report",
    "intake": "do what you asked",
    "daily_review": "read yesterday",
}


def human_infinitive(task: dict[str, Any]) -> str:
    """What this task was going to do, phrased to follow "I can't"."""
    params = task.get("params") or {}
    sentence = INFINITIVE_SENTENCES.get(str(task.get("kind") or ""))
    if sentence is None:
        return human_check(task)
    return sentence.format(
        issue=params.get("issue") or "it",
        person=params.get("person") or "them",
        about=params.get("about") or "it",
    )


def human_working(task: dict[str, Any]) -> str:
    """What this task is doing, right now. Falls back to the scheduled phrasing for a kind with
    no present tense of its own, which still beats printing the kind."""
    params = task.get("params") or {}
    sentence = WORKING_SENTENCES.get(str(task.get("kind") or ""))
    if sentence is None:
        return human_check(task)
    return sentence.format(
        issue=params.get("issue") or "it",
        person=params.get("person") or "them",
        about=params.get("about") or "it",
    )


def human_check(task: dict[str, Any]) -> str:
    """One scheduled task as a sentence. An unfamiliar kind falls back to the reason the planner
    gave, which is already written for a human."""
    params = task.get("params") or {}
    sentence = CHECK_SENTENCES.get(str(task.get("kind") or ""))
    if sentence is None:
        return str(task.get("reason") or task.get("kind") or "check on this")
    return sentence.format(
        issue=params.get("issue") or "it",
        person=params.get("person") or "them",
        about=params.get("about") or "it",
    )


# What a check that came back unmet actually found, in one clause.
UNMET_FINDINGS = {
    "check_pr_exists": "still no pull request",
    "check_pr_reviewed": "still no review",
    "check_pr_merged": "it hasn't landed",
}


MET_FINDINGS = {
    "check_pr_exists": "there's a pull request open",
    "check_pr_reviewed": "the pull request has a review",
    "check_pr_merged": "it's landed",
}


def human_finding(
    task: dict[str, Any], observed: dict[str, Any], *, met: bool = False
) -> str:
    """What a check actually saw, in one clause. A state check reports the state it found:
    "it hasn't started" is false when the issue is in review and the check wanted it merged, and
    a false sentence in a message is how an agent loses the person it is talking to."""
    if str(task.get("kind")) == "check_issue_state":
        state = str(observed.get("state") or "")
        if state:
            # Tracker states are already phrases — avoid "it's in In Progress".
            said = state.lower() if state.lower().startswith("in ") else f"in {state}"
            return f"it's {said}" if met else f"it's still {said}"
        return "it's underway" if met else "it hasn't started"
    table = MET_FINDINGS if met else UNMET_FINDINGS
    return table.get(str(task.get("kind")), "it's moving" if met else "it hasn't moved")

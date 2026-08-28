"""What each kind of scheduled work means, said the way the person waiting for it would say it.

This lives with the kinds rather than with Slack because it is a property of the catalog, not of
any one surface: the channel, the console and the graph all need to name a check in English, and
they must all name it the same way. Adding a kind without adding its sentence is caught by a
test, so a new capability can never reach a person as a bare slug."""

from __future__ import annotations

from typing import Any

CHECK_SENTENCES = {
    "check_issue_state": "check that {issue} is underway",
    "check_pr_exists": "look for a pull request on {issue}",
    "check_pr_reviewed": "make sure {issue}'s PR gets a review",
    "check_pr_merged": "confirm {issue} landed",
    "nudge": "remind {person} about {about}",
    "escalate": "raise {about} in the channel",
}


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

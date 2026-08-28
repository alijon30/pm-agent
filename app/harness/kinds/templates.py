"""What the agent says when it nudges someone.

These are templates, not generated text, for three reasons: a nudge is short enough that a model
adds nothing; a template cannot hallucinate a fact; and a person who receives the same phrasing
every time learns to read it in two seconds. The variable parts are identifiers the harness
already verified.

Tone matters here more than anywhere else in the system. The agent is interrupting someone about
their own work, so it states what it observed and stops — no urgency it was not given, no
apology, no chasing."""

from __future__ import annotations

TEMPLATES: dict[str, str] = {
    "issue_not_started": (
        "{person}, {issue} ({title}) is still {state} — it was expected to be underway by now. "
        "{link}"
    ),
    "issue_overdue": (
        "{person}, {issue} ({title}) was due {due} and is still {state}. {link}"
    ),
    "pr_missing": (
        "{person}, no pull request references {issue} yet. {link}"
    ),
    "pr_unreviewed": (
        "{issue} has an open pull request with no review yet: {pr_url}"
    ),
    "pr_unmerged": (
        "{person}, the pull request for {issue} is reviewed but not merged: {pr_url}"
    ),
    "escalate_stalled": (
        "{issue} ({title}) has not moved and is now past its date. Owner: {person}. {link}"
    ),
    # The one template addressed to whoever asked for the check rather than to the owner. It
    # names their own request back to them, because a ping out of context reads as noise.
    "requester_unmet": (
        "{person}, you asked me to watch {issue} — {finding}. {link}"
    ),
    "escalate_no_owner": (
        "{issue} ({title}) has no owner and has not moved. {link}"
    ),
}


def render(template: str, **values: str) -> str:
    """Templates are code, so an unknown name or a missing value is a bug, not a fallback."""
    if template not in TEMPLATES:
        raise KeyError(f"unknown template {template!r}")
    return TEMPLATES[template].format(**values).strip()

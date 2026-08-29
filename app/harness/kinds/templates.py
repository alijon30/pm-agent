"""What the agent says when it nudges someone.

These are templates, not generated text, for three reasons: a nudge is short enough that a model
adds nothing; a template cannot hallucinate a fact; and a person who receives the same phrasing
every time learns to read it in two seconds. The variable parts are identifiers the harness
already verified.

Tone matters here more than anywhere else in the system. The agent is interrupting someone about
their own work, so it opens with their name, says the one thing it saw, and ends with a question
they can answer in four words — no urgency it was not given, no apology, no chasing. Every
variable arrives already in the voice: `{person}` is a first name, `{issue}` carries its own
link and reads as a thing rather than a key, `{when}` is a day rather than a date."""

from __future__ import annotations

TEMPLATES: dict[str, str] = {
    "issue_not_started": (
        "{person} — {issue} hasn't started, and it was meant to be underway {when}. "
        "Anything in the way?"
    ),
    "issue_overdue": (
        "{person} — {issue} was due {when} and is still in {state}. Is it still happening?"
    ),
    "pr_missing": (
        "{person} — I can't find a pull request for {issue} yet. Is one open somewhere I'm not "
        "looking?"
    ),
    "pr_unreviewed": (
        "{issue} has a pull request nobody has reviewed yet — {pr}. Anyone able to take a look?"
    ),
    "pr_unmerged": (
        "{person} — the pull request for {issue} is reviewed but hasn't landed yet: {pr}."
    ),
    "escalate_stalled": (
        "{issue} hasn't moved and is past its date. {person} owns it — worth a look."
    ),
    "escalate_no_owner": (
        "{issue} hasn't moved and nobody owns it. Who's picking this up?"
    ),
    # The one message addressed to whoever asked for the check rather than to the owner. It
    # names their own request back to them, because a ping out of context reads as noise.
    "requester_unmet": (
        "{person} — you asked me to watch {issue}: {finding}."
    ),
}


def render(template: str, **values: str) -> str:
    """Templates are code, so an unknown name or a missing value is a bug, not a fallback."""
    if template not in TEMPLATES:
        raise KeyError(f"unknown template {template!r}")
    return TEMPLATES[template].format(**values).strip()

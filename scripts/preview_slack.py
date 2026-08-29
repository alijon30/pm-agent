"""Every message the agent can send, rendered with realistic data, as the team would read it.

Copy is reviewed here rather than in the channel: one run prints the whole voice of the system
side by side, which is how a tone problem in one message becomes visible as a pattern across
all of them. Block Kit is flattened to the mrkdwn a reader sees; buttons are shown as [labels].
Where a message has both, the first line is the notification preview and the blocks are the
message — Slack shows one or the other, never both.

    uv run python scripts/preview_slack.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.harness.connectors.slack_blocks import (  # noqa: E402
    call_summary_blocks,
    commitment_blocks,
    plan_summary_blocks,
    report_blocks,
    standup_blocks,
    what_happened,
)
from app.harness.core.voice import issue_phrase  # noqa: E402
from app.harness.kinds.phrasing import (  # noqa: E402
    human_finding,
    human_infinitive,
)
from app.harness.kinds.templates import TEMPLATES, render  # noqa: E402
from app.harness.stages.checks import _values  # noqa: E402
from app.harness.stages.intake import interpretation  # noqa: E402
from app.harness.verify.priority import check_priority  # noqa: E402

# The template values come from the stage that builds them, not from a copy: a preview that
# hardcodes what the code produces is a preview that can be wrong about it.
NOW = datetime(2026, 8, 29, 9, 0, tzinfo=UTC)
OWNERS = {"INV-27": "Nodir", "INV-26": "Priya", "INV-29": "Maya", "INV-25": "Tom"}
TITLES = {"INV-27": "Fix duplicate reminder emails bug", "INV-26": "Ship CSV export"}
ROSTER_MEMBER = {"name": "Nodir Rahimov", "slack_id": "U123"}
OBSERVED = {
    "issue": "INV-27", "title": "Fix duplicate reminder emails bug", "state": "Backlog",
    "due": "2026-08-29", "url": "https://linear.app/x/INV-27",
    "pr_url": "https://github.com/x/pull/4", "assignee": "Nodir Rahimov",
}

MEETING = {"title": "Sprint 1 kickoff sync", "url": "https://fathom.video/x"}
CREATED = [
    {"identifier": "INV-27", "url": "https://linear.app/x/INV-27",
     "title": "Fix duplicate reminder emails bug", "owner": "Nodir Rahimov",
     "due": "2026-08-31", "due_hint": "by Monday"},
    {"identifier": "INV-29", "url": "https://linear.app/x/INV-29",
     "title": "Draft customer announcement for three-day grace period", "owner": "Maya Chen",
     "note": "no due date — 'by Monday' wasn't actually said"},
]
UPDATED = [{"identifier": "INV-26", "url": "https://linear.app/x/INV-26",
            "note": "raised again in this call"}]
SKIPPED = [{"title": "Pause all reminders until the fix lands", "reason": "rejected on the call"}]
CONFLICTS = [{"about": "the reminder cadence", "sides": [
    {"claim": "reminders go out 7 days after due", "source": "code:app/reminders.py:14"},
    {"claim": "reminders go out 5 days after due", "source": "notion:abc123"},
]}]
ACTIONS = [{"id": "a1", "label": "INV-27"}, {"id": "a2", "label": "INV-29"}]
TASKS = [
    {"kind": "check_issue_state", "params": {"issue": "INV-27", "expect": ["started"]},
     "due_at": "2026-08-30T16:00:00+00:00", "on_unmet": "nudge_assignee",
     "reason": "check INV-27 is underway"},
    {"kind": "check_pr_exists", "params": {"issue": "INV-27"},
     "due_at": "2026-09-01T16:00:00+00:00", "on_unmet": "nudge_assignee",
     "reason": "look for a PR on INV-27"},
    {"kind": "check_pr_merged", "params": {"issue": "INV-26"},
     "due_at": "2026-09-04T16:00:00+00:00", "on_unmet": "escalate_channel",
     "reason": "check INV-26 landed"},
]
REPORT = {
    "headline": "Reminder cadence work is moving; the duplicate-email bug is the risk.",
    "sections": [
        {"name": "shipped", "claims": [{"text": "CSV export is behind the flag and in review",
                                       "refs": ["linear:INV-26", "fathom:m@02:46"]}]},
        {"name": "at_risk", "claims": [{"text": "Duplicate reminder emails still open, "
                                                "customers affected", "refs": ["linear:INV-27"]}]},
        {"name": "decisions", "claims": [{"text": "Grace period drops from five days to three",
                                         "refs": ["decision:d1"]}]},
    ],
}
SPRINT = {"name": "Sprint 1", "start": "2026-08-28", "end": "2026-09-11"}
POLICY = {"priority_band": [2, 4], "escalation_phrases": ["urgent", "blocker", "blocked"]}


def flatten(blocks: list[dict[str, Any]]) -> str:
    out: list[str] = []
    for block in blocks:
        kind = block.get("type")
        if kind == "section":
            out.append(str((block.get("text") or {}).get("text", "")))
        elif kind == "context":
            out.append("  ⌊ " + " | ".join(str(e.get("text", "")) for e in block["elements"]))
        elif kind == "actions":
            out.append("  " + "  ".join(
                f"[{(e.get('text') or {}).get('text', '')}]" for e in block["elements"]))
        elif kind == "divider":
            out.append("  ────")
    return "\n".join(out)


def show(title: str, body: str) -> None:
    print(f"\n━━ {title} " + "━" * max(0, 78 - len(title)))
    print(body)


def main() -> None:
    show("status message (webhook received)",
         "✻ Reading *Sprint 1 kickoff sync*… I'll file what was agreed and set up the "
         "follow-through.")
    summary = f"Sprint 1 kickoff sync — {what_happened(CREATED, UPDATED, SKIPPED, CONFLICTS)}."
    show("call summary (notification line)", summary)
    show("call summary", flatten(call_summary_blocks(
        MEETING, CREATED, UPDATED, SKIPPED, CONFLICTS, ACTIONS, post_ref="p1", now=NOW)))
    show("plan announcement", "Here's how I'll follow through:\n" + flatten(
        plan_summary_blocks(TASKS, ["INV-999 doesn't exist"], OWNERS, NOW)))
    show("plan announcement (dates I chose myself)", flatten(
        plan_summary_blocks(TASKS[:2], [], OWNERS, NOW, defaulted=True)))
    show("early resolution (thread note)",
         "Priya's already on INV-26 — I've cleared the Sunday check. Next up: looking for a "
         "pull request on INV-26, Tuesday.")

    for name in TEMPLATES:
        values = _values(OBSERVED, ROSTER_MEMBER, NOW)
        finding = human_finding({"kind": "check_pr_exists"}, OBSERVED)
        show(f"nudge template · {name}", render(name, **{**values, "finding": finding}))

    show("intake reply (committed)", "Got it — I'll watch INV-27 for you.\n" + flatten(
        commitment_blocks(TASKS[:2], "", OWNERS, NOW)))
    show("intake reply (the ask needed interpreting)", flatten(commitment_blocks(
        TASKS[:1], interpretation("keep an eye on the reminders thing", TASKS[:1]),
        OWNERS, NOW)))
    watched = issue_phrase("INV-27", "Fix duplicate reminder emails bug",
                           "https://linear.app/x/INV-27")
    saw = human_finding({"kind": "check_issue_state"}, {"state": "In Progress"}, met=True)
    show("first look (thread note, once per commitment)",
         f"First look at {watched}: {saw} — I'll keep watching quietly and only speak up if "
         "that changes.")
    show("intake reply (nothing I can do)", flatten(commitment_blocks(
        [], "I can watch issues, look for pull requests and reviews, schedule nudges and "
            "write status reports — I can't reassign work in Linear.")))
    show("intake reply (cancel)", "Done — I've stopped watching INV-27.")
    show("blocker ping (requester)",
         f"<@U123> — I can't {human_infinitive(TASKS[1])}: GitHub isn't connected for this "
         "project. I'll leave it with you.")

    standup = standup_blocks(
        sprint=SPRINT, today="2026-08-31", watching=TASKS[:2],
        since={"met": 1, "early": 1, "nudged": 0,
               "movers": [{"who": "Priya Nair", "issue": "INV-26"},
                          {"who": "", "issue": "INV-25"}]},
        unmet=[TASKS[2]], overdue=[{"issue": "INV-25", "due": "2026-08-29", "state": "Todo"}],
        lesson="checks on Fridays come back unmet more often; I plan them for Monday now.",
        owners=OWNERS, titles=TITLES, now=NOW)
    first = str((standup[0].get("text") or {}).get("text") or "").splitlines()[0].strip("*")
    show("standup", first + "\n" + flatten(standup))
    show("standup (quiet day)", flatten(standup_blocks(
        sprint=SPRINT, today="2026-08-31", watching=[], since={}, unmet=[], overdue=[],
        next_due="2026-09-03T16:00:00+00:00", now=NOW)))

    show("sprint report", REPORT["headline"] + "\n" + flatten(report_blocks(REPORT, SPRINT)))
    show("gate notes (as they appear under a ticket)", "\n".join([
        check_priority(1, ["can you take the export"], POLICY).note,
        check_priority(1, ["this is a blocker, customers are being spammed"], POLICY).note,
        "Sam isn't on this project, so I left it unassigned",
        "no due date — 'by Monday' wasn't actually said",
    ]))
    show("revert replies (ephemeral)", "\n".join([
        "Reverted INV-27. I've also stopped 2 checks that were watching it.",
        "That was already reverted.",
        "I don't have that action on record any more.",
        "That never completed, so there's nothing to undo.",
        "I can't undo that right now: linear unavailable.",
        "_reverted_ (the edited message)"]))


if __name__ == "__main__":
    main()

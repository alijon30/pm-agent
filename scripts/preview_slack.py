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
from app.harness.kinds.templates import TEMPLATES, render  # noqa: E402

MEETING = {"title": "Sprint 1 kickoff sync", "url": "https://fathom.video/x"}
CREATED = [
    {"identifier": "INV-27", "url": "https://linear.app/x/INV-27",
     "title": "Fix duplicate reminder emails bug", "owner": "Nodir Rahimov"},
    {"identifier": "INV-29", "url": "https://linear.app/x/INV-29",
     "title": "Draft customer announcement for three-day grace period", "owner": "Maya Chen",
     "note": "no due date set: 'by Monday' was not spoken"},
]
UPDATED = [{"identifier": "INV-26", "url": "https://linear.app/x/INV-26",
            "note": "PR expected Monday — Priya"}]
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
    show("call summary (notification line)",
         what_happened(CREATED, UPDATED, SKIPPED, CONFLICTS))
    show("call summary", flatten(call_summary_blocks(
        MEETING, CREATED, UPDATED, SKIPPED, CONFLICTS, ACTIONS, post_ref="p1")))
    show("plan announcement", "I'll follow up on 3 things\n" + flatten(
        plan_summary_blocks(TASKS, ["a moon-phase check I could not verify"])))
    show("early resolution (thread note)",
         "✓ INV-26 is already underway — I've closed 1 planned check early.")
    for name in TEMPLATES:
        show(f"nudge template · {name}", render(
            name, person="<@U123>", issue="INV-27", title="Fix duplicate reminder emails bug",
            state="Backlog", due="Sep 1", link="https://linear.app/x/INV-27",
            pr_url="https://github.com/x/pull/4", finding="no pull request yet"))
    show("intake reply (committed)", "Committed: 2 checks\n" + flatten(
        commitment_blocks(TASKS[:2], "I'll watch INV-27 for you this week.")))
    show("intake reply (nothing I can do)", flatten(commitment_blocks(
        [], "I can watch issues, look for pull requests and reviews, schedule nudges and "
            "write status reports — I can't reassign work in Linear.")))
    show("intake reply (cancel)", "Done — stopped 2 checks on INV-27.")
    show("blocker ping (requester)",
         "<@U123>, I'm blocked on look for a pull request on INV-27 — GitHub is not "
         "configured for this project. I'll leave this with you.")
    show("standup", "Morning — here's today.\n" + flatten(standup_blocks(
        sprint=SPRINT, today="2026-08-31", watching=TASKS[:2],
        since={"met": 1, "early": 1, "moved": 2, "nudged": 0},
        unmet=[TASKS[2]], overdue=[{"issue": "INV-25", "due": "2026-08-29", "state": "Todo"}],
        lesson="checks on Fridays come back unmet more often; I plan them for Monday now.")))
    show("standup (quiet day)", flatten(standup_blocks(
        sprint=SPRINT, today="2026-08-31", watching=[], since={}, unmet=[], overdue=[],
        next_due="2026-09-03T16:00:00+00:00")))
    show("sprint report", "Sprint 1: " + REPORT["headline"] + "\n" + flatten(
        report_blocks(REPORT, SPRINT)))
    show("revert replies (ephemeral)", "\n".join([
        "reverted INV-27", "already reverted", "that action is no longer on record",
        "that action never completed, so there is nothing to undo",
        "could not undo it: linear unavailable", "_reverted_ (the edited message)"]))


if __name__ == "__main__":
    main()

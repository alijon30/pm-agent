"""Where everything sits on the graph, worked out before the page loads.

The old view was a force simulation: position meant nothing, and a reviewer asking the only
questions that matter — what came in, what did it do, what is it doing now, what happens next —
got a hairball. Here position is the answer. **X is time**, one column per day that holds
something. **Y is a lane**, one per kind of work:

    HEARD       what arrived — calls, and asks from Slack
    UNDERSTOOD  what it made of them — decisions, disagreements
    DID         what it changed in the world — issues, posts, nudges
    WATCHING    what it is still holding — checks, past and scheduled
    LEARNED     what it took away

Every function here is pure and takes its clock from the caller, because the layout is a claim
about the agent's day and a claim has to be testable without a browser. The script positions
what this decides; it never decides anything itself."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

LANES = ("heard", "understood", "did", "watching", "learned")
LANE_OF = {
    "meeting": "heard", "intake": "heard",
    "decision": "understood", "conflict": "understood",
    "issue": "did", "post": "did",
    "check": "watching",
    "lesson": "learned",
}
STAGE_NAMES = ("read", "triaged", "reconciled", "filed", "planned")
# Which task kind carries each segment. "triaged" has no task of its own — it is the step inside
# extract that decides which transcript lines the model ever sees — so it reads extract's state
# and carries its own note.
STAGE_KIND = {
    "read": "extract", "triaged": "extract", "reconciled": "reconcile",
    "filed": "act", "planned": "plan",
}
# Every node is a chip or a row that carries its own label inside it, so the room one needs is
# the width it is drawn at. Nothing hangs a caption underneath any more.
# Hard minimums. Everything here is the width at which the thing is still readable, and
# nothing is allowed below it: a page that fits the viewport by cutting "Sprint 1 kickoff sync"
# into "Sprint 1 kick / sync" has traded the only thing it was for. When the week is wider than
# the screen, the screen scrolls.
CARD_WIDTH = 220
ISSUE_WIDTH = 260
CHIP_WIDTH = 220
CHECK_WIDTH = 200
GAP = 24
CARD_SLOT = CARD_WIDTH + GAP
ISSUE_SLOT = ISSUE_WIDTH + GAP
CHIP_SLOT = CHIP_WIDTH + GAP
CHECK_SLOT = CHECK_WIDTH + GAP
SMALL_SLOT = 14
MIN_COLUMN = CHECK_SLOT
LABEL_SLOT = CHIP_SLOT
# A strip stops widening at two of the widest thing it holds; past that it wraps to more rows.
MAX_COLUMN = ISSUE_SLOT * 2
# A day still ahead holds one pill per row and nothing else: a 150px pill with padding round
# it. Four scheduled days should cost a fifth of the screen, not half of it.
FUTURE_COLUMN = 190
# A day whose whole record is a standup post has nothing to lay out. Giving it a working day's
# width pushes the days that do have content off the screen.
QUIET_COLUMN = 110
OPEN_STATUSES = ("queued", "blocked", "leased", "deferred")

# Two baselines per lane. The primary row carries the things a reviewer came to see; the
# secondary row carries what the agent said about them — real work, but not what you scan for,
# and twelve Slack posts sharing a row with twelve issues made both unreadable.
PRIMARY, SECONDARY = "primary", "secondary"
ROW_OF = {
    "meeting": PRIMARY, "intake": PRIMARY, "decision": PRIMARY, "issue": PRIMARY,
    "check": PRIMARY, "lesson": PRIMARY,
    "post": SECONDARY, "conflict": SECONDARY,
}
LANE_MIN = 72
LANE_EMPTY = 40
ROW_HEIGHT = 62
SETTLED = ("met", "early", "unmet", "failed")


def zone(project: dict[str, Any]) -> ZoneInfo:
    """The project's own timezone, falling back to UTC.

    A day boundary is the one thing on this page a viewer checks against their own memory of
    the week, so it has to be the team's midnight rather than the server's."""
    try:
        return ZoneInfo(str(project.get("timezone") or "UTC"))
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def day_key(ts: str, tz: ZoneInfo) -> str:
    """The local calendar day an ISO timestamp falls on. Empty for anything unparseable, which
    the caller drops rather than guessing a day for."""
    text = str(ts or "").strip()
    if not text:
        return ""
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return moment.astimezone(tz).date().isoformat()


def day_label(key: str, today: str) -> str:
    """"Today" for today, otherwise the weekday and date a person would say out loud."""
    if key == today:
        return "Today"
    try:
        day = datetime.fromisoformat(key).date()
    except ValueError:
        return key
    return f"{day.strftime('%a')} {day.strftime('%b')} {day.day}"


def build_days(keys: list[str], today: str) -> list[dict[str, Any]]:
    """One column per day that holds something, in order.

    Days with nothing in them are not drawn: a week of empty columns says the agent was idle
    when it simply was not working that weekend, and the horizontal room is better spent.

    Today is the exception and always gets a column, even on a quiet morning. It is where the
    now line lives — the boundary between what happened and what is scheduled — and a reader
    looking for "what is going on right now" must never fail to find the place it would be."""
    columns: list[dict[str, Any]] = []
    for key in sorted({k for k in keys if k} | {today}):
        columns.append({
            "key": key, "label": day_label(key, today),
            "today": key == today, "future": key > today,
        })
    return columns


def slot_width(lane: str, row: str) -> int:
    """The horizontal room one node in this lane and row needs.

    Cards are counted at their real width — measuring a call at a mark's slot is what let three
    of them stack on top of each other — and a labelled mark is counted at the width its title
    wraps to, which is what keeps two labels from touching."""
    if row == SECONDARY:
        return SMALL_SLOT
    if lane == "heard":
        return CARD_SLOT
    if lane == "did":
        return ISSUE_SLOT
    return CHECK_SLOT if lane == "watching" else CHIP_SLOT


def row_of(node_type: str) -> str:
    """Which of a lane's two baselines a node sits on."""
    return ROW_OF.get(str(node_type), PRIMARY)


def short_day(key: str) -> str:
    """"Aug 31" — a day named the way somebody says it mid-sentence."""
    try:
        day = datetime.fromisoformat(key).date()
    except ValueError:
        return key
    return f"{day.strftime('%b')} {day.day}"


def check_day(node: dict[str, Any], today: str, tz: ZoneInfo) -> str:
    """The column a check belongs in.

    A finished check sits on the day it finished, whatever day it was booked for. Drawing a
    resolved ✓ in a future column says the agent has already done something it has not done
    yet, which is the one thing a timeline must never claim. Work still ahead sits on its due
    day, and work in flight sits on today, next to the now line."""
    state = str(node.get("state") or "")
    if state in SETTLED:
        return str(node.get("finished_day") or "") or day_key(str(node.get("ts") or ""), tz)
    if state == "leased":
        return today
    return str(node.get("due_day") or "") or day_key(str(node.get("ts") or ""), tz)


def lane_of(node_type: str) -> str:
    """Which row a node lives in. Anything unrecognised goes to DID, the lane about things that
    happened, because a node with no lane would not be drawn at all."""
    return LANE_OF.get(str(node_type), "did")


def place(nodes: list[dict[str, Any]], tz: ZoneInfo, today: str) -> list[dict[str, Any]]:
    """Give every node its day, its lane, and its position within them.

    `seq` is the node's index among its own lane on its own day, in event order, so a burst of
    work fans out across the column instead of stacking into one illegible pile. A future check
    is placed on the day it is due rather than the day it was created — that column is the
    question it is there to answer."""
    placed: list[dict[str, Any]] = []
    for node in nodes:
        kind = str(node.get("type"))
        key = (check_day(node, today, tz) if kind == "check"
               else day_key(str(node.get("ts") or ""), tz))
        placed.append({**node, "lane": lane_of(kind), "row": row_of(kind), "day": key})

    counters: dict[tuple[str, str, str, str], int] = {}
    for node in sorted(placed, key=lambda n: (str(n["day"]), str(n["ts"]), str(n["id"]))):
        slot = (str(node["day"]), str(node.get("group") or "day"), str(node["lane"]),
                str(node["row"]))
        node["seq"] = counters.get(slot, 0)
        counters[slot] = node["seq"] + 1
    return placed


def sub_columns(nodes: list[dict[str, Any]], days: list[dict[str, Any]]) -> dict[str, Any]:
    """The sub-columns inside each day, and how wide each one has to be.

    A day is not one grid — it is one strip per conversation. Everything a call produced sits
    beneath that call, so reading down a sub-column is that call's story and the question
    "which call filed INV-27?" is answered by looking up rather than by clicking. Work no
    conversation produced — a standup, a lesson, an early resolution — goes in a trailing
    strip of its own, because attributing it to a call would be a lie the alignment tells."""
    first_seen: dict[tuple[str, str], str] = {}
    needed: dict[tuple[str, str, str, str], int] = {}
    for node in nodes:
        day = str(node.get("day") or "")
        if not day:
            continue
        group = str(node.get("group") or "day")
        key = (day, group)
        stamp = str(node.get("ts") or "")
        # A sub-column is ordered by the moment its conversation started, so the strips run
        # left to right in the order the day actually happened.
        if node.get("type") in ("meeting", "intake") or key not in first_seen:
            first_seen[key] = stamp if node.get("type") in ("meeting", "intake") else (
                min(first_seen.get(key, stamp), stamp)
            )
        slot = (day, group, str(node.get("lane")), str(node.get("row")))
        needed[slot] = needed.get(slot, 0) + slot_width(str(node.get("lane")),
                                                        str(node.get("row")))

    out: dict[str, Any] = {}
    for column in days:
        day = str(column["key"])
        here = [(g, first_seen[(d, g)]) for (d, g) in first_seen if d == day]
        # "day" trails the conversations whatever time its contents carry.
        here.sort(key=lambda pair: (pair[0] == "day", pair[1], pair[0]))
        strips = []
        for group, _ in here:
            widest = max(
                (v for (d, g, _lane, _row), v in needed.items() if d == day and g == group),
                default=MIN_COLUMN,
            )
            # The floor is whatever the widest thing in this strip actually needs. A strip
            # holding only a check does not have to be card-wide, and one holding a card
            # cannot be narrower than the card.
            strips.append({"group": group,
                           "width": min(MAX_COLUMN, max(MIN_COLUMN, widest))})
        out[day] = strips
    return out


def lane_heights(nodes: list[dict[str, Any]]) -> dict[str, int]:
    """How tall each lane needs to be for what is actually in it.

    A lane reserving a quarter of the screen for the one lesson the agent has drawn all week
    is space stolen from the lanes doing the work. An empty lane collapses to a label."""
    rows: dict[str, set[str]] = {lane: set() for lane in LANES}
    for node in nodes:
        lane = str(node.get("lane") or "")
        if lane in rows:
            rows[lane].add(str(node.get("row") or PRIMARY))
    return {
        lane: LANE_EMPTY if not used else max(LANE_MIN, ROW_HEIGHT * len(used))
        for lane, used in rows.items()
    }


def column_widths(nodes: list[dict[str, Any]], days: list[dict[str, Any]]) -> dict[str, int]:
    """How wide each day has to be to hold its busiest lane without overlapping."""
    needed: dict[str, int] = {}
    for node in nodes:
        day = str(node.get("day") or "")
        if not day:
            continue
        lane, row = str(node.get("lane") or ""), str(node.get("row") or "")
        key = f"{day}|{lane}|{row}"
        needed[key] = needed.get(key, 0) + slot_width(lane, row)
    strips = sub_columns(nodes, days)
    has_primary = {str(n.get("day")) for n in nodes if str(n.get("row")) == PRIMARY}
    widths: dict[str, int] = {}
    for column in days:
        key = str(column["key"])
        here = strips.get(key) or []
        if key not in has_primary:
            # Nothing to lay out but dots. Today keeps enough room to be a place you look at.
            widths[key] = FUTURE_COLUMN if column.get("today") else QUIET_COLUMN
            continue
        if column.get("future"):
            # A scheduled day is a column of pills, so it is sized by how many conversations
            # put work there rather than by what a working day needs.
            widths[key] = FUTURE_COLUMN * max(1, len(here))
            continue
        # A working day is as wide as its conversations laid side by side.
        widths[key] = max(FUTURE_COLUMN, sum(s["width"] for s in here))
    return widths


# --- what a call's five stages did -------------------------------------------------------------


def check_state(task: dict[str, Any]) -> str:
    """A check's state in the one word the glyph is drawn from."""
    status = str(task.get("status") or "")
    result = task.get("result") or {}
    if status == "done":
        if result.get("early"):
            return "early"
        return "met" if result.get("met") else "unmet"
    if status in ("leased", "failed", "blocked", "deferred"):
        return "leased" if status == "leased" else status
    return "queued"


def _triage_note(result: dict[str, Any], lines: int = 0) -> str:
    """How much of the transcript the model was actually shown.

    Triage is the one step that decides what the agent could possibly have heard, so the strip
    says it plainly. Calls recorded before the count existed fall back to the length of the
    transcript, which says something true and smaller. With neither, the segment carries no
    note rather than a guess."""
    triage = result.get("triage") or {}
    kept, total = triage.get("kept"), triage.get("total")
    if isinstance(kept, int) and isinstance(total, int) and total:
        return f"{kept} / {total} lines kept" if kept < total else f"{total} lines"
    return f"{lines} lines" if lines else ""


def _filed_note(runs: list[dict[str, Any]]) -> str:
    """What the act stage actually changed, counted separately.

    Created and updated are different outcomes and the second one is the whole duplicate
    discipline story — a call that re-raised existing work and got a comment on the existing
    ticket did not file "nothing new", it updated something."""
    made = sum(len(r.get("created") or []) for r in runs)
    touched = sum(len(r.get("updated") or []) for r in runs)
    parts = []
    if made:
        parts.append(f"filed {made}")
    if touched:
        parts.append(f"updated {touched}")
    return " \u00b7 ".join(parts) if parts else "nothing new"


def _stage_note(name: str, runs: list[dict[str, Any]], lines: int = 0) -> str:
    """One clause saying what this stage produced — including when that was nothing.

    Takes every run of the stage, not just one: a call whose act stage ran twice filed the
    union of both, and showing only the last run is how "updated INV-25" disappeared."""
    if name == "triaged":
        for result in runs:
            note = _triage_note(result, lines)
            if note:
                return note
        return _triage_note({}, lines)
    if name == "read":
        items = sum(len(r.get("action_items") or []) for r in runs)
        decisions = sum(len(r.get("decision_ids") or []) for r in runs)
        if not items and not decisions:
            return "nothing to act on"
        parts = [f"{items} action item{'s' if items != 1 else ''}"] if items else []
        if decisions:
            parts.append(f"{decisions} decision{'s' if decisions != 1 else ''}")
        return ", ".join(parts)
    if name == "reconciled":
        kept = sum(len(r.get("items") or []) for r in runs)
        return f"{kept} item{'s' if kept != 1 else ''}" if kept else "nothing survived checking"
    if name == "filed":
        return _filed_note(runs)
    if name == "planned":
        watched = sum(len(r.get("accepted") or []) for r in runs)
        return f"{watched} check{'s' if watched != 1 else ''}" if watched else "nothing to watch"
    return ""


def stage_strip(chain: list[dict[str, Any]], lines: int = 0) -> list[dict[str, Any]]:
    """The five segments under a call card: what has run, what is running, what never happened.

    A stage with no task never started — a real state, and usually the honest one (no plan task
    exists when nothing needed watching). It shows as skipped rather than being left off,
    because a strip that hides its empty segments cannot be read as a progress bar.

    A stage can have run more than once for one call — a retry, or a second pass over the same
    event. All of its runs count."""
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for task in chain:
        by_kind.setdefault(str(task.get("kind") or ""), []).append(task)

    strip: list[dict[str, Any]] = []
    for name in STAGE_NAMES:
        tasks = by_kind.get(STAGE_KIND[name]) or []
        if not tasks:
            strip.append({"name": name, "state": "skipped", "note": ""})
            continue
        states = {str(t.get("status") or "") for t in tasks}
        # Done wins: if any run of this stage finished, the stage finished.
        if "done" in states:
            state = "done"
        elif "leased" in states:
            state = "leased"
        elif "failed" in states:
            state = "failed"
        elif "blocked" in states:
            state = "blocked"
        else:
            state = "queued"
        done = [t.get("result") or {} for t in tasks if t.get("status") == "done"]
        strip.append({"name": name, "state": state,
                      "note": _stage_note(name, done, lines) if state == "done" else ""})
    return strip


def roster_view(
    roster: list[dict[str, Any]], owns: dict[str, list[str]], pings: dict[str, int]
) -> list[dict[str, Any]]:
    """The people strip. People stopped being nodes because they are not events — they do not
    happen on a day, and putting them on a timeline pushed the work off it."""
    out: list[dict[str, Any]] = []
    for member in roster:
        name = str(member.get("name") or "")
        if not name:
            continue
        out.append({
            "name": name,
            "first_name": name.split()[0],
            "role": str(member.get("role") or ""),
            "owns": sorted(owns.get(name) or []),
            "pings": int(pings.get(name) or 0),
        })
    return out

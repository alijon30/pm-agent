"""Where everything sits on the graph, worked out before the page loads."""

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
# Which task kind carries each segment; "triaged" has no task of its own and reads extract's.
STAGE_KIND = {
    "read": "extract", "triaged": "extract", "reconciled": "reconcile",
    "filed": "act", "planned": "plan",
}
# Hard minimums: the width at which each thing is still readable. Wider weeks scroll.
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
# The narrowest a chip may be drawn before its text stops being readable.
ISSUE_FLOOR = 240 + GAP
CHIP_FLOOR = 190 + GAP
MIN_COLUMN = CHECK_SLOT
LABEL_SLOT = CHIP_SLOT
# A strip stops widening at two of the widest thing it holds; past that it wraps to more rows.
MAX_COLUMN = ISSUE_SLOT * 2
# A day still ahead holds one pill per row and nothing else.
FUTURE_COLUMN = 170
# A day whose whole record is a standup post has nothing to lay out.
QUIET_COLUMN = 110
# A strip inside a working day that holds only posts — dots on a hairline.
POSTS_COLUMN = 64
# What the compact columns may be squeezed to when the week is a little too wide.
FUTURE_FLOOR, QUIET_FLOOR, POSTS_FLOOR = 140, 80, 40
OPEN_STATUSES = ("queued", "blocked", "leased", "deferred")

# Two baselines per lane: primary carries the work, secondary what the agent said about it.
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
    """The project's own timezone, falling back to UTC."""
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
    """One column per day that holds something, in order. Today always gets a column — it is
    where the now line lives."""
    columns: list[dict[str, Any]] = []
    for key in sorted({k for k in keys if k} | {today}):
        columns.append({
            "key": key, "label": day_label(key, today),
            "today": key == today, "future": key > today,
        })
    return columns


def slot_floor(lane: str, row: str) -> int:
    """The narrowest this lane's chip may be squeezed to before the page gives up and scrolls."""
    if row == SECONDARY:
        return SMALL_SLOT
    if lane == "heard":
        return CARD_SLOT
    return ISSUE_FLOOR if lane == "did" else CHIP_FLOOR


def slot_width(lane: str, row: str) -> int:
    """The horizontal room one node in this lane and row needs."""
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

    A finished check sits on the day it finished, whatever day it was booked for; work still
    ahead sits on its due day, and work in flight sits on today."""
    state = str(node.get("state") or "")
    if state in SETTLED:
        return str(node.get("finished_day") or "") or day_key(str(node.get("ts") or ""), tz)
    if state == "leased":
        return today
    return str(node.get("due_day") or "") or day_key(str(node.get("ts") or ""), tz)


def lane_of(node_type: str) -> str:
    """Which row a node lives in. Anything unrecognised goes to DID."""
    return LANE_OF.get(str(node_type), "did")


def place(nodes: list[dict[str, Any]], tz: ZoneInfo, today: str) -> list[dict[str, Any]]:
    """Give every node its day, its lane, and its position within them.

    `seq` is the node's index among its own lane on its own day, in event order."""
    placed: list[dict[str, Any]] = []
    for node in nodes:
        kind = str(node.get("type"))
        key = (check_day(node, today, tz) if kind == "check"
               else day_key(str(node.get("ts") or ""), tz))
        entry = {**node, "lane": lane_of(kind), "row": row_of(kind), "day": key}
        if key > today:
            # The source call stays on the node as `origin` for the "from:" chip and the panel.
            entry["origin"] = str(node.get("group") or "")
            entry["group"] = "day"
        placed.append(entry)

    counters: dict[tuple[str, str, str, str], int] = {}
    for node in sorted(placed, key=lambda n: (str(n["day"]), str(n["ts"]), str(n["id"]))):
        slot = (str(node["day"]), str(node.get("group") or "day"), str(node["lane"]),
                str(node["row"]))
        node["seq"] = counters.get(slot, 0)
        counters[slot] = node["seq"] + 1
    return placed


def sub_columns(nodes: list[dict[str, Any]], days: list[dict[str, Any]]) -> dict[str, Any]:
    """The sub-columns inside each day, and how wide each one has to be.

    One strip per conversation; work no conversation produced goes in a trailing strip."""
    first_seen: dict[tuple[str, str], str] = {}
    needed: dict[tuple[str, str, str, str], int] = {}
    tight: dict[tuple[str, str, str, str], int] = {}
    for node in nodes:
        day = str(node.get("day") or "")
        if not day:
            continue
        group = str(node.get("group") or "day")
        key = (day, group)
        stamp = str(node.get("ts") or "")
        # Strips run left to right in the order the day's conversations started.
        if node.get("type") in ("meeting", "intake") or key not in first_seen:
            first_seen[key] = stamp if node.get("type") in ("meeting", "intake") else (
                min(first_seen.get(key, stamp), stamp)
            )
        lane, row = str(node.get("lane")), str(node.get("row"))
        slot = (day, group, lane, row)
        # One node wide: inside a strip, things stack down rather than out.
        needed[slot] = max(needed.get(slot, 0), slot_width(lane, row))
        tight[slot] = max(tight.get(slot, 0), slot_floor(lane, row))

    out: dict[str, Any] = {}
    for column in days:
        day = str(column["key"])
        if column.get("future"):
            # One strip: the pills stack down, whoever scheduled them.
            out[day] = [{"group": "day", "width": FUTURE_COLUMN, "floor": FUTURE_FLOOR}]
            continue
        here = [(g, first_seen[(d, g)]) for (d, g) in first_seen if d == day]
        # "day" trails the conversations whatever time its contents carry.
        here.sort(key=lambda pair: (pair[0] == "day", pair[1], pair[0]))
        strips = []
        for group, _ in here:
            # A strip that holds nothing but Slack dots is a hairline, not a column.
            if not any(
                d == day and g == group and row == PRIMARY
                for (d, g, _lane, row) in needed
            ):
                strips.append({"group": group, "width": POSTS_COLUMN, "floor": POSTS_FLOOR})
                continue
            widest = max(
                (v for (d, g, _lane, _row), v in needed.items() if d == day and g == group),
                default=MIN_COLUMN,
            )
            # The floor is whatever the widest thing in this strip actually needs.
            tightest = max(
                (v for (d, g, _lane, _row), v in tight.items() if d == day and g == group),
                default=MIN_COLUMN,
            )
            width = min(MAX_COLUMN, max(MIN_COLUMN, widest))
            strips.append({"group": group, "width": width,
                           "floor": min(width, max(MIN_COLUMN, tightest))})
        out[day] = strips
    return out


FUTURE_STRETCH = 1.3
"""A scheduled day may take a little more room when there is spare, but not a working day's
worth."""


SQUEEZE_LIMIT = 1.2
"""How much over the viewport a week may be and still be squeezed into it."""


def spread(columns: list[dict[str, Any]], room: int) -> list[int]:
    """Widths for one row of day columns, given what each needs and the room available.

    When the timeline fits, spare width goes to the days that hold work; when it does not,
    every column keeps its minimum and the caller scrolls. Each column is
    {"width": int, "future": bool, "primary": bool}."""
    mins = [max(0, int(c.get("width") or 0)) for c in columns]
    total = sum(mins)
    if not columns:
        return mins
    if total > room:
        # A little too wide is not a reason to scroll: squeeze toward the floors first.
        floors = [max(0, int(c.get("floor") or mins[i])) for i, c in enumerate(columns)]
        if total > room * SQUEEZE_LIMIT or sum(floors) > room:
            return mins
        give = total - room
        slack = total - sum(floors)
        squeezed = [
            m - int(give * ((m - f) / slack)) if slack else m
            for m, f in zip(mins, floors, strict=True)
        ]
        # Rounding leaves a pixel or two; take them off whichever column still has slack.
        over = sum(squeezed) - room
        for i in sorted(range(len(squeezed)), key=lambda i: floors[i] - squeezed[i]):
            if over <= 0:
                break
            take = min(over, squeezed[i] - floors[i])
            squeezed[i] -= take
            over -= take
        return squeezed
    if total == room:
        return mins

    caps = [
        int(m * FUTURE_STRETCH) if c.get("future") else (m if not c.get("primary") else room)
        for m, c in zip(mins, columns, strict=True)
    ]
    widths = list(mins)
    # Settle rather than solve: a capped column hands its spare back to the ones still growing.
    for _ in range(4):
        spare = room - sum(widths)
        if spare <= 0:
            break
        growable = [i for i in range(len(widths)) if widths[i] < caps[i]]
        if not growable:
            break
        weight = sum(mins[i] for i in growable) or len(growable)
        for i in growable:
            share = spare * (mins[i] or 1) / weight
            widths[i] = min(caps[i], widths[i] + int(share))
    # Whatever rounding left over goes to the widest column that will take it.
    left = room - sum(widths)
    if left > 0:
        takers = [i for i in range(len(widths)) if widths[i] < caps[i]]
        if takers:
            widths[max(takers, key=lambda i: widths[i])] += left
    return widths


# --- the width algorithm ---------------------------------------------------------------------
#
# One function decides the whole horizontal layout; `data-layout` on <body> reports which
# branch was taken so the result can be checked without a screenshot.

SHRUNK = {"issue": 240, "card": 200, "decision": 200, "check": 200}
SHRUNK_FUTURE = 150
SHRUNK_COLLAPSED = 96
SPARE_CAP = 1.5
"""A column may take half again its minimum from the spare, and no more."""
TODAY_AT = 0.45
"""Where today sits when the week has to scroll — recent history left, futures right."""


def layout_columns(
    nodes: list[dict[str, Any]], days: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Everything plan_widths needs about each day, computed once on the server."""
    strips = sub_columns(nodes, days)
    widths = column_widths(nodes, days)
    primary = {str(n.get("day")) for n in nodes if str(n.get("row")) == PRIMARY}
    counts: dict[str, int] = {}
    for node in nodes:
        if str(node.get("row")) == PRIMARY:
            counts[str(node.get("day"))] = counts.get(str(node.get("day")), 0) + 1

    out: list[dict[str, Any]] = []
    for column in days:
        key = str(column["key"])
        here = strips.get(key) or []
        collapsed = key not in primary and not column.get("future")
        shrunk = (
            SHRUNK_COLLAPSED if collapsed else
            SHRUNK_FUTURE if column.get("future") else
            max(FUTURE_COLUMN, sum(int(x["floor"]) for x in here)) if here else widths[key]
        )
        out.append({
            "key": key, "min": widths[key], "shrunk": min(widths[key], shrunk),
            "future": bool(column.get("future")), "collapsed": collapsed,
            "today": bool(column.get("today")), "primary": counts.get(key, 0),
            "strips": [int(x["width"]) for x in here] or [widths[key]],
        })
    return out


def plan_widths(
    columns: list[dict[str, Any]], viewport: int, gutter: int = 0
) -> dict[str, Any]:
    """Every column's width, which branch decided it, and where the view opens.

    Three outcomes, in order of preference: **fit** (minimums, spare to past days holding
    work), **shrink** (chips drop to their floors), **scroll** (minimums, view opens on a
    sub-column boundary). Each column is
    {"min", "shrunk", "future", "collapsed", "today", "primary", "strips"}."""
    mins = [max(0, int(c.get("min") or 0)) for c in columns]
    total = gutter + sum(mins)
    if not columns:
        return {"mode": "fit", "widths": [], "scroll_left": 0, "total": gutter}

    if total <= viewport:
        return _fit(columns, mins, viewport, gutter, "fit")

    tight = [max(0, int(c.get("shrunk") or c.get("min") or 0)) for c in columns]
    if total <= viewport * SQUEEZE_LIMIT and gutter + sum(tight) <= viewport:
        # Shrinking is for getting on screen, not for filling it: no spare is handed out.
        return {"mode": "shrink", "widths": tight, "scroll_left": 0,
                "total": gutter + sum(tight)}

    return {"mode": "scroll", "widths": mins, "total": total,
            "scroll_left": _opening(columns, mins, viewport, gutter)}


def _fit(
    columns: list[dict[str, Any]], mins: list[int], viewport: int, gutter: int, mode: str
) -> dict[str, Any]:
    widths = list(mins)
    spare = viewport - gutter - sum(mins)
    # Only a past day holding real work grows.
    growable = [
        i for i, c in enumerate(columns)
        if not c.get("future") and not c.get("collapsed") and int(c.get("primary") or 0) > 0
    ]
    weight = sum(int(columns[i].get("primary") or 0) for i in growable)
    if spare > 0 and weight:
        for i in growable:
            share = spare * (int(columns[i].get("primary") or 0) / weight)
            widths[i] = min(int(mins[i] * SPARE_CAP), mins[i] + int(share))
    return {"mode": mode, "widths": widths, "scroll_left": 0, "total": gutter + sum(widths)}


def _opening(
    columns: list[dict[str, Any]], mins: list[int], viewport: int, gutter: int
) -> int:
    """Where a scrolling week opens: the last sub-column boundary that leaves today around the
    middle, so the days that explain today are on its left."""
    edges, at = [0], gutter
    today_left = 0
    for column, width in zip(columns, mins, strict=True):
        if column.get("today"):
            today_left = at
        strips = [int(w) for w in (column.get("strips") or []) if int(w) > 0] or [width]
        span = at
        for strip in strips:
            edges.append(max(0, span - gutter))
            span += strip
        at += width
    want = today_left - int(viewport * TODAY_AT)
    limit = max(0, gutter + sum(mins) - viewport)
    reachable = [e for e in sorted(set(edges)) if e <= min(want, limit)]
    return reachable[-1] if reachable else 0


# What share of a tall screen each lane gets when there is height to spare.
LANE_SHARE = {
    "heard": 0.18, "understood": 0.17, "did": 0.30, "watching": 0.22, "learned": 0.13,
}


def lane_heights(nodes: list[dict[str, Any]]) -> dict[str, int]:
    """How tall each lane needs to be for what is actually in it. An empty lane collapses to
    a label."""
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
    floors: dict[str, int] = {}
    for column in days:
        key = str(column["key"])
        here = strips.get(key) or []
        floors[key] = max(FUTURE_COLUMN, sum(int(x["floor"]) for x in here)) if here else (
            FUTURE_COLUMN)
        if key not in has_primary:
            # Nothing to lay out but dots. Today keeps enough room to be a place you look at.
            widths[key] = FUTURE_COLUMN if column.get("today") else QUIET_COLUMN
            floors[key] = widths[key]
            continue
        if column.get("future"):
            # A scheduled day is one column of pills, stacked.
            widths[key] = FUTURE_COLUMN
            floors[key] = widths[key]
            continue
        # A working day is as wide as its conversations laid side by side.
        widths[key] = max(FUTURE_COLUMN, sum(s["width"] for s in here))
    return widths


def column_floors(nodes: list[dict[str, Any]], days: list[dict[str, Any]]) -> dict[str, int]:
    """The narrowest each day may be squeezed to before the page scrolls instead."""
    strips = sub_columns(nodes, days)
    has_primary = {str(n.get("day")) for n in nodes if str(n.get("row")) == PRIMARY}
    out: dict[str, int] = {}
    for column in days:
        key = str(column["key"])
        here = strips.get(key) or []
        if column.get("future"):
            out[key] = FUTURE_FLOOR
            continue
        if key not in has_primary:
            out[key] = FUTURE_FLOOR if column.get("today") else QUIET_FLOOR
            continue
        out[key] = max(FUTURE_COLUMN, sum(int(x["floor"]) for x in here))
    return out


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

    Older calls fall back to the transcript length; with neither, the segment carries no note."""
    triage = result.get("triage") or {}
    kept, total = triage.get("kept"), triage.get("total")
    if isinstance(kept, int) and isinstance(total, int) and total:
        return f"{kept} / {total} lines kept" if kept < total else f"{total} lines"
    return f"{lines} lines" if lines else ""


def _filed_note(runs: list[dict[str, Any]]) -> str:
    """What the act stage actually changed, created and updated counted separately."""
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

    Takes every run of the stage, not just one."""
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
        # How many lines that sounded like a commitment became items.
        recall = next((r.get("recall") for r in runs if r.get("recall")), None)
        tail = ""
        if recall and recall.get("cues"):
            tail = f" \u00b7 recall {recall.get('covered_final', 0)}/{recall['cues']} cues"
        return ", ".join(parts) + tail
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

    A stage with no task shows as skipped; a stage that ran more than once counts all its runs."""
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
    """The people strip."""
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

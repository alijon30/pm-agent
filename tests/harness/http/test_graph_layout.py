"""Where things sit on the graph is a claim about the agent's week, so it is tested like one.

None of this needs a browser: the page positions what these functions decide, and if the
decision is wrong the picture is wrong in a way no screenshot review would reliably catch."""

from typing import Any
from zoneinfo import ZoneInfo

from app.harness.http.graph_layout import (
    CARD_SLOT,
    CHIP_SLOT,
    FUTURE_COLUMN,
    ISSUE_SLOT,
    LANE_EMPTY,
    LANE_MIN,
    LANES,
    MAX_COLUMN,
    MIN_COLUMN,
    QUIET_COLUMN,
    SMALL_SLOT,
    build_days,
    check_state,
    column_widths,
    day_key,
    day_label,
    lane_heights,
    lane_of,
    place,
    roster_view,
    row_of,
    short_day,
    slot_width,
    stage_strip,
    sub_columns,
    zone,
)

LA = ZoneInfo("America/Los_Angeles")
TODAY = "2026-08-30"


def node(node_id: str, kind: str, ts: str, **extra: Any) -> dict[str, Any]:
    return {"id": node_id, "type": kind, "ts": ts, "label": node_id, **extra}


# --- days ---------------------------------------------------------------------------------------

def test_a_day_is_the_teams_midnight_not_the_servers() -> None:
    """08:30 UTC on the 29th is still the evening of the 28th in California. A reviewer checks
    these columns against their own memory of the week."""
    assert day_key("2026-08-29T03:30:00+00:00", LA) == "2026-08-28"
    assert day_key("2026-08-29T18:00:00+00:00", LA) == "2026-08-29"


def test_an_unreadable_timestamp_gets_no_day_rather_than_a_guessed_one() -> None:
    assert day_key("", LA) == ""
    assert day_key("not a date", LA) == ""


def test_a_project_with_a_broken_timezone_still_renders() -> None:
    assert zone({"timezone": "Mars/Olympus"}) == ZoneInfo("UTC")
    assert zone({}) == ZoneInfo("UTC")
    assert zone({"timezone": "America/Los_Angeles"}) == LA


def test_today_is_called_today_and_everything_else_is_dated() -> None:
    assert day_label(TODAY, TODAY) == "Today"
    assert day_label("2026-08-27", TODAY) == "Thu Aug 27"


def test_only_days_that_hold_something_get_a_column() -> None:
    """A week of empty columns says the agent was idle when it simply was not working the
    weekend, and the horizontal room is worth more than the calendar."""
    days = build_days(["2026-08-27", "2026-08-27", "2026-09-03", TODAY, ""], TODAY)

    assert [d["key"] for d in days] == ["2026-08-27", TODAY, "2026-09-03"]
    assert [d["label"] for d in days] == ["Thu Aug 27", "Today", "Thu Sep 3"]
    assert [d["future"] for d in days] == [False, False, True]
    assert [d["today"] for d in days] == [False, True, False]


# --- lanes --------------------------------------------------------------------------------------

def test_today_always_gets_a_column_even_on_a_quiet_morning() -> None:
    """It is where the now line lives. A reader looking for what is happening right now must
    never fail to find the place it would be."""
    days = build_days(["2026-08-27"], TODAY)

    assert [d["key"] for d in days] == ["2026-08-27", TODAY]
    assert days[-1]["today"] is True


def test_each_kind_of_work_has_its_own_row() -> None:
    assert lane_of("meeting") == "heard"
    assert lane_of("intake") == "heard"
    assert lane_of("decision") == "understood"
    assert lane_of("conflict") == "understood"
    assert lane_of("issue") == "did"
    assert lane_of("post") == "did"
    assert lane_of("check") == "watching"
    assert lane_of("lesson") == "learned"
    assert set(LANES) == {lane_of(k) for k in
                          ("meeting", "decision", "issue", "check", "lesson")}


def test_an_unknown_kind_is_still_drawn_somewhere() -> None:
    """A node with no lane would not be drawn at all, which is the one outcome worse than
    being in the wrong row."""
    assert lane_of("something_new") == "did"


# --- placement ----------------------------------------------------------------------------------

def test_a_burst_of_work_fans_out_instead_of_stacking() -> None:
    nodes = [
        node("i1", "issue", "2026-08-30T17:00:00+00:00"),
        node("i2", "issue", "2026-08-30T17:00:01+00:00"),
        node("i3", "issue", "2026-08-30T17:00:02+00:00"),
    ]

    placed = place(nodes, LA, TODAY)

    assert [n["seq"] for n in placed] == [0, 1, 2]
    assert {n["day"] for n in placed} == {TODAY}


def test_seq_counts_within_a_lane_not_across_the_column() -> None:
    placed = place([
        node("m1", "meeting", "2026-08-30T17:00:00+00:00"),
        node("i1", "issue", "2026-08-30T17:00:01+00:00"),
        node("i2", "issue", "2026-08-30T17:00:02+00:00"),
    ], LA, TODAY)
    seq = {n["id"]: n["seq"] for n in placed}

    assert seq == {"m1": 0, "i1": 0, "i2": 1}


def test_the_order_is_stable_when_two_things_share_a_timestamp() -> None:
    same = "2026-08-30T17:00:00+00:00"
    first = place([node("b", "issue", same), node("a", "issue", same)], LA, TODAY)
    again = place([node("a", "issue", same), node("b", "issue", same)], LA, TODAY)

    assert {n["id"]: n["seq"] for n in first} == {n["id"]: n["seq"] for n in again}


def test_a_scheduled_check_sits_in_the_column_of_the_day_it_will_run() -> None:
    """That column is the question the check exists to answer. Placing it on the day it was
    written down would pile every future check onto today."""
    placed = place([node("t1", "check", "2026-08-30T17:00:00+00:00",
                         due_day="2026-09-03")], LA, TODAY)

    assert placed[0]["day"] == "2026-09-03"


def test_a_check_that_has_already_run_stays_on_the_day_it_ran() -> None:
    placed = place([node("t1", "check", "2026-08-28T17:00:00+00:00",
                         due_day="2026-08-28")], LA, TODAY)

    assert placed[0]["day"] == "2026-08-28"


def test_a_column_is_wide_enough_for_its_busiest_lane() -> None:
    nodes = place([
        node("i1", "issue", "2026-08-30T17:00:00+00:00"),
        node("i2", "issue", "2026-08-30T17:00:01+00:00"),
        node("i3", "issue", "2026-08-30T17:00:02+00:00"),
        node("m1", "meeting", "2026-08-30T17:00:00+00:00"),
    ], LA, TODAY)
    days = build_days([n["day"] for n in nodes], TODAY)

    widths = column_widths(nodes, days)

    assert widths[TODAY] >= MIN_COLUMN
    assert widths[TODAY] > MIN_COLUMN, "three issues in one lane need more than the minimum"


def test_a_quiet_day_still_gets_a_readable_column() -> None:
    """A day that heard a call is wide enough for the card; a day that only holds a scheduled
    check is not, which is what keeps a week of follow-ups on the screen."""
    heard = place([node("m1", "meeting", "2026-08-30T17:00:00+00:00")], LA, TODAY)
    quiet = place([node("t1", "check", "2026-08-30T17:00:00+00:00", state="queued",
                        due_day=TODAY)], LA, TODAY)

    assert column_widths(heard, build_days([TODAY], TODAY))[TODAY] == CARD_SLOT
    assert column_widths(quiet, build_days([TODAY], TODAY))[TODAY] == MIN_COLUMN


# --- what a check is doing ------------------------------------------------------------------------

def test_a_check_reports_the_state_its_glyph_is_drawn_from() -> None:
    assert check_state({"status": "done", "result": {"met": True}}) == "met"
    assert check_state({"status": "done", "result": {"met": True, "early": True}}) == "early"
    assert check_state({"status": "done", "result": {"met": False}}) == "unmet"
    assert check_state({"status": "leased"}) == "leased"
    assert check_state({"status": "blocked"}) == "blocked"
    assert check_state({"status": "failed"}) == "failed"
    assert check_state({"status": "queued"}) == "queued"


# --- the stage strip under a call -----------------------------------------------------------------

def test_the_strip_shows_every_stage_a_call_goes_through() -> None:
    assert [s["name"] for s in stage_strip([])] == [
        "read", "triaged", "reconciled", "filed", "planned"]


def test_a_stage_that_never_ran_says_so_rather_than_being_left_off() -> None:
    """No plan task exists when nothing needed watching. That is a real state, and a strip that
    quietly drops its empty segments cannot be read as a progress bar."""
    strip = {s["name"]: s for s in stage_strip([
        {"kind": "extract", "status": "done", "result": {}},
        {"kind": "reconcile", "status": "done", "result": {"items": [{}]}},
    ])}

    assert strip["read"]["state"] == "done"
    assert strip["filed"]["state"] == "skipped"
    assert strip["planned"]["state"] == "skipped"


def test_a_stage_in_flight_is_distinguishable_from_one_that_is_waiting() -> None:
    strip = {s["name"]: s for s in stage_strip([
        {"kind": "extract", "status": "done", "result": {}},
        {"kind": "reconcile", "status": "leased"},
        {"kind": "act", "status": "queued"},
        {"kind": "plan", "status": "failed"},
    ])}

    assert strip["reconciled"]["state"] == "leased"
    assert strip["filed"]["state"] == "queued"
    assert strip["planned"]["state"] == "failed"
    assert strip["planned"]["note"] == "", "an unfinished stage has produced nothing to report"


def test_the_triage_segment_says_how_much_of_the_call_the_model_saw() -> None:
    strip = {s["name"]: s for s in stage_strip([
        {"kind": "extract", "status": "done", "result": {"triage": {"kept": 14, "total": 22}}}])}

    assert strip["triaged"]["note"] == "14 / 22 lines kept"


def test_triage_that_kept_everything_does_not_dress_it_up_as_a_ratio() -> None:
    strip = {s["name"]: s for s in stage_strip([
        {"kind": "extract", "status": "done", "result": {"triage": {"kept": 22, "total": 22}}}])}

    assert strip["triaged"]["note"] == "22 lines"


def test_a_call_recorded_before_triage_counts_existed_says_nothing_rather_than_guessing() -> None:
    strip = {s["name"]: s for s in stage_strip([
        {"kind": "extract", "status": "done", "result": {"action_items": [{}]}}])}

    assert strip["triaged"]["note"] == ""


def test_a_stage_that_finished_with_nothing_says_so() -> None:
    """The honest empty is the whole point: "filed" with no note reads as a stage that has not
    reported, and "filed — nothing new" reads as a decision."""
    strip = {s["name"]: s for s in stage_strip([
        {"kind": "extract", "status": "done", "result": {}},
        {"kind": "reconcile", "status": "done", "result": {"items": []}},
        {"kind": "act", "status": "done", "result": {"created": [], "updated": []}},
        {"kind": "plan", "status": "done", "result": {"accepted": []}},
    ])}

    assert strip["read"]["note"] == "nothing to act on"
    assert strip["reconciled"]["note"] == "nothing survived checking"
    assert strip["filed"]["note"] == "nothing new"
    assert strip["planned"]["note"] == "nothing to watch"


def test_a_stage_that_did_something_counts_it() -> None:
    strip = {s["name"]: s for s in stage_strip([
        {"kind": "extract", "status": "done",
         "result": {"action_items": [{}, {}, {}], "decision_ids": ["d1"]}},
        {"kind": "act", "status": "done",
         "result": {"created": [{}, {}], "updated": [{}]}},
        {"kind": "plan", "status": "done", "result": {"accepted": ["k1", "k2"]}},
    ])}

    assert strip["read"]["note"] == "3 action items, 1 decision"
    assert strip["filed"]["note"] == "filed 2 · updated 1"
    assert strip["planned"]["note"] == "2 checks"


# --- the roster strip -----------------------------------------------------------------------------

def test_the_roster_carries_what_a_badge_and_a_panel_need() -> None:
    view = roster_view(
        [{"name": "Nodir Rahimov", "role": "backend"}, {"name": "Priya Nair", "role": "eng"}],
        {"Nodir Rahimov": ["issue:INV-27", "issue:INV-26"]},
        {"Nodir Rahimov": 2},
    )

    assert view[0] == {"name": "Nodir Rahimov", "first_name": "Nodir", "role": "backend",
                       "owns": ["issue:INV-26", "issue:INV-27"], "pings": 2}
    assert view[1]["owns"] == [] and view[1]["pings"] == 0


def test_a_roster_entry_with_no_name_is_not_a_person() -> None:
    assert roster_view([{"role": "eng"}], {}, {}) == []


# --- two baselines per lane -----------------------------------------------------------------------

def test_what_the_agent_said_does_not_share_a_row_with_what_it_changed() -> None:
    """Twelve Slack posts sitting in the same row as twelve issues made both unreadable."""
    assert row_of("issue") == "primary"
    assert row_of("decision") == "primary"
    assert row_of("check") == "primary"
    assert row_of("post") == "secondary"
    assert row_of("conflict") == "secondary"


def test_seq_counts_within_a_row_so_the_two_baselines_do_not_interleave() -> None:
    placed = place([
        node("i1", "issue", "2026-08-30T17:00:00+00:00"),
        node("p1", "post", "2026-08-30T17:00:01+00:00"),
        node("i2", "issue", "2026-08-30T17:00:02+00:00"),
        node("p2", "post", "2026-08-30T17:00:03+00:00"),
    ], LA, TODAY)
    seq = {n["id"]: (n["row"], n["seq"]) for n in placed}

    assert seq == {"i1": ("primary", 0), "p1": ("secondary", 0),
                   "i2": ("primary", 1), "p2": ("secondary", 1)}


# --- a lane is as tall as what is in it --------------------------------------------------------------

def test_an_empty_lane_collapses_to_its_label() -> None:
    """The lesson the agent has not drawn yet should not take a quarter of the screen from the
    lanes doing the work."""
    heights = lane_heights(place([node("i1", "issue", "2026-08-30T17:00:00+00:00")], LA, TODAY))

    assert heights["learned"] == LANE_EMPTY
    assert heights["understood"] == LANE_EMPTY
    assert heights["did"] >= LANE_MIN


def test_a_lane_using_both_baselines_is_taller_than_one_using_a_single_row() -> None:
    one = lane_heights(place([node("i1", "issue", "2026-08-30T17:00:00+00:00")], LA, TODAY))
    two = lane_heights(place([
        node("i1", "issue", "2026-08-30T17:00:00+00:00"),
        node("p1", "post", "2026-08-30T17:00:01+00:00"),
    ], LA, TODAY))

    assert two["did"] > one["did"]


def test_every_lane_gets_a_height_even_with_nothing_on_the_graph() -> None:
    heights = lane_heights([])

    assert set(heights) == set(LANES)
    assert all(h == LANE_EMPTY for h in heights.values())


# --- a column can only get so wide ---------------------------------------------------------------

def test_one_very_busy_lane_cannot_push_every_other_day_off_the_screen() -> None:
    """Twenty issues in a day used to make a column wider than the viewport, and the days that
    explained it ended up scrolled away. Past the bound the answer is another row, not width."""
    busy = place([node(f"i{n}", "issue", f"2026-08-30T17:00:{n:02d}+00:00") for n in range(20)],
                 LA, TODAY)

    width = column_widths(busy, build_days([TODAY], TODAY))[TODAY]

    assert width == MAX_COLUMN, "one conversation's strip stops widening at the bound"
    assert width // ISSUE_SLOT == 2, "twenty issues wrap into rows two wide, not one wide strip"


def test_a_column_is_wide_enough_for_the_calls_it_has_to_hold() -> None:
    """Three calls in a day used to stack on top of each other, because a card was being
    measured at a mark's slot. A card is counted at the width it is actually drawn."""
    calls = place([node(f"m{n}", "meeting", f"2026-08-30T1{n}:00:00+00:00") for n in range(2)],
                  LA, TODAY)

    width = column_widths(calls, build_days([TODAY], TODAY))[TODAY]

    assert width >= 2 * CARD_SLOT or width == MAX_COLUMN
    one = place([node("m1", "meeting", "2026-08-30T10:00:00+00:00")], LA, TODAY)
    assert column_widths(one, build_days([TODAY], TODAY))[TODAY] >= CARD_SLOT, (
        "one card always fits without being cut"
    )


def test_a_labelled_mark_is_counted_at_the_width_its_title_wraps_to() -> None:
    marks = place([node(f"d{n}", "decision", f"2026-08-30T1{n}:00:00+00:00") for n in range(2)],
                  LA, TODAY)

    assert column_widths(marks, build_days([TODAY], TODAY))[TODAY] == 2 * CHIP_SLOT


def test_a_row_of_dots_does_not_demand_a_labels_worth_of_room_each() -> None:
    """A secondary mark carries no standing label, so twelve of them are not twelve labels."""
    posts = place([node(f"p{n}", "post", f"2026-08-30T1{n}:00:00+00:00") for n in range(4)],
                  LA, TODAY)
    labelled = place([node(f"d{n}", "decision", f"2026-08-30T1{n}:00:00+00:00")
                      for n in range(4)], LA, TODAY)
    days = build_days([TODAY], TODAY)

    assert column_widths(posts, days)[TODAY] < column_widths(labelled, days)[TODAY]


# --- a finished check sits where it finished --------------------------------------------------------

def test_a_check_that_resolved_early_is_drawn_on_the_day_it_resolved() -> None:
    """Drawing a resolved tick in a future column says the agent has already done something it
    has not done yet, which is the one thing a timeline must never claim."""
    placed = place([node("t1", "check", "2026-08-27T17:00:00+00:00", state="early",
                         due_day="2026-08-31", finished_day="2026-08-28")], LA, TODAY)

    assert placed[0]["day"] == "2026-08-28"


def test_a_check_that_came_back_unmet_or_failed_also_sits_in_the_past() -> None:
    for state in ("met", "unmet", "failed"):
        placed = place([node("t1", "check", "2026-08-27T00:00:00+00:00", state=state,
                             due_day="2026-09-03", finished_day="2026-08-29")], LA, TODAY)
        assert placed[0]["day"] == "2026-08-29", state


def test_work_still_ahead_sits_on_the_day_it_is_due() -> None:
    for state in ("queued", "blocked"):
        placed = place([node("t1", "check", "2026-08-27T00:00:00+00:00", state=state,
                             due_day="2026-09-03", finished_day="")], LA, TODAY)
        assert placed[0]["day"] == "2026-09-03", state


def test_a_check_running_this_second_sits_on_today_beside_the_now_line() -> None:
    placed = place([node("t1", "check", "2026-08-27T00:00:00+00:00", state="leased",
                         due_day="2026-09-03", finished_day="")], LA, TODAY)

    assert placed[0]["day"] == TODAY


def test_a_day_can_be_said_the_way_somebody_says_it_mid_sentence() -> None:
    assert short_day("2026-08-31") == "Aug 31"


# --- the triage note falls back rather than going blank ------------------------------------------------

def test_a_call_from_before_the_counts_existed_says_how_long_it_was() -> None:
    """Every production call predates the triage counter. A blank segment reads as a stage
    that did nothing; the transcript length is smaller but true."""
    strip = {s["name"]: s for s in stage_strip(
        [{"kind": "extract", "status": "done", "result": {}}], lines=61)}

    assert strip["triaged"]["note"] == "61 lines"


def test_the_real_count_still_wins_when_there_is_one() -> None:
    strip = {s["name"]: s for s in stage_strip(
        [{"kind": "extract", "status": "done",
          "result": {"triage": {"kept": 14, "total": 22}}}], lines=61)}

    assert strip["triaged"]["note"] == "14 / 22 lines kept"


def test_a_call_is_measured_at_the_width_a_card_is_actually_drawn() -> None:
    """The three-calls-in-a-column bug was this one number: a card was being counted at a
    mark's slot, so the column was a third of the width the cards needed."""
    assert slot_width("heard", "primary") == CARD_SLOT
    assert slot_width("did", "primary") == ISSUE_SLOT
    assert slot_width("understood", "primary") == CHIP_SLOT
    assert slot_width("did", "secondary") == SMALL_SLOT


# --- what a call's stages really did ----------------------------------------------------------------

def test_updating_an_existing_ticket_is_not_nothing_new() -> None:
    """A call that re-raised work already tracked and got a comment on the existing ticket is
    the duplicate-discipline story. Reporting it as "nothing new" hides the best thing the
    agent did that day."""
    strip = {s["name"]: s for s in stage_strip([
        {"kind": "act", "status": "done",
         "result": {"created": [], "updated": [{"identifier": "INV-25"}]}}])}

    assert strip["filed"]["note"] == "updated 1"


def test_filing_and_updating_are_counted_apart() -> None:
    strip = {s["name"]: s for s in stage_strip([
        {"kind": "act", "status": "done",
         "result": {"created": [{}, {}], "updated": [{}]}}])}

    assert strip["filed"]["note"] == "filed 2 · updated 1"


def test_nothing_new_is_said_only_when_nothing_happened() -> None:
    strip = {s["name"]: s for s in stage_strip([
        {"kind": "act", "status": "done", "result": {"created": [], "updated": []}}])}

    assert strip["filed"]["note"] == "nothing new"


def test_a_stage_that_ran_twice_for_one_call_counts_both_runs() -> None:
    """This is what hid "updated INV-25": two act tasks share the call's root event, and
    keeping only the last one reported the empty run as the whole story."""
    strip = {s["name"]: s for s in stage_strip([
        {"kind": "act", "status": "done",
         "result": {"created": [{"identifier": "INV-26"}],
                    "updated": [{"identifier": "INV-25"}]}},
        {"kind": "act", "status": "done", "result": {"created": [], "updated": []}},
    ])}

    assert strip["filed"]["note"] == "filed 1 · updated 1"


def test_a_stage_that_finished_on_any_run_reads_as_finished() -> None:
    strip = {s["name"]: s for s in stage_strip([
        {"kind": "act", "status": "failed"},
        {"kind": "act", "status": "done", "result": {"created": [{}], "updated": []}},
    ])}

    assert strip["filed"]["state"] == "done"
    assert strip["filed"]["note"] == "filed 1"


def test_a_day_still_ahead_stays_narrow_but_never_narrower_than_its_pill() -> None:
    """Scheduled work is the point of the view, so those columns stay compact — but a 200px
    check drawn in a 150px column overlaps the next day, and readability wins."""
    future = place([node("t1", "check", "2026-08-30T00:00:00+00:00", state="queued",
                         due_day="2026-09-03")], LA, TODAY)
    days = build_days([n["day"] for n in future], TODAY)

    assert column_widths(future, days)["2026-09-03"] == FUTURE_COLUMN
    assert FUTURE_COLUMN < CARD_SLOT, "much narrower than a day that heard something"


# --- one strip per conversation ---------------------------------------------------------------------

def test_a_day_is_one_strip_per_conversation_not_one_grid() -> None:
    """Reading down a strip is that call's story. Without this, three calls and eight issues
    are an undifferentiated grid and nothing says which call produced which ticket."""
    nodes = place([
        node("meeting:a", "meeting", "2026-08-30T09:00:00+00:00", group="meeting:a"),
        node("meeting:b", "meeting", "2026-08-30T14:00:00+00:00", group="meeting:b"),
        node("issue:1", "issue", "2026-08-30T09:30:00+00:00", group="meeting:a"),
        node("issue:2", "issue", "2026-08-30T14:30:00+00:00", group="meeting:b"),
    ], LA, TODAY)

    strips = sub_columns(nodes, build_days([TODAY], TODAY))[TODAY]

    assert [s["group"] for s in strips] == ["meeting:a", "meeting:b"], "in the order they ran"


def test_work_no_conversation_produced_gets_its_own_trailing_strip() -> None:
    """A standup and a lesson are the agent's own initiative. Filing them under a call would
    be a lie told by alignment."""
    nodes = place([
        node("meeting:a", "meeting", "2026-08-30T14:00:00+00:00", group="meeting:a"),
        node("post:s", "post", "2026-08-30T09:00:00+00:00", group="day"),
    ], LA, TODAY)

    strips = sub_columns(nodes, build_days([TODAY], TODAY))[TODAY]

    assert [s["group"] for s in strips] == ["meeting:a", "day"], "the day strip trails"


def test_a_strip_is_as_wide_as_its_widest_row() -> None:
    nodes = place([
        node("meeting:a", "meeting", "2026-08-30T09:00:00+00:00", group="meeting:a"),
        node("issue:1", "issue", "2026-08-30T09:30:00+00:00", group="meeting:a"),
        node("issue:2", "issue", "2026-08-30T09:31:00+00:00", group="meeting:a"),
    ], LA, TODAY)

    strips = sub_columns(nodes, build_days([TODAY], TODAY))[TODAY]

    assert strips[0]["width"] == 2 * ISSUE_SLOT


def test_a_day_is_as_wide_as_its_strips_together() -> None:
    nodes = place([
        node("meeting:a", "meeting", "2026-08-30T09:00:00+00:00", group="meeting:a"),
        node("meeting:b", "meeting", "2026-08-30T14:00:00+00:00", group="meeting:b"),
    ], LA, TODAY)
    days = build_days([TODAY], TODAY)

    strips = sub_columns(nodes, days)[TODAY]

    assert column_widths(nodes, days)[TODAY] == sum(s["width"] for s in strips)


def test_seq_restarts_inside_each_strip() -> None:
    """Two calls that each filed one issue both put it first in their own strip."""
    nodes = place([
        node("issue:1", "issue", "2026-08-30T09:30:00+00:00", group="meeting:a"),
        node("issue:2", "issue", "2026-08-30T14:30:00+00:00", group="meeting:b"),
    ], LA, TODAY)

    assert [n["seq"] for n in nodes] == [0, 0]


def test_four_scheduled_days_cost_a_fifth_of_the_screen_not_half() -> None:
    """A column of pills is sized by how many conversations put work there, not by what a
    working day needs."""
    ahead = place([node(f"t{n}", "check", "2026-08-30T00:00:00+00:00", state="queued",
                        due_day="2026-09-03", group=f"meeting:{n}") for n in range(2)],
                  LA, TODAY)
    days = build_days([n["day"] for n in ahead], TODAY)

    assert column_widths(ahead, days)["2026-09-03"] == 2 * FUTURE_COLUMN
    assert 4 * FUTURE_COLUMN < 800, "four scheduled days stay under half a 1920 screen"


# --- the team's midnight, not the server's ------------------------------------------------------

def test_today_is_the_teams_day_not_the_servers() -> None:
    """At 22:30 in California the UTC date is already tomorrow. Deriving "today" from the
    server clock split the evening into a past column plus an empty Today, and put work due
    tomorrow into it."""
    clock = "2026-08-30T05:30:00+00:00"

    today = day_key(clock, LA)

    assert today == "2026-08-29"
    days = build_days(["2026-08-29", "2026-08-30"], today)
    assert [(d["label"], d["today"], d["future"]) for d in days] == [
        ("Today", True, False), ("Sun Aug 30", False, True)]


def test_work_due_tomorrow_is_not_filed_under_today() -> None:
    placed = place([node("t1", "check", "2026-08-29T20:00:00-07:00", state="queued",
                         due_day="2026-08-30")], LA, "2026-08-29")

    assert placed[0]["day"] == "2026-08-30"


# --- a day with nothing to lay out ---------------------------------------------------------------

def test_a_day_whose_whole_record_is_a_standup_gives_its_room_back() -> None:
    """A working day's width for one post pushes the days that do have content off screen."""
    quiet = place([node("post:s", "post", "2026-08-29T17:00:00+00:00", group="day")],
                  LA, TODAY)
    days = build_days([n["day"] for n in quiet], TODAY)

    assert column_widths(quiet, days)["2026-08-29"] == QUIET_COLUMN


def test_today_stays_a_place_you_can_look_at_even_when_nothing_has_happened() -> None:
    days = build_days([], TODAY)

    assert column_widths([], days)[TODAY] == FUTURE_COLUMN


def test_a_day_with_real_work_is_not_collapsed() -> None:
    busy = place([
        node("meeting:a", "meeting", "2026-08-29T17:00:00+00:00", group="meeting:a"),
        node("post:p", "post", "2026-08-29T18:00:00+00:00", group="meeting:a"),
    ], LA, TODAY)
    days = build_days([n["day"] for n in busy], TODAY)

    assert column_widths(busy, days)["2026-08-29"] >= CARD_SLOT

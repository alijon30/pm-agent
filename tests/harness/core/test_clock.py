from datetime import UTC, datetime

from app.harness.core.clock import human_delta, iso, parse_iso

from tests.fakes.fake_clock import FakeClock


def test_iso_renders_utc_with_second_precision_so_strings_sort_like_times() -> None:
    a = datetime(2026, 8, 27, 9, 0, 0, 123456, tzinfo=UTC)
    b = datetime(2026, 8, 27, 9, 0, 1, tzinfo=UTC)
    assert iso(a) == "2026-08-27T09:00:00+00:00"
    assert iso(a) < iso(b)


def test_parse_iso_round_trips_and_normalises_to_utc() -> None:
    dt = parse_iso("2026-08-27T11:00:00+02:00")
    assert dt == datetime(2026, 8, 27, 9, 0, 0, tzinfo=UTC)
    assert iso(dt) == "2026-08-27T09:00:00+00:00"


def test_fake_clock_advances_deterministically() -> None:
    clock = FakeClock(datetime(2026, 8, 27, 9, 0, tzinfo=UTC))
    clock.advance(minutes=16)
    assert iso(clock.now()) == "2026-08-27T09:16:00+00:00"


# --- how far off something is --------------------------------------------------------------------

NOW = datetime(2026, 8, 28, 16, 0, tzinfo=UTC)


def test_minutes_while_it_is_still_minutes() -> None:
    assert human_delta("2026-08-28T16:12:00+00:00", NOW) == "in 12 min"
    assert human_delta("2026-08-28T16:00:30+00:00", NOW) == "in 1 min"


def test_hours_while_it_is_still_today() -> None:
    assert human_delta("2026-08-28T19:00:00+00:00", NOW) == "in 3 h"
    assert human_delta("2026-08-28T23:30:00+00:00", NOW) == "in 8 h"


def test_the_date_turns_before_the_hours_run_out() -> None:
    """23:00 today and 01:00 tomorrow are two hours apart, but one of them is tomorrow and
    saying so is what a person actually needs."""
    late = datetime(2026, 8, 28, 23, 0, tzinfo=UTC)
    assert human_delta("2026-08-29T01:00:00+00:00", late) == "tomorrow 01:00"
    assert human_delta("2026-08-29T09:00:00+00:00", NOW) == "tomorrow 09:00"


def test_beyond_tomorrow_the_hour_stops_mattering() -> None:
    assert human_delta("2026-09-03T16:00:00+00:00", NOW) == "Thu Sep 3"


def test_something_already_due_says_so() -> None:
    assert human_delta("2026-08-28T16:00:00+00:00", NOW) == "due now"
    assert human_delta("2026-08-27T09:00:00+00:00", NOW) == "due now"


def test_a_date_that_is_not_one_is_left_out_entirely() -> None:
    assert human_delta("", NOW) == "" and human_delta("next Friday", NOW) == ""

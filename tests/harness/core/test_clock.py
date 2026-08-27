from datetime import UTC, datetime

from app.harness.core.clock import iso, parse_iso

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

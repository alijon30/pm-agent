"""CodeSearch runs against the real fixture repo — no fake, because the repo is the fixture."""

from pathlib import Path

from app.harness.connectors.code import CodeSearch

REPO = Path(__file__).parents[3] / "tests" / "fixtures" / "acme-invoicing"


def search() -> CodeSearch:
    return CodeSearch(REPO)


def test_grep_finds_the_reminder_window_in_config_with_path_and_line() -> None:
    hits = search().grep(r"REMINDER_DAYS\s*=")
    assert hits, "expected REMINDER_DAYS in the fixture repo"
    top = hits[0]
    assert top["path"] == "acme/config.py"
    assert top["line"] > 0 and "REMINDER_DAYS" in top["text"]


def test_grep_is_case_insensitive_and_respects_max_hits() -> None:
    assert search().grep("reminder_days")
    assert len(search().grep("reminder", max_hits=2)) <= 2


def test_grep_finds_the_dead_path_the_call_never_mentions() -> None:
    hits = search().grep("legacy_reminder_window")
    assert [h["path"] for h in hits] == ["acme/reminders/scheduler.py"]


def test_an_invalid_regex_returns_no_hits_instead_of_raising() -> None:
    assert search().grep("([unclosed") == []


def test_read_returns_the_requested_line_window() -> None:
    hits = search().grep(r"REMINDER_DAYS\s*=")
    line = hits[0]["line"]
    window = search().read("acme/config.py", line, line)
    assert "REMINDER_DAYS" in window and window.count("\n") == 0


def test_paths_outside_the_repo_are_refused() -> None:
    code = search()
    assert code.read("../../.env", 1, 5) == ""
    assert code.exists("../../pyproject.toml") is False
    assert code.read("acme/nope.py", 1, 5) == ""


def test_exists_checks_the_file_and_the_line_number() -> None:
    code = search()
    assert code.exists("acme/config.py") is True
    assert code.exists("acme/config.py", 1) is True
    assert code.exists("acme/config.py", 9999) is False
    assert code.exists("acme/ghost.py") is False

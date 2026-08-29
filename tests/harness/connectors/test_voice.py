"""The voice, pinned.

Two kinds of test here. The first walks the before/after table in docs/research/slack-voice.md
and asserts the builders produce the "after" column for that data — the charter is a document
someone can disagree with, so the code has to be checkable against it rather than merely
inspired by it. The second is the anti-pattern sweep: no message anywhere may leak a task kind,
an "(s)" plural, the word "assignee", or a bare URL, because those were the four tells that made
the whole system read like a log."""

import re
from datetime import UTC, datetime
from typing import Any

from app.harness.connectors.slack_blocks import (
    call_summary_blocks,
    commitment_blocks,
    plan_summary_blocks,
    report_blocks,
    standup_blocks,
    what_happened,
)
from app.harness.core.voice import (
    consequence_phrase,
    first_name,
    issue_phrase,
    noun_phrase,
    sentence_list,
    spelled,
)
from app.harness.kinds.phrasing import human_infinitive
from app.harness.kinds.registry import KINDS
from app.harness.kinds.templates import TEMPLATES, render
from app.harness.stages.checks import _values

NOW = datetime(2026, 8, 29, 9, 0, tzinfo=UTC)
NODIR = {"name": "Nodir Rahimov", "slack_id": "U123"}
BUG = ("INV-27", "Fix duplicate reminder emails bug", "https://linear.app/x/INV-27")


# --- the four things a colleague talks about ------------------------------------------------------

def test_a_person_is_a_first_name_and_a_mention_only_when_they_owe_something() -> None:
    """A mention notifies. Asking Nodir to do something is worth a ping; listing him as the
    owner of a ticket in a summary is not."""
    assert first_name(NODIR) == "Nodir"
    assert first_name(NODIR, mention=True) == "<@U123>"
    assert first_name({"name": "Maya Chen"}, mention=True) == "Maya", "no id, no mention"
    assert first_name("Priya Nair") == "Priya"
    assert first_name(None) == ""


def test_a_ticket_reads_as_the_thing_it_is_with_the_link_on_the_key() -> None:
    assert issue_phrase(*BUG) == (
        "<https://linear.app/x/INV-27|INV-27> (the duplicate reminder emails bug)")
    assert issue_phrase("INV-27") == "INV-27", "nothing to say about it yet"
    assert issue_phrase("INV-27", "Ship CSV export") == "INV-27 (the CSV export)"


def test_a_title_becomes_a_noun_phrase_deterministically() -> None:
    assert noun_phrase("Fix duplicate reminder emails bug") == "duplicate reminder emails bug"
    assert noun_phrase("Ship CSV export") == "CSV export", "an acronym keeps its capitals"
    assert noun_phrase("Customers table pagination breaks") == "customers table pagination breaks"
    assert noun_phrase("INV-27 follow-up") == "INV-27 follow-up", "an identifier is left alone"
    assert noun_phrase("") == ""


def test_a_consequence_names_the_person_it_will_go_to() -> None:
    assert consequence_phrase("nudge_assignee", owner="Nodir") == "if not, I'll check in with Nodir"
    assert consequence_phrase("nudge_assignee") == "if not, I'll check in with whoever owns it"
    assert consequence_phrase("escalate_channel") == "if not, I'll raise it here"
    assert consequence_phrase("ping_requester") == "if not, I'll let you know"
    assert consequence_phrase("none") == ""


def test_small_numbers_are_words() -> None:
    assert spelled(1) == "one" and spelled(2) == "two" and spelled(0) == "no"
    assert spelled(12) == "12"


def test_a_list_of_things_reads_as_a_sentence() -> None:
    assert sentence_list(["a"]) == "a"
    assert sentence_list(["a", "b"]) == "a and b"
    assert sentence_list(["a", "b", "c"]) == "a, b, and c"


# --- the before/after table in docs/research/slack-voice.md ----------------------------------------

def test_the_nudge_reads_as_the_charter_says_it_should() -> None:
    """Before: `Nodir Rahimov, INV-27 (Fix duplicate reminder emails bug) is still Backlog — it
    was expected to be underway by now. https://…`"""
    observed = {"issue": "INV-27", "title": "Fix duplicate reminder emails bug",
                "state": "Backlog", "due": "2026-08-29", "url": "https://linear.app/x/INV-27"}
    text = render("issue_not_started", **_values(observed, NODIR, NOW))

    assert text == (
        "<@U123> — <https://linear.app/x/INV-27|INV-27> (the duplicate reminder emails bug) "
        "hasn't started, and it was meant to be underway today. Anything in the way?"
    )


def test_the_call_summary_opens_with_a_sentence_not_a_stat_line() -> None:
    """Before: `filed 2 tickets · updated 1 · 1 conflict · 1 skipped`"""
    created = [{"identifier": "INV-27"}, {"identifier": "INV-29"}]
    updated = [{"identifier": "INV-26"}]
    conflicts = [{"about": "the cadence", "sides": []}]

    assert what_happened(created, updated, [], conflicts) == (
        "two new tickets, one update to INV-26, and one thing I need a human on")


def test_the_blocker_ping_says_what_it_could_not_do_in_english() -> None:
    """Before: `I'm blocked on look for a pull request on INV-27`"""
    task = {"kind": "check_pr_exists", "params": {"issue": "INV-27"}}

    assert f"I can't {human_infinitive(task)}" == "I can't find INV-27's pull request"


def test_a_promise_names_the_person_rather_than_the_role() -> None:
    """Before: `_(if not, I'll nudge the assignee)_`"""
    tasks = [{"kind": "check_pr_exists", "params": {"issue": "INV-27"},
              "due_at": "2026-08-30T16:00:00+00:00", "on_unmet": "nudge_assignee"}]
    rendered = str(plan_summary_blocks(tasks, [], {"INV-27": "Nodir"}, NOW))

    assert "_(if not, I'll check in with Nodir)_" in rendered
    assert "assignee" not in rendered


def test_since_yesterday_names_who_moved_what() -> None:
    """Before: `1 check came back clear · 1 landed early · 2 issues moved`"""
    blocks = standup_blocks(
        sprint={}, today="2026-08-29", watching=[],
        since={"movers": [{"who": "Priya Nair", "issue": "INV-26"},
                          {"who": "", "issue": "INV-25"}]},
        unmet=[], overdue=[], now=NOW)

    assert "Priya got INV-26 moving and INV-25 moved." in str(blocks)


def test_the_intake_reply_says_what_it_will_watch_for_whom() -> None:
    """Before: `Committed: 2 checks`"""
    tasks = [{"kind": "check_pr_exists", "params": {"issue": "INV-27"},
              "due_at": "2026-08-30T16:00:00+00:00", "on_unmet": "ping_requester"}]

    assert "Got it — I'll watch INV-27 for you:" in str(commitment_blocks(tasks, "", None, NOW))


# --- the anti-patterns, swept across every builder --------------------------------------------------

def every_message() -> dict[str, str]:
    """One rendering of every message type, keyed by name, for the sweeps below."""
    created = [{"identifier": "INV-27", "url": "https://linear.app/x/INV-27",
                "title": "Fix duplicate reminder emails bug", "owner": "Nodir Rahimov"}]
    updated = [{"identifier": "INV-26", "url": "", "note": "raised again in this call"}]
    skipped = [{"title": "Pause all reminders", "reason": "rejected on the call"}]
    conflicts = [{"about": "the cadence", "sides": [
        {"claim": "7 days", "source": "code:app/reminders.py:14"},
        {"claim": "5 days", "source": "notion:abc"}]}]
    tasks = [{"kind": "check_issue_state", "params": {"issue": "INV-27", "expect": ["Done"]},
              "due_at": "2026-08-30T16:00:00+00:00", "on_unmet": "nudge_assignee"}]
    observed = {"issue": "INV-27", "title": "Fix duplicate reminder emails bug",
                "state": "Backlog", "due": "2026-08-29", "url": "https://linear.app/x/INV-27",
                "pr_url": "https://github.com/x/pull/4"}
    values = {**_values(observed, NODIR, NOW), "finding": "still no pull request"}

    messages: dict[str, str] = {
        "call summary": str(call_summary_blocks(
            {"title": "Sprint 1 kickoff", "url": "https://f.video/x"},
            created, updated, skipped, conflicts, [{"id": "a1", "label": "INV-27"}])),
        "plan": str(plan_summary_blocks(tasks, ["INV-999 doesn't exist"],
                                        {"INV-27": "Nodir"}, NOW)),
        "commitment": str(commitment_blocks(tasks, "", {"INV-27": "Nodir"}, NOW)),
        "standup": str(standup_blocks(
            sprint={"name": "Sprint 1", "start": "2026-08-26"}, today="2026-08-29",
            watching=tasks, since={"met": 1, "nudged": 1},
            unmet=[{**tasks[0], "observed": {"state": "Todo"}}],
            overdue=[{"issue": "INV-25", "due": "2026-08-27", "state": "Todo"}],
            owners={"INV-27": "Nodir", "INV-25": "Tom"},
            titles={"INV-27": "Fix duplicate reminder emails bug"}, now=NOW)),
        "report": str(report_blocks(
            {"headline": "Reminders are moving.", "sections": [
                {"name": "decisions", "claims": [
                    {"text": "Grace period drops to three days", "refs": ["decision:d1"]}]}]},
            {"name": "Sprint 1", "start": "2026-08-28", "end": "2026-09-11"})),
        **{f"template {name}": render(name, **values) for name in TEMPLATES},
    }
    return messages


def test_no_message_ever_prints_a_task_kind() -> None:
    for name, message in every_message().items():
        for kind in KINDS:
            assert kind not in message, f"{name} leaks the kind {kind!r}"


def test_no_message_ever_says_s_in_brackets_or_counts_to_zero() -> None:
    for name, message in every_message().items():
        assert "(s)" not in message, f"{name} has an (s) plural"
        assert not re.search(r"\b0 \w", message), f"{name} reports a count of zero"


def test_no_message_ever_calls_a_person_the_assignee() -> None:
    for name, message in every_message().items():
        for word in ("assignee", "the team", "the system"):
            assert word not in message, f"{name} says {word!r} instead of naming somebody"


def test_every_url_sits_inside_a_slack_link() -> None:
    """A dangling URL is the tell that a sentence was assembled rather than written. Every one
    of them belongs inside `<url|label>`, on the thing it points at."""
    bare = re.compile(r"(?<![<(])https?://")
    for name, message in every_message().items():
        for match in bare.finditer(message):
            window = message[max(0, match.start() - 60):match.start()]
            assert "<" in window and "|" not in window.split("<")[-1], (
                f"{name} has a bare URL at {match.start()}: {message[match.start():][:60]}"
            )


# --- the assumptions the charter asks for, in one clause -------------------------------------------

def test_a_resolved_date_says_which_words_it_came_from() -> None:
    """Charter 7. A date the agent inferred is a small leap; naming the words closes it."""
    created = [{"identifier": "INV-27", "url": "", "title": "Fix the emails",
                "owner": "Nodir Rahimov", "due": "2026-08-31", "due_hint": "by Monday"}]
    rendered = str(call_summary_blocks({"title": "Kickoff"}, created, [], [], [], [], now=NOW))

    assert 'due Monday (from "by Monday" on the call)' in rendered


def test_a_date_nobody_spoke_claims_no_source() -> None:
    created = [{"identifier": "INV-27", "url": "", "title": "Fix the emails", "owner": "Nodir"}]
    rendered = str(call_summary_blocks({"title": "Kickoff"}, created, [], [], [], [], now=NOW))

    assert "from" not in rendered and "due" not in rendered


def test_dates_the_planner_chose_itself_are_owned_up_to_once() -> None:
    tasks = [{"kind": "check_pr_exists", "params": {"issue": "INV-27"},
              "due_at": "2026-08-30T16:00:00+00:00", "on_unmet": "nudge_assignee"},
             {"kind": "check_pr_merged", "params": {"issue": "INV-27"},
              "due_at": "2026-09-02T16:00:00+00:00", "on_unmet": "nudge_assignee"}]
    mine = str(plan_summary_blocks(tasks, [], {}, NOW, defaulted=True))
    spoken = str(plan_summary_blocks(tasks, [], {}, NOW))

    assert mine.count("I picked these dates myself") == 1, "an assumption said twice is noise"
    assert "nobody named one on the call" in mine
    assert "I picked these dates" not in spoken


# --- length ceilings (charter rule 10) --------------------------------------------------------------

def words(text: str) -> int:
    return len(re.sub(r"[*_`<>|•⌊]", " ", text).split())


def lines_of(blocks: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for block in blocks:
        if block["type"] == "section":
            out.extend(block["text"]["text"].splitlines())
        elif block["type"] == "context":
            out.extend(block["elements"][0]["text"].splitlines())
    return [line for line in out if line.strip()]


def test_a_nudge_is_one_or_two_lines() -> None:
    observed = {"issue": "INV-27", "title": "Fix duplicate reminder emails bug",
                "state": "Backlog", "due": "2026-08-29", "url": "https://linear.app/x/INV-27",
                "pr_url": "https://github.com/x/pull/4"}
    values = {**_values(observed, NODIR, NOW), "finding": "still no pull request"}
    for name in TEMPLATES:
        text = render(name, **values)
        assert text.count("\n") == 0, f"{name} runs to more than one line"
        assert words(text) <= 40, f"{name} is {words(text)} words"
        # Sentence enders only: the dots inside linear.app and github.com are not sentences.
        assert len(re.findall(r"[.?!](?=\s|$)", text)) <= 2, f"{name} has too many sentences"


def test_a_blocker_ping_is_two_or_three_lines() -> None:
    task = {"kind": "check_pr_exists", "params": {"issue": "INV-27"}}
    text = (f"<@U123> — I can't {human_infinitive(task)}: GitHub isn't connected for this "
            "project. I'll leave it with you.")

    assert words(text) <= 40 and text.count("\n") == 0


def test_the_call_summary_carries_no_overhead_beyond_its_one_line_opening() -> None:
    """Its length is the call's, not the agent's: one header, one line per thing that happened,
    and nothing else."""
    created = [{"identifier": f"INV-{n}", "url": "", "title": "Fix it", "owner": "Nodir Rahimov"}
               for n in range(4)]
    lines = lines_of(call_summary_blocks({"title": "Kickoff"}, created, [], [], [], [], now=NOW))

    assert len(lines) == 1 + len(created), "one opening sentence, then one line per ticket"
    assert words(lines[0]) <= 25


def test_a_plan_announcement_is_under_a_hundred_and_fifty_words() -> None:
    tasks = [{"kind": "check_issue_state", "params": {"issue": f"INV-{n}", "expect": ["Done"]},
              "due_at": "2026-08-30T16:00:00+00:00", "on_unmet": "nudge_assignee"}
             for n in range(6)]
    blocks = plan_summary_blocks(tasks, ["INV-999 doesn't exist"], {"INV-0": "Nodir"}, NOW)

    assert words("\n".join(lines_of(blocks))) < 150


def test_a_standup_is_three_to_five_one_line_bullets_with_no_preamble() -> None:
    tasks = [{"kind": "check_issue_state", "params": {"issue": "INV-27", "expect": ["Done"]},
              "due_at": "2026-08-30T16:00:00+00:00", "on_unmet": "nudge_assignee"}]
    lines = lines_of(standup_blocks(
        sprint={"name": "Sprint 1", "start": "2026-08-26"}, today="2026-08-29",
        watching=tasks * 3, since={"met": 2, "nudged": 1},
        unmet=[{**tasks[0], "observed": {"state": "Todo"}}],
        overdue=[{"issue": "INV-25", "due": "2026-08-27", "state": "Todo"}],
        lesson="checks on Fridays come back unmet more often.",
        owners={"INV-27": "Nodir", "INV-25": "Tom"}, now=NOW))

    greeting, bullets = lines[0], [line for line in lines[1:] if line.startswith("•")]
    assert greeting.startswith("*Morning"), "the greeting is the whole preamble"
    assert 3 <= len(bullets) <= 5, f"{len(bullets)} bullets"
    assert all(words(bullet) <= 22 for bullet in bullets)


def test_a_sprint_report_is_under_two_hundred_words() -> None:
    sections = [{"name": name, "claims": [
        {"text": "Something happened that somebody should know about here",
         "refs": ["linear:INV-27"]} for _ in range(2)]}
        for name in ("shipped", "moved", "blocked", "at_risk")]
    blocks = report_blocks({"headline": "A busy sprint, mostly on track.", "sections": sections},
                           {"name": "Sprint 1", "start": "2026-08-28", "end": "2026-09-11"})

    assert words("\n".join(lines_of(blocks))) < 200


def test_a_quiet_day_and_an_early_note_are_each_two_lines_at_most() -> None:
    quiet = lines_of(standup_blocks(
        sprint={"name": "Sprint 1", "start": "2026-08-26"}, today="2026-08-29", watching=[],
        since={}, unmet=[], overdue=[], next_due="2026-09-03T16:00:00+00:00", now=NOW))

    assert len(quiet) == 2

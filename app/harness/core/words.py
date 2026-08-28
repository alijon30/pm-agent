"""Counting things in words.

One pluralisation rule for the whole system, in core because five modules need it and none of
them owns it: the channel, the console, the graph, the queue's own summaries and the standup all
have to say "1 check" and "2 checks" the same way, or the agent sounds like two different
things depending on where you read it."""

from __future__ import annotations


def count_of(number: int, singular: str) -> str:
    """"1 ticket", "2 tickets". So no message ever has to say "check(s)"."""
    return f"{number} {singular}" if number == 1 else f"{number} {singular}s"

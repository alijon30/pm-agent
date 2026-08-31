"""Counting things in words."""

from __future__ import annotations


def count_of(number: int, singular: str) -> str:
    """"1 ticket", "2 tickets"."""
    return f"{number} {singular}" if number == 1 else f"{number} {singular}s"

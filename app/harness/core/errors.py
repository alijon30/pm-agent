"""Exceptions whose messages are safe to surface after redact()."""

from __future__ import annotations


class PmError(Exception):
    """Base class. Message is intended for humans and must never carry a secret value."""


class SourceUnavailable(PmError):
    """A read source (Linear, Notion, code) could not be reached. The model must not infer."""

    def __init__(self, source: str, detail: str = "") -> None:
        self.source = source
        self.detail = detail
        super().__init__(f"{source} unavailable" + (f": {detail}" if detail else ""))


class GateFailed(PmError):
    """A deterministic gate refused an item. Carries the specific reason for the one bounce."""

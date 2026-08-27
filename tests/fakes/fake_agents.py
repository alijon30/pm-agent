from __future__ import annotations

from typing import Any


class FakeExtractor:
    """Returns canned results in order; records every payload it was given."""

    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = list(results)
        self.calls: list[dict[str, Any]] = []

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        if not self.results:
            raise AssertionError("FakeExtractor has no more canned results")
        return self.results.pop(0)

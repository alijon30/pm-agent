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


class FakeReconciler:
    """Returns canned ReconcileResult dicts in order; records every payload it was given."""

    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = list(results)
        self.calls: list[dict[str, Any]] = []

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        if not self.results:
            raise AssertionError("FakeReconciler has no more canned results")
        return self.results.pop(0)


class FakePlanner:
    """Returns canned Plan dicts in order; records every payload it was given."""

    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = list(results)
        self.calls: list[dict[str, Any]] = []

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        if not self.results:
            raise AssertionError("FakePlanner has no more canned results")
        return self.results.pop(0)


class FakeReporter:
    """Returns canned Report dicts in order; records every payload it was given."""

    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = list(results)
        self.calls: list[dict[str, Any]] = []

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        if not self.results:
            raise AssertionError("FakeReporter has no more canned results")
        return self.results.pop(0)


class FakeSteward:
    """Returns canned Plan dicts in order; records every payload it was given."""

    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = list(results)
        self.calls: list[dict[str, Any]] = []

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        if not self.results:
            raise AssertionError("FakeSteward has no more canned results")
        return self.results.pop(0)


class FakeReviewer:
    """Returns canned Lessons dicts in order; records every payload it was given."""

    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = list(results)
        self.calls: list[dict[str, Any]] = []

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        if not self.results:
            raise AssertionError("FakeReviewer has no more canned results")
        return self.results.pop(0)

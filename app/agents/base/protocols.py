"""What a stage needs from the model side. Stages depend on these, never on ADK directly, so
every stage test runs against a fake."""

from __future__ import annotations

from typing import Any, Protocol


class Extractor(Protocol):
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """payload: {"transcript": str, "roster_names": [str], "feedback": str | None}.
        Returns a dict shaped like agents.schemas.ExtractResult (validated by the stage)."""
        ...


class Triage(Protocol):
    def decision_bearing(self, segments: list[dict[str, Any]]) -> list[bool]:
        """One flag per transcript segment: worth showing the extractor?"""
        ...


class Reconciler(Protocol):
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """payload: {"action_items", "decisions", "meeting", "roster", "today", "feedback"}.
        Returns a dict shaped like agents.base.schemas.ReconcileResult."""
        ...


class Planner(Protocol):
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """payload: {"context", "open_tasks", "recent_results", "policy", "now", "feedback"}.
        Returns a dict shaped like agents.base.schemas.Plan."""
        ...


class Reporter(Protocol):
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """payload: {"sprint", "created_issues", "checks", "decisions", "open_conflicts",
        "actions_summary", "today", "feedback"}.
        Returns a dict shaped like agents.base.schemas.Report."""
        ...

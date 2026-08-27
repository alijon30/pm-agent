"""Segment triage. PassthroughTriage keeps everything; GemmaTriage arrives in Plan 4."""

from __future__ import annotations

from typing import Any


class PassthroughTriage:
    def decision_bearing(self, segments: list[dict[str, Any]]) -> list[bool]:
        return [True] * len(segments)

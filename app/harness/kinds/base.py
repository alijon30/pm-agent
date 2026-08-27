"""A task kind is the unit of what the planner may schedule: a name, a parameter schema, and the
unmet-actions it may trigger. Executors are looked up by the same name in stages/checks.py."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictParams(BaseModel):
    """Params models forbid unknown fields, so a planner cannot smuggle intent through extras."""

    model_config = ConfigDict(extra="forbid")


class KindSpec(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    params_schema: type[BaseModel]
    unmet_actions: tuple[str, ...]
    description: str

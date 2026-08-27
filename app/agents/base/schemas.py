"""Output schemas for the ADK agents. ADK forces the model to emit exactly these shapes; the
stages validate again with the same classes, so gates always operate on typed data."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    quote: str = Field(description="Verbatim words from the transcript, at least 12 characters.")
    timestamp: str = Field(default="", description="HH:MM:SS of the segment the quote is from.")
    speaker: str = Field(default="", description="Speaker display name for that segment.")


class Decision(BaseModel):
    statement: str = Field(description="What was decided, as a single declarative sentence.")
    rejected_options: list[str] = Field(
        default_factory=list, description="Alternatives explicitly considered and not chosen."
    )
    evidence: list[Evidence]


class ActionItem(BaseModel):
    title: str = Field(description="Imperative, under 80 characters, suitable as an issue title.")
    description: str = Field(default="", description="One or two sentences of context.")
    owner_name: str | None = Field(
        default=None, description="A roster name if one was named; otherwise null."
    )
    due_hint: str | None = Field(
        default=None, description="The due date exactly as spoken, e.g. 'next Friday'."
    )
    priority_hint: str | None = Field(
        default=None, description="Urgency language exactly as spoken, if any."
    )
    evidence: list[Evidence]


class OpenQuestion(BaseModel):
    question: str
    evidence: list[Evidence]


class ExtractResult(BaseModel):
    decisions: list[Decision] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)


# --- reconcile --------------------------------------------------------------------------------


class Side(BaseModel):
    claim: str = Field(description="What this source says, in a few words: '7 days'.")
    source: str = Field(
        description="A typed reference: linear:INV-142 · notion:<page> · code:<path>:<line> · "
                    "fathom:<meeting>@<mm:ss> · decision:<id> · wiki:<slug>."
    )


class Conflict(BaseModel):
    kind: Literal["code_vs_spec", "spec_vs_call", "ticket_vs_call", "brain_vs_call"]
    about: str = Field(description="The subject they disagree about, e.g. 'reminder window'.")
    sides: list[Side] = Field(description="One entry per source, each with its own citation.")


class Fact(BaseModel):
    text: str = Field(description="One verifiable sentence.")
    source: str = Field(description="A typed reference that supports it.")


class ReconcileItem(BaseModel):
    index: int = Field(description="The action item's position in the extract result.")
    title: str = Field(description="Imperative, under 80 characters.")
    description: str = Field(default="", description="Context for whoever picks this up.")
    disposition: Literal["new", "update", "duplicate_of"]
    target_issue: str | None = Field(
        default=None, description="The existing issue for update/duplicate_of; null for new."
    )
    owner: str | None = Field(default=None, description="A roster name, or null.")
    priority: int | None = Field(
        default=None, description="Linear scale: 1 urgent … 4 low. Null when nobody indicated."
    )
    due: str | None = Field(default=None, description="ISO date (YYYY-MM-DD), or null.")
    due_hint: str | None = Field(default=None, description="The words spoken about timing.")
    citations: list[str] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list, description="Durable facts for the brain.")


class ReconcileResult(BaseModel):
    items: list[ReconcileItem] = Field(default_factory=list)
    decision_conflicts: list[Conflict] = Field(default_factory=list)


# --- plan -------------------------------------------------------------------------------------


class PlanTask(BaseModel):
    key: str = Field(description="Unique within this plan; other tasks depend on it by this key.")
    kind: str = Field(description="One of the task kinds in the catalog.")
    params: dict[str, Any] = Field(default_factory=dict)
    due: str = Field(description="ISO-8601 timestamp when this check should run.")
    depends_on: list[str] = Field(
        default_factory=list, description="Keys in this plan, or ids of existing open tasks."
    )
    reason: str = Field(description="Why this task exists, in one sentence, for a human.")
    on_unmet: str = Field(default="none")
    on_dep_failed: str = Field(default="skip")
    context: dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    tasks: list[PlanTask] = Field(default_factory=list)
    supersedes: list[str] = Field(
        default_factory=list, description="Keys or task ids made obsolete by this plan."
    )
    notes: str = Field(default="", description="What you observed, in one or two sentences.")

"""Output schemas for the ADK agents."""

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


class Investigation(BaseModel):
    """What the code already says about a bug, gathered before the ticket is filed.

    Paths and lines only. A pasted code body is stale the moment somebody edits the file, and
    the engineer who picks this up is going to open the file anyway."""

    files: list[str] = Field(
        default_factory=list,
        description="code:<path>:<line> references you actually opened, most relevant first.",
    )
    note: str = Field(
        default="",
        description="Two or three sentences: where the behaviour lives and the suspected cause.",
    )
    confidence: Literal["likely", "possible", "unknown"] = Field(
        default="unknown",
        description="How sure you are. 'unknown' is the honest answer when you found nothing.",
    )


class ReconcileItem(BaseModel):
    index: int = Field(description="The action item's position in the extract result.")
    title: str = Field(description="Imperative, under 80 characters.")
    description: str = Field(default="", description="Context for whoever picks this up.")
    context: str = Field(
        default="",
        description="One or two sentences on why this matters: who is affected and what it "
                    "costs them. Only what was actually said supports it. Empty if nobody said.",
    )
    acceptance: list[str] = Field(
        default_factory=list,
        description="Testable criteria a reviewer could check, derived from what was said.",
    )
    investigation: Investigation | None = Field(
        default=None,
        description="For a bug or a change to behaviour the product already has: what the code "
                    "says about it. Null for anything else.",
    )
    disposition: Literal["new", "update", "duplicate_of"]
    target_issue: str | None = Field(
        default=None, description="The existing issue for update/duplicate_of; null for new."
    )
    owner: str | None = Field(default=None, description="A roster name, or null.")
    area: Literal["frontend", "backend"] | None = Field(
        default=None,
        description="Which side of the product the work lives on, when the call or the code "
                    "you read makes it clear. Null when it is neither or unclear.",
    )
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


class Memory(BaseModel):
    """Something the team said that should outlive the message. Filled by the intake step when
    somebody is telling the agent how to work rather than asking it for a check."""

    kind: Literal["ownership", "preference", "fact"]
    subject: list[str] = Field(
        default_factory=list,
        description="The 2-6 words a later message about the same thing would contain.",
    )
    person: str | None = Field(
        default=None, description="A roster name, for ownership. Null when nobody was named."
    )
    text: str = Field(description="The rule in their words, trimmed.")


class Plan(BaseModel):
    tasks: list[PlanTask] = Field(default_factory=list)
    supersedes: list[str] = Field(
        default_factory=list, description="Keys or task ids made obsolete by this plan."
    )
    notes: str = Field(default="", description="What you observed, in one or two sentences.")
    memory: Memory | None = Field(
        default=None, description="Set instead of tasks when told how to work from now on."
    )


# --- report -----------------------------------------------------------------------------------


class Claim(BaseModel):
    text: str = Field(description="One sentence a team lead can read and act on.")
    refs: list[str] = Field(
        description="Typed references that prove this claim, at least one: linear:INV-26 · "
                    "fathom:<meeting>@<mm:ss> · decision:<id> · code:<path>:<line>. Every one "
                    "must appear in the JSON you were given — never construct an identifier."
    )


class ReportSection(BaseModel):
    name: Literal[
        "shipped", "moved", "blocked", "at_risk", "conflicts", "open_questions", "decisions"
    ] = Field(description="Which part of the report these claims belong to.")
    claims: list[Claim] = Field(
        description="The claims in this section. Omit the whole section rather than emit it "
                    "empty."
    )


class Report(BaseModel):
    headline: str = Field(
        description="One sentence a team lead could forward to the team without editing it."
    )
    sections: list[ReportSection] = Field(
        default_factory=list,
        description="Sections in this order: shipped, moved, blocked, at_risk, conflicts, "
                    "open_questions, decisions. Skip any that has nothing to say.",
    )


# --- review -----------------------------------------------------------------------------------


class Lesson(BaseModel):
    text: str = Field(
        description="One sentence about how this agent should plan or interrupt people, in the "
                    "imperative. About the agent's own behaviour — never about the product."
    )
    evidence: list[str] = Field(
        description="The task: and action: references from the input that this lesson was drawn "
                    "from. At least one, all of them copied exactly from what you were given."
    )


class Lessons(BaseModel):
    lessons: list[Lesson] = Field(
        default_factory=list,
        description="At most three. Fewer is better; none is a valid answer to a quiet day.",
    )
    notes: str = Field(default="", description="What you observed, in one or two sentences.")

"""Output schemas for the ADK agents. ADK forces the model to emit exactly these shapes; the
stages validate again with the same classes, so gates always operate on typed data."""

from __future__ import annotations

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

"""Generate GATES.md from the code it describes.

    uv run python scripts/gen_gates.py
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from typing import Any

from app.harness.kinds.registry import KINDS, NOT_SCHEDULABLE, UNMET_ACTIONS
from app.harness.stages.reconcile import RETRY_MINUTES
from app.harness.stages.runner import STAGES
from app.harness.store import wiki
from app.harness.store.lessons import MAX_LESSONS
from app.harness.store.tasks import BACKOFF_SECONDS
from app.harness.verify import caps, citations, dates, evidence, ids, lineage, plan, priority
from app.harness.verify import roster as roster_gate

ROOT = Path(__file__).parents[1]
TARGET = ROOT / "GATES.md"
SCRIPT = "scripts/gen_gates.py"


# --- reading the source ---------------------------------------------------------------------------


def paragraphs(text: str | None) -> list[str]:
    """A docstring as the blocks it was written in, indentation inside a block preserved."""
    return [b.rstrip() for b in inspect.cleandoc(text or "").split("\n\n") if b.strip()]


def as_markdown(block: str) -> str:
    """One docstring block as Markdown: an indented block stays a listing, prose is reflowed."""
    lines = [line for line in block.split("\n")]
    if lines and all(line.startswith("    ") for line in lines if line.strip()):
        return "```\n" + "\n".join(line[4:] for line in lines) + "\n```"
    return " ".join(line.strip() for line in lines)


def describe(module: Any) -> tuple[str, list[str]]:
    """The lead sentence and the rest of a module's own account of itself."""
    blocks = paragraphs(module.__doc__)
    return (as_markdown(blocks[0]) if blocks else ""), [as_markdown(b) for b in blocks[1:]]


def second_paragraph(func: Any) -> str:
    blocks = paragraphs(func.__doc__)
    return as_markdown(blocks[1]) if len(blocks) > 1 else ""


def ref_kinds() -> list[str]:
    """The reference kinds the identifier gate knows, read off its own pattern."""
    match = re.search(r"\(([a-z|]+)\)", ids.REF.pattern)
    return match.group(1).split("|") if match else []


def shipped_policy() -> dict[str, Any]:
    """The policy the demo project actually ships with — the numbers a judge would see running."""
    document: dict[str, Any] = json.loads(
        (ROOT / "fixtures" / "projects" / "acme.json").read_text()
    )
    policy: dict[str, Any] = document.get("policy") or {}
    return policy


# --- rendering ------------------------------------------------------------------------------------


def params_of(kind: str) -> str:
    fields = KINDS[kind].params_schema.model_fields
    return ", ".join(
        f"`{name}`" if info.is_required() else f"`{name}?`" for name, info in fields.items()
    )


def kinds_table() -> str:
    rows = [
        "| kind | what it does | params | schedulable | on unmet |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, spec in KINDS.items():
        reason = NOT_SCHEDULABLE.get(name)
        if reason:
            schedulable = f"no — {reason}"
        elif name not in STAGES:
            # Read from the runner rather than asserted, so executor drift shows up here.
            schedulable = "yes — but no executor is registered"
        else:
            schedulable = "yes"
        unmet = ", ".join(f"`{a}`" for a in spec.unmet_actions) or "—"
        rows.append(
            f"| `{name}` | {spec.description} | {params_of(name)} | {schedulable} | {unmet} |"
        )
    return "\n".join(rows)


def gate_section(title: str, module: Any, facts: list[tuple[str, str]]) -> str:
    lead, rest = describe(module)
    out = [f"### {title}", "", lead, ""]
    out += [f"{block}\n" for block in rest]
    if facts:
        out += [f"- **{label}** — {value}" for label, value in facts]
        out.append("")
    return "\n".join(out)


def gates() -> str:
    policy = shipped_policy()
    band = policy.get("priority_band", [2, 4])
    quiet = policy.get("quiet_hours") or list(caps.DEFAULT_QUIET)
    sections = [
        gate_section("Evidence — did anyone actually say this?", evidence, [
            ("minimum quote length", f"{evidence.MIN_QUOTE_CHARS} characters after normalisation"),
        ]),
        gate_section("Identifiers — does the thing it named exist?", ids, [
            ("reference kinds", ", ".join(f"`{k}:`" for k in ref_kinds())),
            ("issue keys must match", f"`{ids.ISSUE_IDENTIFIER.pattern}`"),
        ]),
        gate_section("Roster — is that a real person on this project?", roster_gate, [
            ("matching", as_markdown(paragraphs(roster_gate.resolve_owner.__doc__)[0])),
        ]),
        gate_section("Priority — may it call its own work urgent?", priority, [
            ("band the shipped project allows", f"{band[0]} to {band[1]} (1 urgent … 4 low)"),
            ("escalation phrases", ", ".join(
                f"`{p}`" for p in policy.get("escalation_phrases") or []) or "—"),
        ]),
        gate_section("Dates — did somebody promise this day?", dates, [
            ("accepted date shape", f"`{dates.ISO_DATE.pattern}`"),
        ]),
        gate_section("Caps — how much, and at what hour?", caps, [
            ("writes per day", str(policy.get("daily_write_cap", "—"))),
            ("interruptions per day", str(policy.get("daily_ping_cap", "—"))),
            ("quiet hours", f"{quiet[0]} to {quiet[1]} (default "
                            f"{caps.DEFAULT_QUIET[0]}–{caps.DEFAULT_QUIET[1]})"),
            ("the one exemption", second_paragraph(caps.check_caps)),
        ]),
        gate_section("Lineage — can it give itself unbounded work?", lineage, [
            (f"`{key}`", str(value)) for key, value in lineage.DEFAULT_POLICY.items()
        ]),
        gate_section("Plan — is what it scheduled for itself real?", plan, [
            ("identifier-bearing params", ", ".join(f"`{f}`" for f in plan.ID_PARAM_FIELDS)),
            ("dependency-failure policies", ", ".join(f"`{p}`" for p in plan.DEP_POLICIES)),
            ("grace for a due time just passed", f"{plan.PAST_GRACE_MINUTES} minutes"),
            ("actions a check may take", ", ".join(f"`{a}`" for a in UNMET_ACTIONS)),
        ]),
        gate_section("Citations — can every claim be re-opened?", citations, []),
        brain_section(),
    ]
    return "\n".join(sections)


def brain_section() -> str:
    """What the agent is allowed to remember, and what has to be true before it does."""
    return "\n".join([
        "## Brain — what may it remember, and on whose word?",
        "",
        as_markdown(paragraphs(wiki.__doc__)[0]),
        "",
        "| | |",
        "|---|---|",
        f"| kinds it keeps | {', '.join(f'`{k}`' for k in wiki.KINDS)} |",
        "| a memory needs a source | an entry with no typed `source` ref is refused outright |",
        "| ownership needs a real person | the roster gate runs before it is stored; an "
        "unknown name is answered with a question and nothing is written |",
        "| facts need a verified source | only facts whose reference survived the identifier "
        "gate are kept |",
        f"| handed to a model at most | {wiki.BRAIN_LIMIT} entries, by word overlap |",
        "| replacing, not erasing | a newer owner retires the older claim and keeps it |",
        "| idempotent by source | the same message replayed is one memory |",
        "",
    ])


def failure_posture() -> str:
    backoff = ", ".join(f"{s}s" for s in BACKOFF_SECONDS)
    return "\n".join([
        "## Failure posture",
        "",
        "- **One bounce, then an honest drop.** A gate that refuses hands the model the specific",
        "  reason and asks once more. A second failure removes the item and the removal is",
        "  reported — in the Slack summary, in the task result, and on the console.",
        "- **An outage is not a verdict.** A source that cannot be reached makes an item",
        f"  `unverified` rather than false, and the task re-enqueues itself once for +{RETRY_MINUTES}",
        "  minutes. The model is never asked to infer what a tool would have said.",
        f"- **Retries back off** on {backoff} and then the task is marked failed. Work somebody",
        "  asked for says so in their thread instead of disappearing.",
        "- **Intent before effect.** Every write is recorded as `pending` with a deterministic",
        "  idempotency key before it happens and marked `done` after, carrying the payload that",
        "  undoes it. A crash between the two is recoverable; revert is data, not a code path.",
        "- **Caps defer, they never drop.** Work held back by a cap or by quiet hours is",
        "  rescheduled with the reason recorded, and re-observes reality when it runs.",
        f"- **Memory is bounded.** The agent keeps at most {MAX_LESSONS} lessons about its own",
        "  behaviour, each citing the tasks and actions it was drawn from; a lesson whose",
        "  evidence is not in that day's record is discarded before it is ever stored.",
    ])


def render() -> str:
    return "\n".join([
        "# Gates",
        "",
        "Every judgement this agent makes is a model's output, and no model output reaches",
        "Linear, Slack or the queue without passing the deterministic checks below. Each gate is",
        "ordinary Python with no model in it: it either finds the quote in the transcript or it",
        "does not, either re-fetches the identifier or it does not. A gate that refuses gives the",
        "model **one** retry with the specific failure, and a second refusal drops the item and",
        "records the drop. Nothing here fails silently, and nothing here can be talked past.",
        "",
        f"This file is generated from the code it describes by `{SCRIPT}`; the catalog, the",
        "limits and the descriptions are read out of the modules at generation time so the",
        "document cannot drift from the system. Regenerate with:",
        "",
        "```",
        f"uv run python {SCRIPT}",
        "```",
        "",
        "`tests/test_gates_doc.py` fails if this file and the code disagree.",
        "",
        "## What the agent may do",
        "",
        "The whole of it. A kind that is not in this table cannot be scheduled, executed or",
        "named by any model in the system — the catalog is a whitelist, not a suggestion.",
        "",
        kinds_table(),
        "",
        "## The gates",
        "",
        gates(),
        failure_posture(),
        "",
    ])


def main() -> None:
    TARGET.write_text(render())
    print(f"wrote {TARGET.relative_to(ROOT)} ({len(render().splitlines())} lines)")


if __name__ == "__main__":
    main()

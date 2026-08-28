# How OpenAI's product teams operate — research notes (2026-08-28)

Compiled by a research subagent, web-only. Confidence markers: Symphony README/SPEC and the
Agents SDK guardrails doc were fetched directly (high confidence); openai.com launch posts were
verified via search snippets only (403 on direct fetch); the Codex-lead interview is paywalled
secondhand. Verify wording before publishing quotes.

## Findings

1. **Symphony** — OpenAI's internal coding-agent orchestrator, open-sourced as a spec: a Linear
   board becomes the control plane; "teams manage work instead of supervising coding agents";
   some teams reported ~500% more landed PRs in three weeks.
   https://github.com/openai/symphony
2. **Symphony deliberately declines dependency ordering and verification** — "not a
   general-purpose workflow engine or distributed job scheduler"; tracker `blocked_by` is
   advisory metadata only; proof-of-work lives in the workflow prompt, not the orchestrator.
3. **Runs may end at `Human Review`, not `Done`** — handoff states are workflow-defined; the
   spec "does not require a single approval, sandbox, or operator-confirmation policy" and
   expects implementations to document their trust posture.
4. **Credential isolation**: the coding-agent child process never holds raw tracker credentials.
5. **Guardrails vs. Approvals** is a named two-tier design in the Agents SDK: guardrails =
   automatic, fast, binary; approvals = pause the run for a human ("approval interruption").
   "Put validation next to the tool that creates the side effect."
   https://developers.openai.com/api/docs/guides/agents/guardrails-approvals
6. **Fail-closed is a named policy**: "record decisions and execution outcomes, and fail closed
   if review times out or becomes unavailable." (same doc)
7. **Workspace agents** — named, shared, scheduled, admin-governed agents for "close and
   reporting, project status"; e.g. a weekly metrics agent that pulls data, drafts the
   narrative, and delivers the report on schedule. (launch post; snippet-verified)
8. (Secondhand, thin) Internal Codex adoption framed as ~90-100% of employees; "zone defense"
   role-blurring per the Codex lead, with a caution against abandoning discipline practice.
9. OpenAI's org-usage research reports ~7x output-token growth Jun 2025→Mar 2026.
10. Like Anthropic, **no published "how our PM org runs planning/retros" essay** — the primary
    literature at both labs is engineering-workflow-shaped.

## What pm-agent already embodies (name these in the README)

- **Fail-closed** is already our behavior everywhere (gates drop, caps defer, signatures 401,
  unresolved identity stays unresolved) — adopt OpenAI's *name* for it.
- **Proof-of-work on the ticket**: build_description already puts the verbatim quote, citations
  and conflicts in the Linear issue body — Symphony's proof-of-work pattern, surfaced where the
  human reviews.
- **Vocabulary pass**: our deterministic gates = "guardrails" (tool-level, exactly as OpenAI
  recommends); our revert window = the human-control tier. Label them so for judges.

## The differentiator (state plainly in the submission)

Dependency-ordered, gate-validated follow-up scheduling is something **OpenAI's own Symphony
spec explicitly declines to build** and Anthropic's harness writeup does not address. pm-agent's
task-graph queue (planner proposes → plan gate validates → queue materialises blocked/queued
chains → Linear webhooks resolve met checks early) fills a gap neither lab ships.

## Compared to Anthropic

- Both replace synchronous status rituals with artifacts (demos at Anthropic, agent-authored
  scheduled reports at OpenAI).
- Verification emphasis differs: Anthropic → environmental containment (sandbox, classifier
  accepting ~17% overeager actions); OpenAI → explicit workflow control (guardrails/approvals,
  mandated fail-closed). pm-agent takes the OpenAI-style explicit-gate posture with
  Anthropic-style non-negotiables.
- Role framing: Anthropic keeps PM judgment central ("the handful of true non-negotiables");
  OpenAI is more radical ("zone defense"). pm-agent sits closer to Anthropic's philosophy.
- Both ship runnable artifacts (knowledge-work-plugins vs. Symphony spec) rather than prose.

## Quotes (verify wording; first two fetched verbatim)

- "Engineers do not need to supervise Codex; they can manage the work at a higher level." —
  Symphony README
- "This specification does not require a single approval, sandbox, or operator-confirmation
  policy…" — Symphony SPEC (contrast: pm-agent bakes its trust posture in as non-negotiable
  gates)
- "Record decisions and execution outcomes, and fail closed if review times out or becomes
  unavailable." — OpenAI Agents SDK

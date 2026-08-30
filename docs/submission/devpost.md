# Devpost submission draft

Paste-ready field by field. Upload `docs/media/architecture.png` as the architecture image
(Devpost does not render Mermaid) and `docs/media/graph.png` + `panel.png` as gallery shots. Submit **Sunday well before 5:00 PM PDT**. Attach: repo link,
video link, live demo URL (`https://pm-agent-999960779013.us-central1.run.app/console/graph`).

## Project name

pm-agent

## Elevator pitch (≤ ~200 chars)

An autonomous product manager: the call ends, the cited tickets exist, the follow-ups schedule
themselves, and the team just gets told — with a revert button on every action.

## Inspiration

My team asked for help building a "Product Agent" — the PM busywork after every product call
(minutes, tickets, follow-ups, status chasing) is exactly the work everyone postpones. Most
agent products wrap that work in approval prompts. Anthropic's engineers measured what that
buys: users approve ~93% of permission prompts — oversight decays into a rubber stamp. So I
built the opposite bet for the Taskmaster track: an agent that **acts first and makes reverting
trivial**, with determinism where trust actually needs to live.

## What it does

A Fathom call recording lands and pm-agent, running 24/7 on Cloud Run, does the PM's next two
hours in about a minute: extracts decisions and action items (each backed by a verbatim quote
or dropped), reconciles them against Linear, Notion and the codebase so nothing gets re-filed,
files cited issues with owners and defensible priorities, then **schedules its own future** —
a dependency-ordered graph of checks ("issue underway by Sep 1 → then a PR exists by Sep 3"),
each with a declared consequence if unmet. Good news resolves early: an engineer moving a
ticket unblocks the chain within seconds via webhook. It posts a morning standup, answers
Slack requests (commits to watches, pings on blockers), writes the sprint report with 100%
cited claims, and runs a daily review that turns evidence into next-day lessons. Every action
carries a one-click revert. Its whole world is visible as a live knowledge graph with time
replay, a "Now" dock showing what it's doing this second, and a story panel on every node —
what the agent did about that thing, and why.

## How we built it

Five ADK `LlmAgent`s on **Gemini 3.5** (extractor, reconciler, planner, reporter, reviewer)
with schema-enforced structured output and per-agent tool allowlists; **Gemma 4 (31B)** as a
second Google model for transcript triage and Slack intent classification, called directly
through the GenAI SDK. The orchestrator is not a framework — it is a **Firestore task graph**
(leases, `depends_on`, backoff, atomic plan materialisation) drained by a Cloud Scheduler tick
and short-circuited by webhooks. Between every model output and every external effect sit
**deterministic gates**: evidence quotes, re-fetched identifiers, roster membership, priority
bands with escalation quotes, date rules, daily caps and quiet hours, plan lineage limits, and
report citation coverage (see GATES.md — generated from the code so it cannot drift). Writes
are intent-before-effect with idempotency keys and stored revert payloads. Stack: Cloud Run,
Firestore, Cloud Scheduler, Secret Manager; connectors for Linear, Slack, Notion, GitHub,
Fathom. The knowledge graph is a self-contained vanilla-JS force simulation — no CDN, renders
with the network down.

## Challenges we ran into

ADK delivers structured output through an internal `set_model_response` tool — my per-agent
tool guard silently blocked it, producing empty agent responses that only a live test caught.
Free-tier rate limits (5 RPM) shaped real architecture: retry-with-backoff in the runner, a
cheaper model for triage, and an eval run that proved the degradation posture. Firestore's
composite-index requirement turned every new filtered query into an ops step (11 indexes,
documented). And Cloud Build's us-central1 pool jammed for an hour mid-submission-week —
the runbook now has the us-east1 detour.

## Accomplishments that we're proud of

The whole loop is **live-proven, end to end, off a real recorded call** — extraction caught
every planted moment, reconciliation caught a real accidental duplicate (updated INV-25
instead of re-filing it), the planner's dependency chain resolved four days early off a Linear
webhook within seconds, and the first autonomous standup fired at 9:00 sharp. Across six eval
runs: **0 fabricated identifiers, 100% report citation coverage, 0 invalid plans
materialised**. The best results were the worst runs: quota starvation and small-model variance
dropped judgment scores, and the guarantees held anyway — the agent degrades to silence, never to lies.

## What we learned

Autonomy is a trust-engineering problem, not a capability problem. The model was never the
bottleneck — the bet that paid off was moving trust out of the model entirely: deterministic
gates, act-then-revert, honest failure. Also: OpenAI's own internal orchestrator (Symphony)
explicitly declines dependency ordering as "not a policy concern" — the self-scheduling task
graph turned out to be the genuinely novel part.

## What's next

Slack Socket Mode surfaces, a prompt-injection classifier ahead of extract (transcripts are
untrusted input), human-review states for the rare action class where revert isn't enough,
audience-shaped reports, and recurring routines.

## Built with

`gemini-3.5` · `gemma` · `google-adk` · `genai-sdk` · `cloud-run` · `firestore` ·
`cloud-scheduler` · `secret-manager` · `python` · `fastapi` · `linear` · `slack` · `notion` ·
`fathom` · `svg`

## Links

- Repo: https://github.com/alijon30/pm-agent
- Live graph: https://pm-agent-999960779013.us-central1.run.app/console/graph
- Live console: https://pm-agent-999960779013.us-central1.run.app/console
- Demo company (synthetic): https://github.com/alijon30/acme-invoicing
- Video: (add Friday)
- Blog post: (add link when published — bonus)

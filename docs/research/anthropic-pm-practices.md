# How Anthropic's PMs and agent teams operate — research notes (2026-08-28)

Compiled by a research subagent from Anthropic first-party sources, for pm-agent's remaining
build and the submission write-up. Verify exact quote wording against the URL before publishing.

## Findings (sourced)

1. **Demo-first replaces status meetings.** Cat Wu (Anthropic PM): teams "share demos of new
   ideas" instead of stand-ups; "when a product manager can go from idea to working prototype in
   an afternoon, the gap between 'what if we tried…' and 'here, try this' nearly disappears."
   https://claude.com/blog/product-management-on-the-ai-exponential
2. **Hand-crafted evals are the reliability layer** for agent teams — "measuring whether the
   feature is working makes it easier to improve it." (same post)
3. **PM judgment is selective:** "identify the handful of true non-negotiables and let the rest
   go." (same post)
4. **Human review before anything customer-facing ships** — GTM CLAFTS tool: reps review every
   AI-drafted email; guardrails stress-tested adversarially.
   https://claude.com/blog/how-anthropic-uses-claude-gtm-engineering
5. **Workflows scale as packaged plugins** (Sales plugin → ~80% of the sales org).
6. **Anthropic ships a PM plugin** (`/write-spec`, `/roadmap-update`, `/stakeholder-update`,
   `/synthesize-research`…) framed as a thinking partner, not an autonomous decider; research
   synthesis requires supporting evidence. https://github.com/anthropics/knowledge-work-plugins
7. **Deterministic containment over trusting the model** — OS-level sandboxing; users approved
   ~93% of permission prompts (approval fatigue), so they moved to a classifier + contained
   environment. Audit is pull-based OTLP.
   https://www.anthropic.com/engineering/how-we-contain-claude
8. **Long-running agents verify against a written contract** — a feature list that starts
   "failing", "unacceptable to remove or edit tests", plus a human-readable
   `claude-progress.txt` trail so a fresh session picks up state.
   https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
9. **Tool design is a control surface** — unambiguous parameter names; validation failures as
   actionable messages, never tracebacks.
   https://www.anthropic.com/engineering/writing-tools-for-agents
10. **"Routines"** — cron/webhook/API-triggered agent jobs; PR routines keep one session per PR
    and feed it new events. https://claude.com/blog/introducing-routines-in-claude-code

## What pm-agent already embodies (submission narrative)

- 93% approval fatigue (finding 7) is the argument FOR act-then-revert + deterministic gates
  instead of per-action approval — cite it.
- The written-contract harness (finding 8) is our gates: verbatim evidence, id existence,
  roster, bands — non-negotiable, not advisory.
- Their PM plugin's evidence-required synthesis (finding 6) is our citation gate.
- Routines (finding 10) are our task-graph queue + Linear-webhook early resolution.

## Adopt now (decided)

- **Decision journal in the console** (finding 8's claude-progress.txt): a human-skimmable
  narrative of what the agent decided and why, rendered from the reasons/notes we already store.
  Folded into the Plan 4 console task.
- **Stakeholder-digest framing** for the report stage (finding 6) — the Slack-triggered report
  IS this pattern; name it so in the README.
- **Tools pass** (finding 9): already mostly true (status dicts, no tracebacks); quick review of
  parameter naming during Plan 4, no churn to live-tested signatures.

## Roadmap (README future work)

- First-class named routines (cron/webhook/API) replacing bespoke scheduling code.
- A classifier layer atop the rule gates for transcript prompt-injection (bogus/priority-inflated
  tickets).
- Published eval suite for filing/priority decisions (in progress — Plan 4).
- Pull-based audit export (OTLP pattern) for after-the-fact decision history.

## Quotes for the blog/submission (verify wording first)

- "When a product manager can go from idea to working prototype in an afternoon, the gap between
  'what if we tried…' and 'here, try this' nearly disappears." — Cat Wu, Anthropic
- "Users approved roughly 93% of permission prompts" — Anthropic engineering, on approval fatigue
- "It is unacceptable to remove or edit tests…" — Anthropic's own harness instruction

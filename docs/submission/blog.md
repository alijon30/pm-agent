# Blog post draft — publish before Sunday, tag #AllThingsAgenticHackathon

Suggested venues: dev.to / Medium / personal blog. Add 2–3 screenshots from `docs/media/`
and a link to the video once recorded. Social post templates at the bottom.

---

# I built a PM that never asks permission — and that's why you can trust it

I'm an engineer, and most of my tickets arrive broken: requirements that changed since the
call, no acceptance criteria, no business context. Reconstructing what a ticket means costs
more energy than building it. As a lead I have the mirror problem: no way to see the team's
progress without chasing people. The knowledge existed — someone said it out loud in a call —
and it evaporated before it reached the ticket. So for Google's All Things Agentic Hackathon I built
**pm-agent** — an autonomous product manager on Gemini 3.5, Google ADK, and Cloud Run — and I
made one decision early that shaped everything else:

**It never asks permission.**

That sounds reckless until you look at the data. Anthropic's engineering team measured what
per-action approval actually buys: users approved roughly **93% of permission prompts**.
Approval fatigue turns human oversight into a rubber stamp — you get the friction of a gate
with none of the safety. So where does trust live, if not in a prompt the human stopped
reading months ago?

Three places.

## 1. Determinism where it matters

Every model output passes through gates that are code, not vibes: every extracted decision
needs a verbatim quote from the transcript or it's dropped; every identifier the model
mentions is re-fetched from the source system or the write is refused; owners must exist in
the roster; a priority above its band needs an escalation quote; a sprint report claim
without a citation is removed by the gate, not by hoping the model was honest. A failed gate
gets exactly one retry with specific feedback, then an honest, logged drop.

My favourite eval run is the one that scored worst. Back-to-back runs exhausted the free-tier
quota mid-pipeline, judgment scores cratered — and the guarantees held anyway: zero fabricated
identifiers, 100% citation coverage, zero invalid plans. A starved pm-agent writes *nothing*.
It degrades to silence, never to lies. That's the property I'd want from a colleague.

## 2. Revert is cheaper than approve

Every action the agent takes is recorded *before* it happens — with an idempotency key and a
revert payload. Every Slack notification carries a revert button. The economics flip:
instead of a human paying attention N times a day so the agent can act, the human pays
attention only when something looks wrong — and fixing it is one click. Act-then-notify with
trivial undo beats ask-then-act with fatigued approval.

## 3. The agent schedules its own future — inside a fence

The part I expected to be exotic turned out to be the differentiator. When pm-agent files an
issue from a call, it also plans the follow-through: *check the issue is underway by Sep 1 →
then look for a PR by Sep 3 → then check it merged* — a real dependency graph in a Firestore
task queue, with declared consequences if a check comes back unmet. Good news travels fast:
when an engineer moved a ticket to In Progress four days early, a Linear webhook resolved the
pending check and unblocked its dependents in seconds. Nobody waits for a deadline to learn
things went well.

(For contrast: OpenAI's open-sourced internal orchestrator, Symphony, explicitly declines
dependency ordering and verification as out of scope. This is the gap pm-agent lives in.)

And because an agent that schedules its own work could talk itself into infinite employment,
the fence is deterministic too: plans are capped at depth 4 and 12 children, cycles are
rejected, and one task kind — intake — can never be self-scheduled, because an agent that
could schedule its own intakes could talk to itself.

## The part judges (and teammates) actually look at

The agent's work is a live timeline — time across, work down. Each column is a day, each row
a kind of work: heard, understood, did, watching, learned. Every call is a card with a
five-stage strip (read · triaged · reconciled · filed · planned) and everything it produced
lines up beneath it, so reading down a column is reading one call's story. A now line splits
what happened from what's scheduled; a replay scrubber plays it all from the first webhook; the
toolbar says what it's doing this second; and everything opens a story panel: click INV-26 and read
what the agent did about it and why, in plain sentences with timestamps. It's the audit log
wearing a good suit — and it's a self-contained page, no CDN, renders with the network down.

## Stack notes, briefly

Five ADK `LlmAgent`s on Gemini 3.5 with schema-enforced output (tip: if you combine
`output_schema` with tools, ADK routes the answer through an internal `set_model_response`
tool — don't let your tool guard block it). Gemma 4 (31B) triages transcripts and classifies
Slack intent — the failure posture is the design: triage fails open, intent defaults to
"help". Cloud Run + Firestore + Cloud Scheduler + Secret Manager. The queue is the
orchestrator; there is no workflow engine.

The demo company — Acme Invoicing, its codebase, roster, and call — is fully synthetic.
Everything else is real: the tickets, the webhooks, the 9:00 standup that fired this morning
without me.

*Built solo for the All Things Agentic Hackathon 2026, Taskmaster track.*
*Repo: github.com/alijon30/pm-agent · Live graph: pm-agent-999960779013.us-central1.run.app/console/graph*

---

## Social templates (#AllThingsAgenticHackathon)

**X/LinkedIn:**
> I built a product manager that never asks permission — and that's why you can trust it.
> Gemini 3.5 + ADK + a Firestore task graph that schedules its own follow-ups, deterministic
> gates instead of approval fatigue, and a timeline of its work that replays from the first call.
> #AllThingsAgenticHackathon
> [video/blog link]

**Short version:**
> The call ends. The cited tickets exist. The follow-ups scheduled themselves. The team just
> got told — with a revert button on every action. pm-agent, my #AllThingsAgenticHackathon
> entry: [link]

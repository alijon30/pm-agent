# Devpost submission draft

Paste-ready field by field. Upload `docs/media/architecture.png` as the architecture image
(Devpost does not render Mermaid) and `docs/media/graph.png` + `panel.png` as gallery shots. Submit **Sunday well before 5:00 PM PDT**. Make the repo public (or invite
testing@devpost.com and cloudhackathons@google.com) — the rules require repo access.
Keep the service and billing on until Oct 1 (judging period). Attach: repo link,
video link, live demo URL (`https://pm-agent-999960779013.us-central1.run.app/console/graph`).

## Project name

Autonomous PM Agent

## Elevator pitch (≤ ~200 chars)

A PM agent that acts without asking, safely. Every ticket traces to spoken words, every
follow-up schedules itself, every action reverts in one click.

## Inspiration

I'm an engineer. Most mornings I open a ticket that says something like "fix the news page"
and nothing else. No context, no acceptance criteria, requirements that changed since a call
nobody minuted. Reconstructing what the ticket actually means costs more energy than building
it. As a lead I have the opposite problem: I can't see where the team really is without
pinging everyone.

The annoying part is that all of this information existed. Someone said it out loud in a
meeting, and then it evaporated before it reached the ticket. So I built an agent that catches
it at the source.

I made one design bet up front: no approval prompts. Anthropic's engineers measured that
people approve about 93% of agent confirmation prompts, which means oversight decays into a
rubber stamp. This agent acts first, proves everything with citations, and makes undo one
click.

## What it does

A product call ends. Fathom fires a webhook, and pm-agent, which runs around the clock on
Cloud Run, does the PM's next two hours in about a minute:

- It reads the call. Every action item needs a verbatim quote behind it, or it gets dropped.
- It checks Linear, the docs and the actual codebase before filing anything. A re-raised issue
  becomes a note on the existing ticket instead of a duplicate.
- It files tickets I'd actually want to receive: why this matters, what was said (with who
  said it and when), acceptance criteria as checkboxes, and an Investigation section pointing
  at the file and line where the bug probably lives, with an honest confidence label.
- It schedules its own follow-through: a dependency-ordered chain of checks (underway by
  Tuesday, then a PR exists, then it landed), each with a date and a declared consequence.
  Bad news waits for its deadline. Good news doesn't: when an engineer drags a ticket to In
  Progress, the pending check resolves in seconds off the webhook.
- You can just talk to it in Slack. It reacts 👀 instantly, drops "On it…", and that same
  message turns into the answer. Tell it "from now on, assign frontend bugs to Priya" and it
  stores the rule with your message as the source, then cites that exact message the next
  time it applies the rule.
- Every action carries a one-click revert. That's the deal behind never asking permission.
- Everything it does is visible on a live timeline: time across, work down (heard,
  understood, did, watching, learned), with a replay scrubber and a plain-sentence story
  panel on every node.

It also posts a morning standup and writes sprint reports where every single claim carries a
citation. That's a gate, not a habit.

## How we built it

Five ADK LlmAgents on Gemini 3.5 through Vertex AI (extractor, reconciler, planner, reporter,
reviewer), with schema-enforced output and per-agent tool allowlists. Gemma rides along as a
second Google model, triaging transcript segments and classifying Slack intents through the
GenAI SDK.

The orchestrator is not a framework. It's a Firestore task graph: leases via transactions,
depends_on edges, retry with backoff, and plans that materialise atomically, so a plan is
never half-scheduled. Cloud Scheduler ticks it once a minute, webhooks short-circuit it the
moment reality moves, and Cloud Run scales the whole thing to zero between ticks.

Between every model output and every external effect sit deterministic gates: quotes must
exist in the transcript, identifiers are re-fetched before they may be cited, owners must be
on the roster, a priority only escalates if someone actually said escalation words, a date is
only set if someone actually spoke it, and daily caps plus quiet hours bound the blast
radius. GATES.md is generated from the code, so the documentation cannot drift from the
enforcement. Writes are intent-before-effect, with idempotency keys and stored revert
payloads. The timeline is self-contained vanilla JS with no CDN; it renders with the network
down.

## Challenges we ran into

Honestly, the biggest one was quotas, and it hit on deadline week. The free Gemini tier turned
out to allow 20 requests a day for the model I needed. I made a fresh API key and ran into AI
Studio's prepayment wall instead. I ended up moving all inference to Vertex AI so it just
bills the project, and weirdly I'm glad it happened, because the retry and backoff code I had
written "just in case" finally got tested for real.

Then the planner started breaking its own JSON on Vertex. Around 14,000 characters of plan
output, malformed, six runs in a row. I was sure the thinking budget was the culprit, turned
it off, and it broke again. So I stopped hunting the culprit and changed the rule instead: a
plan that doesn't parse now falls back to a boring deterministic follow-up chain, labelled as
such. The checks get scheduled either way, which is what actually matters.

ADK also has an internal tool called set_model_response that carries structured output. My
per-agent tool guard was blocking it, silently, so agents returned nothing at all while every
unit test stayed green. Only a live run caught it.

The one I didn't expect to be hard: making the agent sound like a person in Slack. The first
posts were painfully robotic, so tone became actual code, with tests. There's now a function
that knows "set up" is a phrasal verb, written the day the agent proudly announced "the up a
regression test".

Also, the first version of my timeline computed 4,736 pixels of day columns. No monitor fits
that. I keep the number around as a reminder.

## Accomplishments that we're proud of

Across six eval runs: 0 fabricated identifiers, 100% report citation coverage, 0 invalid
plans materialised. The runs I'm proudest of are the worst ones, the quota-starved ones where
judgment scores dropped, because every guarantee held anyway. The agent degrades to silence,
never to lies.

The whole loop is live-proven off real recorded calls against my real product. It caught a
re-raised issue and updated the existing ticket instead of filing a duplicate. Its
investigation sections point at the actual file and line. A scheduled check resolved four
days early, within seconds of a Linear webhook. Median time from call ended to tickets filed:
about a minute.

## What we learned

Autonomy is a trust-engineering problem, not a capability problem. The model was never the
bottleneck. The bet that paid off was moving trust out of the model entirely: give it
judgment, never authority. A model that writes JSON needs a deterministic floor under it. And
asking permission is not a safety mechanism when 93% of the answers are yes. Undo is.

## What's next for Autonomous PM Agent

More trackers (Jira, GitHub Issues) behind the same connector seam. Deeper PR awareness: it
already checks that pull requests exist, and next it should notice ones going stale. A brain
that spans projects, so a rule taught once holds everywhere. Lessons from the daily review
feeding prompts automatically instead of just advisorily. A prompt-injection screen ahead of
extraction, because transcripts are untrusted input. And human review for the rare class of
action where a revert isn't enough.

## Built with

`gemini-3.5` · `gemma` · `google-adk` · `genai-sdk` · `cloud-run` · `firestore` ·
`cloud-scheduler` · `secret-manager` · `python` · `fastapi` · `linear` · `slack` · `notion` ·
`fathom` · `svg`

## Links

- Repo: https://github.com/alijon30/pm-agent
- Live graph: https://pm-agent-999960779013.us-central1.run.app/console/graph
- Live console: https://pm-agent-999960779013.us-central1.run.app/console
- Demo target: InterviewPrepPro, the author's real product (trimmed source vendored in-repo)
- Video: (add Friday)
- Blog post: (add link when published — bonus)

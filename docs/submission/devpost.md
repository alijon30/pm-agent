# Devpost submission draft

Paste-ready field by field. Upload `docs/media/architecture.png` as the architecture image
(Devpost does not render Mermaid) and `docs/media/graph.png` + `panel.png` as gallery shots. Submit **Sunday well before 5:00 PM PDT**. Make the repo public (or invite
testing@devpost.com and cloudhackathons@google.com) — the rules require repo access.
Keep the service and billing on until Oct 1 (judging period). Attach: repo link,
video link, live demo URL (`https://pm-agent-999960779013.us-central1.run.app/console/graph`).

## Project name

Autonomous PM Agent

## Elevator pitch (≤ ~200 chars)

A PM agent that acts without asking — safely. Every ticket traces to spoken words, every
follow-up schedules itself, every action reverts in one click.

## Inspiration

I'm an engineer. Most mornings I open a ticket that says something like "fix the news page" —
and that's it. No context, no acceptance criteria, requirements that changed since a call
nobody minuted. Reconstructing what the ticket *means* costs more energy than building it. And
when I put on the lead hat I get the opposite problem: there's no way to see where the team
actually is without pinging everyone.

The annoying part is that all of that information existed. Someone said it out loud in a
meeting — and it evaporated before it reached the ticket. So I built an agent that catches it
at the source.

One design bet up front: **no approval prompts.** Anthropic's engineers measured that people
approve ~93% of agent confirmation prompts — oversight decays into a rubber stamp. This agent
acts first, proves everything with citations, and makes undo one click.

## What it does

A product call ends. Fathom fires a webhook, and pm-agent — running around the clock on Cloud
Run — does the PM's next two hours in about a minute:

- **It reads the call.** Every action item needs a verbatim quote behind it, or it's dropped.
- **It checks before it files** — against Linear, the docs and the actual codebase. A
  re-raised issue becomes a note on the existing ticket, not a duplicate.
- **It files tickets I'd actually want to receive**: why this matters, what was said (with who
  said it and when), acceptance criteria as checkboxes, and an Investigation section pointing
  at the file and line where the bug probably lives, with an honest confidence label.
- **It schedules its own follow-through**: a dependency-ordered chain of checks — underway by
  Tuesday, then a PR exists, then it landed — each with a date and a declared consequence. Bad
  news waits for its deadline; good news doesn't. An engineer dragging a ticket to In Progress
  resolves the pending check in seconds, off the webhook.
- **You can just talk to it in Slack.** It reacts 👀 instantly, drops "On it…", and that same
  message becomes the answer. Tell it "from now on, assign frontend bugs to Priya" and it
  stores the rule with your message as the source — then cites that exact message the next
  time it applies it.
- **Every action carries a one-click revert.** That's the deal behind never asking permission.
- **Everything it does is visible** on a live timeline — time across, work down (heard ·
  understood · did · watching · learned), with a replay scrubber and a plain-sentence story
  panel on every node.

It also posts a morning standup and writes sprint reports where every claim carries a
citation. All of them. It's a gate, not a habit.

## How we built it

Five ADK `LlmAgent`s on **Gemini 3.5 through Vertex AI** — extractor, reconciler, planner,
reporter, reviewer — with schema-enforced output and per-agent tool allowlists. **Gemma** rides
along as a second Google model, triaging transcript segments and classifying Slack intents
through the GenAI SDK.

The orchestrator is not a framework. It's a **Firestore task graph**: leases via transactions,
`depends_on` edges, retry with backoff, and plans that materialise atomically — a plan is
never half-scheduled. **Cloud Scheduler** ticks it once a minute; webhooks short-circuit it
the moment reality moves; **Cloud Run** scales the whole thing to zero between ticks.

Between every model output and every external effect sit **deterministic gates**: quotes must
exist in the transcript, identifiers are re-fetched before they may be cited, owners must be
on the roster, a priority only escalates if someone actually said escalation words, a date is
only set if someone actually spoke it, and daily caps plus quiet hours bound the blast radius.
GATES.md is generated from the code, so the documentation cannot drift from the enforcement.
Writes are intent-before-effect with idempotency keys and stored revert payloads. The timeline
is self-contained vanilla JS — no CDN, renders with the network down.

## Challenges we ran into

**The quota maze, on deadline week.** The free tier allows 20 requests a day against the model
I needed; the replacement key ran into AI Studio's prepayment gate. The fix was moving
inference to Vertex AI — same models, billed to the project — and the retry-with-backoff
design got a very real test along the way.

**The planner that broke its own JSON.** On Vertex it started hand-writing ~14,000 characters
of plan JSON and malforming it — six runs in a row. I blamed the thinking budget, turned it
off, and it broke anyway. The real fix wasn't finding the culprit; it was refusing to let a
parse error decide the outcome: an unusable plan now falls back to a deterministic follow-up
chain, honestly labelled. The commitment still gets watched.

**ADK's invisible tool.** Structured output arrives through an internal tool called
`set_model_response` — my per-agent tool guard silently blocked it, producing perfectly empty
responses that only a live test caught.

**Making it sound human.** The first Slack posts were robotic, so the voice became code: a
layer that says "Priya" instead of "the assignee", spells small numbers, and knows a phrasal
verb from a preposition — built the day it announced "the up a regression test". The tone is
enforced by tests now.

**And one humbling layout bug**: the first version of the timeline computed 4,736 pixels of
day columns. There is no monitor on earth it fit.

## Accomplishments that we're proud of

Across six eval runs: **0 fabricated identifiers, 100% report citation coverage, 0 invalid
plans materialised.** The runs I'm proudest of are the worst ones — quota-starved, judgment
scores down — because every guarantee held anyway. The agent degrades to silence, never to
lies.

The whole loop is live-proven off real recorded calls against my real product: it caught a
re-raised issue and updated the existing ticket instead of filing a duplicate, its
investigation sections point at the actual file and line, and a scheduled check resolved four
days early within seconds of a Linear webhook. Median time from call ended to tickets filed:
about a minute.

## What we learned

Autonomy is a trust-engineering problem, not a capability problem. The model was never the
bottleneck; the bet that paid was moving trust out of the model entirely — give it judgment,
never authority. A model that writes JSON needs a deterministic floor under it. And "ask
permission" is not a safety mechanism when 93% of the answers are yes — undo is.

## What's next for Autonomous PM Agent

More trackers (Jira, GitHub Issues) behind the same connector seam. Deeper PR awareness — it
already checks that pull requests exist; next it should notice ones going stale. A brain that
spans projects, so a rule taught once holds everywhere. The daily review's lessons feeding
prompts automatically instead of advisorily. A prompt-injection screen ahead of extraction,
because transcripts are untrusted input. And human-review states for the rare class of action
where revert isn't enough.

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

# Demo video — script

About four minutes, one take, unedited. Two screens: the browser (tabs in order: Slack ·
Linear board · graph · console · GCP console) and a terminal for the one command. The
narration below is written the way you'd actually say it — don't read it, tell it. If your
words are better, use yours.

Pre-flight is in `docs/demo-runbook.md`; the clickable tab kit (live pages + GCP
console links) is on the Recording Desk artifact. One rule: the clock stays on screen. Everything
this agent does in "about a minute" has to be *visibly* about a minute.

---

## 0:00 — Why I built this (Linear board, or any real half-empty ticket)

> Quick story before the demo. I'm an engineer. Most mornings I open a ticket that says
> something like "fix the news page" — and that's it. No context, no acceptance criteria,
> nobody remembers what was decided on the call. I burn an hour reconstructing what the
> ticket means before I write a single line of code. And when I put on the lead hat I get
> the opposite problem — I can't tell where the team actually is without pinging everyone.
>
> Here's the annoying part: all of that information existed. Someone said it out loud in a
> meeting. It just evaporated before it reached the ticket.
>
> So I built an agent that catches it at the source. This is the Autonomous PM Agent. It
> listens to our calls and does the PM work itself. And one weird design choice up front:
> it never asks for approval. I know how that sounds — stay with me, that's kind of the
> whole demo.

## 0:40 — The world (Slack + Linear + the empty graph)

> Real quick, the setup. This is InterviewPrepPro — an actual product of mine. Real
> codebase, real backlog in Linear. The team talks here in Slack, and the agent lives in
> the channel too. It runs on Cloud Run with a one-minute heartbeat.
>
> And this is the agent's timeline — completely empty. It hasn't heard a single call yet.
> Keep this page in mind, because in the next three minutes it's going to fill itself in,
> live, and everything on it will be traceable back to words somebody actually said.

## 0:55 — A call just ended (terminal, then Slack)

> So — the team just finished a two-minute huddle. Tom found that the "related articles"
> section recommends the wrong articles, and the partner demo is tomorrow morning. In real
> life Fathom fires a webhook the moment a call ends. I'm going to send that exact payload
> by hand, so you can watch it happen live.

Run:

```
uv run --env-file .env python scripts/send_call.py \
  fixtures/transcripts/08-ipp-related-news-huddle.md \
  --title "Related articles huddle" \
  --recording-id demo_take1 \
  --roster fixtures/roster.json \
  --url https://pm-agent-999960779013.us-central1.run.app/webhooks/fathom
```

The `--url` line matters on camera: the payload visibly goes to the Cloud Run address.

Switch to Slack. A status message appears carrying the agent's four-step plan, and it ticks
itself off as the work happens.

> There it is — it just posted its plan. Read the call, check it against Linear and the
> code, file what was agreed, set up the follow-through. And watch it tick the steps off as
> it goes — each one gets a little note about what it found.

## 1:15 — Teach it something while it works (Slack)

Type in the channel: `@pm-agent from now on, assign frontend bugs to Priya`

It reacts 👀 instantly, drops *"✻ On it…"* in the thread — and that same message becomes:
*"Noted — frontend bugs go to Priya from now on."*

> While it's busy — you can just talk to it. "From now on, assign frontend bugs to Priya."
> …and, "Noted." That's not a settings page. It stored who said that and where, and the
> next time a call mentions a frontend bug with no owner, it proposes Priya and cites this
> exact message as its reason.

## 1:35 — Meanwhile, in Google Cloud (GCP console)

Flip to the GCP tabs: the Cloud Run service, then the Firestore `tasks` collection.
Refresh the collection once so a new task document appears on camera.

> And while it's working — here's what's actually running. This is Cloud Run: the agent was
> asleep at zero instances until the webhook woke it up. And this is Firestore — every step
> you're watching in Slack is literally a task document in this collection: extract, then
> reconcile, then act, then plan, each one waiting on the one before it. There's no
> orchestration framework in this project — the queue is the orchestrator. And Cloud
> Scheduler pokes it once a minute. That's the heartbeat.

## 2:00 — The ticket (Slack summary → Linear)

The summary lands. Open the new ticket in Linear and take your time with it.

> Summary's in — one new ticket, marked urgent. Let's open it, because honestly, this is
> the ticket I always wished someone had written for me.
>
> Look what's in here. Why this matters — partner demo tomorrow, news section is the first
> thing we show. What was actually said — real quotes, each with who said it and when.
> Acceptance criteria as checkboxes — pulled from what Priya committed to, not made up.
> And my favorite part — the Investigation. The agent searched the actual codebase, and
> it's pointing at the exact filter causing this bug. File and line. With an honest
> confidence label.
>
> And the stuff you *can't* see is my favorite-favorite part: the gates. The owner has to
> exist on the roster — it can't invent people. The priority only got raised because Tom
> literally said "this is urgent" — no escalation words in the transcript, no escalation in
> the ticket. The due date exists because Priya said "by tomorrow." If the agent can't
> prove a claim, the claim doesn't ship.

## 2:45 — It schedules its own future (Slack thread)

Open the follow-through post in the thread.

> Then it did something I haven't seen an orchestrator do — it planned its own follow-up.
> Tomorrow: is the ticket underway? If not, it checks in with Priya. After that: is there a
> PR? Then: did it land? Every check has a date and a consequence, and they wait on each
> other — it won't look for a PR on a ticket nobody started.

Ask for one yourself: `@pm-agent keep an eye on INV-41 until Wednesday`

👀, then *"✻ On it…"* — which becomes the dated checks.

> And you can just ask for your own. "Keep an eye on INV-41 until Wednesday." There —
> dated checks, in the thread, with what it'll do if they fail.

Point at a revert button on the summary.

> One more thing. See this revert button? Every action it takes carries one. That's the
> deal behind "never asks permission" — it doesn't have to ask, because undo is one click.

## 3:10 — Good news travels fast (Linear → graph)

Drag the new ticket to **In Progress**, then jump to the graph tab.

> Now watch what happens when reality moves. I'm the engineer, I just started the work —
> drag it to In Progress. Over on the timeline… there. The check it had scheduled for
> tomorrow just resolved itself early, off the webhook, and the PR check behind it
> unblocked. Bad news waits for its deadline. Good news doesn't wait at all.

## 3:25 — The timeline (graph, full screen)

Hit **Replay**, let it rebuild, then click the new ticket (replay pauses).

> Remember when this page was empty four minutes ago? Time goes across, the kind of work
> goes down — what it heard, what it understood, what it did, what it's watching. Hit
> replay and it rebuilds everything you just watched from the first event. And you can
> click anything — it tells you what it did about that thing and why, in plain sentences.
> It's an audit log, it's just one you'd actually read.

## 3:45 — The brains (Vertex AI → README)

Vertex AI console, then the README guarantees table.

> Back to the cloud for the part I skipped — the brains. Five ADK agents on Gemini 3.5,
> running through Vertex AI: extraction, reconciliation, planning, reporting, review. Plus
> Gemma for triage — two Google models, one bill.
>
> And some numbers, because "trust me" isn't a demo: across every eval run — zero fabricated
> identifiers, one hundred percent citation coverage, zero invalid plans. On its worst,
> quota-starved runs it wrote nothing at all. It degrades to silence — never to lies.

## 4:05 — Close (graph)

> So that's the Autonomous PM Agent. The ticket I always wanted to receive, the team
> overview I always wanted as a lead — and nobody had to babysit it. It acts on its own,
> everything it does can be undone in a click, and it can always, always show its work.
> Thanks for watching.

Hold on the graph for two seconds. Stop.

---

## If something goes wrong on camera

- **Webhook slow:** say "it wakes up every minute — there's the heartbeat" and let the
  clock run. Honest waiting beats a cut.
- **Rate limited:** the status message shows the retry. "It tells you when it's waiting" —
  that's the honesty story landing on its own.
- **Nothing filed:** "that's a drop, not a fabrication" — fire the call again with a new
  recording id. Take two is allowed; a lie is not.
- **Graph sparse:** hit Replay. The story building from nothing beats a full graph
  standing still.

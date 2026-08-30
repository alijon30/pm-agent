# Demo video — script

Four minutes, one take, unedited. Two screens: the browser (tabs pre-opened in order: Slack ·
Linear board · graph · console · GCP console) and a terminal for the one command. Narration is
written to be spoken, not read — keep the rhythm, change the words if yours are better.

Pre-flight is in `docs/demo-runbook.md`. The clock on screen is the point: every "seconds later"
below must be visible as seconds.

---

## 0:00 — The claim (Slack channel, quiet)

> This is pm-agent — an autonomous product manager. It runs around the clock on Cloud Run, and
> it never asks permission. That sounds reckless, so let me show you why it's the safest design
> in the room.

## 0:20 — The call ends (terminal, then Slack)

Run: `uv run --env-file .env python scripts/send_call.py fixtures/transcripts/03-pdf-incident-huddle.md --title "PDF incident huddle" --recording-id demo_<date>`

> A product call just ended. In real life this is Fathom's webhook; today I'm firing the same
> payload by hand so you can see the clock.

Switch to Slack. The status line appears: *Reading "PDF incident huddle"…* — then edits in
place within a minute or so.

> Watch that message. It's editing itself as the agent works — reading, reconciling against
> Linear and the codebase, filing.

When the summary lands, read it aloud, slowly:

> "One new ticket, marked urgent — somebody said so on the call." Every claim you're reading
> was checked before it was allowed to be said: the quote exists in the transcript, the owner
> exists on the roster, the priority needed an escalation word — and there's a revert button.

## 1:10 — The ticket (Linear)

Switch to Linear, open INV-3x.

> Here's the ticket. Owner from the roster — never invented. Priority 1 because Maya said
> "this is urgent" and "a blocker" — the gate found those words; without them this would have
> been clamped to normal and the message would have said so. Due date from "this week" — the
> agent only sets dates someone actually spoke.

Scroll to the description footer.

> And the citation back to the moment in the call. The agent cannot write a reference it didn't
> re-fetch. Zero fabricated identifiers across every eval run — that's a gate, not a hope.

## 1:45 — The plan (Slack thread)

Back to Slack; open the follow-through post.

> Now the part no orchestrator I know of does: it scheduled its own future. "Tomorrow — check
> INV-3x is underway; if not, I'll check in with Nodir." A dependency graph of checks, each
> with a declared consequence. A lineage gate caps how much work it can give itself.

## 2:05 — The reaction (Linear → Slack → graph)

In Linear, drag INV-26 (or the new ticket) to **In Progress**. Switch to the graph tab
immediately.

> An engineer just moved a ticket. Good news travels fast — watch the Now dock.

Within seconds the check resolves; the thread note posts; the Now dock updates.

> The Sep 1 check just resolved itself four days early off the Linear webhook, and the PR check
> behind it unblocked. Bad news waits for its deadline; good news doesn't wait at all.

## 2:35 — The graph (full screen)

Hit **Replay**.

> This is the agent's world — every call, decision, ticket, person, check and lesson, replayed
> from the first event.

Let it run ~15 seconds; click the INV-26 node mid-replay (replay pauses).

> Click anything and it tells you what it did about it and why, in plain sentences, with
> timestamps. This is the audit log — it just dresses well.

Point at the Now dock.

> And this is what it's doing right now, what wakes next, and what it's waiting on. Nothing on
> this page is a second source of truth; it's all derived from the same records.

## 3:20 — The proof (GCP console + README)

GCP tab: Cloud Run service → Firestore collections → Scheduler jobs, five seconds each.

> Gemini 3.5 through ADK for the five reasoning agents; Gemma for triage. Cloud Run, Firestore
> as the task graph, Cloud Scheduler as the heartbeat, Secret Manager for every credential.

README tab, scroll to the guarantees table.

> Across every eval run: zero fabricated identifiers, one hundred percent citation coverage,
> zero invalid plans. Our worst run was quota-starved and scored badly on judgment — and the
> guarantees held anyway. A starved pm-agent writes nothing. It degrades to silence, never to
> lies.

## 3:50 — Close (graph tab)

> Autonomy isn't a capability problem. It's a trust-engineering problem — and trust lives in
> the gates, not in the model. pm-agent: it acts, you can always undo, and it can always show
> its work.

Hold on the graph for two seconds. Stop.

---

## If something goes wrong on camera

- **Webhook slow:** narrate the Now dock — "it wakes every minute" — and let the clock run; it
  is more honest than a cut.
- **Rate limited:** the status message shows the retry; say "this is the honesty story — it
  tells you when it's waiting." Let it land.
- **Model flake (nothing filed):** say so — "that's a drop, not a fabrication" — and fire the
  call again with a new recording id. Take two is allowed; a lie is not.
- **Graph sparse:** Replay is always more compelling than a still graph.

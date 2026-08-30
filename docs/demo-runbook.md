# Demo runbook — recording day

The video is 4 minutes, unedited, one take that can be re-taken. The agent does real work
against real services on camera; this file is the flight plan and the parachutes.

## The night before

- [ ] **Turn billing on** (or verify quota headroom). The one bad eval run (15/26) was
  free-tier starvation: 5 RPM on flash strangled the pipeline mid-flight. It degraded honestly
  — but a demo that says nothing is still a failed demo. Recording day is not the day for
  free-tier quota.
- [ ] **Freeze deploys.** The last deploy happens the night before, verified. If something
  must ship on recording day, remember: if the deploy hangs after "Uploading sources… done",
  the us-central1 build queue is jammed — the us-east1 detour is in `deploy/secrets.md`.
- [ ] **Verify the service is healthy**: `/health` returns ok; `/console` and `/console/graph`
  render; the toolbar status shows the queue honestly.
- [ ] **Verify integrations**: Slack posts arrive in the channel (reinstall done, reactions
  working); Linear webhook fires (move any archive-probe issue and watch the event doc);
  Fathom webhook destination is set.
- [ ] **Stage the fixture state**: sprint dates current in `fixtures/projects/acme.json`;
  roster seeded; the two dummy Linear members visible; archive-probe issues INV-20..24
  archived so the board is clean.
- [ ] **Pre-open browser tabs**, in order: Slack channel · Linear board · the graph ·
  the console · GCP console (Cloud Run + Firestore + Scheduler, to show the stack).
- [ ] **Do one full off-camera rehearsal** with a throwaway call recording. If the rehearsal
  worked, change nothing afterwards.

## The 4 minutes

| Time | Beat | On screen |
|---|---|---|
| 0:00–0:25 | The claim: "a PM agent that acts, doesn't ask" — one sentence on act-then-revert + gates | Title/README hero, then Slack channel |
| 0:25–1:10 | **The call.** End the (pre-recorded) Fathom call → webhook fires → Slack: extract summary posts with revert buttons; Linear: cited issues appear with owners and priorities | Slack + Linear split |
| 1:10–1:50 | **The plan.** Show the follow-up announcement: the dependency chain in words ("check underway Sep 1 → then look for a PR Sep 3"), each with its if-unmet promise | Slack thread |
| 1:50–2:30 | **The reaction.** Move an issue to In Progress in Linear on camera → seconds later the check resolves early, the dependent unblocks, the thread gets the good-news note | Linear + Slack |
| 2:30–3:20 | **The graph.** Open `/console/graph`: hit Replay and narrate the timeline building column by column; pause on INV-26, open its story panel and read the agent's reasoning aloud; point at the toolbar status ("this is what it's doing right now") and at the Scheduled columns ("this is its plan") | The graph, full screen |
| 3:20–3:50 | **The proof.** GCP console flash (Cloud Run, Firestore, Scheduler); eval numbers: 0 fabricated identifiers, 100% citation coverage, invalid plans 0, across six runs | GCP console + README table |
| 3:50–4:00 | Close: stack recap (Gemini 3.5 + ADK + Gemma + Cloud Run) and the URL | README |

## Parachutes

- **The webhook doesn't fire** → the tick will drain it within a minute; narrate the toolbar status
  while waiting ("it wakes every minute"). If two minutes pass, replay the event: re-send from
  Fathom's webhook log, or `X-Tick` manually.
- **Rate limited on camera** → the status message edits in place with the retry state; that IS
  the honesty story — narrate it and let the retry land.
- **Slack is down / channel broken** → the console journal shows every action with the same
  words; pivot: "Slack is one surface; the journal is the record."
- **The graph looks sparse** → hit Replay; the story building from nothing is more compelling
  than a full graph standing still.
- **Total service failure** → previous take, or the recorded rehearsal. An unedited take of a
  real system is the requirement; a second take is not a crime.

## Still owed by a human (before recording)

- [ ] Slack app **reinstalled** with `reactions:write` (manifest updated — needs reinstall to take)
- [ ] **Notion integration token** shared with the 3 pages (Reminders PRD, Invoice Export spec, process doc) → `PM_NOTION_TOKEN`
- [ ] **GitHub fine-grained PAT** for `alijon30/acme-invoicing` (Contents: Read, Pull requests: Read) → `PM_GITHUB_TOKEN`, `PM_GITHUB_REPO=alijon30/acme-invoicing`
- [ ] **Two dummy Linear members** invited so assignees render with faces
- [ ] **The final two-voice call recording** of `fixtures/transcripts/01-q3-planning.md` in Fathom

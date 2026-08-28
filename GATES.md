# Gates

Every judgement this agent makes is a model's output, and no model output reaches
Linear, Slack or the queue without passing the deterministic checks below. Each gate is
ordinary Python with no model in it: it either finds the quote in the transcript or it
does not, either re-fetches the identifier or it does not. A gate that refuses gives the
model **one** retry with the specific failure, and a second refusal drops the item and
records the drop. Nothing here fails silently, and nothing here can be talked past.

This file is generated from the code it describes by `scripts/gen_gates.py`; the catalog, the
limits and the descriptions are read out of the modules at generation time so the
document cannot drift from the system. Regenerate with:

```
uv run python scripts/gen_gates.py
```

`tests/test_gates_doc.py` fails if this file and the code disagree.

## What the agent may do

The whole of it. A kind that is not in this table cannot be scheduled, executed or
named by any model in the system — the catalog is a whitelist, not a suggestion.

| kind | what it does | params | schedulable | on unmet |
| --- | --- | --- | --- | --- |
| `check_issue_state` | Is the issue in one of the expected states? | `issue`, `expect` | yes | `nudge_assignee`, `escalate_channel`, `ping_requester` |
| `check_pr_exists` | Does a pull request reference the issue? | `issue` | yes | `nudge_assignee`, `ping_requester` |
| `check_pr_reviewed` | Has the pull request received at least one review? | `issue?`, `pr?` | yes | `nudge_reviewer`, `ping_requester` |
| `check_pr_merged` | Is the pull request merged? | `issue?`, `pr?` | yes | `nudge_assignee`, `escalate_channel`, `ping_requester` |
| `nudge` | Send one templated nudge to a person about something. | `person`, `about`, `template` | yes | — |
| `escalate` | Post one templated escalation to the project channel. | `about`, `template` | yes — but no executor is registered | — |
| `reconcile_item` | Re-run reconciliation for one action item. | `item` | yes — but no executor is registered | — |
| `daily_review` | Gather the project's state and plan the day. | `project` | yes | — |
| `report` | Write a status report for the project. | `project`, `window?` | yes | — |
| `intake` | Turn one teammate's request into scheduled work, or stop work they asked to stop. | `text?`, `cancel?` | no — an agent that could schedule its own intakes could talk to itself | — |

## The gates

### Evidence — did anyone actually say this?

The evidence gate: an extracted item survives only if at least one of its quotes appears verbatim in the transcript. This single rule removes most hallucinated action items.

- **minimum quote length** — 12 characters after normalisation

### Identifiers — does the thing it named exist?

The identifier gate: nothing the agent writes may name something that does not exist.

Every citation is a typed reference and every reference is re-fetched from the system that owns it before the claim carrying it may ship:

```
linear:INV-142                 an issue
notion:<page_id>               a page
fathom:<meeting_id>@<mm:ss>    a moment in a call
code:<path>:<line>             a line in the repo
decision:<id>                  an entry in the decision ledger
wiki:<slug>                    a page in the company brain
```

This is the single most important gate in the system: a plausible-looking ticket id in a Linear comment is how an agent quietly destroys a team's trust.

- **reference kinds** — `linear:`, `notion:`, `fathom:`, `code:`, `decision:`, `wiki:`
- **issue keys must match** — `^[A-Z][A-Z0-9]*-\d+$`

### Roster — is that a real person on this project?

Who may be assigned. The model proposes a name; this decides whether that name is a real person on this project. An unknown name is never guessed at — the issue ships unassigned with the spoken name quoted, which is the honest outcome.

- **matching** — Exact, alias, then first-name match, all case-insensitive. None when nothing matches or when a first name is ambiguous across two people.

### Priority — may it call its own work urgent?

How urgent the agent may say something is.

Linear's scale is 0 none, 1 urgent, 2 high, 3 medium, 4 low — lower is more urgent. The project policy sets a band the agent may assign freely; leaving that band upward requires someone to have actually said an escalation word, quoted verbatim. Without that the priority is clamped, never silently accepted: an agent that can mark its own work urgent stops being trustworthy.

- **band the shipped project allows** — 2 to 4 (1 urgent … 4 low)
- **escalation phrases** — `urgent`, `blocker`, `blocked`, `p0`, `asap`

### Dates — did somebody promise this day?

When something is due.

A due date is a commitment, so the agent may only set one that a human actually spoke. That needs two things to agree: a resolved ISO date from reconcile, and a `due_hint` — the words as said — that appears verbatim in the evidence. Either alone is a guess.

- **accepted date shape** — `^\d{4}-\d{2}-\d{2}$`

### Caps — how much, and at what hour?

How much the agent may do in a day, and when it may interrupt people.

Writes and pings are counted separately because they cost differently: a wrong ticket is noise in a backlog, a wrong ping is noise in someone's evening. Exceeding a cap defers work to the next window and records why — nothing is ever dropped silently.

- **writes per day** — 40
- **interruptions per day** — 10
- **quiet hours** — 20:00 to 08:00 (default 20:00–08:00)
- **the one exemption** — `respect_quiet_hours=False` is for the one message whose whole point is its hour: the morning standup is scheduled for the start of the working day and must not be deferred to it. The daily budget still applies — an exemption from the clock is not an exemption from the cap.

### Lineage — can it give itself unbounded work?

Structural loop prevention. Every enqueue passes here; a chain cannot exceed max_depth and a task cannot fan out beyond max_children, so a runaway agent is impossible rather than unlikely. Plan generations count as depth: a planner that keeps planning follow-ups to its follow-ups stops at the limit and says so.

- **`max_depth`** — 4
- **`max_children`** — 12

### Plan — is what it scheduled for itself real?

The plan gate: what the agent proposes to do to itself, checked before it can.

A plan is the one place the model reaches into the future, so this is where a bad idea is cheapest to stop. Known kinds, valid params, unique keys, dependencies that resolve, no cycles, due times inside the horizon, real identifiers, and a size the project can absorb.

Rejection is per-task where it can be — one bad check should not lose a good plan — but a cycle rejects everything, because a graph that cannot be ordered cannot be partially trusted.

- **identifier-bearing params** — `issue`, `person`
- **dependency-failure policies** — `skip`, `run_anyway`, `cancel`
- **grace for a due time just passed** — 5 minutes
- **actions a check may take** — `none`, `nudge_assignee`, `nudge_reviewer`, `escalate_channel`, `ping_requester`

### Citations — can every claim be re-opened?

The citation gate: a claim ships only if something the agent can re-open supports it.

A status report is read, believed and forwarded. Nobody checks it, so nothing in it may be unverifiable: every claim must carry at least one reference, and every reference is re-fetched from the system that owns it (see verify/ids.py). Claims that fail are removed rather than softened — an agent that hedges an invented ticket number has still invented it — and the removal is reported, so a thin report is visibly thin instead of quietly wrong.

A source outage is not a fake citation. SourceUnavailable propagates out of this gate so the stage can fail and retry, rather than deleting a real claim because Linear was down.

## Failure posture

- **One bounce, then an honest drop.** A gate that refuses hands the model the specific
  reason and asks once more. A second failure removes the item and the removal is
  reported — in the Slack summary, in the task result, and on the console.
- **An outage is not a verdict.** A source that cannot be reached makes an item
  `unverified` rather than false, and the task re-enqueues itself once for +30
  minutes. The model is never asked to infer what a tool would have said.
- **Retries back off** on 60s, 300s, 900s and then the task is marked failed. Work somebody
  asked for says so in their thread instead of disappearing.
- **Intent before effect.** Every write is recorded as `pending` with a deterministic
  idempotency key before it happens and marked `done` after, carrying the payload that
  undoes it. A crash between the two is recoverable; revert is data, not a code path.
- **Caps defer, they never drop.** Work held back by a cap or by quiet hours is
  rescheduled with the reason recorded, and re-observes reality when it runs.
- **Memory is bounded.** The agent keeps at most 12 lessons about its own
  behaviour, each citing the tasks and actions it was drawn from; a lesson whose
  evidence is not in that day's record is discarded before it is ever stored.

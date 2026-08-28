# Sprint 1 kickoff sync — Acme Invoicing

Second fixture call. Two voices are enough (one reads Maya + Tom, one reads Nodir + Priya);
speaker names matter, exact phrasing of the **planted moments** matters, filler can drift.

Planted moments the agent must catch:

1. **Decision** — the late-fee grace period drops from five days to three.
2. **Urgent bug with an escalation quote** — duplicate reminder emails; "this is a blocker"
   must be said out loud (priority gate needs the spoken escalation to leave the band).
3. **Rejected option** — pausing all reminders while the bug is fixed: considered, refused.
4. **Cross-call reference** — Priya reports INV-26 (CSV export) in progress, PR expected
   Monday. The agent must link this to the existing issue, not file a duplicate.
5. **Spoken dates** — Maya "by Monday", Tom "by Wednesday". The dates gate needs the words.

---

[00:04] Maya Chen: Okay, quick kickoff for Sprint one, we've got the board from Tuesday's
planning call so let's keep this short.

[00:15] Tom Alvarez: Before we start — I need to flag something from support. Since last
night we've had eleven tickets about customers getting the same payment reminder email two,
sometimes three times.

[00:31] Nodir Rahimov: The same reminder? Not different templates?

[00:36] Tom Alvarez: Identical. Same invoice, same email, minutes apart. Customers think we're
chasing them. Honestly this is a blocker, customers are getting spammed and two of them
threatened to cancel this morning.

[00:52] Maya Chen: Okay, that jumps the queue. Nodir, can you own the duplicate reminder
emails bug? Drop the retry work until it's fixed.

[01:03] Nodir Rahimov: Yes. My guess is the reminder job double-fires when a send times out —
the timeout path doesn't mark the invoice as reminded. I'll take it today.

[01:14] Maya Chen: Good. While we're on reminders — should we just pause all reminder sends
until the fix lands? Tom raised that in the ticket thread.

[01:25] Nodir Rahimov: I'd rather not. We're not switching off reminders entirely, that's
revenue — overdue collection drops the moment we go quiet.

[01:36] Maya Chen: Agreed, reminders stay on, we fix in place. Decision made.

[01:43] Maya Chen: Next thing. Finance signed off yesterday: the late-fee grace period drops
from five days to three days, starting with September invoices.

[01:55] Nodir Rahimov: Just the config, or the copy too?

[01:59] Maya Chen: Both — the grace period constant, and the reminder email copy that mentions
five days. That can ride behind the same flag as the cadence change.

[02:10] Nodir Rahimov: Fine, I'll pick that up after the duplicate fix, it's a small change.

[02:16] Maya Chen: And I owe finance the customer comms for the grace period change — I'll
draft the customer announcement for the new three-day grace period by Monday.

[02:28] Tom Alvarez: When the fix ships I want to make it right with the people we spammed.
I'll audit which customers received duplicate reminders and follow up with each of them by
Wednesday.

[02:41] Maya Chen: Perfect. Priya, where's the CSV export?

[02:46] Priya Nair: In progress, going well. The export behind the flag is done locally, I'm
writing tests now — pull request should be up Monday.

[02:56] Maya Chen: So INV-26 stays on track for the sprint. Anything blocking you?

[03:01] Priya Nair: Nothing blocking. If the reminder fix touches the invoice model I want a
heads-up, that's all.

[03:08] Nodir Rahimov: It won't, it's all in the job runner.

[03:12] Maya Chen: Great. So: Nodir on the duplicate emails first, then the grace period
change. I do the comms draft by Monday. Tom audits affected customers by Wednesday. Priya
lands the export PR Monday. Let's move.

[03:26] Tom Alvarez: Thanks all.

# Architecture review — Acme Invoicing

Fifth fixture call, adapted from the shape of a real weekly architecture review (names, products
and customers replaced; trimmed from ~54 minutes to the two debates that matter). Its value: a
lead re-scoping a project live into three problem statements, and a technical proposal that gets
approved with the ownership question left open — the kind of "decided, but who owns it?" moment
a PM agent should catch.

Roster voices: Maya Chen (leads the review, plays product), Nodir Rahimov (backend, presents the
denormalization proposal), Priya Nair (presents the payouts design), Tom Alvarez (ops/finance
questions). Non-roster: Omar (platform lead), Sam (finance stakeholder).

Planted moments:

1. **Decision (re-scope)** — the payouts project is de-scoped to three problems: per-employee
   payroll reporting, finer payable categories, and accrual posting by settlement date. Manual
   payroll entry is out of scope.
2. **Decision (approved proposal)** — denormalized fields move to Postgres triggers, rolled out
   in waves, starting with customer and contact full names.
3. **Open question / no owner** — who owns the rollout across teams; "the ownership has to come
   from you."
4. **Action items with owners** — Priya updates the technical design after re-scoping; Nodir
   implements wave one and backfills all tenants; Omar runs a bulk-import performance test.
5. **Spoken constraint** — "we can't run this during business hours" is NOT in this call; no
   dates are spoken at all, so no due dates may be set.

---

[01:13] Maya Chen: Where is everybody? Thirteen people. Is that all? All right. Who's got topics for today? Priya?

[02:35] Priya Nair: Yeah. We are planning to implement payouts as a feature in Acme Ledger. There was no such feature before. I have a rough design, I talked with the billing team about how their settlements are structured, and I wrote a small document about my plan and want feedback. What I think of payouts is a payment to staff — the company's contractors, W2 and 1099. Let's start from the batch. It's a payout batch for a selected period and selected staff members, and each staff member has one settlement. The batch and the settlement store no amounts, they're all metadata and statuses. The core is the lines — earnings, deductions, other pays, withholdings. I abstracted it so it's one table with a type, and we show it grouped by type. Any questions?

[06:05] Maya Chen: I definitely have questions. Is there not a safe way to iterate towards the goal here rather than build the whole thing at once? For example — could we start with just the batch? We import a batch and we process it. Why could we not start there?

[06:46] Priya Nair: We could, but for context, we separated payouts into bigger phases. The one here is the manual phase — the user manually inserts each line, each deduction, each earning, then creates a settlement, then a batch.

[07:23] Maya Chen: I understand that, but that's the assumption I'm calling into question. The team's hypothesis is that the most valuable problem we can solve for our customers is offering them a manual payroll process. I question that assumption. Today the billing product already produces a gross settlement. It doesn't do taxes, withholdings — the nerdy payroll stuff — but the settlement process is there, it's messy, we're needing to refactor it. Any Ledger customer can use billing for that part already.

[08:59] Priya Nair: Yeah. We could phase it out.

[09:17] Maya Chen: So knowing the types and the rules and the lines and the settlements already exist somewhere in our domain — what problem are we really seeking to solve here? Is it taking a batch and actually sending the money? Is it matching the bank transfer to the batch? I don't see the answer to that question yet. To put it in a provocative light: what I see is, hey, billing has all this payroll stuff, we need the same thing on our side. My question is why.

[11:08] Tom Alvarez: We are not doing that, Maya. In the financial reports there are two lines for payroll — W2s and 1099s — and nothing else. What we want first is to break those two totals down: the list of employees, their pays, their deductions. And we want to create payroll cycles, and in the end match them with the bank transaction. No integration with billing, no payments yet, no automations. Everything is manual.

[12:12] Maya Chen: Okay. So you've just stated two specific problems, which appear very different from what we're looking at here. A reporting problem — we need a report of payroll amounts per employee. And a mapping problem — we have two payable categories and we need more granularity.

[13:06] Tom Alvarez: On top of it, we are enabling accrual accounting. Now everything is cash basis — only when the bank transaction arrives can they categorise it. With payroll we can post the accrual entries before the bank transaction, to have accurate reports on hand.

[13:23] Maya Chen: So there's a third problem statement: for accrual accounting to be accurate, payroll settlements need to exist with the settlement date rather than the cash posting date. Three distinct problem statements. Each has a specific solution set, and all of them can be solved without a lot of what we're proposing to build. This technical design, and the UI design in Figma, both go way beyond the scope of those three. Does everyone agree? We should absolutely de-scope a lot of this complexity and build only what satisfies these three, ranked by importance. It could be three projects, or one project with three milestones. Please disagree — I'm one person and I'm only semi-technical.

[16:10] Omar: My understanding, Maya, is there's a granularity in billing and we want reporting, but to integrate we need some foundations — staff, contract types. Things intersect and can't be built isolated. We don't have to build the UI right away; we could load a CSV from billing and show it. The question is what our goal is and how we sequence the milestones so we don't block each other.

[18:05] Maya Chen: Exactly. I agree with almost everything you said. Tom, you said we're not integrating with billing — so at this point we're talking about a non-integrated import, a flat file. That's the first goal: take some output from billing and import it into Ledger to enable granular reporting, categorisation, and posting with the correct date. And there is very little UI in that. My concern is that the line-item structure itself is about to change drastically in billing, so there's a temporary blocker there — but because these are not integrations we might work around it by structuring the flat file properly.

[20:49] Omar: One of the most important things is staff. Without staff we can't do anything — the batch is on top of staff, contract types, W2 or 1099. We don't have that structure yet.

[21:11] Priya Nair: I agree with Maya here. Duplicating the operational logic from billing into Ledger is cumbersome. If we could get away with just uploading a file from billing to Ledger, it's much easier — Ledger only needs the financial data. But the why was more a question to product and stakeholders.

[22:25] Maya Chen: So first, this project needs re-scoping — which problems we're solving in which projects. Maybe all three in one, maybe three projects. Omar called out prerequisites: employee type, category. Those should be answered first, and once we have the clear scope, Priya, you refine your technical proposal down to only the entities necessary for that scope. We already have enough complexity in billing that we're working to simplify; I'd prefer to get through that before bringing it over here. Let's take the redefinition of this project first, and then revisit the design review from that perspective.

[26:25] Maya Chen: All right. Who's next?

[27:15] Nodir Rahimov: I have a topic. Today we're going to talk about how we manage denormalized fields across all our tenant schemas. Right now maintaining consistency in Python is causing subtle bugs, so I am proposing we move this responsibility directly into Postgres. Why do we have denormalized fields? We have 62 of them. Storing them gives us a four to seven times speed-up on list queries because we avoid multi-table joins. The problem is how we synchronise them. We rely on ORM signals, but signals only fire on save. Whenever someone uses a bulk update, raw SQL, or a background script, the signals get skipped, leading to silent data drift. We had an incident where a background sync overwrote sixteen customer names with vendor strings, making those customers vanish from payment search. When we audited all tenants, we found hundreds of unsynchronised rows.

[31:00] Nodir Rahimov: So here's what I propose. Instead of developers remembering to call the sync, let Postgres enforce it with triggers. Whether data is updated from the app, the admin, SQL or background workers, Postgres updates the denormalized column in the same transaction. We declare the triggers inside the models, tracked in standard migrations. Will it slow the database down? No — we check whether the source column actually changed; if not, the trigger exits. For heavy bulk imports we can temporarily bypass triggers. Why not change-data-capture with a queue instead? Because that introduces lag; triggers give instant consistency without new infrastructure. Rollout in four waves across all 62 fields: wave one resolves the incident directly with triggers for customer and contact full names plus a backfill across all tenants; wave two, single-row monetary fields like invoice subtotal and total; wave three, multi-row aggregates; wave four drops four deprecated columns. Every wave: deploy trigger, backfill tenants, validate drift, deprecate the old signals. Questions?

[34:14] Omar: I have a lot of questions. When you say it writes to the standard migration — what does that mean?

[35:15] Nodir Rahimov: You write it as a normal migration. You don't have to go to Postgres and create the triggers by hand.

[35:35] Omar: And what about bulk imports? If a user imports ten thousand records from the UI, we don't know when that happens.

[37:40] Nodir Rahimov: It's a feature you can use if you want — you can disable the trigger for a bulk import if it causes a performance issue.

[37:49] Omar: You can make a regression test — import ten thousand and look at CPU time. I'll set that up.

[38:00] Tom Alvarez: Some denormalizations have bigger logic — amounts, totals. It's business logic, not just copying from another model. Are we moving those as well? And we have chains — one model updates another, which triggers another update. In code we only denormalize if the field changed. At the database level, does the trigger fire anyway?

[40:00] Nodir Rahimov: No — the guard is "old column is distinct from new column". If it didn't change, it's skipped. And for computed amounts like gross revenue we keep the code and add a trigger alongside; that's an architectural decision per class of field.

[41:09] Tom Alvarez: In the incident you showed, the customer name was different because the code updated the denormalized field directly, not because it bypassed the signals. We're not solving that case with triggers.

[42:00] Nodir Rahimov: Agreed — we shouldn't update denormalized fields in code at all. We should mark them read-only in the models so nothing writes to them except the trigger.

[43:00] Omar: Because AI-written code sometimes updates the denormalized field instead of the source, and we didn't catch it in review. We need some kind of annotation for those fields.

[45:18] Omar: Is it working on our managed Postgres?

[45:25] Nodir Rahimov: I think it would — it's standard Postgres.

[46:00] Tom Alvarez: Regarding atomicity — we do operations in a transaction and the trigger fires inside the same transaction, right? So if the transaction fails, the trigger rolls back too.

[46:17] Nodir Rahimov: Yes. Same transaction.

[47:03] Omar: And performance — last month we had two incidents with database CPU.

[47:13] Nodir Rahimov: Triggers run at the C level. Right now doing it in Python is much more expensive than doing it in the database.

[48:48] Maya Chen: Sounds like — what are the next steps here?

[49:00] Nodir Rahimov: Start from wave one, where we update customer and contact full name, and check how it works. I created a project in Linear, denormalization integrity, with the full list of fields.

[50:09] Maya Chen: So you're going to implement the first couple. Are you going to implement all the rest? How are we going to ensure this gets done, or prioritised?

[50:32] Omar: The question is, do you want to do it alone, or should we split it into teams? It would be better if we split it across all teams.

[50:55] Tom Alvarez: Who's going to review these changes?

[51:34] Maya Chen: Nodir, thank you for raising this. I think we need to identify who's going to finish it. That's the question. Was the proposal approved by the committee here?

[52:06] Omar: It sounds like it was, yes.

[52:15] Tom Alvarez: Yes, I think it was. Now we need to decide the timing.

[52:21] Maya Chen: This team needs to have that discussion. I'm not the owner. You guys get to own this — how to divide the work, how to share it. If you have questions on how to show that in Linear, I'd be happy to help. But the ownership has to come from you.

[53:00] Maya Chen: All right, I think we're just about out of time. Thank you all, see you online.

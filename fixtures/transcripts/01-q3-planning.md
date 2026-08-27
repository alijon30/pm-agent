# Call 1 — Q3 Billing planning (≈5 minutes, four voices)

Read naturally; small deviations are fine. Planted moments are marked in the margin comments
(do not read those aloud). Speakers: Maya (PM), Nodir (backend), Priya (frontend), Tom (support).

**Maya Chen:** Okay, let's get going. Agenda is reminders, the export request from Northwind, the overdue dashboard, and whatever Tom has from support.

**Tom Alvarez:** Support first then, since it's short. We had eleven tickets last week about people not noticing their invoice was overdue until a week after. They want the nudge sooner.

**Maya Chen:** Right. Today the first reminder goes out seven days after the due date. The PRD says five. So we're already off spec.
<!-- planted: spec says 5, code says 7 -->

**Nodir Rahimov:** The seven is just the default in config. It's one constant.

**Maya Chen:** Then let's move payment reminders to three days after the due date. Nodir, can you own that?
<!-- planted decision + owner: reminders → 3 days, Nodir -->

**Nodir Rahimov:** Sure, I can have that done by next Friday.
<!-- planted due date said aloud -->

**Priya Nair:** Should we also do SMS reminders? Two customers asked.

**Maya Chen:** We considered SMS reminders last quarter — decided no for now, email only until we have a provider we trust.
<!-- planted rejected option -->

**Tom Alvarez:** Fine by me. Second thing: Northwind is blocked on the CSV export. They can't close their books without it.

**Maya Chen:** This is urgent, a customer is blocked. Priya, can you take the invoice CSV export and get it behind the flag this week?
<!-- planted escalation → priority may leave the band; owner Priya -->

**Priya Nair:** Yes. One question — the spec says the export includes payments. The current code only writes the invoice columns.
<!-- planted code-vs-spec conflict on export -->

**Maya Chen:** Noted, let's keep that as an open question for now and ship the invoice columns first.

**Nodir Rahimov:** Also, Sam should look at the Stripe webhook retries. We dropped two events on Tuesday.
<!-- planted roster miss: Sam is not on the roster -->

**Maya Chen:** Sam's on the platform side, I'll ping them. Third: the overdue dashboard. Where are we?

**Priya Nair:** We need the overdue dashboard for the finance team. I think there's already a ticket from last quarter.
<!-- planted near-duplicate of a seeded issue (Plan 2) -->

**Maya Chen:** Probably. Let's check before we open another one. Last thing — do we charge late fees? Finance asked again.

**Tom Alvarez:** We've never decided that.

**Maya Chen:** Then it stays an open question. Need to check with finance before anything goes in the product.
<!-- planted open question -->

**Maya Chen:** That's it. Thanks all.

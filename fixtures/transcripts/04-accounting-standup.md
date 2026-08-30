# Billing — standup + triage — Acme Invoicing

Fourth fixture call, adapted from the shape of a real 25-minute engineering standup (all names,
products and customers replaced). Its value is texture: overlapping speakers, half-finished
sentences, a blocker that turns out to be someone's phone number, and decisions made in passing.
This is what the agent will actually hear in production.

Roster voices: Maya Chen (runs the standup), Nodir Rahimov (backend), Priya Nair (engineer),
Tom Alvarez (support/ops). Non-roster voices on purpose: Omar (platform lead, contractor) and
Lena (new engineer) — the roster gate should leave anything owned by them unassigned and say so.

Planted moments:

1. **Decision** — line-item rates allow six decimal places everywhere; totals always round to two.
2. **Explicit deprioritisation** — the decimals request is "not urgent, it's low" (priority must
   NOT leave the band; there is no escalation language anywhere in this call).
3. **Roster miss** — Lena owns the feature-flag verification; she is not on the roster.
4. **Cross-reference to existing work** — the recurring-invoice schedule fix is a follow-up to a PR
   already in review; "seven upcoming from today, whatever happened in the history."
5. **Spoken timing** — "by today" (Priya's PR), "after the customer call" (doc review).
6. **Conflict candidate** — code hard-codes credit notes as refunds; the statement spec says
   otherwise; changing it affects historical statement PDFs.

---

[00:00] Maya Chen: Okay, standup. Nodir, you first — is the template redesign blocked on anything?

[00:04] Nodir Rahimov: Not really. Not really? No. Only time. I'm mostly working on the statement things.

[00:29] Maya Chen: Okay, yeah. But the design is already unblocked, right?

[00:37] Nodir Rahimov: Design is mostly, yes, unblocked.

[00:40] Maya Chen: Okay, thank you. Lena, any blockers? Do you know about the sandbox task?

[00:56] Lena: Yeah, I have started working on it. But I need a real account on the payments sandbox and I'm trying to sign up. It's something with a phone number verification and I can't sign up yet.

[01:25] Maya Chen: So we only have the one shared sandbox account.

[01:29] Tom Alvarez: Yeah, I invited her, but she can't get past the sign-up.

[01:36] Lena: The validation error says the phone number is high risk and it's not letting me create an account. Yeah, I'm using my own. It's valid but it's not...

[02:00] Tom Alvarez: You need another number. I can give you mine, or I also have a US number, Lena, you can send the SMS to that.

[02:29] Maya Chen: Okay. Sometimes the shared account uses my number, so that happens. Thank you. Omar, any blockers? No? Okay.

[03:11] Nodir Rahimov: But on this ticket, like yesterday, we talked about this — changing how credit notes show on statements, from refund to credit. We can change it in a way that does not affect historical statements, they're all PDFs already. But we need to change the code side as well, because right now it's hard-coded that a credit note is always shown as a refund, not a credit. And another thing — it affects all customers, we cannot do it for just one customer, because it's a system-wide type. So these are two decisions from this investigation, and product must decide.

[04:23] Maya Chen: But I thought Omar wanted the historical statements changed too, right?

[04:35] Nodir Rahimov: He said it shouldn't affect old statements. I said it will affect all statements as well, which causes a discrepancy between the web view and the PDFs. So that's what I'm saying today, that we can do it in a way that does not affect all statements.

[05:05] Maya Chen: Okay. Can you please leave that as a comment on the credit notes ticket? Your findings, and tag Sam and the finance lead.

[05:21] Nodir Rahimov: Okay, I'll write it up and send it to them. Thank you.

[05:31] Maya Chen: Priya, any blockers?

[05:35] Priya Nair: Not necessarily blockers, but I need reviews and I need approval on the design doc so I can continue to make progress. And this ticket is empty — it has just a summary and nothing else.

[05:56] Maya Chen: Which one? This one? Yeah, the doc is in the actual project, not on the ticket.

[06:02] Priya Nair: I'll post a link to the doc on the ticket. But who needs to review this one?

[06:09] Maya Chen: I already sent it to everyone who needs to review it. They're already looking at it. Maybe we check it together, Priya, after the customer call.

[06:28] Priya Nair: Okay. And Tom, what about the migration for the payment terms? Did you run it?

[06:34] Tom Alvarez: No, I didn't get all the reviews and approvals in time. I'm trying to get that this morning. It will be out soon.

[06:43] Priya Nair: We can't run migrations during business hours, Tom.

[06:48] Tom Alvarez: It should have been run before, yeah, I apologize for that. I didn't get PR reviews in time. It'll have to wait a little bit, but it's almost done.

[07:04] Maya Chen: Are you going to get it done by tomorrow?

[07:10] Tom Alvarez: Hopefully by today — not hopefully, we'll get it done by today. I just need reviews.

[07:23] Maya Chen: Okay. Any questions from anyone? Lena, I just sent you an SMS code, if you can check.

[08:39] Lena: Yeah, got it. Okay, I'm in. Thank you.

[08:53] Maya Chen: Okay. We're going to stay with Nodir, Omar and Priya. Others can drop the call. Thank you. So regarding this one — Contoso wants four decimal places for line-item rates on invoices. They are now asking for decimals. Do we support that on the back end or not? According to the investigation, we support up to six decimal places.

[09:33] Nodir Rahimov: Yep.

[09:34] Maya Chen: But the API is returning three decimals, right? When we save it, it was returning up to three.

[10:03] Nodir Rahimov: Yeah, at that time we were discussing adding some kind of configuration for six decimals. The database already stores six. It's just the serializer that rounds to three.

[10:44] Maya Chen: So are we okay to increase to four decimals, and is it only done on the frontend, or do we have to change the serializer?

[10:58] Omar: Why four? We just need to allow six decimal places, like the database. We don't have any reason for four.

[11:04] Nodir Rahimov: When are we going to start rounding, then?

[11:06] Omar: Because in some places we don't show six decimals, we round to two, and then we're going to start having a mismatch and questions like, hey, I set it to 0.256 and I don't see it here.

[11:29] Nodir Rahimov: I think rates up to six is okay, but the total should be rounded to two. But I need to check one thing — in the invoice line model, the rate column supports three decimals in the database and quantity supports six. If the per-unit rate goes into the rate column, then we have to change the invoice line model as well. That's one potential constraint. Okay, are we going to do this now?

[12:47] Maya Chen: We can postpone it, it's not urgent, it's a low.

[12:54] Nodir Rahimov: Yeah, but in the new transaction model we support quantity and rate up to six decimal places everywhere, and total amount always two decimals, rounded everywhere, so there won't be any rounding issues in any such requests.

[13:30] Maya Chen: Let me snooze this one. Is Contoso a big customer or small?

[13:42] Nodir Rahimov: Medium. Globex asked for the same thing, I don't know why they want four.

[13:50] Omar: I think the frontend restricts it to three, but we have to just remove that and make it six. Also there's a feature flag for six decimals, enabled for everyone anyway. Let me check that one and remove the feature flag also.

[14:17] Maya Chen: Okay, so let's check this with Lena, and on localhost we'll remove the flag and check the flow — invoice, line items, and the PDF. Because I remember we worked on the PDF also to support up to six.

[14:40] Nodir Rahimov: Yeah, but I need to check the column thing I said. Let me check right now. Okay — it goes to the quantity column, so it's safe to change to six decimal places. I checked the invoice line model as well, it will go to a six-decimal field.

[15:12] Maya Chen: Okay. So regarding this other one — this is more likely platform. The customer was trying to update a billing profile, but the issue is on the main page of the customer profile, I think. Can I send it to platform?

[15:39] Tom Alvarez: Yeah, that's platform.

[15:55] Nodir Rahimov: I think it's just the PATCH API not working correctly — the frontend is sending the whole address block as well. It should be a PATCH, not a POST.

[16:04] Tom Alvarez: Can you add a comment? Should be a PATCH request, not POST. Omar will know, he's working on a similar issue. Tag Omar.

[16:37] Maya Chen: Okay, that's it. We're going to stay with Priya and Nodir to check the recurring invoices ticket.

[17:01] Maya Chen: So in this task, we were going to show seven upcoming invoices from today's date. Let me create one. Recurring, every week, always. As you can see, we already have two expired ones, and they're coming here, and they should. So what we have to do is — one, two, three, four, five, six, seven, okay? It's working once we edit, but when they were expired, it wasn't working.

[19:43] Priya Nair: So before, it was just creating seven, and if two were expired, then it counted those as part of the seven upcoming. I made a change, and there are two PRs going out in this single merge — the first one was the version you just described, the second one is the fix. It was a two-step implementation.

[20:21] Maya Chen: Can we fix this one? You want the two expired plus the seven upcoming?

[20:29] Priya Nair: Yes.

[20:30] Maya Chen: Any status on the history side, but we have to always show seven upcoming invoices from today's date. No matter what happened in the history, just take today's date and create seven upcoming if the option is "always."

[20:55] Priya Nair: Yes. Yeah, that was the requirement. It doesn't matter what happened in the history.

[21:00] Maya Chen: Completed, cancelled or expired — any status other than upcoming, we need to keep seven upcoming from today's date.

[21:13] Priya Nair: All right, that's a simple change. I'll make that and send the PR up today.

[21:24] Nodir Rahimov: I just want to check one thing. What if we choose the start date earlier, like in June?

[21:42] Maya Chen: It didn't show any upcoming. That's the issue.

[21:47] Nodir Rahimov: That's why I'm worrying about this one. It just creates seven invoices in the past and nothing upcoming.

[22:00] Maya Chen: So this is for Priya too — we need to show seven invoices if all of them are upcoming; otherwise, if they are creating with a historical start date, we need to show the ones up to today's date and then plus seven upcoming.

[22:22] Priya Nair: Okay, but in which scenario would they create something that is already expired?

[22:32] Nodir Rahimov: We don't know this, but there might be cases — they migrated to our system in the middle of the year, and they want to create the recurring schedule to get the correct financial report, so they need all the invoices, they just mark the old ones as paid. That's their choice.

[22:54] Priya Nair: Okay, all right, this is a quick fix, I'll send another one. Do you have anything else? The other PR — we can hop on a separate call, I'll send you a link. Yesterday I couldn't even get that PR out because there were so many AI review comments, must-haves and so on, and I don't think they're all relevant, but you still approved it, so it's confusing to me.

[24:07] Nodir Rahimov: I approved that one because it's only for Initech and there are product decisions needed, so they will tell us. But for other PRs like the scheduling ones that affect everyone, the must-haves are finding real gaps, real edge cases, and we should fix them.

[24:47] Priya Nair: All right, understood. Thank you. I'll talk to you later.

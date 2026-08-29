# PDF incident huddle — Acme Invoicing

Third fixture call: a two-minute incident huddle, two voices. Its job is to prove the
escalation path — the planted moments are the **spoken urgency** ("urgent", "a blocker")
and the commitment, said by different people, which is exactly the shape the extractor must
stitch together. The work is deliberately unlike anything already filed: nothing existing
covers PDF generation, so reconciliation must file it as new.

---

[00:03] Maya Chen: Sorry to pull you in — enterprise customers can't download invoice PDFs
since this morning. The generate endpoint returns a five hundred for anything with more than
forty line items.

[00:16] Nodir Rahimov: Since the template change on Tuesday? That touched the renderer.

[00:22] Maya Chen: Probably. Look, this is urgent — three enterprise accounts are mid-audit
and they need those PDFs this week. It's a blocker for their finance close.

[00:34] Nodir Rahimov: Understood. I'll take fixing the invoice PDF generation for large
invoices, starting now — I'll drop the grace period change until this is out.

[00:45] Maya Chen: Thank you. Ping the channel when it's fixed and I'll tell the accounts.

[00:52] Nodir Rahimov: Will do.

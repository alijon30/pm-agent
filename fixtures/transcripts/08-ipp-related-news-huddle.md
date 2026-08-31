# InterviewPrepPro — related articles huddle

Eighth fixture: the ON-CAMERA call. Two voices, under a minute, one fresh finding no earlier
call has used, plus a re-raise of the seeded pricing ticket so an update lands as a comment. Every claim matches `newsUtils.ts` exactly: `getRelatedNews` (line 71) excludes
by bare numeric id — ids restart from one in every content list — then takes the first three
of the same type, with no relevance at all.

Planted moments: "frontend bug" is said aloud and NOBODY takes the work (Nodir declines), so
the taught ownership rule ("frontend bugs go to Priya") decides the owner and the ticket gets
a frontend label. Spoken urgency ("this is urgent") and a spoken date ("by tomorrow") come
from Tom, so the priority and date gates both fire on camera.

---

[00:03] Tom Alvarez: Quick one before the partner demo. The related-articles rail at the bottom of every article is broken in a weird way — every page shows basically the same three suggestions, and the piece you'd actually expect to see there half the time never shows up at all.

[00:16] Nodir Rahimov: I looked this morning. It's a frontend bug in getRelatedNews — it filters the combined list by the bare numeric id, and our ids restart from one in every content list, so anything that shares the current article's number gets dropped as if it were the same article. And there's no relevance ranking behind it at all: after that filter it literally just takes the first three of the same type.

[00:31] Tom Alvarez: The partner demo is tomorrow morning and the news section is the first thing we show. This is urgent — I need it fixed by tomorrow.

[00:38] Nodir Rahimov: I'm heads-down on the sign-in work, so I can't take this one. The fix itself is small — the exclusion needs a composite key, the type and the list rather than the bare number, and the rail should match on category before it slices.

[00:47] Tom Alvarez: Okay. Let's get an owner on it right after this call. One more thing — the pricing page. We already have a ticket for building it, so don't file a new one, but the nav links to it today and just 404s. Can we get that noted on the existing ticket?

[00:58] Nodir Rahimov: Noted works for me. That's everything.

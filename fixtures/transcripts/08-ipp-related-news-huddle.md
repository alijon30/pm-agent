# InterviewPrepPro — related articles huddle

Eighth fixture: the ON-CAMERA call. Two voices, under two minutes, one fresh finding no earlier
call has used. Every claim below matches `newsUtils.ts` exactly: `getRelatedNews` (line 71)
excludes by bare numeric id — and ids restart from one in every content list — then takes the
first three of the same type, with no relevance at all. Spoken urgency is planted ("this is
urgent") so the priority-gate beat happens on camera.

---

[00:03] Tom Alvarez: Quick one before the partner demo. The related-articles rail at the bottom of every article is broken in a weird way — every page shows basically the same three suggestions, and the piece you'd actually expect to see there half the time never shows up at all.

[00:16] Priya Nair: I found why. getRelatedNews filters the combined list by the bare numeric id, and our ids restart from one in every content list — so anything that happens to share the current article's number gets dropped as if it were the same article. And there's no relevance ranking behind it at all: after that filter it literally just takes the first three of the same type.

[00:31] Tom Alvarez: The partner demo is tomorrow morning and the news section is the first thing we show. This is urgent — can you take it?

[00:38] Priya Nair: Yes. Same fix family as the detail lookup: the exclusion needs a composite key — the type and the list, not the bare number — and the rail should match on category before it slices. I'll fold it into the news work and have it up by tomorrow.

[00:47] Tom Alvarez: Thank you. That's all I had.

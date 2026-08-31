# InterviewPrepPro — related articles huddle

Eighth fixture: the ON-CAMERA call. Two voices, under two minutes, one fresh finding that no
earlier call has used — the "related news" rail shares the ID-collision root cause (the filter
in `newsUtils.ts` excludes by id across mixed lists), so the investigation has somewhere real
to land. Spoken urgency is planted ("this is urgent") so the priority gate beat happens on
camera.

---

[00:03] Tom Alvarez: Quick one before the partner demo. On any article page, the related-articles rail at the bottom is showing the wrong things — I opened the SEVP announcement and the rail suggested two events and the same article I was already reading.

[00:16] Priya Nair: That's the same disease as the detail-page bug. The related list filters out the current item by numeric id, but the ids repeat across the featured, events and announcements lists — so it drops unrelated items that happen to share the id and keeps near-duplicates.

[00:31] Tom Alvarez: The partner demo is tomorrow morning and the news section is the first thing we show. This is urgent — can you take it?

[00:38] Priya Nair: Yes. Same fix family as the detail lookup: the related filter needs the type in the key, not just the number. I'll fold it into the news work and have it up by tomorrow.

[00:47] Tom Alvarez: Thank you. That's all I had.

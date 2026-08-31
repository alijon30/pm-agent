# InterviewPrepPro — practice session sync

Seventh fixture call, the second over the real vendored codebase. Shorter, two topics: the
practice-session pipeline and the difficulty vocabulary.

Planted moments:

1. **Bug with a privacy edge** — every practice session runs under one hardcoded identity, and
   the difficulty the student picks is logged and thrown away. Spoken urgency ("this is
   urgent") — the identity part is a real data problem.
2. **Refactor decision** — one shared difficulty type across API, UI data and display copy.
3. **Owners and dates** — Nodir "by Tuesday" on the identity fix; the vocabulary work is
   deliberately left unowned ("who takes this?" — no answer), which the agent should surface
   honestly rather than invent an owner.

---

[00:05] Maya Chen: Quick sync on practice sessions. Nodir, you looked at why beginner and advanced interviews feel identical?

[00:12] Nodir Rahimov: They are identical. The difficulty picker on the practice page collects the choice, logs it to the console, and navigates to the interview with nothing attached. No query param, no state. The interview then starts the voice session from a constants file.

[00:29] Maya Chen: Meaning what, exactly?

[00:31] Nodir Rahimov: Meaning every session on the platform runs as the same hardcoded user — same id, same name, same email, baked into the code. The agent never learns who the student is or what difficulty they picked. Beginner and advanced produce the same interview because the agent is never told.

[00:47] Maya Chen: So the per-student feedback we're advertising is scored against one frozen identity. That's — okay, this is urgent. If a student's transcript gets attached to somebody else's account when the backend starts keying on that id, that's a data problem, not a polish problem.

[01:02] Nodir Rahimov: Agreed. The fix is to thread the signed-in user and the picked difficulty through to the session start — the conversation manager already accepts dynamic variables, we're just not passing them. I can have it done by Tuesday.

[01:13] Maya Chen: Take it. And the voice preference in settings — the options are named after the other vendor's voices. Shimmer and echo don't exist on our voice provider.

[01:22] Nodir Rahimov: Same wiring job, I'll fold the voice preference into the same change.

[01:27] Priya Nair: While we're in there — difficulty is spelled four different ways across the app. The API type says easy, medium, hard. The practice cards and settings say beginner, intermediate, advanced. The feedback page relabels those as entry level, mid level, advanced level. And the feedback data disagrees with the practice cards about how long an intermediate session even is.

[01:47] Maya Chen: Four vocabularies for one concept. Let's decide it here: one shared difficulty type, one label map, everything imports from it. Beginner, intermediate, advanced as the canonical values.

[01:58] Priya Nair: Agreed. That's the decision, but it's a cross-cutting change — API types, the data files, the display copy. Who takes this?

[02:06] Maya Chen: Let's see where we are after the funnel work lands. Leave it unassigned for now, but I want it tracked.

[02:12] Nodir Rahimov: Fine by me.

[02:14] Maya Chen: Okay — Nodir on the session identity and difficulty wiring by Tuesday, voice preference folded in, and the vocabulary consolidation tracked without an owner yet. Thanks both.

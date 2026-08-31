# InterviewPrepPro — weekly planning

Sixth fixture call, and the first about a real codebase: the vendored InterviewPrepPro app in
`fixtures/interviewpreppro/`. Every problem discussed here is real and verifiable in that code,
so the agent's investigations should land on actual files and lines.

Planted moments:

1. **Escalation** — the sign-up funnel is dead end to end (inert landing CTAs + Google sign-in
   that never completes): "this is a blocker" is said aloud, so the funnel ticket may leave the
   priority band.
2. **Bug with a code trail** — news/event/announcement detail pages collide on shared IDs;
   the investigation should find `newsUtils.ts` checking `featuredContent` first.
3. **Update, not duplicate** — the pricing-page 404 is already tracked in the seeded backlog
   ("Build the pricing page"); the call re-raises it, and the agent should update, not re-file.
4. **Spoken dates** — "by Wednesday" (Priya), "end of the week" avoided; Nodir says "Friday".
5. **Rejected option** — hiding the news section entirely: considered, refused.
6. **Decision** — sign-up funnel is this sprint's top priority.

---

[00:04] Maya Chen: Okay, weekly planning. Agenda: the sign-up funnel, the news mix-up Tom found, and whatever's left from last week. Tom, you first.

[00:15] Tom Alvarez: Two things from support. First one's weird — three students wrote in saying they clicked the visa workshop card on the News page and got an article about application guides instead. Different cards, same wrong article.

[00:31] Priya Nair: I can reproduce that. The detail page looks things up by a numeric id, and the featured articles, the events and the announcements each start counting from one. The lookup checks the featured list first, so any event or announcement with a low id opens the wrong thing.

[00:49] Maya Chen: So the workshop card and the processing-times announcement both open the 2024 application guide?

[00:54] Priya Nair: Exactly that. Most of the event and announcement cards are unreachable — they all resolve into the featured articles.

[01:02] Maya Chen: Okay. Priya, can you take fixing the news detail lookup so events and announcements open their own pages? Give each list its own key space or prefix the type, your call.

[01:12] Priya Nair: Yes. I'll have it done by Wednesday.

[01:16] Tom Alvarez: Second thing, and honestly this one's worse. Two students emailed saying they can't sign in with Google at all. They click Continue with Google and nothing happens. No error, nothing.

[01:29] Priya Nair: The Google button calls sign-in with redirect turned off and then never navigates anywhere. The result comes back with a URL and we just drop it. So the button genuinely does nothing.

[01:41] Maya Chen: And on top of that — I was showing the landing page to the university partners yesterday, and none of the buttons work. Sign in, Get Started, both hero buttons. They're just styled buttons with no links. And the nav points at a features page and a pricing page that don't exist, so those are straight 404s.

[01:58] Nodir Rahimov: So from the homepage there is no working path into the product at all. Someone lands there, they cannot sign up.

[02:04] Maya Chen: None. And with the partner demo in two weeks, this is a blocker — we are literally uninstallable from the front door. I want the funnel to be this sprint's top priority. Decision made.

[02:16] Nodir Rahimov: I'll take the funnel: wire the landing buttons to the login page, and fix the Google sign-in so it actually follows the redirect. By Friday.

[02:24] Maya Chen: Thank you. And the missing pricing page — I think we already have a ticket for building pricing, from the pre-launch list.

[02:31] Tom Alvarez: We do, it's in the backlog. The 404 makes it more urgent though.

[02:35] Maya Chen: Then let's note on the existing pricing ticket that the nav links to it already and 404s today. Don't file a second one.

[02:43] Nodir Rahimov: On the news thing — should we just hide the news section until it's fixed? It's making us look broken.

[02:50] Maya Chen: No. We're not hiding the section — students use the SEVP announcements, that's real value. We fix the lookup, we don't amputate the feature.

[03:00] Tom Alvarez: Agreed.

[03:03] Maya Chen: Okay. Priya on the news lookup by Wednesday, Nodir on the sign-up funnel by Friday, pricing note goes on the existing ticket. Anything else? No? Thanks everyone.

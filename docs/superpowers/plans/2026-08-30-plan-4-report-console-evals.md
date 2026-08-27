# PM Agent — Plan 4 of 4: Report, Console, Gemma, Evals (Day 4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. The human writes the code: per task, deliver failing tests and implementation as paste-ready blocks; the human applies, runs the four gates, commits.

**Goal:** Everything a judge touches: an on-request status report with 100% citation coverage, the single-page console (task graph, audit log, wiki) at the hosted URL, Gemma doing real triage for the bonus, and the eval set printing the numbers that go in the README and the last 20 seconds of the video.

**Spec:** rev 2 §7.7 (report), §7.1 triage (Gemma), §12 console, §14 evals; day 4 of §17. Day 5 (diagram, README, video, posts, submit) is the §18 checklist, not a code plan.

## Global Constraints
Same as Plans 1–3. The console is read-only and imports `store` only (import-linter contract added today). No JS framework; one inline SVG for the graph.

---

### Task 1: `verify/citations.py`, `Report` schema, `reporter` agent, `stages/report.py`
**Interfaces:**
```python
class Claim(BaseModel): text: str; refs: list[str]
class Section(BaseModel): name: Literal["moved","blocked","at_risk","conflicts","open_questions","decisions"]; claims: list[Claim]
class Report(BaseModel): project: str; window: str; sections: list[Section]
async def check_citations(report: dict, id_gate: IdGate) -> CitationVerdict(ok, report: dict, removed: list[{section, text, reason}])
#   every claim has ≥1 ref and every ref exists; claims failing are removed (after one bounce) and the removal is listed at the end of the report
async def report(task, deps) -> StageResult    # kind "report": tools = reconciler's read tools + list_actions_since, list_decisions, list_open_conflicts, list_recent_results; posts to the requesting channel/thread
```
Trigger: `POST /slack/events` `app_mention` with text matching `report( <project>)?` → triage (Task 2) classifies intent `report` → enqueue `report` task with `params={project, window:"7d"}` and `context={channel, thread_ts}`.
**Tests:** `test_every_claim_needs_an_existing_ref`, `test_uncited_claims_are_removed_after_one_bounce_and_listed`, `test_at_risk_includes_unmet_checks_and_overdue_issues`, `test_the_report_is_posted_in_the_requesting_thread`, `@live test_the_real_reporter_cites_everything_on_the_fixtures`.
**Commit:** `feat: status report with the citation gate`.

### Task 2: Gemma triage
**Interfaces:** `GemmaTriage(model: str)` implements `Triage.decision_bearing(segments)` (batch classify windows of 5 segments → per-segment bool; on any failure return all-True — triage must never lose content) and `classify_intent(text) -> Literal["report","correction","question","noise"]`. Model id from `PM_MODEL_TRIAGE` (verify with `scripts/list_models.py`; documented fallback: the fast Gemini tier, which forfeits the bonus but not the feature).
**Tests:** `test_triage_failures_degrade_to_keeping_everything`, `test_intent_classification_maps_report_requests`, `@live test_gemma_flags_the_decision_segments_of_the_fixture_call`.
**Commit:** `feat(agents): Gemma triage for segments and Slack intent (+0.2 bonus, honestly earned)`.

### Task 3: `http/console.py` — the single page
**Routes:** `GET /console` (HTML): header with project + eval numbers (from the latest `evals` doc) · **task graph** (open and recent tasks grouped by `plan_id`, inline SVG with edges from `depends_on`, status colours, hover = reason) · **audit log** (last 50 actions: kind, target, checks_passed, revert status) · **open conflicts** (from wiki pages) · **wiki pages** (type, title, facts count, links) · **corrections** · **queue health** (queued / blocked / deferred / failed counts). `GET /console/page/<slug>` renders one wiki page. `GET /console/vault.zip` (from Plan 3's export). Read-only; no secrets, no raw payloads.
**Tests:** `test_the_console_renders_with_an_empty_database`, `test_the_graph_draws_one_edge_per_dependency`, `test_the_console_never_renders_event_payloads_or_secret_shaped_strings`, `test_vault_zip_contains_one_markdown_file_per_page`.
**Commit:** `feat(http): read-only console — graph, audit, brain`.

### Task 4: Evals — `evals/questions.jsonl`, `evals/run_evals.py`
**Design:** each question is `{id, kind, input, expected, check}` where `check` names a scorer in `evals/scorers.py`: `extract_recall` (planted items found with matching quotes), `duplicate_detected`, `conflict_detected(kind)`, `roster_miss_unassigned`, `priority_band_respected`, `escalation_honoured`, `due_only_when_stated`, `plan_dependency_order`, `plan_rejects_cycle`, `plan_rejects_unknown_issue`, `unmet_nudges_once`, `brain_page_has_conflict`, `revert_restores`, `correction_not_repeated`, `report_citation_coverage`. The runner executes the real pipeline against the fixtures with `FakeLinear`/`FakeNotion`/`FakeGitHub`/`FakeSlack` seeded from `fixtures/` (so it is reproducible for judges without any workspace) and the **real** Gemini/Gemma agents; prints a table and writes `evals/results/<date>.json` plus an `evals` Firestore doc for the console. Headline numbers: factual accuracy, fabricated identifiers (0), citation coverage (100%), corrections recurred (0), invalid plans materialised (0).
**Tests:** `test_every_scorer_named_in_questions_exists`, `test_the_runner_produces_the_five_headline_numbers` (with fake agents), `test_fabricated_identifier_count_is_computed_from_actions_and_wiki_facts`.
**Commit:** `feat(evals): 25 known-answer questions and a reproducible runner`.

### Task 5: README and `docs/architecture.md`
README sections: what it does (3 sentences) · the 4-minute video link · architecture diagram (mermaid, from the spec §4 kept in sync) · how autonomy is kept safe (gates table) · the brain · setup: local (`uv sync`, fakes, `uv run pytest`), cloud (`deploy/*.sh`, secrets table, Fathom webhook) · eval results table · roadmap (§3 out-of-scope list) · disclosures: AI coding assistants used; design lineage from an internal Claude-based harness at DataTruck, all code written during the submission period; models used (Gemini tiers, Gemini embeddings, Gemma). `docs/architecture.md`: the diagram plus one paragraph per component, exported PNG for Devpost.
**Commit:** `docs: README and architecture for submission`.

### Task 6: Day-4 deploy and full rehearsal
Deploy; run `evals/run_evals.py` once against the deployed config; walk the video script end to end with a timer (§18): problem → call ends → tickets → plan graph + Reminders page → revert + correction → a check firing + Cloud Run/Trace → eval numbers. Fix only what breaks the story.

## Day 5 checklist (§18, not code)
- [ ] Record the 4-minute video unedited (Cloud Run console visible), upload to YouTube (public), captions on
- [ ] Architecture PNG exported; README final; repo public; `testing@devpost.com` and `cloudhackathons@google.com` not needed for a public repo
- [ ] Hosted URL = console `https://pm-agent-….run.app/console`
- [ ] Blog post (≈600 words: the friction, the planner-not-scheduler idea, the brain, the eval numbers) with hackathon disclosure; social post with `#AllThingsAgenticHackathon`
- [ ] Devpost form: category Taskmaster; description (features, tech, data sources, findings/learnings from the eval set); Gemma noted; links
- [ ] Submit before **17:00 PDT, Aug 31**; confirm the confirmation email

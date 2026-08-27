# PM Agent — Plan 3 of 4: Follow-through and the Company Brain (Day 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. The human writes the code: per task, deliver failing tests and implementation as paste-ready blocks; the human applies, runs the four gates, commits.

**Goal:** The agent comes back on its own — remaining check kinds, a morning `daily_review` that re-plans against reality, quiet hours and ping caps — corrections stick, every verified fact lands in a cited wiki-style knowledge graph the reconciler and planner read first, and one Cloud Trace span shows a call becoming a Linear write becoming a follow-up check.

**Architecture:** Executors stay deterministic; `daily_review` is a kind that gathers state and enqueues `plan`. The brain is Firestore (`wiki_pages`, `wiki_revisions`) with a deterministic bootstrap, a `wiki_writer` agent that only proposes cited additive facts, `verify/wiki.py` gating them, keyword + Firestore vector search for retrieval, and an Obsidian-compatible export.

**Spec:** rev 2 §7.5 (remaining kinds), §7.6 (brain), §7.8 (corrections), §8 (tracing), §9 (`daily_review_at`), §10; day 3 of §17.

## Global Constraints
Same as Plans 1–2. Additionally: wiki writes are **additive only** — no code path deletes a fact or a page; supersession is a new fact referencing the old one. Embeddings are computed harness-side after the gate, never by the model.

---

## File structure
```
app/
  stages/checks.py (+check_pr_reviewed, check_pr_merged, nudge, escalate, reconcile_item, daily_review)  wiki.py  bootstrap.py
  store/routines.py  corrections.py  wiki.py
  connectors/embeddings.py
  verify/wiki.py
  agents/instructions.py  wiki_writer.py  schemas.py (+WikiUpdate)  tools.py (+search_wiki, get_page)
  core/tracing.py
  http/routines.py  console.py (vault export only today)
deploy/scheduler.sh (+daily_review job)
tests/… mirrors
```

---

### Task 1: Remaining check kinds and actions
**Files:** modify `app/stages/checks.py`, `app/kinds/templates.py`; tests `tests/stages/test_checks.py`.
**Interfaces:** `check_pr_reviewed(task, deps) -> (met, observed)` (reviews ≥ 1 on the newest PR for the issue), `check_pr_merged`, `nudge` (acts immediately: templated post to `params.person` about `params.about`, through `check_caps("ping")`), `escalate` (post to the project channel), `reconcile_item` (enqueues one `reconcile` child for a single item payload).
**Tests:** `test_pr_reviewed_is_met_with_at_least_one_review_on_the_newest_pr`, `test_pr_merged_is_met_only_when_merged`, `test_nudge_posts_once_and_records_a_ping_action`, `test_escalate_goes_to_the_project_channel_not_a_person`, `test_reconcile_item_enqueues_exactly_one_child`, `test_every_kind_in_the_registry_has_an_executor` (parametrised over `KINDS`).
**Commit:** `feat(kinds): PR review/merge checks, nudge, escalate, reconcile_item`.

### Task 2: `store/routines.py`, `daily_review`, `http/routines.py`, Scheduler job
**Interfaces:**
```python
class RoutineStore: get(project_id, kind) / upsert(project_id, kind, cron, timezone, enabled) / mark_fired(project_id, kind, at)
# POST /routines/fire  {kind: "daily_review"}  header X-Tick-Token — enqueues one daily_review task per enabled project whose local time matches daily_review_at (idempotent per day via key f"daily_review:{project}:{date}")
async def daily_review(task, deps) -> StageResult
#   gathers: open tasks (grouped by plan), results of the last 24h (met/unmet), overdue issues (Linear), unmet checks, open conflicts (actions/wiki), decisions since yesterday
#   → children: [plan task with context = the gathering, reason "daily review"]; posts a 3-line Slack summary ("today: 4 checks; at risk: INV-142; 1 open conflict")
```
`deploy/scheduler.sh` adds job `pm-daily-review` at `0 * * * *` (hourly; the endpoint decides which projects are at 09:00 local).
**Tests:** `test_the_daily_review_is_created_once_per_project_per_local_day`, `test_the_gathering_includes_unmet_checks_and_overdue_issues`, `test_daily_review_enqueues_exactly_one_plan_task_with_the_gathering_as_context`.
**Commit:** `feat: daily_review routine — gather, plan, summarise`.

### Task 3: Corrections — store, modal submit, instruction provider
**Interfaces:**
```python
class CorrectionStore: add(project_id, stage, wrong, right, matcher, scope, source_action_id, author) / for_stage(project_id, stage) -> list[Doc]
# agents/instructions.py
def with_corrections(base: str, corrections_loader: Callable[[str], list[dict]]) -> Callable[[ReadonlyContext], str]
#   appends "Corrections from the team (apply when relevant): - wrong → right (matcher)" for the stage found in ctx.state["stage"]
```
`http/slack.py` `view_submission` → `CorrectionStore.add`; reconciler/planner/extractor instructions wrapped with `with_corrections`.
**Tests:** `test_a_correction_is_stored_with_scope_and_matcher`, `test_the_instruction_provider_appends_only_matching_stage_corrections`, `test_a_correction_changes_the_next_extraction` (FakeExtractor asserts the feedback text is present in the instruction — via a seam that exposes the rendered instruction).
**Commit:** `feat: corrections that shape the next run`.

### Task 4: Brain — `store/wiki.py`, `connectors/embeddings.py`
**Interfaces:**
```python
class WikiStore:
    async def get(self, slug) -> Doc | None
    async def upsert_additive(self, *, slug, type, title, aliases, facts_add, links_add, conflicts_add, task_id) -> int   # returns new revision; creates page if absent; never removes
    async def search_keyword(self, project_id, text, limit=5) -> list[Doc]         # title/aliases/facts substring
    async def search_vector(self, project_id, vector, limit=5) -> list[Doc]        # Firestore find_nearest on `embedding`
    async def set_embedding(self, slug, vector) -> None
    async def list_pages(self, project_id) -> list[Doc]
    async def export_markdown(self, project_id) -> dict[str, str]                  # slug → markdown with [[links]]
class Embeddings:  # connectors/embeddings.py
    def __init__(self, model: str = "gemini-embedding-001") -> None                # verify id day 3 via list_models
    async def embed(self, text: str) -> list[float]
```
`FakeEmbeddings` returns deterministic vectors (hash-based) so `search_vector` tests are stable. `Db` gains `nearest(collection, field, vector, limit, filters)` (FakeDb: cosine similarity).
**Tests:** `test_upsert_is_additive_and_bumps_the_revision`, `test_a_superseding_fact_references_the_old_one_and_the_old_one_stays`, `test_keyword_search_matches_aliases`, `test_vector_search_returns_the_closest_page_first`, `test_export_renders_wikilinks_and_conflicts`.
**Commit:** `feat(store): wiki pages, revisions, keyword+vector search, vault export`.

### Task 5: `verify/wiki.py` and `WikiUpdate`
**Interfaces:**
```python
class Fact(BaseModel): text: str; source: str
class PageUpdate(BaseModel): slug: str; type: Literal[...8 types]; title: str; aliases: list[str] = []; facts_add: list[Fact] = []; links_add: list[Link] = []; conflicts_add: list[Conflict] = []
class WikiUpdate(BaseModel): pages: list[PageUpdate]
async def check_wiki_update(update: dict, *, id_gate: IdGate, existing_slugs: Callable[[str], Awaitable[bool]], policy: dict) -> WikiVerdict(ok, pages: list[dict], rejected: list[{slug, reason}])
#   every fact.source passes IdGate.ref_exists; link targets exist or are created in the batch; slug is kebab-case; ≤ policy.max_facts_per_update (40); ≤ 300 chars per fact
```
**Tests:** `test_a_fact_with_an_unknown_source_is_rejected_by_slug`, `test_links_may_target_pages_created_in_the_same_batch`, `test_slugs_must_be_kebab_case`, `test_oversized_updates_are_trimmed_with_a_reason`.
**Commit:** `feat(verify): the wiki gate`.

### Task 6: `wiki_writer` agent, `stages/wiki.py`, `stages/bootstrap.py`, tools for the reconciler and planner
**Behavior:** `wiki` stage payload = `{source_stage, stage_result, touched: [slugs]}` → load current pages → `deps.wiki_writer.run` → `check_wiki_update` → bounce once → `WikiStore.upsert_additive` per page → embed → result `{pages_touched, facts_added, rejected}`. Extract/reconcile/act enqueue a `wiki` child (Plan 1's extract gets its child added here). `bootstrap` (deterministic): roster → person pages; Linear issues → issue pages (facts: state, assignee, title; source `linear:`); Notion tree → spec pages (facts: title, first heading list; source `notion:`); repo modules → module pages (facts: file list, top-level constants like `REMINDER_DAYS = 7` with `code:` refs). `make_read_tools(..., wiki=)` adds `search_wiki(text)` and `get_page(slug)`; reconciler instruction: consult the brain first; planner tools too.
**Tests:** `test_bootstrap_creates_pages_for_every_roster_member_issue_spec_and_module`, `test_bootstrap_is_idempotent`, `test_the_wiki_stage_applies_only_gated_facts_and_records_the_rest`, `test_the_reminders_topic_page_ends_up_with_the_7_5_3_conflict_after_reconcile` (fake reconciler + fake wiki_writer outputs), `@live test_the_real_wiki_writer_cites_every_fact`.
**Commit:** `feat: the company brain — bootstrap, wiki stage, brain-first retrieval`.

### Task 7: Tracing — `core/tracing.py`
**Interfaces:** `setup_tracing(service_name, project) -> None` (OTLP → Cloud Trace exporter; no-op without `PM_GCP_PROJECT`), `task_span(task) -> ContextManager` with attributes `task_id, kind, root_event_id, project_id, plan_id, depth`; runner wraps each stage run. ADK spans nest under it automatically.
**Tests:** `test_task_span_carries_the_task_attributes` (in-memory exporter), `test_tracing_is_a_no_op_without_a_project`.
**Commit:** `feat(core): OpenTelemetry task spans to Cloud Trace`.

### Task 8: Deploy and the day-3 demo
Scheduler job for routines; secrets unchanged; run `bootstrap` for `acme` (`scripts/bootstrap_brain.py`); replay call 1; open a real PR on the fixture repo referencing `INV-142`; force a `check_pr_exists` due now (`scripts/run_task_now.py <id>` sets `due_at=now`) and watch it come back met; force an unmet `check_issue_state` and watch the nudge; open the Reminders page export; open a Cloud Trace trace.
**Commit:** `feat: day-3 wiring, bootstrap and helper scripts`.

## Self-review against the spec
§7.5 all kinds (Task 1, plus `daily_review` Task 2, `report` in Plan 4), §7.6 brain (Tasks 4–6), §7.8 corrections soft rules (Task 3), §8 tracing (Task 7), §9 `daily_review_at` (Task 2), §10 rows for unavailable sources in checks and wiki gate failures (Tasks 1, 5). Hard-rule corrections, page summaries, Memory Bank remain out of scope as the spec states.

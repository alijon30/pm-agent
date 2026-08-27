# PM Agent — Plan 2 of 4: Reconcile, Act, Plan (Day 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. In this project the human writes the code: for each task, produce the failing tests and the implementation as paste-ready code blocks, the human applies them, runs the four gates, and commits. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A call's extracted items are reconciled against Linear, Notion and the code; cited issues are created and assigned in Linear under policy; the team sees a Slack summary with revert/wrong; and the planner's own follow-through plan materialises as a task graph — end to end on Cloud Run.

**Architecture:** Thin HTTP clients with hand-rolled fakes; the reconciler and planner are ADK `LlmAgent`s with read-only `FunctionTool`s and fixed output schemas; `act` is deterministic (gates → intent-before-effect writes); `plan` validates the planner's proposal with `check_plan` and hands the accepted graph to `TaskQueue.complete()`. Two check executors close the loop.

**Tech Stack:** as Plan 1, plus `httpx` for Linear GraphQL / Notion REST / Slack Web API / GitHub REST.

**Spec:** `docs/superpowers/specs/2026-08-26-pm-agent-design.md` (rev 2) §7.2–§7.5, §10, §12, §13; day 2 of §17.

## Global Constraints

Same as Plan 1. Additionally:
- Every client method raises `SourceUnavailable(<source>)` on network/5xx/auth failure and never returns partial data silently.
- Every write to Linear or Slack goes through `ActionStore.begin()` → perform → `finish()`; no exceptions.
- Nudge and escalation text is **templated** (`kinds/templates.py`), never generated.
- Secrets added today (Linear, Notion, Slack bot token + signing secret, GitHub) live in Secret Manager as `pm-linear-api-key`, `pm-notion-token`, `pm-slack-bot-token`, `pm-slack-signing-secret`, `pm-github-token`; `deploy.sh` grows matching `--set-secrets` entries.

---

## File structure (what Plan 2 creates or modifies)

```
app/
  clients/linear.py  notion.py  code.py  github.py  slack.py  slack_blocks.py
  verify/ids.py  roster.py  priority.py  dates.py  caps.py
  store/actions.py
  kinds/templates.py                nudge/escalation text
  agents/schemas.py (+Reconcile*, Plan*)  tools.py  spec.py  reconciler.py  planner.py
  stages/reconcile.py  act.py  plan.py  checks.py  runner.py (STAGES grows)
  http/slack.py
  config.py (+linear_api_key, notion_token, slack_bot_token, slack_signing_secret, github_token, github_repo)
  deps.py (+linear, notion, code, github, slack, actions, reconciler, planner)
fixtures/linear_seed.py  slack_manifest.json  notion/README.md
tests/fakes/fake_linear.py  fake_notion.py  fake_github.py  fake_slack.py  fake_agents.py (+FakeReconciler, FakePlanner)
tests/clients/ verify/ store/ agents/ stages/ http/ (mirrors)
```

---

### Task 1: `clients/linear.py` + `FakeLinear`

**Files:** Create `app/clients/linear.py`, `tests/fakes/fake_linear.py`; Test `tests/clients/test_linear.py`, `tests/fakes/test_fake_linear.py`

**Interfaces:**
```python
class LinearClient:
    def __init__(self, api_key: str, *, base_url: str = "https://api.linear.app/graphql") -> None
    async def get_issue(self, identifier: str) -> dict | None            # {id, identifier, title, description, state, priority, assignee:{id,name}|None, dueDate, url, updatedAt}
    async def search_issues(self, team_id: str, text: str, *, limit: int = 8) -> list[dict]
    async def list_states(self, team_id: str) -> list[dict]             # {id, name, type}
    async def list_members(self, team_id: str) -> list[dict]            # {id, name, email}
    async def create_issue(self, *, team_id: str, project_id: str | None, title: str, description: str,
                           assignee_id: str | None, priority: int | None, due_date: str | None) -> dict   # {id, identifier, url}
    async def update_issue(self, issue_id: str, fields: dict) -> dict   # assigneeId / priority / dueDate / stateId
    async def comment(self, issue_id: str, body: str) -> str            # comment id
```
Errors: any transport/GraphQL error → `SourceUnavailable("linear", detail)`; detail passes through `redact()`.
`FakeLinear(issues: list[dict], members: list[dict], states: list[dict])` implements the same methods in memory; records `writes: list[dict]` (`{"op": "create"|"update"|"comment", ...}`); `search_issues` is case-insensitive substring over title+description; `create_issue` mints `INV-<n>` identifiers.

**Tests (behavior sentences):**
- `test_get_issue_returns_none_for_an_unknown_identifier`
- `test_search_is_case_insensitive_over_title_and_description_and_respects_limit`
- `test_create_issue_records_the_write_and_mints_the_next_identifier`
- `test_update_and_comment_record_writes_against_an_existing_issue_only`
- `test_a_graphql_error_becomes_source_unavailable_with_a_redacted_detail` (real client against a `httpx.MockTransport`)
- `test_the_real_client_parses_the_documented_issue_shape` (MockTransport fixture JSON)

**Steps:** write fake tests → fake → real client tests with `httpx.MockTransport` → client → gates → commit `feat(clients): Linear GraphQL client and in-memory fake`.

---

### Task 2: `clients/notion.py` + `FakeNotion`; `clients/code.py`

**Interfaces:**
```python
class NotionClient:
    def __init__(self, token: str) -> None
    async def search(self, text: str, *, limit: int = 5) -> list[dict]          # {id, title, url}
    async def get_page_text(self, page_id: str) -> dict                          # {id, title, url, markdown}
    async def list_children(self, page_id: str) -> list[dict]                    # {id, title} (for bootstrap, Plan 3)

class CodeSearch:
    def __init__(self, repo_root: Path) -> None
    def grep(self, pattern: str, *, glob: str = "**/*.py", max_hits: int = 20) -> list[dict]   # {path, line, text}
    def read(self, path: str, start: int, end: int) -> str
    def exists(self, path: str, line: int | None = None) -> bool
```
`FakeNotion(pages: dict[str, dict])`. `CodeSearch` needs no fake — tests run over `fixtures/acme-invoicing`. Paths are repo-relative and jailed (`..` rejected).

**Tests:** `test_search_matches_titles_and_body_case_insensitively`, `test_get_page_text_flattens_blocks_to_markdown_headings_and_bullets`, `test_grep_finds_reminder_days_in_config_with_path_and_line`, `test_read_returns_the_requested_line_window`, `test_paths_outside_the_repo_are_rejected`, `test_exists_checks_the_line_is_within_the_file`.

**Commit:** `feat(clients): Notion client + fake; jailed code search over the fixture repo`.

---

### Task 3: `clients/github.py` + `FakeGitHub`

**Interfaces:**
```python
class GitHubClient:
    def __init__(self, token: str, repo: str) -> None                   # repo = "owner/name"
    async def find_prs_for_issue(self, identifier: str) -> list[dict]  # PRs whose title/body/branch mention INV-142; {number, state, merged, url, reviews, title}
    async def get_pr(self, number: int) -> dict | None
```
`FakeGitHub(prs: list[dict])`.

**Tests:** `test_prs_are_matched_by_issue_identifier_in_title_body_or_branch`, `test_reviews_count_and_merged_flag_are_exposed`, `test_an_api_error_becomes_source_unavailable`.

**Commit:** `feat(clients): GitHub PR lookup + fake`.

---

### Task 4: `clients/slack.py`, `clients/slack_blocks.py`, `FakeSlack`

**Interfaces:**
```python
def verify_slack_signature(signing_secret: str, headers: Mapping[str, str], raw_body: bytes, now_epoch: int) -> bool   # v0 HMAC, 5-min tolerance

class SlackClient:
    def __init__(self, bot_token: str) -> None
    async def post(self, channel: str, text: str, blocks: list[dict] | None = None, *, thread_ts: str | None = None) -> str   # ts
    async def update(self, channel: str, ts: str, text: str, blocks: list[dict] | None = None) -> None
    async def open_modal(self, trigger_id: str, view: dict) -> None
    async def user_info(self, user_id: str) -> dict | None            # {id, name, email}

# slack_blocks.py — pure builders
def call_summary_blocks(meeting: dict, created: list[dict], updated: list[dict], skipped: list[dict], conflicts: list[dict], actions: list[dict]) -> list[dict]
def revert_button(action_id: str) -> dict
def wrong_button(post_ref: str) -> dict
def wrong_modal(post_ref: str) -> dict
def plan_summary_blocks(tasks: list[dict], trimmed: list[str]) -> list[dict]
def nudge_text(template: str, **kw: str) -> str                         # delegates to kinds/templates
```
`FakeSlack()` records `posts`, `updates`, `modals`; `post` returns incrementing `ts`.

**Tests:** `test_a_correctly_signed_slack_request_verifies_and_a_stale_one_does_not`, `test_call_summary_blocks_have_one_revert_button_per_action_and_one_wrong_button`, `test_blocks_never_exceed_slacks_50_block_limit` (truncate with a "+N more" line), `test_fake_slack_records_posts_with_incrementing_ts`.

**Commit:** `feat(clients): Slack client, signature check, block builders, fake`.

---

### Task 5: `verify/ids.py`, `verify/roster.py`, `verify/priority.py`, `verify/dates.py`, `verify/caps.py`

**Interfaces:**
```python
# ids.py — the "zero fabricated identifiers" rule as code. Ref grammar:
#   linear:INV-142 | notion:<page_id> | fathom:<meeting_id>@<hh:mm:ss> | code:<path>:<line> | decision:<id> | wiki:<slug>
class IdGate:
    def __init__(self, *, linear: LinearLike, notion: NotionLike, code: CodeSearch, roster: list[dict],
                 decisions: DecisionStore, known_meetings: Callable[[str], Awaitable[bool]], wiki: WikiLike | None = None) -> None
    async def issue_exists(self, identifier: str) -> bool
    def person_exists(self, name: str) -> bool                             # roster names + aliases, case-insensitive
    async def ref_exists(self, ref: str) -> bool
    async def missing_refs(self, refs: Sequence[str]) -> list[str]
    async def exists(self, token: str) -> bool                             # for check_plan's id_exists: INV-… → issue, else person

# roster.py
def resolve_owner(name: str | None, roster: list[dict]) -> dict | None      # exact, alias, case-insensitive; None otherwise

# priority.py
@dataclass(frozen=True)
class PriorityVerdict: priority: int | None; note: str
def check_priority(proposed: int | None, evidence_quotes: Sequence[str], policy: dict) -> PriorityVerdict
#   inside band → as proposed; outside band with an escalation phrase in a quote → allowed, note says why;
#   outside band without → clamped to band edge, note says clamped; None → None

# dates.py
def resolve_due(due_iso: str | None, due_hint: str | None, evidence_quotes: Sequence[str]) -> str | None
#   only when reconcile supplied an ISO date AND a due_hint that appears (normalized) in a quote

# caps.py
@dataclass(frozen=True)
class CapsVerdict: ok: bool; defer_until: datetime | None; reason: str
def check_caps(kind: Literal["write", "ping"], counts_today: dict[str, int], now_local: datetime, policy: dict) -> CapsVerdict
#   kind write: daily_write_cap; kind ping: daily_ping_cap + quiet_hours (["20:00","08:00"] in project tz) → defer to window start
def next_window(now_local: datetime, quiet_hours: Sequence[str]) -> datetime
```

**Tests (selection):** `test_a_ref_with_an_unknown_issue_is_missing`, `test_code_refs_check_the_file_and_the_line`, `test_fathom_refs_are_valid_only_for_a_known_meeting`, `test_aliases_resolve_case_insensitively_and_unknown_names_do_not`, `test_priority_inside_the_band_passes_through`, `test_urgent_is_allowed_only_with_an_escalation_quote`, `test_priority_outside_the_band_without_evidence_is_clamped_and_noted`, `test_a_due_date_needs_both_an_iso_value_and_a_spoken_hint`, `test_pings_inside_quiet_hours_defer_to_the_window_start_in_the_project_timezone`, `test_the_daily_write_cap_defers_to_the_next_day`.

**Commit:** `feat(verify): id, roster, priority, date and caps gates`.

---

### Task 6: `store/actions.py`

**Interfaces:**
```python
class ActionStore:
    def __init__(self, db: Db, clock: Clock) -> None
    async def begin(self, *, task_id: str, project_id: str, kind: str, idempotency_key: str, inputs: dict,
                    citations: list[str], checks_passed: list[str]) -> str                       # pending
    async def finish(self, action_id: str, *, target_ids: dict, revert: dict) -> None           # done
    async def fail(self, action_id: str, error: str) -> None
    async def find_by_key(self, idempotency_key: str) -> Doc | None
    async def get(self, action_id: str) -> Doc | None
    async def mark_reverted(self, action_id: str, by: str) -> None
    async def counts_today(self, project_id: str, day: str) -> dict[str, int]                   # {"write": n, "ping": n}; slack.post to a person counts as ping
    async def list_since(self, project_id: str, since_iso: str) -> list[Doc]
```
**Tests:** `test_begin_creates_a_pending_action_with_its_idempotency_key`, `test_finish_records_targets_and_the_inverse_payload`, `test_find_by_key_returns_the_earlier_action_so_a_retry_can_skip_the_write`, `test_counts_today_separates_writes_from_pings`.

**Commit:** `feat(store): action audit log with idempotency lookup`.

---

### Task 7: Schemas, tools, `AgentSpec`, the reconciler agent

**Interfaces:**
```python
# agents/schemas.py additions
class Conflict(BaseModel): kind: Literal["code_vs_spec","spec_vs_call","ticket_vs_call","brain_vs_call"]; about: str; sides: list[Side]   # Side: claim, source(ref)
class ReconcileItem(BaseModel):
    index: int; title: str; description: str; disposition: Literal["new","update","duplicate_of"]; target_issue: str | None
    owner: str | None; priority: int | None; due: str | None; due_hint: str | None
    citations: list[str]; conflicts: list[Conflict]; facts: list[Fact]     # Fact: text, source
class ReconcileResult(BaseModel): items: list[ReconcileItem]; decision_conflicts: list[Conflict]

class PlanTask(BaseModel): key: str; kind: str; params: dict; due: str; depends_on: list[str] = []; reason: str; on_unmet: str = "none"; on_dep_failed: str = "skip"; context: dict = {}
class Plan(BaseModel): tasks: list[PlanTask]; supersedes: list[str] = []; notes: str = ""

# agents/tools.py — closures over deps; every tool returns a dict with "status"
def make_read_tools(*, linear, notion, code, roster, wiki=None) -> dict[str, Callable]
#   search_issues(text) get_issue(identifier) search_notion(text) get_notion_page(page_id) grep_code(pattern, glob) list_roster()
#   (+ search_wiki(text) get_page(slug) when wiki is given — Plan 3)
def make_planner_tools(*, linear, github, queue, actions, project_id, wiki=None) -> dict[str, Callable]
#   get_issue, list_open_tasks(), list_recent_results(days=3), get_pr_status(issue)

# agents/spec.py
@dataclass(frozen=True)
class AgentSpec: name: str; model: str; instruction: str | Callable; tools: list[Callable]; output_schema: type[BaseModel]; max_tool_calls: int = 12; max_output_tokens: int = 8192
def build_agent(spec: AgentSpec) -> LlmAgent        # attaches before_tool_callback that denies names not in spec.tools (logged) and counts calls

# agents/reconciler.py
RECONCILER_INSTRUCTION: str   # consult brain first (when available), then Linear, Notion, code; propose owner from roster only; due only if spoken; cite everything; report conflicts, never resolve
class GeminiReconciler:  # Protocol Reconciler: run(payload) -> dict ; payload = {items, decisions, meeting, roster, project, feedback}
```
`FakeReconciler(results)` in `tests/fakes/fake_agents.py`.

**Tests:** `test_the_tool_allowlist_denies_anything_not_in_the_spec_and_keeps_running`, `test_tool_call_budget_is_enforced`, `test_read_tools_return_status_dicts_and_never_raise_to_the_model` (SourceUnavailable → `{"status":"unavailable"}`), `test_reconcile_result_validates_the_documented_shape`, `@live test_the_real_reconciler_flags_the_reminders_conflict_on_the_fixtures`.

**Commit:** `feat(agents): reconcile/plan schemas, read-only tools with allowlist, reconciler agent`.

---

### Task 8: `stages/reconcile.py`

**Behavior:** load parent extract result (`payload.extract_task_id`) → build payload → `deps.reconciler.run` → validate → **ids gate** on every `target_issue`, `owner`, `citations`, conflict sources (bounce once with the specific missing refs) → items still failing become `unverified` → `SourceUnavailable` during tools marks affected items `unverified` and re-enqueues one `reconcile` retry at +30 min (once, via `payload.retry=1`) → result `{items: [...verified], unverified: [...], decision_conflicts, meeting}` → children: `act` (always, even with zero verified items — Act posts the summary), and (Plan 3) `wiki`.

**Tests:** `test_verified_items_flow_to_act_with_their_citations`, `test_an_item_citing_an_unknown_issue_is_bounced_once_then_marked_unverified`, `test_a_source_outage_marks_items_unverified_and_schedules_exactly_one_retry`, `test_duplicates_are_kept_as_duplicate_dispositions_not_dropped`.

**Commit:** `feat(stages): reconcile — brain/Linear/Notion/code triangulation with the id gate`.

---

### Task 9: `stages/act.py`

**Behavior (deterministic):** for each verified item in order: `resolve_owner` → `check_priority` → `resolve_due` → `check_caps("write")` (defer the whole task to the window if exceeded; items already written stay written) → `idempotency_key(root_event_id, index, kind)`; `actions.find_by_key` → skip if done → `begin` → write (`create_issue` with description built by `build_description(item, meeting, decision_ids, key)` incl. hidden footer; or `comment` for update/duplicate) → `finish` with `revert` (`{"op": "archive"|"unassign"|"set_priority"|"set_due"|"delete_comment", ...}`) → after the batch: one Slack post via `call_summary_blocks` (its own action, kind `slack.post`, revert = edit to "reverted") → conflicts posted in the same message as "sources disagree" → children: `plan` with `context = {created: [{identifier, owner, due, title}], updated: [...], decision_ids, meeting}`.

**Tests:** `test_each_item_becomes_exactly_one_linear_write_with_a_footer_and_citations`, `test_a_retry_after_a_crash_finds_the_key_and_does_not_duplicate`, `test_an_owner_not_in_the_roster_leaves_the_issue_unassigned_and_says_who_was_named`, `test_urgent_without_an_escalation_quote_is_clamped_to_the_band`, `test_the_daily_write_cap_defers_the_remainder_and_keeps_what_was_written`, `test_conflicts_are_posted_not_resolved`, `test_the_summary_has_one_revert_button_per_action`, `test_act_enqueues_plan_with_the_created_issues_as_context`.

**Commit:** `feat(stages): act — gated, idempotent Linear writes and the Slack summary`.

---

### Task 10: `http/slack.py` — interactions

**Routes:** `POST /slack/interactions` (form-encoded `payload`): `block_actions` → `revert:<action_id>` → replay `revert` via the matching client, `actions.mark_reverted`, `queue.cancel` any open tasks whose `context.created` includes the reverted identifier, edit the post; `wrong:<post_ref>` → `open_modal(wrong_modal)`; `view_submission` → `corrections` doc (Plan 3 wires the prompt side; today: store + ack). `POST /slack/events` → url_verification challenge + `app_mention` storing an `events` doc for Plan 4's report command. Signature verified first; 401 otherwise.

**Tests:** `test_unsigned_interactions_are_rejected`, `test_revert_replays_the_inverse_and_marks_the_action_reverted`, `test_revert_of_a_create_cancels_its_follow_up_tasks`, `test_wrong_opens_the_modal`, `test_url_verification_echoes_the_challenge`.

**Commit:** `feat(http): Slack interactions — revert, wrong, events`.

---

### Task 11: Planner agent + `stages/plan.py`

**Behavior:** payload context from act (or daily_review, Plan 3) → planner tools → `deps.planner.run` → `Plan.model_validate` → `check_plan(plan, now, policy, open_tasks=queue.open_count, existing_ids=<open task id exists>, id_exists=IdGate.exists)` → if `rejected` or `reasons`: bounce once with them → trim to the verdict's `tasks` → `StageResult(result={plan_notes, accepted: keys, rejected, reasons}, children=verdict.tasks)`; the runner calls `queue.complete(task, result, children, supersedes=plan.supersedes ∩ open ids)` — extend `StageResult` with `supersedes: list[str] = []` and `runner.run_task` to pass it. Post one Slack line via `plan_summary_blocks`: "Planned 3 checks for INV-142 (Thu, Fri, Mon)".
Default when the planner returns nothing usable: `default_followups(context, policy)` builds the `-1d/0d/+3d` chain deterministically.

**Tests:** `test_a_valid_plan_becomes_blocked_and_queued_tasks_with_resolved_keys`, `test_an_invalid_plan_is_bounced_once_then_trimmed_and_the_trim_is_reported`, `test_supersedes_only_touches_open_tasks_of_this_project`, `test_with_no_usable_plan_the_default_follow_up_chain_is_used`, `@live test_the_real_planner_orders_pr_checks_after_the_in_progress_check`.

**Commit:** `feat(stages): plan — the planner proposes, the plan gate decides, the queue materialises`.

---

### Task 12: `stages/checks.py` — `check_issue_state`, `check_pr_exists`; `kinds/templates.py`

**Interfaces:**
```python
# checks.py — one executor per kind, all deterministic
async def run_check(task: Doc, deps: Deps) -> StageResult     # dispatch on task["kind"]; result = {met: bool, observed: dict, acted: list[action_id]}
async def check_issue_state(task, deps) -> tuple[bool, dict]
async def check_pr_exists(task, deps) -> tuple[bool, dict]
async def on_unmet(task, deps, observed) -> list[str]          # nudge_assignee / nudge_reviewer / escalate_channel → check_caps("ping") → templated Slack post as an action; deferred → queue.defer

# kinds/templates.py
TEMPLATES: dict[str, str]   # "issue_not_started": "…{person}… {issue} …", "pr_missing", "pr_unreviewed", "pr_unmerged", "escalate_overdue", "still_open"
def render(template: str, **kw: str) -> str      # KeyError on unknown template — templates are code
```
`runner.STAGES` gains `check_issue_state` and `check_pr_exists` → `run_check`.

**Tests:** `test_a_met_check_records_observed_state_and_acts_on_nothing`, `test_an_unmet_check_sends_exactly_one_templated_nudge_within_caps`, `test_an_unmet_check_in_quiet_hours_is_deferred_not_dropped`, `test_a_source_outage_records_observed_unavailable_and_does_not_nudge`, `test_pr_exists_matches_by_issue_identifier`.

**Commit:** `feat(kinds): issue-state and PR-exists checks with templated, capped nudges`.

---

### Task 13: Fixtures for day 2 — Linear seed, Notion pages, GitHub repo, Slack app

- `fixtures/linear_seed.py`: creates 15 issues in team `INV` incl. `INV-104 "Overdue invoices dashboard for finance"` (stale, Backlog), a closed twin `INV-088 "Reminder cadence experiment"`, and mixed states; writes identifiers back into `fixtures/projects/acme.json` (`seed_identifiers`). Idempotent via a `[seed]` label.
- Notion: three pages by hand (Reminders PRD — **5 days**; Invoice Export spec — **includes payments**; Release process); ids into `acme.json`; `fixtures/notion/README.md` holds the page text so the eval set has ground truth.
- GitHub: push `fixtures/acme-invoicing` to a public repo `acme-invoicing`; `PM_GITHUB_REPO=<owner>/acme-invoicing`.
- Slack: `fixtures/slack_manifest.json` (bot scopes `chat:write`, `chat:write.customize`, `commands`, `app_mentions:read`, `users:read`, `users:read.email`; interactivity URL `<run>/slack/interactions`; events URL `<run>/slack/events`); install to the Acme workspace; channel `#product` id into `acme.json`; roster `slack_id`s and Linear `linear_user_id`s filled.
- `scripts/seed_project.py` re-run.

**Commit:** `feat(fixtures): Linear seed, Notion ground truth, Slack manifest, workspace ids`.

---

### Task 14: Config, deps, deploy for day 2; end-to-end run

- `config.py` + `.env.example`: `linear_api_key`, `notion_token`, `slack_bot_token`, `slack_signing_secret`, `github_token`, `github_repo`.
- `deps.py`/`main.py`: construct clients; `IdGate`; `ActionStore`; `GeminiReconciler`, `GeminiPlanner`; `has_linear()` etc. gate the stages that need them (a missing Linear key makes `act` fail closed with a clear reason, not a crash).
- `deploy.sh`: five new `--set-secrets`, `PM_GITHUB_REPO` env.
- Record call 1 again (or reuse the stored event: `scripts/replay_event.py <event_id>` enqueues a fresh `extract` for an existing event — useful all week).
- **Demo check:** Slack summary with 3–4 created issues, one unassigned "Sam", one urgent (Priya, CSV export), one conflict posted (reminders 7/5/3), one duplicate comment on INV-104; the planner's line; `tasks` collection shows a blocked/queued graph; click revert on one action and watch Linear + the task graph react.

**Commit:** `feat: day-2 wiring and deploy; event replay script`.

---

## Self-review against the spec
§7.2 reconcile (Task 7–8), §7.3 act (Task 9), §7.4 plan (Task 11), §7.5 two kinds + templates (Task 12), §10 rows for ids/roster/priority/caps/idempotency/partial batch/revert (Tasks 5, 6, 9, 10), §12 Slack surface (Tasks 4, 10), §13 Linear/Notion/GitHub/Slack fixtures (Task 13). Wiki tools and `daily_review` are Plan 3 by design. `StageResult` gains `supersedes` in Task 11 — Plan 1's `StageResult` keeps its default so Plan 1 tests stay green.

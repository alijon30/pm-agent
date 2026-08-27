# PM Agent — Plan 1 of 4: Foundation (Day 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A deployed Cloud Run service that receives a real Fathom webhook, stores the event idempotently, runs the `extract` stage through a durable **task-graph** queue (dependencies, promotion, cascade cancel, plan materialisation), validates planner output through the plan gate, and leaves evidence-gated decisions and action items in Firestore — with the fake company's fixtures ready for day 2.

**Architecture:** One FastAPI service. Firestore is the queue and the audit store; a `/tick` endpoint (called by Cloud Scheduler every minute) claims due tasks with a lease and runs the stage for each. The `extract` stage calls an ADK `LlmAgent` (Gemini, fixed output schema, no tools) behind a `Protocol` so every test uses a fake; a deterministic evidence gate drops any item without a verbatim transcript quote. Everything crossing the task boundary is JSON-native.

**Tech Stack:** Python 3.12 · uv · FastAPI · google-cloud-firestore (async) · google-adk · google-genai · pydantic v2 · pydantic-settings · pytest + pytest-asyncio · ruff · mypy (strict) · import-linter · Cloud Run · Firestore · Cloud Scheduler · Secret Manager.

**Spec:** `docs/superpowers/specs/2026-08-26-pm-agent-design.md` (rev 2) — this plan implements §4–§6 (task-graph queue), §7.1, §7.4's plan gate and §7.5's kinds registry (schemas only; executors are Plan 2), §8 (extractor only), §10 (queue/webhook/stage/plan rows), §13 (fixtures), §15–§16, and day 1 of §17. Plans 2–4 (days 2–4) are written at the start of each day, argued from the spec and from what this plan actually produced.

## Global Constraints

- Python `>=3.12`; dependency manager is **uv**; run everything as `uv run …`.
- Four CI gates and nothing else: `uv run ruff check . && uv run mypy app && uv run lint-imports && uv run pytest -q`.
- ruff rule set: `["E4", "E7", "E9", "F", "I", "W", "B", "UP"]`, line length 100.
- mypy `strict = true` on `app/`; **no debt list**. Third-party packages without stubs get `ignore_missing_imports`, nothing else.
- Layering (import-linter): `core`, `store`, `verify`, `clients`, `kinds` never import `agents`, `stages`, `http`, `deps`, `main`; `agents` imports only `clients`, `core`, `kinds` (plus its own package); stages never import each other (independence contract added in Plan 2 when a second stage exists).
- Everything crossing a task boundary is JSON-native: dicts, lists, str, int, float, bool, None. Timestamps are ISO-8601 UTC strings with second precision (`2026-08-27T09:00:00+00:00`) so string comparison equals time comparison.
- Never log or store a secret value; errors that may reach a human pass through `redact()`.
- Test names are behavior sentences; fakes are hand-rolled (no `unittest.mock` for our own seams); comments say *why*.
- Model IDs come from config: `PM_MODEL_FAST=gemini-3.5-flash-lite`, `PM_MODEL_STRONG=gemini-3.5-flash`; verified via `models.list()` in Task 0 before use.
- Git: stage files **by name** (never `git add -A`); no AI attribution in commit messages; conventional prefixes `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- Firestore document IDs must not contain `/`; we use `provider:provider_event_id` for events and `uuid4().hex` for tasks.

---

## File structure (what Plan 1 creates)

```
pm-agent/
  pyproject.toml            deps, ruff, mypy, import-linter, pytest config
  .python-version           3.12
  .env.example              every PM_* key with a comment; no values
  .github/workflows/ci.yml  the four gates
  app/
    __init__.py
    py.typed
    config.py               Settings (pydantic-settings, PM_ prefix)
    deps.py                 Deps dataclass: everything a stage or route needs
    main.py                 create_app(deps), build_deps(settings), create_default_app()
    core/
      __init__.py
      clock.py              Clock protocol, SystemClock, iso(), parse_iso()
      keys.py               new_id(), event_doc_id(), idempotency_key()
      redact.py             redact()
      errors.py             PmError, SourceUnavailable, GateFailed
    store/
      __init__.py
      db.py                 Db protocol (get/create/set/update/query/count/cas)
      firestore.py          FirestoreDb — the only file that imports google.cloud.firestore
      events.py             EventStore.record()/get()/note()
      tasks.py              TaskQueue — enqueue/due/claim/complete(+plan)/fail/defer/cancel/promote_ready
      decisions.py          DecisionStore.add_many()
      projects.py           ProjectStore.get()/default()/upsert()
    verify/
      __init__.py
      lineage.py            check_lineage()
      evidence.py           normalize(), quote_in_transcript(), check_evidence()
      plan.py               check_plan() — the plan gate
    kinds/
      __init__.py
      base.py               KindSpec, StrictParams
      registry.py           KINDS, get_kind(), validate_params()
    clients/
      __init__.py
      fathom.py             verify_signature(), parse_meeting(), transcript_plain(), render_transcript()
    agents/
      __init__.py
      schemas.py            Evidence, Decision, ActionItem, OpenQuestion, ExtractResult
      protocols.py          Extractor, Triage protocols
      triage.py             PassthroughTriage (Gemma arrives in Plan 4)
      adk_runner.py         run_agent_once()
      extractor.py          GeminiExtractor, EXTRACTOR_INSTRUCTION
    stages/
      __init__.py
      base.py               StageResult, StageHandler type
      extract.py            run(), select_with_context()
      runner.py             STAGES, run_task()
    http/
      __init__.py
      webhooks.py           POST /webhooks/fathom
      tick.py               POST /tick
  tests/
    conftest.py             fixtures: clock, db, settings, deps, client
    fakes/
      __init__.py
      fake_db.py            FakeDb
      fake_clock.py         FakeClock
      fake_agents.py        FakeExtractor
    core/  store/  verify/  kinds/  clients/  agents/  stages/  http/   (mirrors app/)
    fixtures/
      fathom_webhook_sample.json   hand-built from the documented Meeting schema; replaced by a real capture in Task 14
  fixtures/
    acme-invoicing/         the fake product's repo
    transcripts/01-q3-planning.md
    roster.json
    projects/acme.json
  scripts/
    seed_project.py
    list_models.py
  deploy/
    Dockerfile  deploy.sh  scheduler.sh  secrets.md
```

---

### Task 0: Manual prerequisites (accounts, project, keys)

No code. Everything below is yours to do once; later tasks assume it. Tick each as you go.

**Files:**
- Create: `deploy/secrets.md` (the checklist below, kept in the repo without values)

- [ ] **Step 1: Google Cloud project**

```bash
gcloud auth login
gcloud projects create pm-agent-hack-2026 --name="pm-agent"     # or pick your own id
gcloud config set project pm-agent-hack-2026
gcloud billing accounts list                                    # then link one:
gcloud billing projects link pm-agent-hack-2026 --billing-account=XXXXXX-XXXXXX-XXXXXX
gcloud services enable run.googleapis.com firestore.googleapis.com cloudscheduler.googleapis.com \
  secretmanager.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  cloudtrace.googleapis.com
gcloud firestore databases create --location=us-central1 --type=firestore-native
```

Also submit the hackathon credits form (https://forms.gle/5PtXmw1dSbDnpYke9) with this project id.

- [ ] **Step 2: Gemini API key and model check**

Create a key at https://aistudio.google.com/apikey. Then:

```bash
export GOOGLE_API_KEY=...          # shell only; never in a file
export GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

Model verification runs in Task 1 Step 8 once the project exists (`scripts/list_models.py`).

- [ ] **Step 3: Secrets in Secret Manager (values only ever live here and in your shell)**

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))' | gcloud secrets create pm-tick-token --data-file=-
printf '%s' "$GOOGLE_API_KEY" | gcloud secrets create pm-google-api-key --data-file=-
# pm-fathom-webhook-secret is created in Task 14 after the webhook exists (Fathom returns the secret).
```

- [ ] **Step 4: Fathom**

Fathom account with API access (Settings → API Access → generate key). Export it in your shell as `FATHOM_API_KEY`. The webhook itself is created in Task 14, after the service has a URL.

- [ ] **Step 5: Fake-company workspaces (needed from day 2; create today so invites propagate)**

- Slack: new workspace "Acme Invoicing"; invite 4 fictional members (you'll own their mailboxes — use `+alias` addresses).
- Linear: new workspace, team key `INV`, one project "Q3 Billing"; note the team id and project id for `fixtures/projects/acme.json` (Plan 2 seeds issues).
- Notion: new workspace; create three pages (Reminders PRD — says **5 days**; Invoice Export spec; Release process). Note page ids.
- Google Meet + Fathom: schedule two 5-minute calls for tomorrow morning with one colleague (or two browsers); read `fixtures/transcripts/01-q3-planning.md` (Task 13) aloud with Fathom recording.

- [ ] **Step 6: Local tooling**

```bash
brew install uv gh              # if missing
uv python install 3.12
```

---

### Task 1: Repository scaffold, tooling, CI

**Files:**
- Create: `pyproject.toml`, `.python-version`, `.env.example`, `.github/workflows/ci.yml`, `app/__init__.py`, `app/py.typed`, `app/{core,store,verify,clients,agents,stages,http}/__init__.py`, `tests/__init__.py`, `tests/fakes/__init__.py`, `tests/test_smoke.py`, `scripts/list_models.py`

**Interfaces:**
- Produces: the four gates runnable and green on an empty package.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "pm-agent"
version = "0.1.0"
description = "Autonomous PM agent: a product call ends → reconciled, cited Linear issues → self-scheduled follow-ups"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn>=0.30",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "google-cloud-firestore>=2.16",
    "google-adk>=1.0",
    "google-genai>=1.0",
    "httpx>=0.27",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "ruff>=0.5",
    "mypy>=1.10",
    "import-linter>=2.0",
]

[build-system]
requires = ["uv_build>=0.9,<0.10"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-name = "app"
module-root = ""

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]
markers = ["live: hits real Google APIs; skipped unless GOOGLE_API_KEY is set"]

[tool.ruff]
line-length = 100
src = ["app", "tests", "scripts"]
extend-exclude = ["fixtures"]

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "W", "B", "UP"]

[tool.mypy]
python_version = "3.12"
strict = true
mypy_path = "app"

[[tool.mypy.overrides]]
# Third-party packages that ship no type stubs. This is NOT a debt list for our code.
module = ["google.cloud.*", "google.adk.*", "google.genai.*", "google.api_core.*"]
ignore_missing_imports = true

[tool.importlinter]
root_packages = ["app"]

[[tool.importlinter.contracts]]
name = "core, store, verify, clients and kinds never import the model side or the wiring"
type = "forbidden"
source_modules = ["app.core", "app.store", "app.verify", "app.clients", "app.kinds"]
forbidden_modules = ["app.agents", "app.stages", "app.http", "app.deps", "app.main"]

[[tool.importlinter.contracts]]
name = "agents import only clients, core and kinds — the model cannot reach the store or the queue"
type = "forbidden"
source_modules = ["app.agents"]
forbidden_modules = ["app.store", "app.verify", "app.stages", "app.http", "app.deps", "app.main"]
```

- [ ] **Step 2: Write `.python-version`, `.env.example`, package markers**

`.python-version`:
```
3.12
```

`.env.example`:
```bash
# Every key is optional locally; a missing key disables that feature (see app/config.py).
PM_GCP_PROJECT=pm-agent-hack-2026
PM_FIRESTORE_DATABASE=(default)
PM_DEFAULT_PROJECT_SLUG=acme
PM_MODEL_FAST=gemini-3.5-flash-lite
PM_MODEL_STRONG=gemini-3.5-flash
# Secrets: set in your shell or Secret Manager, never in a committed file.
# PM_FATHOM_WEBHOOK_SECRET=whsec_...
# PM_TICK_TOKEN=...
# GOOGLE_API_KEY=...            # read by ADK / google-genai directly
# GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

```bash
mkdir -p app/core app/store app/verify app/kinds app/clients app/agents app/stages app/http tests/fakes tests/kinds scripts
for d in app app/core app/store app/verify app/kinds app/clients app/agents app/stages app/http tests tests/fakes tests/kinds; do : > "$d/__init__.py"; done
: > app/py.typed
```

- [ ] **Step 3: Write `tests/test_smoke.py`**

```python
def test_the_app_package_imports() -> None:
    import app

    assert app is not None
```

- [ ] **Step 4: Write `.github/workflows/ci.yml`**

```yaml
name: ci
on:
  push:
  pull_request:
jobs:
  gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv python install 3.12
      - run: uv sync --dev
      - run: uv run ruff check .
      - run: uv run mypy app
      - run: uv run lint-imports
      - run: uv run pytest -q
```

- [ ] **Step 5: Write `scripts/list_models.py`**

```python
"""Print the Gemini/Gemma model ids visible to this API key. Run once on day 1 and paste the
result into the README's "verified on" line; config defaults must be in this list."""

from google import genai


def main() -> None:
    client = genai.Client()
    names = sorted(m.name.removeprefix("models/") for m in client.models.list())
    for name in names:
        if name.startswith(("gemini-3", "gemma")):
            print(name)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Install and run the four gates**

```bash
uv sync --dev
uv run ruff check . && uv run mypy app && uv run lint-imports && uv run pytest -q
```
Expected: all four pass; pytest reports `1 passed`.

- [ ] **Step 7: Create `README.md` stub** (one paragraph; the real README is Plan 4)

```markdown
# pm-agent

Autonomous product-manager agent. A product call ends; the agent extracts decisions and action
items, reconciles them against Linear, Notion and the codebase, files cited issues, and schedules
its own follow-ups. Built for the All Things Agentic Hackathon 2026 (The Taskmaster).

Design: `docs/superpowers/specs/2026-08-26-pm-agent-design.md`.

    uv sync --dev
    uv run ruff check . && uv run mypy app && uv run lint-imports && uv run pytest -q
```

- [ ] **Step 8: Verify model ids**

```bash
uv run python scripts/list_models.py
```
Expected: the list contains `gemini-3.5-flash-lite` and `gemini-3.5-flash`. If either is missing, change the defaults in `.env.example` and (Task 3) `config.py` to ids that are present and note it in the README.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml .python-version .env.example .github/workflows/ci.yml README.md uv.lock \
  app/__init__.py app/py.typed app/core/__init__.py app/store/__init__.py app/verify/__init__.py \
  app/kinds/__init__.py app/clients/__init__.py app/agents/__init__.py app/stages/__init__.py \
  app/http/__init__.py tests/__init__.py tests/fakes/__init__.py tests/kinds/__init__.py \
  tests/test_smoke.py scripts/list_models.py
git commit -m "chore: scaffold pm-agent with uv, the four gates and CI"
```

---

### Task 2: `core/` — clock, keys, redact, errors

**Files:**
- Create: `app/core/clock.py`, `app/core/keys.py`, `app/core/redact.py`, `app/core/errors.py`, `tests/fakes/fake_clock.py`
- Test: `tests/core/test_clock.py`, `tests/core/test_keys.py`, `tests/core/test_redact.py`

**Interfaces:**
- Produces: `Clock` protocol with `now() -> datetime`; `SystemClock`; `iso(dt) -> str`; `parse_iso(s) -> datetime`; `new_id() -> str`; `event_doc_id(provider, provider_event_id) -> str`; `idempotency_key(root_event_id, item_index, kind) -> str`; `redact(text) -> str`; exceptions `PmError`, `SourceUnavailable(source, detail)`, `GateFailed`. Test fake: `FakeClock(start)` with `advance(**timedelta_kwargs)`.

- [ ] **Step 1: Write the failing tests**

`tests/core/test_clock.py`:
```python
from datetime import UTC, datetime

from app.core.clock import iso, parse_iso
from tests.fakes.fake_clock import FakeClock


def test_iso_renders_utc_with_second_precision_so_strings_sort_like_times() -> None:
    a = datetime(2026, 8, 27, 9, 0, 0, 123456, tzinfo=UTC)
    b = datetime(2026, 8, 27, 9, 0, 1, tzinfo=UTC)
    assert iso(a) == "2026-08-27T09:00:00+00:00"
    assert iso(a) < iso(b)


def test_parse_iso_round_trips_and_normalises_to_utc() -> None:
    dt = parse_iso("2026-08-27T11:00:00+02:00")
    assert dt == datetime(2026, 8, 27, 9, 0, 0, tzinfo=UTC)
    assert iso(dt) == "2026-08-27T09:00:00+00:00"


def test_fake_clock_advances_deterministically() -> None:
    clock = FakeClock(datetime(2026, 8, 27, 9, 0, tzinfo=UTC))
    clock.advance(minutes=16)
    assert iso(clock.now()) == "2026-08-27T09:16:00+00:00"
```

`tests/core/test_keys.py`:
```python
from app.core.keys import event_doc_id, idempotency_key, new_id


def test_new_ids_are_unique_hex_and_safe_as_firestore_doc_ids() -> None:
    a, b = new_id(), new_id()
    assert a != b
    assert len(a) == 32 and "/" not in a


def test_event_doc_id_is_deterministic_per_provider_event() -> None:
    assert event_doc_id("fathom", "msg_123") == "fathom:msg_123"
    assert event_doc_id("fathom", "msg_123") == event_doc_id("fathom", "msg_123")


def test_idempotency_key_is_stable_and_changes_with_any_input() -> None:
    k = idempotency_key("fathom:msg_123", 0, "linear.create_issue")
    assert k == idempotency_key("fathom:msg_123", 0, "linear.create_issue")
    assert len(k) == 16
    assert k != idempotency_key("fathom:msg_123", 1, "linear.create_issue")
    assert k != idempotency_key("fathom:msg_123", 0, "linear.assign")
```

`tests/core/test_redact.py`:
```python
from app.core.redact import redact


def test_known_secret_shapes_are_redacted_but_surrounding_text_survives() -> None:
    text = (
        "slack xoxb-123-abc failed; linear lin_api_ABC123; notion ntn_ZZZ; "
        "fathom whsec_QUJDMTIz; google AIzaSyABCDEFGHIJKLMNOPQRSTUVWX; Bearer eyJhbGciOi.xx"
    )
    out = redact(text)
    for token in ("xoxb-123-abc", "lin_api_ABC123", "ntn_ZZZ", "whsec_QUJDMTIz",
                  "AIzaSyABCDEFGHIJKLMNOPQRSTUVWX", "eyJhbGciOi.xx"):
        assert token not in out
    assert "slack" in out and "failed" in out and "[redacted]" in out


def test_ordinary_text_is_unchanged() -> None:
    assert redact("INV-142 moved to In Progress") == "INV-142 moved to In Progress"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/core -q
```
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.clock'` (and siblings).

- [ ] **Step 3: Write the implementations**

`app/core/clock.py`:
```python
"""Time, injectable. Everything that reads the clock takes a Clock so tests can move time."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def iso(dt: datetime) -> str:
    """UTC, second precision, fixed width — so Firestore string comparison equals time
    comparison and no document ever needs a Timestamp type."""
    return dt.astimezone(UTC).replace(microsecond=0).isoformat()


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)
```

`tests/fakes/fake_clock.py`:
```python
from __future__ import annotations

from datetime import datetime, timedelta


class FakeClock:
    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now += timedelta(**kwargs)
```

`app/core/keys.py`:
```python
"""Identifiers. Deterministic where idempotency depends on it, random otherwise."""

from __future__ import annotations

import hashlib
import uuid


def new_id() -> str:
    return uuid.uuid4().hex


def event_doc_id(provider: str, provider_event_id: str) -> str:
    """Doc id for an inbound event. Creating it twice fails the second time, which is how a
    redelivered webhook becomes a no-op without any extra bookkeeping."""
    return f"{provider}:{provider_event_id}"


def idempotency_key(root_event_id: str, item_index: int, kind: str) -> str:
    """Stable per (call, item, action kind). Stamped into the Linear issue so a retried Act can
    recognise its own earlier write."""
    raw = f"{root_event_id}|{item_index}|{kind}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]
```

`app/core/redact.py`:
```python
"""Strip credential-shaped substrings before text is logged, stored, or shown to a human."""

from __future__ import annotations

import re

_PATTERNS = [
    re.compile(p)
    for p in (
        r"xox[abpe]-[A-Za-z0-9-]+",          # Slack tokens
        r"lin_api_[A-Za-z0-9]+",             # Linear
        r"ntn_[A-Za-z0-9]+",                 # Notion
        r"whsec_[A-Za-z0-9+/=]+",            # webhook secrets
        r"AIza[0-9A-Za-z_-]{20,}",           # Google API keys
        r"Bearer\s+[A-Za-z0-9._-]+",         # bearer tokens
    )
]


def redact(text: str) -> str:
    out = text
    for pattern in _PATTERNS:
        out = pattern.sub("[redacted]", out)
    return out
```

`app/core/errors.py`:
```python
"""Exceptions whose messages are safe to surface after redact()."""

from __future__ import annotations


class PmError(Exception):
    """Base class. Message is intended for humans and must never carry a secret value."""


class SourceUnavailable(PmError):
    """A read source (Linear, Notion, code) could not be reached. The model must not infer."""

    def __init__(self, source: str, detail: str = "") -> None:
        self.source = source
        self.detail = detail
        super().__init__(f"{source} unavailable" + (f": {detail}" if detail else ""))


class GateFailed(PmError):
    """A deterministic gate refused an item. Carries the specific reason for the one bounce."""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/core -q && uv run mypy app && uv run ruff check .
```
Expected: `6 passed`; mypy and ruff clean.

- [ ] **Step 5: Commit**

```bash
git add app/core/clock.py app/core/keys.py app/core/redact.py app/core/errors.py \
  tests/fakes/fake_clock.py tests/core/test_clock.py tests/core/test_keys.py tests/core/test_redact.py
git commit -m "feat(core): clock, ids, redaction and error types"
```

---

### Task 3: `config.py` — Settings

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Settings` with fields `gcp_project: str`, `firestore_database: str`, `fathom_webhook_secret: str`, `tick_token: str`, `default_project_slug: str`, `model_fast: str`, `model_strong: str`, `stage_timeout_seconds: int`, `lease_minutes: int`, `tick_batch: int`; env prefix `PM_`; `Settings.for_tests(**overrides)` classmethod that ignores `.env`.

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:
```python
import pytest

from app.config import Settings


def test_defaults_are_sane_and_secrets_are_empty_by_default() -> None:
    s = Settings.for_tests()
    assert s.default_project_slug == "acme"
    assert s.model_fast.startswith("gemini-")
    assert s.fathom_webhook_secret == ""
    assert s.tick_token == ""
    assert s.lease_minutes == 15
    assert s.stage_timeout_seconds == 600


def test_env_overrides_use_the_pm_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PM_TICK_TOKEN", "t0k3n")
    monkeypatch.setenv("PM_LEASE_MINUTES", "20")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.tick_token == "t0k3n"
    assert s.lease_minutes == 20
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_config.py -q
```
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config'`.

- [ ] **Step 3: Write `app/config.py`**

```python
"""Env-only configuration. A missing secret disables the feature that needs it; nothing else
about a missing key is ever fatal, so a partial .env still boots."""

from __future__ import annotations

from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PM_", env_file=".env", extra="ignore")

    gcp_project: str = ""
    firestore_database: str = "(default)"

    # Secrets — empty means "feature off" (webhook rejects everything; tick rejects everything).
    fathom_webhook_secret: str = ""
    tick_token: str = ""

    default_project_slug: str = "acme"

    # Verified against models.list() on day 1 (scripts/list_models.py).
    model_fast: str = "gemini-3.5-flash-lite"
    model_strong: str = "gemini-3.5-flash"

    stage_timeout_seconds: int = 600
    lease_minutes: int = 15
    tick_batch: int = 10

    @classmethod
    def for_tests(cls, **overrides: Any) -> Settings:
        """Ignore any local .env so tests never depend on the developer's machine."""
        return cls(_env_file=None, **overrides)  # type: ignore[call-arg]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -q && uv run mypy app
```
Expected: `2 passed`; mypy clean.

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: env-only Settings with PM_ prefix"
```

---

### Task 4: `store/db.py` protocol, `FakeDb`, `FirestoreDb`

**Files:**
- Create: `app/store/db.py`, `app/store/firestore.py`, `tests/fakes/fake_db.py`
- Test: `tests/store/test_fake_db.py`, `tests/store/test_firestore_live.py`

**Interfaces:**
- Produces:
  ```python
  Doc = dict[str, Any]                      # always includes "id"
  Filter = tuple[str, str, Any]             # (field, op, value); op in ==, <, <=, >, >=, in
  Predicate = Callable[[Doc], bool]
  Updater = Callable[[Doc], dict[str, Any]]
  Create = tuple[str, str, dict[str, Any]]  # (collection, doc_id, data)
  Update = tuple[str, str, dict[str, Any]]  # (collection, doc_id, fields)

  class Db(Protocol):
      async def get(self, collection: str, doc_id: str) -> Doc | None
      async def create(self, collection: str, doc_id: str, data: dict[str, Any]) -> bool   # False if exists
      async def set(self, collection: str, doc_id: str, data: dict[str, Any]) -> None
      async def update(self, collection: str, doc_id: str, fields: dict[str, Any]) -> None
      async def query(self, collection: str, filters: Sequence[Filter], *, order_by: str | None = None, limit: int | None = None) -> list[Doc]
      async def count(self, collection: str, filters: Sequence[Filter]) -> int
      async def cas(self, collection: str, doc_id: str, predicate: Predicate, updater: Updater, creates: Sequence[Create] = (), updates: Sequence[Update] = ()) -> bool
  ```
  Ops: `==`, `<`, `<=`, `>`, `>=`, `in`, `array_contains`.
  `FakeDb()` implements it in memory; `FirestoreDb(project, database)` implements it on Firestore.

- [ ] **Step 1: Write the failing tests for FakeDb (they define the contract FirestoreDb must match)**

`tests/store/test_fake_db.py`:
```python
from tests.fakes.fake_db import FakeDb


async def test_create_is_first_writer_wins() -> None:
    db = FakeDb()
    assert await db.create("events", "fathom:1", {"a": 1}) is True
    assert await db.create("events", "fathom:1", {"a": 2}) is False
    doc = await db.get("events", "fathom:1")
    assert doc == {"id": "fathom:1", "a": 1}


async def test_get_returns_none_for_missing_docs() -> None:
    db = FakeDb()
    assert await db.get("tasks", "nope") is None


async def test_update_merges_fields_and_set_replaces() -> None:
    db = FakeDb()
    await db.set("tasks", "t1", {"status": "queued", "attempts": 0})
    await db.update("tasks", "t1", {"status": "leased"})
    assert await db.get("tasks", "t1") == {"id": "t1", "status": "leased", "attempts": 0}
    await db.set("tasks", "t1", {"status": "done"})
    assert await db.get("tasks", "t1") == {"id": "t1", "status": "done"}


async def test_query_filters_orders_and_limits() -> None:
    db = FakeDb()
    await db.set("tasks", "a", {"status": "queued", "due_at": "2026-08-27T09:02:00+00:00"})
    await db.set("tasks", "b", {"status": "queued", "due_at": "2026-08-27T09:00:00+00:00"})
    await db.set("tasks", "c", {"status": "done", "due_at": "2026-08-27T08:00:00+00:00"})
    await db.set("tasks", "d", {"status": "queued", "due_at": "2026-08-27T10:00:00+00:00"})
    rows = await db.query(
        "tasks",
        [("status", "==", "queued"), ("due_at", "<=", "2026-08-27T09:05:00+00:00")],
        order_by="due_at",
        limit=5,
    )
    assert [r["id"] for r in rows] == ["b", "a"]
    rows = await db.query("tasks", [("status", "in", ["queued", "done"])], order_by="due_at", limit=2)
    assert [r["id"] for r in rows] == ["c", "b"]


async def test_count_counts_matching_docs() -> None:
    db = FakeDb()
    await db.set("tasks", "a", {"parent_task_id": "p"})
    await db.set("tasks", "b", {"parent_task_id": "p"})
    await db.set("tasks", "c", {"parent_task_id": "q"})
    assert await db.count("tasks", [("parent_task_id", "==", "p")]) == 2


async def test_cas_applies_updater_and_creates_only_when_predicate_holds() -> None:
    db = FakeDb()
    await db.set("tasks", "t1", {"status": "queued", "attempts": 0})
    ok = await db.cas(
        "tasks", "t1",
        predicate=lambda d: d["status"] == "queued",
        updater=lambda d: {"status": "leased", "attempts": d["attempts"] + 1},
        creates=[("tasks", "child", {"status": "queued"})],
    )
    assert ok is True
    assert (await db.get("tasks", "t1"))["status"] == "leased"  # type: ignore[index]
    assert (await db.get("tasks", "t1"))["attempts"] == 1  # type: ignore[index]
    assert await db.get("tasks", "child") is not None

    ok = await db.cas(
        "tasks", "t1",
        predicate=lambda d: d["status"] == "queued",
        updater=lambda d: {"status": "leased"},
        creates=[("tasks", "child2", {"status": "queued"})],
    )
    assert ok is False
    assert await db.get("tasks", "child2") is None


async def test_cas_on_a_missing_doc_is_false_and_creates_nothing() -> None:
    db = FakeDb()
    ok = await db.cas("tasks", "ghost", lambda d: True, lambda d: {}, [("tasks", "x", {})])
    assert ok is False
    assert await db.get("tasks", "x") is None


async def test_cas_applies_extra_updates_to_other_docs_in_the_same_transaction() -> None:
    db = FakeDb()
    await db.set("tasks", "t1", {"status": "leased"})
    await db.set("tasks", "old", {"status": "queued"})
    ok = await db.cas("tasks", "t1", lambda d: d["status"] == "leased", lambda d: {"status": "done"},
                      updates=[("tasks", "old", {"status": "cancelled"})])
    assert ok is True
    assert (await db.get("tasks", "old"))["status"] == "cancelled"  # type: ignore[index]
    ok = await db.cas("tasks", "t1", lambda d: d["status"] == "leased", lambda d: {},
                      updates=[("tasks", "old", {"status": "queued"})])
    assert ok is False
    assert (await db.get("tasks", "old"))["status"] == "cancelled"  # type: ignore[index]


async def test_array_contains_matches_list_fields() -> None:
    db = FakeDb()
    await db.set("tasks", "a", {"depends_on": ["x", "y"]})
    await db.set("tasks", "b", {"depends_on": ["z"]})
    await db.set("tasks", "c", {"depends_on": []})
    rows = await db.query("tasks", [("depends_on", "array_contains", "y")])
    assert [r["id"] for r in rows] == ["a"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/store/test_fake_db.py -q
```
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.fakes.fake_db'`.

- [ ] **Step 3: Write `app/store/db.py`**

```python
"""The tiny document-store surface the harness needs. FirestoreDb implements it for real;
tests use FakeDb. Nothing outside store/ imports google.cloud.firestore."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol

Doc = dict[str, Any]
Filter = tuple[str, str, Any]
Predicate = Callable[[Doc], bool]
Updater = Callable[[Doc], dict[str, Any]]
Create = tuple[str, str, dict[str, Any]]
Update = tuple[str, str, dict[str, Any]]

OPS = ("==", "<", "<=", ">", ">=", "in", "array_contains")


class Db(Protocol):
    async def get(self, collection: str, doc_id: str) -> Doc | None: ...

    async def create(self, collection: str, doc_id: str, data: dict[str, Any]) -> bool:
        """Create only if absent. False when the doc already exists — the idempotency primitive."""
        ...

    async def set(self, collection: str, doc_id: str, data: dict[str, Any]) -> None: ...

    async def update(self, collection: str, doc_id: str, fields: dict[str, Any]) -> None: ...

    async def query(
        self,
        collection: str,
        filters: Sequence[Filter],
        *,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[Doc]: ...

    async def count(self, collection: str, filters: Sequence[Filter]) -> int: ...

    async def cas(
        self,
        collection: str,
        doc_id: str,
        predicate: Predicate,
        updater: Updater,
        creates: Sequence[Create] = (),
        updates: Sequence[Update] = (),
    ) -> bool:
        """Compare-and-set in one transaction: read the doc, and if predicate(doc) holds, apply
        updater(doc), create every doc in `creates`, and update every doc in `updates`. False
        (and no writes at all) otherwise."""
        ...
```

- [ ] **Step 4: Write `tests/fakes/fake_db.py`**

```python
"""In-memory Db. Single-threaded, so cas() is trivially atomic. Mirrors the semantics the
FirestoreDb tests in tests/store/test_firestore_live.py check against the real service."""

from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any

from app.store.db import Create, Doc, Filter, Predicate, Update, Updater


def _matches(doc: dict[str, Any], filters: Sequence[Filter]) -> bool:
    for field, op, value in filters:
        actual = doc.get(field)
        if op == "==":
            ok = actual == value
        elif op == "<":
            ok = actual is not None and actual < value
        elif op == "<=":
            ok = actual is not None and actual <= value
        elif op == ">":
            ok = actual is not None and actual > value
        elif op == ">=":
            ok = actual is not None and actual >= value
        elif op == "in":
            ok = actual in value
        elif op == "array_contains":
            ok = isinstance(actual, list) and value in actual
        else:
            raise ValueError(f"unsupported op {op!r}")
        if not ok:
            return False
    return True


class FakeDb:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, dict[str, Any]]] = {}

    def _col(self, collection: str) -> dict[str, dict[str, Any]]:
        return self._data.setdefault(collection, {})

    async def get(self, collection: str, doc_id: str) -> Doc | None:
        raw = self._col(collection).get(doc_id)
        return None if raw is None else {"id": doc_id, **copy.deepcopy(raw)}

    async def create(self, collection: str, doc_id: str, data: dict[str, Any]) -> bool:
        col = self._col(collection)
        if doc_id in col:
            return False
        col[doc_id] = copy.deepcopy(data)
        return True

    async def set(self, collection: str, doc_id: str, data: dict[str, Any]) -> None:
        self._col(collection)[doc_id] = copy.deepcopy(data)

    async def update(self, collection: str, doc_id: str, fields: dict[str, Any]) -> None:
        self._col(collection)[doc_id].update(copy.deepcopy(fields))

    async def query(
        self,
        collection: str,
        filters: Sequence[Filter],
        *,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[Doc]:
        rows = [
            {"id": doc_id, **copy.deepcopy(raw)}
            for doc_id, raw in self._col(collection).items()
            if _matches(raw, filters)
        ]
        if order_by:
            rows.sort(key=lambda r: (r.get(order_by) is None, r.get(order_by)))
        return rows[:limit] if limit is not None else rows

    async def count(self, collection: str, filters: Sequence[Filter]) -> int:
        return sum(1 for raw in self._col(collection).values() if _matches(raw, filters))

    async def cas(
        self,
        collection: str,
        doc_id: str,
        predicate: Predicate,
        updater: Updater,
        creates: Sequence[Create] = (),
        updates: Sequence[Update] = (),
    ) -> bool:
        current = await self.get(collection, doc_id)
        if current is None or not predicate(current):
            return False
        await self.update(collection, doc_id, updater(current))
        for c_col, c_id, c_data in creates:
            await self.set(c_col, c_id, c_data)
        for u_col, u_id, u_fields in updates:
            await self.update(u_col, u_id, u_fields)
        return True
```

- [ ] **Step 5: Run FakeDb tests to verify they pass**

```bash
uv run pytest tests/store/test_fake_db.py -q
```
Expected: `9 passed`.

- [ ] **Step 6: Write `app/store/firestore.py`**

```python
"""Db on Firestore (native mode), async client. The only module that imports google.cloud."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from google.api_core import exceptions as gexc
from google.cloud import firestore
from google.cloud.firestore_v1.async_transaction import AsyncTransaction, async_transactional
from google.cloud.firestore_v1.base_query import FieldFilter

from app.store.db import Create, Doc, Filter, Predicate, Update, Updater


class FirestoreDb:
    def __init__(self, project: str, database: str = "(default)") -> None:
        self._client = firestore.AsyncClient(project=project or None, database=database)

    def _ref(self, collection: str, doc_id: str) -> Any:
        return self._client.collection(collection).document(doc_id)

    async def get(self, collection: str, doc_id: str) -> Doc | None:
        snap = await self._ref(collection, doc_id).get()
        if not snap.exists:
            return None
        return {"id": doc_id, **(snap.to_dict() or {})}

    async def create(self, collection: str, doc_id: str, data: dict[str, Any]) -> bool:
        try:
            await self._ref(collection, doc_id).create(data)
        except gexc.AlreadyExists:
            return False
        return True

    async def set(self, collection: str, doc_id: str, data: dict[str, Any]) -> None:
        await self._ref(collection, doc_id).set(data)

    async def update(self, collection: str, doc_id: str, fields: dict[str, Any]) -> None:
        await self._ref(collection, doc_id).update(fields)

    def _filtered(self, collection: str, filters: Sequence[Filter]) -> Any:
        q: Any = self._client.collection(collection)
        for field, op, value in filters:
            q = q.where(filter=FieldFilter(field, op, value))
        return q

    async def query(
        self,
        collection: str,
        filters: Sequence[Filter],
        *,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[Doc]:
        q = self._filtered(collection, filters)
        if order_by:
            q = q.order_by(order_by)
        if limit is not None:
            q = q.limit(limit)
        return [{"id": snap.id, **(snap.to_dict() or {})} async for snap in q.stream()]

    async def count(self, collection: str, filters: Sequence[Filter]) -> int:
        result = await self._filtered(collection, filters).count().get()
        return int(result[0][0].value)

    async def cas(
        self,
        collection: str,
        doc_id: str,
        predicate: Predicate,
        updater: Updater,
        creates: Sequence[Create] = (),
        updates: Sequence[Update] = (),
    ) -> bool:
        ref = self._ref(collection, doc_id)
        client = self._client

        @async_transactional
        async def _run(tx: AsyncTransaction) -> bool:
            snap = await ref.get(transaction=tx)
            if not snap.exists:
                return False
            current: Doc = {"id": doc_id, **(snap.to_dict() or {})}
            if not predicate(current):
                return False
            tx.update(ref, updater(current))
            for c_col, c_id, c_data in creates:
                tx.create(client.collection(c_col).document(c_id), c_data)
            for u_col, u_id, u_fields in updates:
                tx.update(client.collection(u_col).document(u_id), u_fields)
            return True

        return bool(await _run(client.transaction()))
```

- [ ] **Step 7: Write the live contract test (skipped without credentials)**

`tests/store/test_firestore_live.py`:
```python
"""Runs the FakeDb contract against real Firestore. Needs ADC and PM_GCP_PROJECT; skipped in CI."""

import os
import uuid

import pytest

from app.store.firestore import FirestoreDb

pytestmark = pytest.mark.live
live = pytest.mark.skipif(not os.environ.get("PM_GCP_PROJECT"), reason="no PM_GCP_PROJECT")


@live
async def test_firestore_db_honours_the_fake_db_contract() -> None:
    db = FirestoreDb(os.environ["PM_GCP_PROJECT"])
    col = f"_contract_{uuid.uuid4().hex[:8]}"
    assert await db.create(col, "t1", {"status": "queued", "attempts": 0, "due_at": "b"}) is True
    assert await db.create(col, "t1", {"status": "x"}) is False
    await db.set(col, "t2", {"status": "queued", "attempts": 0, "due_at": "a"})
    rows = await db.query(col, [("status", "==", "queued")], order_by="due_at", limit=5)
    assert [r["id"] for r in rows] == ["t2", "t1"]
    assert await db.count(col, [("status", "==", "queued")]) == 2
    ok = await db.cas(col, "t1", lambda d: d["status"] == "queued",
                      lambda d: {"status": "leased", "attempts": d["attempts"] + 1},
                      [(col, "child", {"status": "queued"})])
    assert ok is True
    assert (await db.get(col, "t1")) == {"id": "t1", "status": "leased", "attempts": 1, "due_at": "b"}
    assert await db.get(col, "child") is not None
    assert await db.cas(col, "t1", lambda d: d["status"] == "queued", lambda d: {}) is False
    ok = await db.cas(col, "t1", lambda d: d["status"] == "leased", lambda d: {"status": "done"},
                      updates=[(col, "t2", {"status": "cancelled"})])
    assert ok is True and (await db.get(col, "t2"))["status"] == "cancelled"  # type: ignore[index]
    await db.set(col, "t3", {"depends_on": ["t1"]})
    assert [r["id"] for r in await db.query(col, [("depends_on", "array_contains", "t1")])] == ["t3"]
```

- [ ] **Step 8: Run all gates; run the live test once against your project**

```bash
uv run ruff check . && uv run mypy app && uv run lint-imports && uv run pytest -q
gcloud auth application-default login
PM_GCP_PROJECT=pm-agent-hack-2026 uv run pytest tests/store/test_firestore_live.py -q -m live
```
Expected: gates green with the live test skipped; the live run reports `1 passed`. If `count()` raises on the aggregation result shape, print `result` once and adapt the indexing — the contract test is the arbiter.

- [ ] **Step 9: Commit**

```bash
git add app/store/db.py app/store/firestore.py tests/fakes/fake_db.py \
  tests/store/test_fake_db.py tests/store/test_firestore_live.py
git commit -m "feat(store): Db protocol with in-memory fake and Firestore implementation"
```

---

### Task 5: `verify/lineage.py`

**Files:**
- Create: `app/verify/lineage.py`
- Test: `tests/verify/test_lineage.py`

**Interfaces:**
- Produces: `LineageVerdict(ok: bool, depth: int, reason: str = "")`; `check_lineage(parent: Doc | None, existing_children: int, policy: dict[str, Any]) -> LineageVerdict`; `DEFAULT_POLICY = {"max_depth": 4, "max_children": 12}` (a plan is one parent with several children).

- [ ] **Step 1: Write the failing tests**

`tests/verify/test_lineage.py`:
```python
from app.verify.lineage import DEFAULT_POLICY, check_lineage


def test_a_root_task_has_depth_zero_and_is_always_allowed() -> None:
    v = check_lineage(None, 0, DEFAULT_POLICY)
    assert v.ok and v.depth == 0


def test_a_child_is_one_deeper_than_its_parent() -> None:
    v = check_lineage({"id": "p", "depth": 2}, 0, DEFAULT_POLICY)
    assert v.ok and v.depth == 3


def test_a_child_beyond_max_depth_is_refused_with_the_reason() -> None:
    v = check_lineage({"id": "p", "depth": 4}, 0, DEFAULT_POLICY)
    assert not v.ok
    assert "depth 5 exceeds max_depth 4" in v.reason


def test_a_parent_at_its_child_limit_may_not_fan_out_further() -> None:
    v = check_lineage({"id": "p", "depth": 1}, 12, DEFAULT_POLICY)
    assert not v.ok
    assert "already has 12 children" in v.reason


def test_project_policy_overrides_defaults() -> None:
    v = check_lineage({"id": "p", "depth": 1}, 1, {"max_depth": 2, "max_children": 1})
    assert not v.ok and "max_children 1" in v.reason
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/verify/test_lineage.py -q
```
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `app/verify/lineage.py`**

```python
"""Structural loop prevention. Every enqueue passes here; a chain cannot exceed max_depth and a
task cannot fan out beyond max_children, so a runaway agent is impossible rather than unlikely.
Plan generations count as depth: a planner that keeps planning follow-ups to its follow-ups
stops at the limit and says so."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_POLICY: dict[str, Any] = {"max_depth": 4, "max_children": 12}


@dataclass(frozen=True)
class LineageVerdict:
    ok: bool
    depth: int
    reason: str = ""


def check_lineage(
    parent: dict[str, Any] | None, existing_children: int, policy: dict[str, Any]
) -> LineageVerdict:
    max_depth = int(policy.get("max_depth", DEFAULT_POLICY["max_depth"]))
    max_children = int(policy.get("max_children", DEFAULT_POLICY["max_children"]))
    if parent is None:
        return LineageVerdict(ok=True, depth=0)
    depth = int(parent.get("depth", 0)) + 1
    if depth > max_depth:
        return LineageVerdict(False, depth, f"depth {depth} exceeds max_depth {max_depth}")
    if existing_children >= max_children:
        return LineageVerdict(
            False,
            depth,
            f"parent {parent.get('id')} already has {existing_children} children "
            f"(max_children {max_children})",
        )
    return LineageVerdict(ok=True, depth=depth)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/verify/test_lineage.py -q && uv run mypy app
```
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add app/verify/lineage.py tests/verify/test_lineage.py
git commit -m "feat(verify): lineage gate — depth and fan-out limits"
```

---

### Task 6: `store/tasks.py` — the task-graph queue

**Files:**
- Create: `app/store/tasks.py`
- Test: `tests/store/test_tasks.py`

**Interfaces:**
- Consumes: `Db` (with `cas(..., creates, updates)` and the `array_contains` op), `Clock`, `iso`, `new_id`, `check_lineage`, `DEFAULT_POLICY`.
- Produces:
  ```python
  OPEN_STATUSES = ("queued", "blocked", "leased", "deferred")
  TERMINAL_BAD = ("failed", "cancelled", "skipped")

  class TaskQueue:
      def __init__(self, db: Db, clock: Clock, *, lease_minutes: int = 15) -> None
      async def enqueue(self, *, kind: str, project_id: str, payload: dict, reason: str,
                        due_at: datetime | None = None, parent: Doc | None = None,
                        root_event_id: str | None = None, policy: dict | None = None,
                        params: dict | None = None, depends_on: Sequence[str] = (),
                        on_dep_failed: str = "skip", on_unmet: str = "none",
                        context: dict | None = None, key: str | None = None,
                        plan_id: str | None = None) -> str | None
      async def promote_ready(self) -> int          # blocked → queued / skipped / cancelled per deps; returns promoted count
      async def due(self, kinds: Sequence[str], limit: int) -> list[Doc]   # calls promote_ready() first
      async def claim(self, task_id: str) -> Doc | None
      async def complete(self, task: Doc, result: dict, children: Sequence[dict],
                         *, supersedes: Sequence[str] = ()) -> list[str]
      async def fail(self, task: Doc, reason: str, *, max_attempts: int = 3) -> str
      async def defer(self, task: Doc, until: datetime, reason: str) -> None
      async def cancel(self, task_id: str, reason: str) -> list[str]   # cascades; returns cancelled ids
      async def open_count(self, project_id: str) -> int
  ```
  A child spec for `complete()` is a dict with keys `kind`, `payload`, `reason`, and optionally `due_at` (ISO str), `params`, `key`, `depends_on` (a list of sibling **keys** or existing task **ids**), `on_dep_failed`, `on_unmet`, `context`, `policy`. All children of one `complete()` call share a fresh `plan_id`.
  Task doc fields: `kind, params, payload, reason, status, due_at, created_at, lease_until, attempts, result, error, root_event_id, parent_task_id, depth, refused_enqueues, finished_at, defer_reason, key, plan_id, depends_on, on_dep_failed, on_unmet, context, project_id`.
  `BACKOFF_SECONDS = (60, 300, 900)`.

- [ ] **Step 1: Write the failing tests**

`tests/store/test_tasks.py`:
```python
from datetime import UTC, datetime, timedelta

from app.store.tasks import TaskQueue
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_db import FakeDb

T0 = datetime(2026, 8, 27, 9, 0, tzinfo=UTC)


def make() -> tuple[TaskQueue, FakeDb, FakeClock]:
    db, clock = FakeDb(), FakeClock(T0)
    return TaskQueue(db, clock, lease_minutes=15), db, clock


async def enqueue(q: TaskQueue, **kw) -> str:  # type: ignore[no-untyped-def]
    kw.setdefault("kind", "extract")
    kw.setdefault("project_id", "acme")
    kw.setdefault("payload", {})
    kw.setdefault("reason", "test")
    tid = await q.enqueue(**kw)
    assert tid is not None
    return tid


async def status(db: FakeDb, tid: str) -> str:
    doc = await db.get("tasks", tid)
    assert doc is not None
    return str(doc["status"])


# --- basics -----------------------------------------------------------------------------------

async def test_enqueue_creates_a_queued_root_task_due_now_by_default() -> None:
    q, db, _ = make()
    tid = await enqueue(q, payload={"event_id": "e1"}, reason="call finished", root_event_id="e1")
    doc = await db.get("tasks", tid)
    assert doc is not None
    assert doc["status"] == "queued" and doc["depth"] == 0 and doc["attempts"] == 0
    assert doc["due_at"] == "2026-08-27T09:00:00+00:00"
    assert doc["root_event_id"] == "e1" and doc["parent_task_id"] is None
    assert doc["depends_on"] == [] and doc["on_dep_failed"] == "skip" and doc["on_unmet"] == "none"


async def test_due_returns_only_matching_kinds_that_are_due_oldest_first() -> None:
    q, _, clock = make()
    a = await enqueue(q, reason="a", due_at=T0 + timedelta(minutes=2))
    b = await enqueue(q, reason="b")
    await enqueue(q, kind="reconcile", reason="c")
    await enqueue(q, reason="d", due_at=T0 + timedelta(hours=1))
    clock.advance(minutes=3)
    assert [t["id"] for t in await q.due(["extract"], limit=10)] == [b, a]


async def test_claim_leases_a_due_task_and_counts_the_attempt() -> None:
    q, _, _ = make()
    tid = await enqueue(q)
    claimed = await q.claim(tid)
    assert claimed is not None
    assert claimed["status"] == "leased" and claimed["attempts"] == 1
    assert claimed["lease_until"] == "2026-08-27T09:15:00+00:00"
    assert await q.claim(tid) is None


async def test_an_expired_lease_is_reclaimable_and_a_live_one_is_not() -> None:
    q, _, clock = make()
    tid = await enqueue(q)
    await q.claim(tid)
    clock.advance(minutes=14)
    assert await q.due(["extract"], limit=10) == []
    clock.advance(minutes=2)
    assert [t["id"] for t in await q.due(["extract"], limit=10)] == [tid]
    reclaimed = await q.claim(tid)
    assert reclaimed is not None and reclaimed["attempts"] == 2


async def test_complete_marks_done_and_creates_children_atomically_with_lineage() -> None:
    q, db, _ = make()
    tid = await enqueue(q, root_event_id="e1")
    task = await q.claim(tid)
    assert task is not None
    ids = await q.complete(task, {"n": 3}, [
        {"kind": "reconcile", "payload": {"k": 1}, "reason": "reconcile 3 items"},
    ])
    assert len(ids) == 1
    parent = await db.get("tasks", tid)
    child = await db.get("tasks", ids[0])
    assert parent is not None and child is not None
    assert parent["status"] == "done" and parent["result"] == {"n": 3}
    assert child["status"] == "queued" and child["depth"] == 1
    assert child["parent_task_id"] == tid and child["root_event_id"] == "e1"
    assert child["project_id"] == "acme" and child["plan_id"] is not None


async def test_complete_refuses_children_beyond_max_depth_and_records_it() -> None:
    q, db, _ = make()
    tid = await enqueue(q, kind="check_issue_state")
    await db.update("tasks", tid, {"depth": 4})
    task = await q.claim(tid)
    assert task is not None
    ids = await q.complete(task, {}, [{"kind": "nudge", "payload": {}, "reason": "again"}])
    assert ids == []
    parent = await db.get("tasks", tid)
    assert parent is not None and parent["status"] == "done"
    assert parent["refused_enqueues"][0]["kind"] == "nudge"
    assert "max_depth" in parent["refused_enqueues"][0]["reason"]


async def test_complete_is_a_no_op_if_the_lease_was_lost() -> None:
    q, db, _ = make()
    tid = await enqueue(q)
    task = await q.claim(tid)
    assert task is not None
    await db.update("tasks", tid, {"status": "queued"})
    ids = await q.complete(task, {"n": 1}, [{"kind": "reconcile", "payload": {}, "reason": "r"}])
    assert ids == []
    assert await db.count("tasks", [("kind", "==", "reconcile")]) == 0


async def test_fail_requeues_with_backoff_then_marks_failed_on_the_third_attempt() -> None:
    q, db, clock = make()
    tid = await enqueue(q)
    t = await q.claim(tid)
    assert t is not None and await q.fail(t, "boom") == "queued"
    doc = await db.get("tasks", tid)
    assert doc is not None and doc["due_at"] == "2026-08-27T09:01:00+00:00"
    clock.advance(minutes=2)
    t = await q.claim(tid)
    assert t is not None and await q.fail(t, "boom") == "queued"
    doc = await db.get("tasks", tid)
    assert doc is not None and doc["due_at"] == "2026-08-27T09:07:00+00:00"
    clock.advance(minutes=6)
    t = await q.claim(tid)
    assert t is not None and await q.fail(t, "boom") == "failed"
    assert await status(db, tid) == "failed"


async def test_defer_pushes_due_at_and_a_deferred_task_becomes_due_again() -> None:
    q, db, clock = make()
    tid = await enqueue(q, kind="nudge")
    t = await q.claim(tid)
    assert t is not None
    await q.defer(t, T0 + timedelta(hours=12), "quiet hours")
    doc = await db.get("tasks", tid)
    assert doc is not None and doc["status"] == "deferred" and doc["defer_reason"] == "quiet hours"
    assert await q.due(["nudge"], limit=10) == []
    clock.advance(hours=12)
    assert [x["id"] for x in await q.due(["nudge"], limit=10)] == [tid]


# --- dependencies -----------------------------------------------------------------------------

async def test_a_task_with_an_unfinished_dependency_is_blocked_and_not_due() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state", reason="in progress?")
    b = await enqueue(q, kind="check_pr_exists", reason="pr?", depends_on=[a])
    assert await status(db, b) == "blocked"
    assert [t["id"] for t in await q.due(["check_issue_state", "check_pr_exists"], 10)] == [a]


async def test_completing_a_dependency_promotes_the_dependent_on_the_next_due_sweep() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state")
    b = await enqueue(q, kind="check_pr_exists", depends_on=[a])
    ta = await q.claim(a)
    assert ta is not None
    await q.complete(ta, {"met": True}, [])
    assert [t["id"] for t in await q.due(["check_pr_exists"], 10)] == [b]
    assert await status(db, b) == "queued"


async def test_a_dependent_waits_for_all_of_its_dependencies() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state")
    b = await enqueue(q, kind="check_pr_exists")
    c = await enqueue(q, kind="check_pr_reviewed", depends_on=[a, b])
    ta = await q.claim(a)
    assert ta is not None
    await q.complete(ta, {}, [])
    await q.due(["check_pr_reviewed"], 10)
    assert await status(db, c) == "blocked"
    tb = await q.claim(b)
    assert tb is not None
    await q.complete(tb, {}, [])
    await q.due(["check_pr_reviewed"], 10)
    assert await status(db, c) == "queued"


async def test_a_failed_dependency_skips_the_dependent_by_default() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state")
    b = await enqueue(q, kind="check_pr_exists", depends_on=[a])
    await db.update("tasks", a, {"status": "failed"})
    await q.promote_ready()
    assert await status(db, b) == "skipped"


async def test_run_anyway_treats_a_failed_dependency_as_satisfied() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state")
    b = await enqueue(q, kind="check_pr_exists", depends_on=[a], on_dep_failed="run_anyway")
    await db.update("tasks", a, {"status": "failed"})
    await q.promote_ready()
    assert await status(db, b) == "queued"


async def test_cancel_on_dep_failed_cascades_down_the_chain() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state")
    b = await enqueue(q, kind="check_pr_exists", depends_on=[a], on_dep_failed="cancel")
    c = await enqueue(q, kind="check_pr_reviewed", depends_on=[b])
    await db.update("tasks", a, {"status": "failed"})
    await q.promote_ready()
    assert await status(db, b) == "cancelled"
    assert await status(db, c) == "cancelled"


async def test_cancel_cascades_to_dependents_and_reports_every_id() -> None:
    q, db, _ = make()
    a = await enqueue(q, kind="check_issue_state")
    b = await enqueue(q, kind="check_pr_exists", depends_on=[a])
    c = await enqueue(q, kind="check_pr_reviewed", depends_on=[b])
    d = await enqueue(q, kind="nudge")  # unrelated
    cancelled = await q.cancel(a, "issue reverted")
    assert set(cancelled) == {a, b, c}
    assert await status(db, d) == "queued"
    doc = await db.get("tasks", c)
    assert doc is not None and doc["error"] == "cancelled: issue reverted"


async def test_a_done_task_cannot_be_cancelled() -> None:
    q, db, _ = make()
    a = await enqueue(q)
    ta = await q.claim(a)
    assert ta is not None
    await q.complete(ta, {}, [])
    assert await q.cancel(a, "late") == []
    assert await status(db, a) == "done"


# --- plans ------------------------------------------------------------------------------------

PLAN = [
    {"key": "impl", "kind": "check_issue_state", "payload": {}, "reason": "in progress by Thu",
     "params": {"issue": "INV-142", "expect": ["In Progress", "Done"]},
     "due_at": "2026-08-28T16:00:00+00:00", "on_unmet": "nudge_assignee"},
    {"key": "pr", "kind": "check_pr_exists", "payload": {}, "reason": "pr open",
     "params": {"issue": "INV-142"}, "depends_on": ["impl"],
     "due_at": "2026-08-29T16:00:00+00:00", "on_unmet": "nudge_assignee"},
    {"key": "review", "kind": "check_pr_reviewed", "payload": {}, "reason": "reviewed",
     "params": {"issue": "INV-142"}, "depends_on": ["pr"],
     "due_at": "2026-08-30T16:00:00+00:00", "on_unmet": "nudge_reviewer"},
]


async def test_a_plan_materialises_as_a_graph_with_keys_resolved_to_ids() -> None:
    q, db, _ = make()
    planner_task = await enqueue(q, kind="plan", root_event_id="e1")
    tp = await q.claim(planner_task)
    assert tp is not None
    ids = await q.complete(tp, {"plan": "ok"}, PLAN)
    assert len(ids) == 3
    impl, pr, review = (await db.get("tasks", i) for i in ids)
    assert impl is not None and pr is not None and review is not None
    assert impl["status"] == "queued" and impl["depends_on"] == []
    assert pr["status"] == "blocked" and pr["depends_on"] == [impl["id"]]
    assert review["status"] == "blocked" and review["depends_on"] == [pr["id"]]
    assert impl["key"] == "impl" and impl["params"]["issue"] == "INV-142"
    assert impl["on_unmet"] == "nudge_assignee" and pr["plan_id"] == impl["plan_id"]
    assert impl["depth"] == 1 and impl["root_event_id"] == "e1"


async def test_a_plan_may_depend_on_an_existing_open_task_by_id() -> None:
    q, db, _ = make()
    existing = await enqueue(q, kind="check_issue_state")
    planner_task = await enqueue(q, kind="plan")
    tp = await q.claim(planner_task)
    assert tp is not None
    ids = await q.complete(tp, {}, [
        {"kind": "nudge", "payload": {}, "reason": "after", "depends_on": [existing]},
    ])
    doc = await db.get("tasks", ids[0])
    assert doc is not None and doc["status"] == "blocked" and doc["depends_on"] == [existing]


async def test_supersedes_cancels_the_named_open_tasks_and_their_dependents() -> None:
    q, db, _ = make()
    old_a = await enqueue(q, kind="check_issue_state")
    old_b = await enqueue(q, kind="check_pr_exists", depends_on=[old_a])
    planner_task = await enqueue(q, kind="plan")
    tp = await q.claim(planner_task)
    assert tp is not None
    ids = await q.complete(tp, {}, [{"kind": "check_issue_state", "payload": {}, "reason": "new"}],
                           supersedes=[old_a])
    assert len(ids) == 1
    assert await status(db, old_a) == "cancelled" and await status(db, old_b) == "cancelled"


async def test_open_count_counts_only_open_statuses() -> None:
    q, db, _ = make()
    a = await enqueue(q)
    await enqueue(q, kind="check_pr_exists", depends_on=[a])
    done = await enqueue(q)
    td = await q.claim(done)
    assert td is not None
    await q.complete(td, {}, [])
    assert await q.open_count("acme") == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/store/test_tasks.py -q
```
Expected: FAIL with `ModuleNotFoundError: No module named 'app.store.tasks'`.

- [ ] **Step 3: Write `app/store/tasks.py`**

```python
"""The durable task-graph queue. Firestore documents are the tasks; a lease is the claim;
dependencies make a task `blocked` until every dependency is done; a cas() that marks a task
done and creates its children (a plan) in one transaction is what makes "did the work but
failed to schedule the follow-up" impossible. The model never touches this module: stages hand
the runner child specs, and the runner calls complete()."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from app.core.clock import Clock, iso
from app.core.keys import new_id
from app.store.db import Create, Db, Doc, Update
from app.verify.lineage import DEFAULT_POLICY, check_lineage

BACKOFF_SECONDS = (60, 300, 900)
OPEN_STATUSES = ("queued", "blocked", "leased", "deferred")
TERMINAL_BAD = ("failed", "cancelled", "skipped")
DEP_POLICIES = ("skip", "run_anyway", "cancel")


class TaskQueue:
    def __init__(self, db: Db, clock: Clock, *, lease_minutes: int = 15) -> None:
        self._db = db
        self._clock = clock
        self._lease = timedelta(minutes=lease_minutes)

    # --- documents ------------------------------------------------------------------------------

    def _doc(
        self,
        *,
        kind: str,
        project_id: str,
        payload: dict[str, Any],
        reason: str,
        due_at: str,
        depth: int,
        parent_task_id: str | None,
        root_event_id: str | None,
        params: dict[str, Any] | None = None,
        depends_on: Sequence[str] = (),
        blocked: bool = False,
        on_dep_failed: str = "skip",
        on_unmet: str = "none",
        context: dict[str, Any] | None = None,
        key: str | None = None,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        if on_dep_failed not in DEP_POLICIES:
            raise ValueError(f"on_dep_failed must be one of {DEP_POLICIES}, got {on_dep_failed!r}")
        return {
            "kind": kind,
            "params": params or {},
            "project_id": project_id,
            "payload": payload,
            "reason": reason,
            "status": "blocked" if blocked else "queued",
            "due_at": due_at,
            "created_at": iso(self._clock.now()),
            "lease_until": None,
            "attempts": 0,
            "result": None,
            "error": None,
            "root_event_id": root_event_id,
            "parent_task_id": parent_task_id,
            "depth": depth,
            "refused_enqueues": [],
            "finished_at": None,
            "defer_reason": None,
            "key": key,
            "plan_id": plan_id,
            "depends_on": list(depends_on),
            "on_dep_failed": on_dep_failed,
            "on_unmet": on_unmet,
            "context": context or {},
        }

    async def _deps_state(self, dep_ids: Sequence[str]) -> tuple[bool, bool]:
        """(all_done, any_bad) over the dependency ids. A missing dependency counts as bad —
        we never run work whose precondition vanished."""
        all_done, any_bad = True, False
        for dep_id in dep_ids:
            dep = await self._db.get("tasks", dep_id)
            if dep is None or dep["status"] in TERMINAL_BAD:
                any_bad = True
                all_done = False
            elif dep["status"] != "done":
                all_done = False
        return all_done, any_bad

    # --- enqueue ------------------------------------------------------------------------------

    async def enqueue(
        self,
        *,
        kind: str,
        project_id: str,
        payload: dict[str, Any],
        reason: str,
        due_at: datetime | None = None,
        parent: Doc | None = None,
        root_event_id: str | None = None,
        policy: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        depends_on: Sequence[str] = (),
        on_dep_failed: str = "skip",
        on_unmet: str = "none",
        context: dict[str, Any] | None = None,
        key: str | None = None,
        plan_id: str | None = None,
    ) -> str | None:
        """Create one task. None when the lineage gate refuses (recorded on the parent).
        Blocked when any dependency is not yet done; dependency failure is resolved later by
        promote_ready() according to on_dep_failed."""
        existing = 0
        if parent is not None:
            existing = await self._db.count("tasks", [("parent_task_id", "==", parent["id"])])
        verdict = check_lineage(parent, existing, policy or DEFAULT_POLICY)
        if not verdict.ok:
            if parent is not None:
                refused = list(parent.get("refused_enqueues") or [])
                refused.append({"kind": kind, "reason": verdict.reason})
                await self._db.update("tasks", parent["id"], {"refused_enqueues": refused})
            return None
        all_done, _ = await self._deps_state(depends_on)
        task_id = new_id()
        doc = self._doc(
            kind=kind, project_id=project_id, payload=payload, reason=reason,
            due_at=iso(due_at or self._clock.now()), depth=verdict.depth,
            parent_task_id=parent["id"] if parent else None,
            root_event_id=root_event_id or (parent or {}).get("root_event_id"),
            params=params, depends_on=depends_on, blocked=bool(depends_on) and not all_done,
            on_dep_failed=on_dep_failed, on_unmet=on_unmet, context=context, key=key,
            plan_id=plan_id,
        )
        await self._db.create("tasks", task_id, doc)
        return task_id

    # --- dependencies -------------------------------------------------------------------------

    async def promote_ready(self) -> int:
        """Resolve every blocked task against its dependencies: all done → queued; any failed /
        cancelled / skipped / missing → skip, run_anyway or cancel per on_dep_failed. Idempotent;
        called by due() on every tick, so a crash between a completion and its promotion heals
        within a minute."""
        promoted = 0
        for task in await self._db.query("tasks", [("status", "==", "blocked")], limit=500):
            all_done, any_bad = await self._deps_state(task.get("depends_on") or [])
            if any_bad:
                policy = task.get("on_dep_failed", "skip")
                if policy == "cancel":
                    await self.cancel(task["id"], "a dependency failed")
                elif policy == "skip":
                    await self._db.cas(
                        "tasks", task["id"], lambda t: t["status"] == "blocked",
                        lambda t: {"status": "skipped", "error": "skipped: a dependency failed",
                                   "finished_at": iso(self._clock.now())},
                    )
                else:  # run_anyway: a bad dependency counts as satisfied
                    remaining = [
                        d for d in task.get("depends_on") or []
                        if (dep := await self._db.get("tasks", d)) is not None
                        and dep["status"] not in TERMINAL_BAD and dep["status"] != "done"
                    ]
                    if not remaining:
                        ok = await self._db.cas(
                            "tasks", task["id"], lambda t: t["status"] == "blocked",
                            lambda t: {"status": "queued"},
                        )
                        promoted += int(ok)
            elif all_done:
                ok = await self._db.cas(
                    "tasks", task["id"], lambda t: t["status"] == "blocked",
                    lambda t: {"status": "queued"},
                )
                promoted += int(ok)
        return promoted

    async def cancel(self, task_id: str, reason: str) -> list[str]:
        """Cancel an open task and, recursively, everything that depends on it. Done tasks are
        left alone. Returns every id that was cancelled."""
        cancelled: list[str] = []
        ok = await self._db.cas(
            "tasks", task_id, lambda t: t["status"] in OPEN_STATUSES,
            lambda t: {"status": "cancelled", "error": f"cancelled: {reason}",
                       "finished_at": iso(self._clock.now()), "lease_until": None},
        )
        if not ok:
            return cancelled
        cancelled.append(task_id)
        dependents = await self._db.query("tasks", [("depends_on", "array_contains", task_id)])
        for dep in dependents:
            cancelled.extend(await self.cancel(dep["id"], reason))
        return cancelled

    # --- tick -----------------------------------------------------------------------------------

    async def due(self, kinds: Sequence[str], limit: int) -> list[Doc]:
        """Due work for the kinds this process can run: queued or deferred tasks past due_at,
        plus leased tasks whose lease expired (a crashed worker). Promotes blocked tasks first."""
        await self.promote_ready()
        now = iso(self._clock.now())
        queued = await self._db.query(
            "tasks", [("status", "in", ["queued", "deferred"]), ("due_at", "<=", now)],
            order_by="due_at", limit=limit,
        )
        expired = await self._db.query(
            "tasks", [("status", "==", "leased"), ("lease_until", "<=", now)],
            order_by="lease_until", limit=limit,
        )
        rows = [t for t in queued + expired if t["kind"] in kinds]
        rows.sort(key=lambda t: t["due_at"])
        return rows[:limit]

    async def claim(self, task_id: str) -> Doc | None:
        now = self._clock.now()
        now_s = iso(now)
        lease_until = iso(now + self._lease)

        def claimable(t: Doc) -> bool:
            if t["status"] in ("queued", "deferred"):
                return bool(t["due_at"] <= now_s)
            if t["status"] == "leased":
                return bool((t.get("lease_until") or "") <= now_s)
            return False

        ok = await self._db.cas(
            "tasks", task_id, claimable,
            lambda t: {"status": "leased", "lease_until": lease_until,
                       "attempts": int(t.get("attempts", 0)) + 1},
        )
        return await self._db.get("tasks", task_id) if ok else None

    # --- completion ---------------------------------------------------------------------------

    async def complete(
        self,
        task: Doc,
        result: dict[str, Any],
        children: Sequence[dict[str, Any]],
        *,
        supersedes: Sequence[str] = (),
    ) -> list[str]:
        """Mark done and, in the same transaction, create the children (a plan) and cancel the
        superseded open tasks with their dependents. Children may depend on each other by `key`
        or on existing tasks by id. Children failing the lineage gate are recorded in
        refused_enqueues. Returns created child ids; [] if the lease was lost (nothing written)."""
        existing = await self._db.count("tasks", [("parent_task_id", "==", task["id"])])
        plan_id = new_id()
        key_to_id: dict[str, str] = {}
        accepted: list[tuple[dict[str, Any], str, int]] = []
        refused: list[dict[str, str]] = list(task.get("refused_enqueues") or [])
        for spec in children:
            verdict = check_lineage(task, existing, spec.get("policy") or DEFAULT_POLICY)
            if not verdict.ok:
                refused.append({"kind": spec["kind"], "reason": verdict.reason})
                continue
            existing += 1
            child_id = new_id()
            if spec.get("key"):
                key_to_id[str(spec["key"])] = child_id
            accepted.append((spec, child_id, verdict.depth))

        creates: list[Create] = []
        for spec, child_id, depth in accepted:
            deps = [key_to_id.get(str(d), str(d)) for d in spec.get("depends_on") or []]
            sibling_ids = {cid for _, cid, _ in accepted}
            external = [d for d in deps if d not in sibling_ids]
            all_done, _ = await self._deps_state(external)
            blocked = bool(deps) and (any(d in sibling_ids for d in deps) or not all_done)
            creates.append((
                "tasks", child_id,
                self._doc(
                    kind=spec["kind"], project_id=task["project_id"],
                    payload=spec.get("payload") or {}, reason=spec["reason"],
                    due_at=spec.get("due_at") or iso(self._clock.now()), depth=depth,
                    parent_task_id=task["id"], root_event_id=task.get("root_event_id"),
                    params=spec.get("params"), depends_on=deps, blocked=blocked,
                    on_dep_failed=spec.get("on_dep_failed", "skip"),
                    on_unmet=spec.get("on_unmet", "none"), context=spec.get("context"),
                    key=spec.get("key"), plan_id=plan_id,
                ),
            ))

        updates: list[Update] = []
        finished = iso(self._clock.now())
        for sid in await self._cascade_ids(supersedes):
            updates.append(("tasks", sid, {
                "status": "cancelled", "error": f"cancelled: superseded by plan {plan_id}",
                "finished_at": finished, "lease_until": None,
            }))

        ok = await self._db.cas(
            "tasks", task["id"],
            lambda t: t["status"] == "leased",
            lambda t: {"status": "done", "result": result, "refused_enqueues": refused,
                       "finished_at": finished, "lease_until": None},
            creates, updates,
        )
        return [cid for _, cid, _ in accepted] if ok else []

    async def _cascade_ids(self, roots: Sequence[str]) -> list[str]:
        """Open tasks among `roots` plus everything open that depends on them, transitively."""
        seen: list[str] = []
        stack = list(roots)
        while stack:
            tid = stack.pop()
            if tid in seen:
                continue
            doc = await self._db.get("tasks", tid)
            if doc is None or doc["status"] not in OPEN_STATUSES:
                continue
            seen.append(tid)
            for dep in await self._db.query("tasks", [("depends_on", "array_contains", tid)]):
                stack.append(dep["id"])
        return seen

    # --- failure --------------------------------------------------------------------------------

    async def fail(self, task: Doc, reason: str, *, max_attempts: int = 3) -> str:
        """Retry with backoff while attempts remain; otherwise mark failed. Dependents are
        resolved by promote_ready() on the next tick. Returns the new status."""
        now = self._clock.now()
        attempts = int(task.get("attempts", 0))
        if attempts >= max_attempts:
            await self._db.update("tasks", task["id"], {
                "status": "failed", "error": reason, "finished_at": iso(now), "lease_until": None,
            })
            return "failed"
        delay = BACKOFF_SECONDS[min(attempts - 1, len(BACKOFF_SECONDS) - 1)]
        await self._db.update("tasks", task["id"], {
            "status": "queued", "error": reason, "lease_until": None,
            "due_at": iso(now + timedelta(seconds=delay)),
        })
        return "queued"

    async def defer(self, task: Doc, until: datetime, reason: str) -> None:
        await self._db.update("tasks", task["id"], {
            "status": "deferred", "due_at": iso(until), "defer_reason": reason,
            "lease_until": None,
        })

    async def open_count(self, project_id: str) -> int:
        return await self._db.count(
            "tasks", [("project_id", "==", project_id), ("status", "in", list(OPEN_STATUSES))]
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/store -q && uv run mypy app && uv run lint-imports && uv run ruff check .
```
Expected: `30 passed` (live skipped); mypy and import-linter clean. If ruff flags the walrus inside the comprehension in `promote_ready`, rewrite it as a small `for` loop — behaviour is what the tests pin, not the shape.

- [ ] **Step 5: Commit**

```bash
git add app/store/tasks.py tests/store/test_tasks.py
git commit -m "feat(store): task-graph queue — leases, dependencies, promotion, cascade cancel, plan materialisation"
```

---

### Task 6b: `kinds/` registry skeleton and `verify/plan.py`

**Files:**
- Create: `app/kinds/__init__.py`, `app/kinds/base.py`, `app/kinds/registry.py`, `app/verify/plan.py`
- Test: `tests/kinds/test_registry.py`, `tests/verify/test_plan.py`

**Interfaces:**
- Produces:
  ```python
  # kinds/base.py
  class KindSpec(BaseModel):            # frozen
      name: str
      params_schema: type[BaseModel]
      unmet_actions: tuple[str, ...]    # allowed on_unmet values
      description: str

  # kinds/registry.py
  KINDS: dict[str, KindSpec]           # check_issue_state, check_pr_exists, check_pr_reviewed,
                                       # check_pr_merged, nudge, escalate, reconcile_item, daily_review, report
  def get_kind(name: str) -> KindSpec | None
  def validate_params(kind: str, params: dict) -> tuple[dict | None, str | None]   # (clean, error)

  # verify/plan.py
  @dataclass(frozen=True)
  class PlanVerdict:
      ok: bool
      tasks: list[dict]        # the accepted tasks, in dependency (topological) order, with ISO due_at
      rejected: list[dict]     # each: {"key", "reason"}
      reasons: list[str]       # plan-level problems (cycle, size, open-task cap)

  def check_plan(plan: dict, *, now: datetime, policy: dict, open_tasks: int,
                 existing_ids: Callable[[str], bool], id_exists: Callable[[str], bool]) -> PlanVerdict
  ```
  Plan shape: `{"tasks": [{"key", "kind", "params", "due", "depends_on": [keys or ids], "reason", "on_unmet", "on_dep_failed", "context"}], "supersedes": [...], "notes": str}`.
  Executors are Plan 2; today each kind is schema + metadata only.

- [ ] **Step 1: Write the failing tests**

`tests/kinds/test_registry.py`:
```python
from app.kinds.registry import KINDS, get_kind, validate_params


def test_the_catalog_lists_every_kind_the_spec_names() -> None:
    assert set(KINDS) == {
        "check_issue_state", "check_pr_exists", "check_pr_reviewed", "check_pr_merged",
        "nudge", "escalate", "reconcile_item", "daily_review", "report",
    }


def test_params_are_validated_against_the_kinds_schema() -> None:
    clean, err = validate_params("check_issue_state", {"issue": "INV-142", "expect": ["Done"]})
    assert err is None and clean == {"issue": "INV-142", "expect": ["Done"]}
    clean, err = validate_params("check_issue_state", {"issue": "INV-142"})
    assert clean is None and err is not None and "expect" in err
    clean, err = validate_params("check_pr_exists", {"issue": "INV-142", "bogus": 1})
    assert clean is None and err is not None and "bogus" in err


def test_unknown_kinds_are_rejected() -> None:
    assert get_kind("delete_everything") is None
    clean, err = validate_params("delete_everything", {})
    assert clean is None and err == "unknown kind 'delete_everything'"


def test_each_kind_declares_which_unmet_actions_it_allows() -> None:
    assert "escalate_channel" in KINDS["check_issue_state"].unmet_actions
    assert KINDS["nudge"].unmet_actions == ()
```

`tests/verify/test_plan.py`:
```python
from datetime import UTC, datetime

from app.verify.plan import check_plan

NOW = datetime(2026, 8, 27, 9, 0, tzinfo=UTC)
POLICY = {"plan_horizon_days": 30, "max_plan_size": 12, "max_open_tasks": 50}
KNOWN_IDS = {"INV-142", "INV-104", "Nodir Rahimov"}


def plan(*tasks: dict, supersedes: list[str] | None = None) -> dict:  # type: ignore[type-arg]
    return {"tasks": list(tasks), "supersedes": supersedes or [], "notes": ""}


def task(key: str, kind: str, params: dict, due: str, **kw) -> dict:  # type: ignore[no-untyped-def, type-arg]
    return {"key": key, "kind": kind, "params": params, "due": due, "reason": f"{key} reason",
            "depends_on": kw.get("depends_on", []), "on_unmet": kw.get("on_unmet", "none"),
            "on_dep_failed": kw.get("on_dep_failed", "skip"), "context": kw.get("context", {})}


def check(p: dict, open_tasks: int = 0):  # type: ignore[no-untyped-def, type-arg]
    return check_plan(p, now=NOW, policy=POLICY, open_tasks=open_tasks,
                      existing_ids=lambda tid: tid.startswith("existing-"),
                      id_exists=lambda ref: ref in KNOWN_IDS)


def test_a_valid_dependency_chain_is_accepted_in_topological_order_with_iso_due_dates() -> None:
    v = check(plan(
        task("review", "check_pr_reviewed", {"issue": "INV-142"}, "2026-08-30T16:00:00Z",
             depends_on=["pr"], on_unmet="nudge_reviewer"),
        task("impl", "check_issue_state", {"issue": "INV-142", "expect": ["In Progress"]},
             "2026-08-28T16:00:00Z", on_unmet="nudge_assignee"),
        task("pr", "check_pr_exists", {"issue": "INV-142"}, "2026-08-29T16:00:00Z",
             depends_on=["impl"]),
    ))
    assert v.ok and v.reasons == [] and v.rejected == []
    assert [t["key"] for t in v.tasks] == ["impl", "pr", "review"]
    assert v.tasks[0]["due_at"] == "2026-08-28T16:00:00+00:00"
    assert v.tasks[1]["depends_on"] == ["impl"]


def test_an_unknown_kind_or_bad_params_rejects_that_task_only() -> None:
    v = check(plan(
        task("ok", "check_issue_state", {"issue": "INV-142", "expect": ["Done"]}, "2026-08-28T09:00:00Z"),
        task("bad_kind", "launch_rockets", {}, "2026-08-28T09:00:00Z"),
        task("bad_params", "check_pr_exists", {"pull": 7}, "2026-08-28T09:00:00Z"),
    ))
    assert v.ok is False  # something was rejected, so the plan is not clean
    assert [t["key"] for t in v.tasks] == ["ok"]
    assert {r["key"] for r in v.rejected} == {"bad_kind", "bad_params"}


def test_a_task_referencing_an_unknown_issue_is_rejected_by_the_id_gate() -> None:
    v = check(plan(task("ghost", "check_issue_state", {"issue": "INV-999", "expect": ["Done"]},
                        "2026-08-28T09:00:00Z")))
    assert v.tasks == [] and "INV-999" in v.rejected[0]["reason"]


def test_a_due_in_the_past_or_beyond_the_horizon_is_rejected() -> None:
    v = check(plan(
        task("past", "check_issue_state", {"issue": "INV-142", "expect": ["Done"]}, "2026-08-27T08:00:00Z"),
        task("far", "check_issue_state", {"issue": "INV-142", "expect": ["Done"]}, "2026-10-15T09:00:00Z"),
    ))
    assert v.tasks == []
    reasons = " ".join(r["reason"] for r in v.rejected)
    assert "in the past" in reasons and "horizon" in reasons


def test_a_cycle_rejects_the_whole_plan_with_a_reason() -> None:
    v = check(plan(
        task("a", "check_issue_state", {"issue": "INV-142", "expect": ["Done"]}, "2026-08-28T09:00:00Z",
             depends_on=["b"]),
        task("b", "check_pr_exists", {"issue": "INV-142"}, "2026-08-28T09:00:00Z", depends_on=["a"]),
    ))
    assert v.ok is False and v.tasks == [] and any("cycle" in r for r in v.reasons)


def test_dependencies_on_rejected_or_unknown_keys_cascade_to_rejection() -> None:
    v = check(plan(
        task("bad", "launch_rockets", {}, "2026-08-28T09:00:00Z"),
        task("child", "check_pr_exists", {"issue": "INV-142"}, "2026-08-28T09:00:00Z",
             depends_on=["bad"]),
        task("orphan", "check_pr_exists", {"issue": "INV-142"}, "2026-08-28T09:00:00Z",
             depends_on=["nope"]),
    ))
    assert v.tasks == []
    assert {r["key"] for r in v.rejected} == {"bad", "child", "orphan"}


def test_a_dependency_on_an_existing_open_task_id_is_allowed() -> None:
    v = check(plan(task("after", "nudge", {"person": "Nodir Rahimov", "about": "INV-142",
                                            "template": "still_open"},
                        "2026-08-28T09:00:00Z", depends_on=["existing-123"])))
    assert v.ok and v.tasks[0]["depends_on"] == ["existing-123"]


def test_an_unmet_action_the_kind_does_not_allow_is_rejected() -> None:
    v = check(plan(task("x", "check_pr_exists", {"issue": "INV-142"}, "2026-08-28T09:00:00Z",
                        on_unmet="escalate_channel")))
    assert v.tasks == [] and "on_unmet" in v.rejected[0]["reason"]


def test_plan_size_and_open_task_caps_trim_from_the_end_and_say_so() -> None:
    many = [task(f"t{i}", "check_issue_state", {"issue": "INV-142", "expect": ["Done"]},
                 "2026-08-28T09:00:00Z") for i in range(14)]
    v = check(plan(*many))
    assert len(v.tasks) == 12 and any("max_plan_size" in r for r in v.reasons)
    v = check(plan(*many[:5]), open_tasks=48)
    assert len(v.tasks) == 2 and any("max_open_tasks" in r for r in v.reasons)


def test_duplicate_keys_reject_the_later_one() -> None:
    v = check(plan(
        task("dup", "check_pr_exists", {"issue": "INV-142"}, "2026-08-28T09:00:00Z"),
        task("dup", "check_pr_exists", {"issue": "INV-104"}, "2026-08-28T09:00:00Z"),
    ))
    assert len(v.tasks) == 1 and v.rejected[0]["reason"] == "duplicate key 'dup'"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/kinds tests/verify/test_plan.py -q
```
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the kinds registry**

`app/kinds/__init__.py`: empty.

`app/kinds/base.py`:
```python
"""A task kind is the unit of what the planner may schedule: a name, a parameter schema, and the
unmet-actions it may trigger. Executors (Plan 2) are looked up by the same name in stages/."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KindSpec(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    params_schema: type[BaseModel]
    unmet_actions: tuple[str, ...]
    description: str


class StrictParams(BaseModel):
    """Params models forbid unknown fields, so a planner cannot smuggle intent through extras."""

    model_config = ConfigDict(extra="forbid")
```

`app/kinds/registry.py`:
```python
"""The whitelist. Adding a capability to the agent = one KindSpec here + one executor in stages."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.kinds.base import KindSpec, StrictParams

UNMET_ACTIONS = ("none", "nudge_assignee", "nudge_reviewer", "escalate_channel")


class IssueStateParams(StrictParams):
    issue: str
    expect: list[str]


class IssueParams(StrictParams):
    issue: str


class IssueOrPrParams(StrictParams):
    issue: str | None = None
    pr: str | None = None


class NudgeParams(StrictParams):
    person: str
    about: str
    template: str


class EscalateParams(StrictParams):
    about: str
    template: str


class ItemParams(StrictParams):
    item: dict[str, Any]


class ProjectParams(StrictParams):
    project: str


class ReportParams(StrictParams):
    project: str
    window: str = "7d"


KINDS: dict[str, KindSpec] = {
    spec.name: spec
    for spec in (
        KindSpec(name="check_issue_state", params_schema=IssueStateParams,
                 unmet_actions=("nudge_assignee", "escalate_channel"),
                 description="Is the Linear issue in one of the expected states?"),
        KindSpec(name="check_pr_exists", params_schema=IssueParams,
                 unmet_actions=("nudge_assignee",),
                 description="Does a pull request reference the issue?"),
        KindSpec(name="check_pr_reviewed", params_schema=IssueOrPrParams,
                 unmet_actions=("nudge_reviewer",),
                 description="Has the PR received at least one review?"),
        KindSpec(name="check_pr_merged", params_schema=IssueOrPrParams,
                 unmet_actions=("nudge_assignee", "escalate_channel"),
                 description="Is the PR merged?"),
        KindSpec(name="nudge", params_schema=NudgeParams, unmet_actions=(),
                 description="Send one templated nudge to a person about something."),
        KindSpec(name="escalate", params_schema=EscalateParams, unmet_actions=(),
                 description="Post one templated escalation to the project channel."),
        KindSpec(name="reconcile_item", params_schema=ItemParams, unmet_actions=(),
                 description="Re-run reconcile for one action item."),
        KindSpec(name="daily_review", params_schema=ProjectParams, unmet_actions=(),
                 description="Gather project state and enqueue a plan."),
        KindSpec(name="report", params_schema=ReportParams, unmet_actions=(),
                 description="Run the status report stage."),
    )
}


def get_kind(name: str) -> KindSpec | None:
    return KINDS.get(name)


def validate_params(kind: str, params: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """(clean params, None) or (None, one-line error the planner can act on)."""
    spec = KINDS.get(kind)
    if spec is None:
        return None, f"unknown kind {kind!r}"
    try:
        return spec.params_schema.model_validate(params).model_dump(), None
    except ValidationError as exc:
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first.get("loc", ())) or "params"
        return None, f"{kind}: {loc}: {first.get('msg', 'invalid')}"
```

- [ ] **Step 4: Write `app/verify/plan.py`**

```python
"""The plan gate. A planner's proposal becomes queue tasks only after this: known kinds, valid
params, unique keys, resolvable dependencies, no cycles, due times inside the horizon, every
referenced issue/person real, and the project's size caps respected."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.core.clock import iso, parse_iso
from app.kinds.registry import KINDS, UNMET_ACTIONS, validate_params

ID_PARAM_FIELDS = ("issue", "person", "pr")
DEP_POLICIES = ("skip", "run_anyway", "cancel")


@dataclass(frozen=True)
class PlanVerdict:
    ok: bool
    tasks: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def _parse_due(raw: Any) -> datetime | None:
    try:
        return parse_iso(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def check_plan(
    plan: dict[str, Any],
    *,
    now: datetime,
    policy: dict[str, Any],
    open_tasks: int,
    existing_ids: Callable[[str], bool],
    id_exists: Callable[[str], bool],
) -> PlanVerdict:
    horizon = now + timedelta(days=int(policy.get("plan_horizon_days", 30)))
    max_plan = int(policy.get("max_plan_size", 12))
    max_open = int(policy.get("max_open_tasks", 50))
    grace = now - timedelta(minutes=5)

    accepted: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, str]] = []
    reasons: list[str] = []

    # 1. per-task validation
    for raw in plan.get("tasks") or []:
        key = str(raw.get("key") or "")
        if not key:
            rejected.append({"key": "", "reason": "missing key"})
            continue
        if key in accepted:
            rejected.append({"key": key, "reason": f"duplicate key {key!r}"})
            continue
        kind = str(raw.get("kind") or "")
        clean, err = validate_params(kind, raw.get("params") or {})
        if err is not None or clean is None:
            rejected.append({"key": key, "reason": err or "invalid params"})
            continue
        spec = KINDS[kind]
        on_unmet = str(raw.get("on_unmet") or "none")
        if on_unmet not in UNMET_ACTIONS or (on_unmet != "none" and on_unmet not in spec.unmet_actions):
            rejected.append({"key": key, "reason": f"on_unmet {on_unmet!r} not allowed for {kind}"})
            continue
        on_dep_failed = str(raw.get("on_dep_failed") or "skip")
        if on_dep_failed not in DEP_POLICIES:
            rejected.append({"key": key, "reason": f"on_dep_failed {on_dep_failed!r} invalid"})
            continue
        due = _parse_due(raw.get("due"))
        if due is None:
            rejected.append({"key": key, "reason": "due is not an ISO-8601 timestamp"})
            continue
        if due < grace:
            rejected.append({"key": key, "reason": f"due {iso(due)} is in the past"})
            continue
        if due > horizon:
            rejected.append({"key": key, "reason": f"due {iso(due)} is beyond the plan horizon"})
            continue
        missing = [str(clean[f]) for f in ID_PARAM_FIELDS if clean.get(f) and not id_exists(str(clean[f]))]
        if missing:
            rejected.append({"key": key, "reason": f"unknown identifier(s): {', '.join(missing)}"})
            continue
        accepted[key] = {
            "key": key, "kind": kind, "params": clean, "due_at": iso(due),
            "reason": str(raw.get("reason") or ""), "depends_on": [str(d) for d in raw.get("depends_on") or []],
            "on_unmet": on_unmet, "on_dep_failed": on_dep_failed,
            "context": dict(raw.get("context") or {}), "payload": {},
        }

    # 2. dependency resolution — a dependency must be an accepted key or an existing open task id
    changed = True
    while changed:
        changed = False
        for key, t in list(accepted.items()):
            bad = [d for d in t["depends_on"] if d not in accepted and not existing_ids(d)]
            if bad:
                rejected.append({"key": key, "reason": f"depends on unknown or rejected: {', '.join(bad)}"})
                del accepted[key]
                changed = True

    # 3. cycle check + topological order (Kahn) over in-plan dependencies
    indeg = {k: sum(1 for d in t["depends_on"] if d in accepted) for k, t in accepted.items()}
    ready = sorted(k for k, n in indeg.items() if n == 0)
    ordered: list[str] = []
    while ready:
        k = ready.pop(0)
        ordered.append(k)
        for other, t in accepted.items():
            if k in t["depends_on"]:
                indeg[other] -= 1
                if indeg[other] == 0:
                    ready.append(other)
                    ready.sort()
    if len(ordered) != len(accepted):
        reasons.append("dependency cycle detected; the whole plan is rejected")
        return PlanVerdict(ok=False, tasks=[], rejected=rejected, reasons=reasons)

    # 4. size caps — trim from the end of the topological order so no accepted task loses a dependency
    tasks = [accepted[k] for k in ordered]
    if len(tasks) > max_plan:
        reasons.append(f"plan trimmed from {len(tasks)} to max_plan_size {max_plan}")
        tasks = tasks[:max_plan]
    room = max(0, max_open - open_tasks)
    if len(tasks) > room:
        reasons.append(f"plan trimmed from {len(tasks)} to {room} by max_open_tasks {max_open}")
        tasks = tasks[:room]
    kept = {t["key"] for t in tasks}
    tasks = [{**t, "depends_on": [d for d in t["depends_on"] if d in kept or existing_ids(d)]} for t in tasks]

    return PlanVerdict(ok=not rejected and not reasons, tasks=tasks, rejected=rejected, reasons=reasons)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/kinds tests/verify -q && uv run mypy app && uv run lint-imports && uv run ruff check .
```
Expected: pass; import-linter allows `verify → kinds` and `kinds → core` only.

- [ ] **Step 6: Commit**

```bash
git add app/kinds/__init__.py app/kinds/base.py app/kinds/registry.py app/verify/plan.py \
  tests/kinds/__init__.py tests/kinds/test_registry.py tests/verify/test_plan.py
git commit -m "feat: task kinds catalog and the plan gate (kinds, params, deps, cycles, horizon, caps)"
```

---

### Task 7: `clients/fathom.py` — signature and payload parsing

**Files:**
- Create: `app/clients/fathom.py`, `tests/fixtures/fathom_webhook_sample.json`
- Test: `tests/clients/test_fathom.py`

**Interfaces:**
- Produces:
  ```python
  def verify_signature(secret: str, headers: Mapping[str, str], raw_body: bytes, now_epoch: int, *, tolerance_seconds: int = 300) -> bool
  def parse_meeting(payload: dict) -> dict   # normalized, keys below
  def transcript_plain(meeting: dict) -> str # all spoken text joined by spaces (for the evidence gate)
  def render_transcript(segments: list[dict]) -> str  # "[HH:MM:SS] Speaker: text" lines (for the model)
  ```
  Normalized meeting: `{"meeting_id": str, "title": str, "url": str, "recorded_at": str, "invitees": [{"name","email"}], "transcript": [{"speaker","email","text","timestamp"}], "summary_md": str, "action_items": [{"description","timestamp","assignee_name"}]}`.

- [ ] **Step 1: Write the sample payload (from the documented Meeting schema; Task 14 replaces it with a real capture)**

`tests/fixtures/fathom_webhook_sample.json`:
```json
{
  "recording_id": 8841201,
  "title": "Q3 Billing planning",
  "meeting_title": "Q3 Billing planning",
  "url": "https://fathom.video/calls/8841201",
  "share_url": "https://fathom.video/share/abc123",
  "created_at": "2026-08-27T09:00:12Z",
  "recording_start_time": "2026-08-27T09:00:12Z",
  "recording_end_time": "2026-08-27T09:06:40Z",
  "calendar_invitees": [
    {"name": "Maya Chen", "email": "maya@acme-invoicing.test", "is_external": false},
    {"name": "Nodir Rahimov", "email": "nodir@acme-invoicing.test", "is_external": false}
  ],
  "transcript": [
    {"speaker": {"display_name": "Maya Chen", "matched_calendar_invitee_email": "maya@acme-invoicing.test"},
     "text": "Let's move payment reminders to three days after the due date. Nodir, can you own that?",
     "timestamp": "00:01:42"},
    {"speaker": {"display_name": "Nodir Rahimov", "matched_calendar_invitee_email": "nodir@acme-invoicing.test"},
     "text": "Sure, I can have that done by next Friday.",
     "timestamp": "00:01:58"}
  ],
  "default_summary": {"template_name": "General", "markdown_formatted": "- Reminders move to 3 days (Nodir)"},
  "action_items": [
    {"description": "Move payment reminders to 3 days", "user_generated": false, "completed": false,
     "recording_timestamp": "00:01:42", "recording_playback_url": "https://fathom.video/calls/8841201?t=102",
     "assignee": {"name": "Nodir Rahimov", "email": "nodir@acme-invoicing.test", "team": null}}
  ]
}
```

- [ ] **Step 2: Write the failing tests**

`tests/clients/test_fathom.py`:
```python
import base64
import hashlib
import hmac
import json
from pathlib import Path

from app.clients.fathom import parse_meeting, render_transcript, transcript_plain, verify_signature

SAMPLE = Path(__file__).parents[1] / "fixtures" / "fathom_webhook_sample.json"
SECRET_BYTES = b"0123456789abcdef0123456789abcdef"
SECRET = "whsec_" + base64.b64encode(SECRET_BYTES).decode()


def sign(body: bytes, msg_id: str, ts: int) -> str:
    signed = f"{msg_id}.{ts}.".encode() + body
    return base64.b64encode(hmac.new(SECRET_BYTES, signed, hashlib.sha256).digest()).decode()


def test_a_correctly_signed_fresh_webhook_verifies() -> None:
    body = b'{"recording_id": 1}'
    ts = 1_800_000_000
    headers = {"webhook-id": "msg_1", "webhook-timestamp": str(ts),
               "webhook-signature": f"v1,{sign(body, 'msg_1', ts)}"}
    assert verify_signature(SECRET, headers, body, now_epoch=ts + 10) is True


def test_a_tampered_body_or_wrong_secret_fails() -> None:
    body = b'{"recording_id": 1}'
    ts = 1_800_000_000
    headers = {"webhook-id": "msg_1", "webhook-timestamp": str(ts),
               "webhook-signature": f"v1,{sign(body, 'msg_1', ts)}"}
    assert verify_signature(SECRET, headers, b'{"recording_id": 2}', now_epoch=ts) is False
    other = "whsec_" + base64.b64encode(b"x" * 32).decode()
    assert verify_signature(other, headers, body, now_epoch=ts) is False


def test_a_stale_timestamp_is_rejected_even_with_a_valid_signature() -> None:
    body = b"{}"
    ts = 1_800_000_000
    headers = {"webhook-id": "m", "webhook-timestamp": str(ts),
               "webhook-signature": f"v1,{sign(body, 'm', ts)}"}
    assert verify_signature(SECRET, headers, body, now_epoch=ts + 301) is False


def test_missing_headers_or_empty_secret_never_verify() -> None:
    assert verify_signature(SECRET, {}, b"{}", now_epoch=0) is False
    assert verify_signature("", {"webhook-id": "m", "webhook-timestamp": "0",
                                 "webhook-signature": "v1,x"}, b"{}", now_epoch=0) is False


def test_parse_meeting_normalises_the_documented_shape() -> None:
    meeting = parse_meeting(json.loads(SAMPLE.read_text()))
    assert meeting["meeting_id"] == "8841201"
    assert meeting["title"] == "Q3 Billing planning"
    assert meeting["url"] == "https://fathom.video/share/abc123"
    assert meeting["recorded_at"] == "2026-08-27T09:00:12Z"
    assert meeting["invitees"][0] == {"name": "Maya Chen", "email": "maya@acme-invoicing.test"}
    seg = meeting["transcript"][0]
    assert seg == {"speaker": "Maya Chen", "email": "maya@acme-invoicing.test",
                   "text": "Let's move payment reminders to three days after the due date. "
                           "Nodir, can you own that?", "timestamp": "00:01:42"}
    assert meeting["summary_md"].startswith("- Reminders")
    assert meeting["action_items"][0] == {"description": "Move payment reminders to 3 days",
                                          "timestamp": "00:01:42", "assignee_name": "Nodir Rahimov"}


def test_parse_meeting_tolerates_missing_optional_sections() -> None:
    meeting = parse_meeting({"recording_id": 5, "title": "x"})
    assert meeting["transcript"] == [] and meeting["action_items"] == []
    assert meeting["summary_md"] == "" and meeting["invitees"] == []


def test_transcript_renderings() -> None:
    meeting = parse_meeting(json.loads(SAMPLE.read_text()))
    assert render_transcript(meeting["transcript"]).splitlines()[0].startswith(
        "[00:01:42] Maya Chen: Let's move payment reminders")
    assert "Sure, I can have that done by next Friday." in transcript_plain(meeting)
    assert "[00:01:42]" not in transcript_plain(meeting)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/clients/test_fathom.py -q
```
Expected: FAIL with `ModuleNotFoundError: No module named 'app.clients.fathom'`.

- [ ] **Step 4: Write `app/clients/fathom.py`**

```python
"""Fathom webhook verification and payload normalisation. The REST client (meetings, transcript
re-fetch) is added in Plan 2 if the webhook payload turns out to omit anything we need."""

from __future__ import annotations

import base64
import hashlib
import hmac
from collections.abc import Mapping
from typing import Any


def _header(headers: Mapping[str, str], name: str) -> str:
    return headers.get(name) or headers.get(name.lower()) or headers.get(name.title()) or ""


def verify_signature(
    secret: str,
    headers: Mapping[str, str],
    raw_body: bytes,
    now_epoch: int,
    *,
    tolerance_seconds: int = 300,
) -> bool:
    """Standard-Webhooks style: HMAC-SHA256 over "<id>.<timestamp>.<body>" with the base64 secret
    after the whsec_ prefix. Fails closed on any missing piece or a stale timestamp."""
    if not secret or "_" not in secret:
        return False
    msg_id = _header(headers, "webhook-id")
    ts_raw = _header(headers, "webhook-timestamp")
    sig_header = _header(headers, "webhook-signature")
    if not (msg_id and ts_raw and sig_header):
        return False
    try:
        ts = int(ts_raw)
        key = base64.b64decode(secret.split("_", 1)[1])
    except ValueError:
        return False
    if abs(now_epoch - ts) > tolerance_seconds:
        return False
    signed = f"{msg_id}.{ts_raw}.".encode() + raw_body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    candidates = [part.split(",", 1)[1] if "," in part else part for part in sig_header.split()]
    return any(hmac.compare_digest(expected, c) for c in candidates)


def parse_meeting(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalise a Fathom meeting object (webhook body or /meetings item) into the shape the
    stages use. Every field is optional upstream; nothing here raises on a missing section."""
    invitees = [
        {"name": i.get("name"), "email": i.get("email")}
        for i in payload.get("calendar_invitees") or []
    ]
    transcript = []
    for seg in payload.get("transcript") or []:
        speaker = seg.get("speaker") or {}
        transcript.append({
            "speaker": speaker.get("display_name") or "Unknown",
            "email": speaker.get("matched_calendar_invitee_email"),
            "text": seg.get("text") or "",
            "timestamp": seg.get("timestamp") or "",
        })
    action_items = [
        {
            "description": a.get("description") or "",
            "timestamp": a.get("recording_timestamp") or "",
            "assignee_name": (a.get("assignee") or {}).get("name"),
        }
        for a in payload.get("action_items") or []
    ]
    return {
        "meeting_id": str(payload.get("recording_id") or payload.get("id") or ""),
        "title": payload.get("title") or payload.get("meeting_title") or "",
        "url": payload.get("share_url") or payload.get("url") or "",
        "recorded_at": payload.get("recording_start_time") or payload.get("created_at") or "",
        "invitees": invitees,
        "transcript": transcript,
        "summary_md": (payload.get("default_summary") or {}).get("markdown_formatted") or "",
        "action_items": action_items,
    }


def render_transcript(segments: list[dict[str, Any]]) -> str:
    """What the model reads: one line per segment with its timestamp and speaker."""
    return "\n".join(f"[{s['timestamp']}] {s['speaker']}: {s['text']}" for s in segments)


def transcript_plain(meeting: dict[str, Any]) -> str:
    """What the evidence gate matches against: spoken words only, no timestamps or names, so a
    quote is judged on the words actually said."""
    return " ".join(s["text"] for s in meeting["transcript"])
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/clients -q && uv run mypy app && uv run ruff check .
```
Expected: `7 passed`; clean.

- [ ] **Step 6: Commit**

```bash
git add app/clients/fathom.py tests/clients/test_fathom.py tests/fixtures/fathom_webhook_sample.json
git commit -m "feat(clients): Fathom webhook signature verification and meeting normalisation"
```

---

### Task 8: `store/events.py`, `store/projects.py`, `deps.py`, the Fathom webhook route

**Files:**
- Create: `app/store/events.py`, `app/store/projects.py`, `app/deps.py`, `app/http/webhooks.py`, `app/main.py` (first version: `create_app` only), `tests/conftest.py`
- Test: `tests/store/test_events.py`, `tests/store/test_projects.py`, `tests/http/test_webhooks.py`

**Interfaces:**
- Produces:
  ```python
  class EventStore:
      def __init__(self, db: Db, clock: Clock) -> None
      async def record(self, *, provider: str, provider_event_id: str, payload: dict, project_id: str) -> str | None
      async def get(self, event_id: str) -> Doc | None
      async def note(self, event_id: str, note: str) -> None

  class ProjectStore:
      def __init__(self, db: Db, default_slug: str) -> None
      async def get(self, slug: str) -> Doc | None
      async def default(self) -> Doc          # raises PmError if the default project is not seeded
      async def upsert(self, slug: str, data: dict) -> None

  @dataclass
  class Deps:  # app/deps.py
      settings: Settings; db: Db; clock: Clock; queue: TaskQueue; events: EventStore
      projects: ProjectStore; decisions: DecisionStore; extractor: Extractor; triage: Triage
  ```
  (`DecisionStore`, `Extractor`, `Triage` are defined in Tasks 9–10; Deps imports them, so those files are created here as minimal stubs and filled in by their own tasks — see Step 4.)
  Route: `POST /webhooks/fathom` → 401 on bad signature; `{"status": "duplicate"}` on redelivery; `{"status": "no_transcript"}` when the payload has no transcript; `{"status": "queued", "task_id": ...}` otherwise.

- [ ] **Step 1: Write the failing tests**

`tests/store/test_events.py`:
```python
from datetime import UTC, datetime

from app.store.events import EventStore
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_db import FakeDb


async def test_recording_the_same_provider_event_twice_returns_none_the_second_time() -> None:
    db = FakeDb()
    events = EventStore(db, FakeClock(datetime(2026, 8, 27, 9, 0, tzinfo=UTC)))
    first = await events.record(provider="fathom", provider_event_id="msg_1",
                                payload={"a": 1}, project_id="acme")
    assert first == "fathom:msg_1"
    second = await events.record(provider="fathom", provider_event_id="msg_1",
                                 payload={"a": 2}, project_id="acme")
    assert second is None
    doc = await events.get("fathom:msg_1")
    assert doc is not None
    assert doc["payload"] == {"a": 1} and doc["received_at"] == "2026-08-27T09:00:00+00:00"


async def test_note_appends_without_touching_the_payload() -> None:
    db = FakeDb()
    events = EventStore(db, FakeClock(datetime(2026, 8, 27, 9, 0, tzinfo=UTC)))
    await events.record(provider="fathom", provider_event_id="m", payload={}, project_id="acme")
    await events.note("fathom:m", "no transcript")
    doc = await events.get("fathom:m")
    assert doc is not None and doc["notes"] == ["no transcript"]
```

`tests/store/test_projects.py`:
```python
import pytest

from app.core.errors import PmError
from app.store.projects import ProjectStore
from tests.fakes.fake_db import FakeDb


async def test_default_project_is_looked_up_by_slug() -> None:
    db = FakeDb()
    store = ProjectStore(db, default_slug="acme")
    await store.upsert("acme", {"slug": "acme", "roster": [], "policy": {}})
    proj = await store.default()
    assert proj["id"] == "acme" and proj["slug"] == "acme"


async def test_a_missing_default_project_fails_closed() -> None:
    store = ProjectStore(FakeDb(), default_slug="acme")
    with pytest.raises(PmError):
        await store.default()
```

`tests/conftest.py`:
```python
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.agents.triage import PassthroughTriage
from app.config import Settings
from app.deps import Deps
from app.main import create_app
from app.store.decisions import DecisionStore
from app.store.events import EventStore
from app.store.projects import ProjectStore
from app.store.tasks import TaskQueue
from tests.fakes.fake_agents import FakeExtractor
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_db import FakeDb

T0 = datetime(2026, 8, 27, 9, 0, tzinfo=UTC)

ACME = {
    "slug": "acme",
    "linear_team_id": "",
    "linear_project_id": "",
    "notion_root_page_id": "",
    "slack_channel_id": "",
    "code_repo": "fixtures/acme-invoicing",
    "roster": [
        {"name": "Maya Chen", "aliases": ["Maya"], "linear_user_id": "", "slack_id": "", "role": "pm"},
        {"name": "Nodir Rahimov", "aliases": ["Nodir"], "linear_user_id": "", "slack_id": "",
         "role": "backend"},
        {"name": "Priya Nair", "aliases": ["Priya"], "linear_user_id": "", "slack_id": "",
         "role": "frontend"},
        {"name": "Tom Alvarez", "aliases": ["Tom"], "linear_user_id": "", "slack_id": "",
         "role": "support"},
    ],
    "policy": {"max_depth": 4, "max_children": 12, "max_plan_size": 12, "max_open_tasks": 50,
               "plan_horizon_days": 30},
}


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(T0)


@pytest.fixture
def db() -> FakeDb:
    return FakeDb()


@pytest.fixture
def settings() -> Settings:
    return Settings.for_tests(fathom_webhook_secret="", tick_token="tick-secret")


@pytest.fixture
def extractor() -> FakeExtractor:
    return FakeExtractor([])


@pytest.fixture
async def deps(db: FakeDb, clock: FakeClock, settings: Settings, extractor: FakeExtractor) -> Deps:
    projects = ProjectStore(db, default_slug=settings.default_project_slug)
    await projects.upsert("acme", ACME)
    return Deps(
        settings=settings,
        db=db,
        clock=clock,
        queue=TaskQueue(db, clock, lease_minutes=settings.lease_minutes),
        events=EventStore(db, clock),
        projects=projects,
        decisions=DecisionStore(db, clock),
        extractor=extractor,
        triage=PassthroughTriage(),
    )


@pytest.fixture
def client(deps: Deps) -> TestClient:
    return TestClient(create_app(deps))
```

`tests/http/test_webhooks.py`:
```python
import base64
import hashlib
import hmac
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.deps import Deps

SAMPLE = (Path(__file__).parents[1] / "fixtures" / "fathom_webhook_sample.json").read_bytes()
SECRET_BYTES = b"0123456789abcdef0123456789abcdef"
SECRET = "whsec_" + base64.b64encode(SECRET_BYTES).decode()
TS = 1_787_821_200  # 2026-08-27T09:00:00Z, matches conftest T0


def signed_headers(body: bytes, msg_id: str = "msg_1") -> dict[str, str]:
    signed = f"{msg_id}.{TS}.".encode() + body
    sig = base64.b64encode(hmac.new(SECRET_BYTES, signed, hashlib.sha256).digest()).decode()
    return {"webhook-id": msg_id, "webhook-timestamp": str(TS), "webhook-signature": f"v1,{sig}"}


def test_an_unsigned_webhook_is_rejected_and_nothing_is_stored(client: TestClient, deps: Deps) -> None:
    deps.settings.fathom_webhook_secret = SECRET
    r = client.post("/webhooks/fathom", content=SAMPLE)
    assert r.status_code == 401


def test_a_webhook_with_no_secret_configured_is_rejected(client: TestClient) -> None:
    r = client.post("/webhooks/fathom", content=SAMPLE, headers=signed_headers(SAMPLE))
    assert r.status_code == 401


async def test_a_signed_webhook_stores_the_event_and_enqueues_extract(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.fathom_webhook_secret = SECRET
    r = client.post("/webhooks/fathom", content=SAMPLE, headers=signed_headers(SAMPLE))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued"
    task = await deps.db.get("tasks", body["task_id"])
    assert task is not None
    assert task["kind"] == "extract" and task["payload"] == {"event_id": "fathom:msg_1"}
    assert task["root_event_id"] == "fathom:msg_1" and task["project_id"] == "acme"
    assert "Q3 Billing planning" in task["reason"]


async def test_a_redelivered_webhook_is_a_no_op(client: TestClient, deps: Deps) -> None:
    deps.settings.fathom_webhook_secret = SECRET
    client.post("/webhooks/fathom", content=SAMPLE, headers=signed_headers(SAMPLE))
    r = client.post("/webhooks/fathom", content=SAMPLE, headers=signed_headers(SAMPLE))
    assert r.json() == {"status": "duplicate"}
    assert await deps.db.count("tasks", []) == 1


async def test_a_call_without_a_transcript_is_recorded_but_not_queued(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.fathom_webhook_secret = SECRET
    payload = json.loads(SAMPLE)
    payload["transcript"] = []
    body = json.dumps(payload).encode()
    r = client.post("/webhooks/fathom", content=body, headers=signed_headers(body, "msg_2"))
    assert r.json() == {"status": "no_transcript"}
    event = await deps.events.get("fathom:msg_2")
    assert event is not None and event["notes"] == ["no transcript in payload"]
    assert await deps.db.count("tasks", []) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/store/test_events.py tests/store/test_projects.py tests/http -q
```
Expected: FAIL with `ModuleNotFoundError` (events/projects/deps/main/decisions/fake_agents).

- [ ] **Step 3: Write the stores**

`app/store/events.py`:
```python
"""Inbound events. The doc id is provider:provider_event_id, so create() failing IS the dedupe."""

from __future__ import annotations

from typing import Any

from app.core.clock import Clock, iso
from app.core.keys import event_doc_id
from app.store.db import Db, Doc


class EventStore:
    def __init__(self, db: Db, clock: Clock) -> None:
        self._db = db
        self._clock = clock

    async def record(
        self, *, provider: str, provider_event_id: str, payload: dict[str, Any], project_id: str
    ) -> str | None:
        """The event id if this is the first delivery; None if we have seen it before."""
        doc_id = event_doc_id(provider, provider_event_id)
        created = await self._db.create("events", doc_id, {
            "provider": provider,
            "provider_event_id": provider_event_id,
            "payload": payload,
            "project_id": project_id,
            "received_at": iso(self._clock.now()),
            "notes": [],
        })
        return doc_id if created else None

    async def get(self, event_id: str) -> Doc | None:
        return await self._db.get("events", event_id)

    async def note(self, event_id: str, note: str) -> None:
        current = await self._db.get("events", event_id)
        notes = list((current or {}).get("notes") or [])
        notes.append(note)
        await self._db.update("events", event_id, {"notes": notes})
```

`app/store/projects.py`:
```python
"""Project configuration: roster, policy, and the ids of the external workspaces."""

from __future__ import annotations

from typing import Any

from app.core.errors import PmError
from app.store.db import Db, Doc


class ProjectStore:
    def __init__(self, db: Db, default_slug: str) -> None:
        self._db = db
        self._default_slug = default_slug

    async def get(self, slug: str) -> Doc | None:
        return await self._db.get("projects", slug)

    async def default(self) -> Doc:
        """Fails closed: with no configured project there is no roster and no policy, and
        nothing may run without those."""
        doc = await self.get(self._default_slug)
        if doc is None:
            raise PmError(f"default project {self._default_slug!r} is not seeded")
        return doc

    async def upsert(self, slug: str, data: dict[str, Any]) -> None:
        await self._db.set("projects", slug, {**data, "slug": slug})
```

- [ ] **Step 4: Write the minimal stubs that Deps needs (filled in by Tasks 9–10)**

`app/store/decisions.py` (stub — Task 10 replaces the body):
```python
"""Decision ledger. Full implementation in Task 10."""

from __future__ import annotations

from typing import Any

from app.core.clock import Clock
from app.store.db import Db


class DecisionStore:
    def __init__(self, db: Db, clock: Clock) -> None:
        self._db = db
        self._clock = clock

    async def add_many(
        self, project_id: str, event_id: str, decisions: list[dict[str, Any]], meeting: dict[str, Any]
    ) -> list[str]:
        raise NotImplementedError
```

`app/agents/protocols.py`:
```python
"""What a stage needs from the model side. Stages depend on these, never on ADK directly, so
every stage test runs against a fake."""

from __future__ import annotations

from typing import Any, Protocol


class Extractor(Protocol):
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """payload: {"transcript": str, "roster_names": [str], "feedback": str | None}.
        Returns a dict shaped like agents.schemas.ExtractResult (validated by the stage)."""
        ...


class Triage(Protocol):
    def decision_bearing(self, segments: list[dict[str, Any]]) -> list[bool]:
        """One flag per transcript segment: worth showing the extractor?"""
        ...
```

`app/agents/triage.py`:
```python
"""Segment triage. PassthroughTriage keeps everything; GemmaTriage arrives in Plan 4."""

from __future__ import annotations

from typing import Any


class PassthroughTriage:
    def decision_bearing(self, segments: list[dict[str, Any]]) -> list[bool]:
        return [True] * len(segments)
```

`tests/fakes/fake_agents.py`:
```python
from __future__ import annotations

from typing import Any


class FakeExtractor:
    """Returns canned results in order; records every payload it was given."""

    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = list(results)
        self.calls: list[dict[str, Any]] = []

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        if not self.results:
            raise AssertionError("FakeExtractor has no more canned results")
        return self.results.pop(0)
```

`app/deps.py`:
```python
"""Everything a route or a stage needs, in one object, so wiring lives in main.py and tests
build it from fakes in one place (tests/conftest.py)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.protocols import Extractor, Triage
from app.config import Settings
from app.core.clock import Clock
from app.store.db import Db
from app.store.decisions import DecisionStore
from app.store.events import EventStore
from app.store.projects import ProjectStore
from app.store.tasks import TaskQueue


@dataclass
class Deps:
    settings: Settings
    db: Db
    clock: Clock
    queue: TaskQueue
    events: EventStore
    projects: ProjectStore
    decisions: DecisionStore
    extractor: Extractor
    triage: Triage
```

- [ ] **Step 5: Write the webhook route and `create_app`**

`app/http/webhooks.py`:
```python
"""Inbound webhooks. Verify, store, enqueue, return — no model work happens on this path."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.clients.fathom import parse_meeting, verify_signature
from app.deps import Deps

router = APIRouter()


@router.post("/webhooks/fathom")
async def fathom_webhook(request: Request) -> dict[str, Any]:
    deps: Deps = request.app.state.deps
    raw = await request.body()
    secret = deps.settings.fathom_webhook_secret
    now_epoch = int(deps.clock.now().timestamp())
    if not verify_signature(secret, request.headers, raw, now_epoch):
        raise HTTPException(status_code=401, detail="bad signature")

    payload = json.loads(raw)
    provider_event_id = request.headers.get("webhook-id") or str(payload.get("recording_id") or "")
    project = await deps.projects.default()
    event_id = await deps.events.record(
        provider="fathom", provider_event_id=provider_event_id, payload=payload,
        project_id=project["id"],
    )
    if event_id is None:
        return {"status": "duplicate"}

    meeting = parse_meeting(payload)
    if not meeting["transcript"]:
        # Plan 2 adds the one-line Slack notice; today the note in the event is the record.
        await deps.events.note(event_id, "no transcript in payload")
        return {"status": "no_transcript"}

    task_id = await deps.queue.enqueue(
        kind="extract",
        project_id=project["id"],
        payload={"event_id": event_id},
        reason=f"Fathom call '{meeting['title']}' finished; extract decisions and action items",
        root_event_id=event_id,
        policy=project.get("policy"),
    )
    return {"status": "queued", "task_id": task_id}
```

`app/main.py` (first version):
```python
"""App factory. create_app(deps) is what tests and the server both use; build_deps() is the
only place real clients are constructed."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from app.deps import Deps
from app.http import webhooks


def create_app(deps: Deps) -> FastAPI:
    app = FastAPI(title="pm-agent", docs_url=None, redoc_url=None)
    app.state.deps = deps
    app.include_router(webhooks.router)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"ok": True}

    return app
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/store tests/http -q && uv run mypy app && uv run lint-imports && uv run ruff check .
```
Expected: all pass; `deps.settings.fathom_webhook_secret = SECRET` mutation works because pydantic-settings models are mutable by default.

- [ ] **Step 7: Commit**

```bash
git add app/store/events.py app/store/projects.py app/store/decisions.py app/agents/protocols.py \
  app/agents/triage.py app/deps.py app/http/webhooks.py app/main.py tests/conftest.py \
  tests/fakes/fake_agents.py tests/store/test_events.py tests/store/test_projects.py \
  tests/http/test_webhooks.py
git commit -m "feat: Fathom webhook — verify, dedupe, enqueue extract"
```

---

### Task 9: `agents/schemas.py` and `verify/evidence.py`

**Files:**
- Create: `app/agents/schemas.py`, `app/verify/evidence.py`
- Test: `tests/agents/test_schemas.py`, `tests/verify/test_evidence.py`

**Interfaces:**
- Produces: pydantic models `Evidence(quote, timestamp="", speaker="")`, `Decision(statement, rejected_options=[], evidence)`, `ActionItem(title, description="", owner_name=None, due_hint=None, priority_hint=None, evidence)`, `OpenQuestion(question, evidence)`, `ExtractResult(decisions=[], action_items=[], open_questions=[])`.
  `normalize(text) -> str`; `quote_in_transcript(quote, transcript_norm) -> bool`; `EvidenceVerdict(kept: list[dict], dropped: list[dict])`; `check_evidence(items, transcript_text) -> EvidenceVerdict`; `MIN_QUOTE_CHARS = 12`.

- [ ] **Step 1: Write the failing tests**

`tests/agents/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError

from app.agents.schemas import ExtractResult


def test_extract_result_validates_the_documented_shape() -> None:
    raw = {
        "decisions": [{"statement": "Reminders move to 3 days", "rejected_options": ["SMS"],
                       "evidence": [{"quote": "move payment reminders to three days",
                                     "timestamp": "00:01:42", "speaker": "Maya Chen"}]}],
        "action_items": [{"title": "Move reminders to 3 days", "owner_name": "Nodir Rahimov",
                          "due_hint": "next Friday",
                          "evidence": [{"quote": "I can have that done by next Friday"}]}],
        "open_questions": [],
    }
    result = ExtractResult.model_validate(raw)
    assert result.decisions[0].rejected_options == ["SMS"]
    assert result.action_items[0].description == ""
    assert result.action_items[0].priority_hint is None


def test_an_item_without_an_evidence_list_is_invalid() -> None:
    with pytest.raises(ValidationError):
        ExtractResult.model_validate({"decisions": [{"statement": "x"}]})


def test_empty_sections_default_to_empty_lists() -> None:
    assert ExtractResult.model_validate({}).model_dump() == {
        "decisions": [], "action_items": [], "open_questions": []}
```

`tests/verify/test_evidence.py`:
```python
from app.verify.evidence import check_evidence, normalize, quote_in_transcript

TRANSCRIPT = (
    "Let's move payment reminders to three days after the due date. Nodir, can you own that? "
    "Sure, I can have that done by next Friday. We considered SMS reminders — decided no for now."
)


def test_normalize_folds_case_whitespace_and_smart_punctuation() -> None:
    assert normalize("Let’s  MOVE “payment”\nreminders") == "let's move \"payment\" reminders"


def test_an_exact_quote_matches() -> None:
    assert quote_in_transcript("move payment reminders to three days", normalize(TRANSCRIPT))


def test_a_quote_with_different_casing_and_curly_quotes_still_matches() -> None:
    assert quote_in_transcript("Let’s move Payment Reminders", normalize(TRANSCRIPT))


def test_a_quote_spanning_two_speakers_matches_because_words_are_what_count() -> None:
    assert quote_in_transcript("can you own that? Sure, I can have", normalize(TRANSCRIPT))


def test_a_paraphrase_does_not_match() -> None:
    assert not quote_in_transcript("reminders will be sent after 3 days", normalize(TRANSCRIPT))


def test_a_trivially_short_quote_never_counts_as_evidence() -> None:
    assert not quote_in_transcript("Sure,", normalize(TRANSCRIPT))


def test_check_evidence_keeps_items_with_a_real_quote_and_drops_the_rest_with_a_reason() -> None:
    items = [
        {"title": "ok", "evidence": [{"quote": "I can have that done by next Friday"},
                                     {"quote": "this was never said in the call"}]},
        {"title": "hallucinated", "evidence": [{"quote": "we will ship SMS reminders in Q4"}]},
    ]
    verdict = check_evidence(items, TRANSCRIPT)
    assert [i["title"] for i in verdict.kept] == ["ok"]
    assert verdict.kept[0]["evidence"] == [{"quote": "I can have that done by next Friday"}]
    assert verdict.dropped[0]["title"] == "hallucinated"
    assert verdict.dropped[0]["gate_reason"] == "no verbatim quote found in transcript"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_schemas.py tests/verify/test_evidence.py -q
```
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `app/agents/schemas.py`**

```python
"""Output schemas for the ADK agents. ADK forces the model to emit exactly these shapes; the
stages validate again with the same classes, so gates always operate on typed data."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    quote: str = Field(description="Verbatim words from the transcript, at least 12 characters.")
    timestamp: str = Field(default="", description="HH:MM:SS of the segment the quote is from.")
    speaker: str = Field(default="", description="Speaker display name for that segment.")


class Decision(BaseModel):
    statement: str = Field(description="What was decided, as a single declarative sentence.")
    rejected_options: list[str] = Field(default_factory=list,
                                        description="Alternatives explicitly considered and not chosen.")
    evidence: list[Evidence]


class ActionItem(BaseModel):
    title: str = Field(description="Imperative, under 80 characters, suitable as an issue title.")
    description: str = Field(default="", description="One or two sentences of context.")
    owner_name: str | None = Field(default=None,
                                   description="A roster name if one was named; otherwise null.")
    due_hint: str | None = Field(default=None,
                                 description="The due date exactly as spoken, e.g. 'next Friday'.")
    priority_hint: str | None = Field(default=None,
                                      description="Urgency language exactly as spoken, if any.")
    evidence: list[Evidence]


class OpenQuestion(BaseModel):
    question: str
    evidence: list[Evidence]


class ExtractResult(BaseModel):
    decisions: list[Decision] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
```

- [ ] **Step 4: Write `app/verify/evidence.py`**

```python
"""The evidence gate: an extracted item survives only if at least one of its quotes appears
verbatim in the transcript. This single rule removes most hallucinated action items."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MIN_QUOTE_CHARS = 12

_FOLD = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-"})


def normalize(text: str) -> str:
    return " ".join(text.translate(_FOLD).lower().split())


def quote_in_transcript(quote: str, transcript_norm: str) -> bool:
    q = normalize(quote).strip(" .,;:!?\"'")
    return len(q) >= MIN_QUOTE_CHARS and q in transcript_norm


@dataclass(frozen=True)
class EvidenceVerdict:
    kept: list[dict[str, Any]]
    dropped: list[dict[str, Any]]


def check_evidence(items: list[dict[str, Any]], transcript_text: str) -> EvidenceVerdict:
    """Keep each item with only its verified quotes; drop items with none, tagging the reason
    so the stage can bounce the model once and report the drop honestly."""
    norm = normalize(transcript_text)
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for item in items:
        good = [e for e in item.get("evidence", []) if quote_in_transcript(e.get("quote", ""), norm)]
        if good:
            kept.append({**item, "evidence": good})
        else:
            dropped.append({**item, "gate_reason": "no verbatim quote found in transcript"})
    return EvidenceVerdict(kept=kept, dropped=dropped)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/agents tests/verify -q && uv run mypy app && uv run lint-imports
```
Expected: `15 passed`; clean.

- [ ] **Step 6: Commit**

```bash
git add app/agents/schemas.py app/verify/evidence.py tests/agents/test_schemas.py tests/verify/test_evidence.py
git commit -m "feat: extraction schemas and the verbatim-evidence gate"
```

---

### Task 10: `store/decisions.py`, `stages/base.py`, `stages/extract.py`

**Files:**
- Modify: `app/store/decisions.py` (replace the stub body)
- Create: `app/stages/base.py`, `app/stages/extract.py`
- Test: `tests/store/test_decisions.py`, `tests/stages/test_extract.py`

**Interfaces:**
- Consumes: `Deps`, `ExtractResult`, `check_evidence`, `parse_meeting`, `render_transcript`, `transcript_plain`.
- Produces:
  ```python
  # stages/base.py
  @dataclass(frozen=True)
  class StageResult:
      result: dict[str, Any]
      children: list[dict[str, Any]]      # child specs for TaskQueue.complete()
  StageHandler = Callable[[Doc, Deps], Awaitable[StageResult]]

  # stages/extract.py
  def select_with_context(segments: list[dict], flags: list[bool], window: int = 2) -> list[dict]
  async def run(task: Doc, deps: Deps) -> StageResult

  # store/decisions.py
  async def add_many(project_id, event_id, decisions: list[dict], meeting: dict) -> list[str]
  ```
  Extract result dict: `{"meeting": {"id","title","url"}, "action_items": [...], "open_questions": [...], "decision_ids": [...], "dropped": [...], "bounced": bool}`. Child enqueued: `{"kind": "reconcile", "payload": {"event_id", "extract_task_id"}, "reason": str}` — only when at least one action item or decision survived.

- [ ] **Step 1: Write the failing tests**

`tests/store/test_decisions.py`:
```python
from datetime import UTC, datetime

from app.store.decisions import DecisionStore
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_db import FakeDb


async def test_decisions_are_stored_with_a_fathom_source_pointer_and_empty_links() -> None:
    db = FakeDb()
    store = DecisionStore(db, FakeClock(datetime(2026, 8, 27, 9, 0, tzinfo=UTC)))
    ids = await store.add_many("acme", "fathom:msg_1", [
        {"statement": "Reminders move to 3 days", "rejected_options": ["SMS"],
         "evidence": [{"quote": "move payment reminders to three days", "timestamp": "00:01:42",
                       "speaker": "Maya Chen"}]},
    ], meeting={"meeting_id": "8841201", "title": "Q3", "url": "https://fathom.video/share/abc"})
    assert len(ids) == 1
    doc = await db.get("decisions", ids[0])
    assert doc is not None
    assert doc["source"] == "fathom:8841201@00:01:42"
    assert doc["quote"] == "move payment reminders to three days"
    assert doc["rejected_options"] == ["SMS"] and doc["linked_issue_ids"] == []
    assert doc["project_id"] == "acme" and doc["event_id"] == "fathom:msg_1"
    assert doc["created_at"] == "2026-08-27T09:00:00+00:00"
```

`tests/stages/test_extract.py`:
```python
import json
from pathlib import Path

from app.deps import Deps
from app.stages.extract import run, select_with_context
from tests.fakes.fake_agents import FakeExtractor

SAMPLE = json.loads((Path(__file__).parents[1] / "fixtures" / "fathom_webhook_sample.json").read_text())

GOOD = {
    "decisions": [{"statement": "Payment reminders move to three days after due date",
                   "rejected_options": [],
                   "evidence": [{"quote": "move payment reminders to three days after the due date",
                                 "timestamp": "00:01:42", "speaker": "Maya Chen"}]}],
    "action_items": [{"title": "Move payment reminders to 3 days", "owner_name": "Nodir Rahimov",
                      "due_hint": "next Friday",
                      "evidence": [{"quote": "I can have that done by next Friday",
                                    "timestamp": "00:01:58", "speaker": "Nodir Rahimov"}]}],
    "open_questions": [],
}
HALLUCINATED = {
    "decisions": [],
    "action_items": [{"title": "Ship SMS reminders", "evidence": [{"quote": "we will ship SMS in Q4"}]}],
    "open_questions": [],
}


async def seed_event_and_task(deps: Deps) -> dict:  # type: ignore[type-arg]
    event_id = await deps.events.record(provider="fathom", provider_event_id="msg_1",
                                        payload=SAMPLE, project_id="acme")
    assert event_id is not None
    tid = await deps.queue.enqueue(kind="extract", project_id="acme", payload={"event_id": event_id},
                                   reason="test", root_event_id=event_id)
    assert tid is not None
    task = await deps.queue.claim(tid)
    assert task is not None
    return task


def test_select_with_context_keeps_flagged_segments_plus_neighbours_in_order() -> None:
    segs = [{"text": str(i)} for i in range(8)]
    flags = [False, False, False, True, False, False, False, False]
    assert [s["text"] for s in select_with_context(segs, flags, window=2)] == ["1", "2", "3", "4", "5"]
    assert select_with_context(segs, [False] * 8) == []


async def test_extract_persists_decisions_and_enqueues_reconcile(deps: Deps) -> None:
    fake = FakeExtractor([GOOD])
    deps.extractor = fake
    task = await seed_event_and_task(deps)
    out = await run(task, deps)
    assert out.result["meeting"]["title"] == "Q3 Billing planning"
    assert [a["title"] for a in out.result["action_items"]] == ["Move payment reminders to 3 days"]
    assert len(out.result["decision_ids"]) == 1
    assert out.result["dropped"] == [] and out.result["bounced"] is False
    assert out.children == [{"kind": "reconcile",
                             "payload": {"event_id": "fathom:msg_1", "extract_task_id": task["id"]},
                             "reason": "reconcile 1 action item(s) and 1 decision(s) from "
                                       "'Q3 Billing planning' against Linear, Notion and code"}]
    payload = fake.calls[0]
    assert "[00:01:42] Maya Chen:" in payload["transcript"]
    assert "Nodir Rahimov" in payload["roster_names"] and payload["feedback"] is None
    assert await deps.db.count("decisions", []) == 1


async def test_an_item_without_a_verbatim_quote_is_bounced_once_then_dropped_not_guessed(
    deps: Deps,
) -> None:
    fake = FakeExtractor([HALLUCINATED, HALLUCINATED])
    deps.extractor = fake
    task = await seed_event_and_task(deps)
    out = await run(task, deps)
    assert out.result["action_items"] == []
    assert out.result["bounced"] is True
    assert out.result["dropped"][0]["title"] == "Ship SMS reminders"
    assert out.result["dropped"][0]["gate_reason"] == "no verbatim quote found in transcript"
    assert len(fake.calls) == 2
    assert "Ship SMS reminders" in (fake.calls[1]["feedback"] or "")
    assert out.children == []  # nothing survived, nothing to reconcile


async def test_the_bounce_can_rescue_an_item_when_the_model_supplies_a_real_quote(deps: Deps) -> None:
    deps.extractor = FakeExtractor([HALLUCINATED, GOOD])
    task = await seed_event_and_task(deps)
    out = await run(task, deps)
    assert out.result["bounced"] is True and out.result["dropped"] == []
    assert len(out.result["action_items"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/store/test_decisions.py tests/stages -q
```
Expected: FAIL (`NotImplementedError` for decisions; `ModuleNotFoundError` for stages).

- [ ] **Step 3: Replace `app/store/decisions.py`**

```python
"""Decision ledger: every decision a call produced, with the exact moment it was said. Started
in v0 so it is queryable later; nothing reads it yet except the report stage (Plan 4)."""

from __future__ import annotations

from typing import Any

from app.core.clock import Clock, iso
from app.core.keys import new_id
from app.store.db import Db


class DecisionStore:
    def __init__(self, db: Db, clock: Clock) -> None:
        self._db = db
        self._clock = clock

    async def add_many(
        self,
        project_id: str,
        event_id: str,
        decisions: list[dict[str, Any]],
        meeting: dict[str, Any],
    ) -> list[str]:
        ids: list[str] = []
        now = iso(self._clock.now())
        for d in decisions:
            first = (d.get("evidence") or [{}])[0]
            doc_id = new_id()
            await self._db.create("decisions", doc_id, {
                "statement": d["statement"],
                "rejected_options": list(d.get("rejected_options") or []),
                "source": f"fathom:{meeting['meeting_id']}@{first.get('timestamp', '')}",
                "quote": first.get("quote", ""),
                "meeting_title": meeting.get("title", ""),
                "meeting_url": meeting.get("url", ""),
                "linked_issue_ids": [],
                "project_id": project_id,
                "event_id": event_id,
                "created_at": now,
            })
            ids.append(doc_id)
        return ids
```

- [ ] **Step 4: Write `app/stages/base.py`**

```python
"""Shared stage types. A stage is a function (task, deps) -> StageResult; it never writes to the
queue itself — the runner does, atomically with marking the task done."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.deps import Deps
from app.store.db import Doc


@dataclass(frozen=True)
class StageResult:
    result: dict[str, Any]
    children: list[dict[str, Any]] = field(default_factory=list)


StageHandler = Callable[[Doc, Deps], Awaitable[StageResult]]
```

- [ ] **Step 5: Write `app/stages/extract.py`**

```python
"""extract: transcript → decisions, action items, open questions — each with verbatim evidence,
or not at all. One bounce on a gate failure, then an honest drop."""

from __future__ import annotations

from typing import Any

from app.agents.schemas import ExtractResult
from app.clients.fathom import parse_meeting, render_transcript, transcript_plain
from app.core.errors import PmError
from app.deps import Deps
from app.stages.base import StageResult
from app.store.db import Doc
from app.verify.evidence import check_evidence

SECTIONS = ("decisions", "action_items", "open_questions")


def select_with_context(
    segments: list[dict[str, Any]], flags: list[bool], window: int = 2
) -> list[dict[str, Any]]:
    """Flagged segments plus `window` neighbours on each side, original order, no duplicates."""
    keep: set[int] = set()
    for i, flagged in enumerate(flags):
        if flagged:
            keep.update(range(max(0, i - window), min(len(segments), i + window + 1)))
    return [segments[i] for i in sorted(keep)]


def _gate(parsed: dict[str, Any], plain: str) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    kept: dict[str, list[dict[str, Any]]] = {}
    dropped: list[dict[str, Any]] = []
    for section in SECTIONS:
        verdict = check_evidence(parsed.get(section, []), plain)
        kept[section] = verdict.kept
        dropped.extend({**d, "section": section} for d in verdict.dropped)
    return kept, dropped


def _label(item: dict[str, Any]) -> str:
    return str(item.get("title") or item.get("statement") or item.get("question") or "?")


async def run(task: Doc, deps: Deps) -> StageResult:
    event = await deps.events.get(task["payload"]["event_id"])
    if event is None:
        raise PmError(f"event {task['payload']['event_id']} not found")
    project = await deps.projects.get(task["project_id"])
    if project is None:
        raise PmError(f"project {task['project_id']} not found")

    meeting = parse_meeting(event["payload"])
    flags = deps.triage.decision_bearing(meeting["transcript"])
    selected = select_with_context(meeting["transcript"], flags)
    payload: dict[str, Any] = {
        "transcript": render_transcript(selected),
        "roster_names": [m["name"] for m in project.get("roster", [])],
        "feedback": None,
    }
    plain = transcript_plain(meeting)

    parsed = ExtractResult.model_validate(await deps.extractor.run(payload)).model_dump()
    kept, dropped = _gate(parsed, plain)
    bounced = False
    if dropped:
        bounced = True
        names = "; ".join(_label(d) for d in dropped)
        feedback = (
            "These items were dropped because none of their quotes appear verbatim in the "
            f"transcript: {names}. Re-extract; every quote must be copied exactly from the "
            "transcript text. Omit any item you cannot support with an exact quote."
        )
        parsed = ExtractResult.model_validate(
            await deps.extractor.run({**payload, "feedback": feedback})
        ).model_dump()
        kept, dropped = _gate(parsed, plain)

    decision_ids = await deps.decisions.add_many(
        task["project_id"], event["id"], kept["decisions"], meeting
    )
    result: dict[str, Any] = {
        "meeting": {"id": meeting["meeting_id"], "title": meeting["title"], "url": meeting["url"]},
        "action_items": kept["action_items"],
        "open_questions": kept["open_questions"],
        "decision_ids": decision_ids,
        "dropped": dropped,
        "bounced": bounced,
    }
    children: list[dict[str, Any]] = []
    if kept["action_items"] or kept["decisions"]:
        children.append({
            "kind": "reconcile",
            "payload": {"event_id": event["id"], "extract_task_id": task["id"]},
            "reason": (
                f"reconcile {len(kept['action_items'])} action item(s) and "
                f"{len(kept['decisions'])} decision(s) from '{meeting['title']}' against "
                "Linear, Notion and code"
            ),
        })
    return StageResult(result=result, children=children)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/store tests/stages -q && uv run mypy app && uv run lint-imports && uv run ruff check .
```
Expected: pass; import-linter confirms `stages` → `deps` → `agents.protocols` is allowed and `agents` imports nothing from `store`.

- [ ] **Step 7: Commit**

```bash
git add app/store/decisions.py app/stages/base.py app/stages/extract.py \
  tests/store/test_decisions.py tests/stages/test_extract.py
git commit -m "feat(stages): extract stage with evidence gate, one bounce, and decision ledger"
```

---

### Task 11: `stages/runner.py` and `POST /tick`

**Files:**
- Create: `app/stages/runner.py`, `app/http/tick.py`
- Modify: `app/main.py` (include the tick router)
- Test: `tests/stages/test_runner.py`, `tests/http/test_tick.py`

**Interfaces:**
- Produces: `STAGES: dict[str, StageHandler] = {"extract": extract.run}`; `async def run_task(task: Doc, deps: Deps) -> str` returning `"done" | "queued" | "failed" | "skipped"`. Route `POST /tick` with header `X-Tick-Token`; 401 without it; returns `{"processed": n, "outcomes": [...]}`.

- [ ] **Step 1: Write the failing tests**

`tests/stages/test_runner.py`:
```python
import asyncio
import json
from pathlib import Path

from app.deps import Deps
from app.stages import runner
from app.stages.base import StageResult
from app.store.db import Doc
from tests.fakes.fake_agents import FakeExtractor

SAMPLE = json.loads((Path(__file__).parents[1] / "fixtures" / "fathom_webhook_sample.json").read_text())
GOOD = {"decisions": [], "open_questions": [],
        "action_items": [{"title": "t", "evidence": [{"quote": "I can have that done by next Friday"}]}]}


async def seed(deps: Deps, kind: str = "extract") -> str:
    event_id = await deps.events.record(provider="fathom", provider_event_id="m", payload=SAMPLE,
                                        project_id="acme")
    tid = await deps.queue.enqueue(kind=kind, project_id="acme", payload={"event_id": event_id},
                                   reason="t", root_event_id=event_id)
    assert tid is not None
    return tid


async def test_a_successful_stage_marks_the_task_done_and_enqueues_its_children(deps: Deps) -> None:
    deps.extractor = FakeExtractor([GOOD])
    tid = await seed(deps)
    task = (await deps.queue.due(["extract"], 10))[0]
    assert await runner.run_task(task, deps) == "done"
    done = await deps.db.get("tasks", tid)
    assert done is not None and done["status"] == "done"
    assert await deps.db.count("tasks", [("kind", "==", "reconcile")]) == 1


async def test_a_raising_stage_is_requeued_with_a_redacted_reason(deps: Deps) -> None:
    class Boom:
        async def run(self, payload: dict) -> dict:  # type: ignore[type-arg]
            raise RuntimeError("linear token lin_api_SECRET123 rejected")

    deps.extractor = Boom()
    tid = await seed(deps)
    task = (await deps.queue.due(["extract"], 10))[0]
    assert await runner.run_task(task, deps) == "queued"
    doc = await deps.db.get("tasks", tid)
    assert doc is not None
    assert "lin_api_SECRET123" not in doc["error"] and "RuntimeError" in doc["error"]


async def test_a_stage_that_exceeds_the_timeout_is_treated_as_a_failure(deps: Deps) -> None:
    async def slow(task: Doc, d: Deps) -> StageResult:
        await asyncio.sleep(0.2)
        return StageResult({})

    runner.STAGES["slow"] = slow
    try:
        deps.settings.stage_timeout_seconds = 0
        tid = await seed(deps, kind="slow")
        task = (await deps.queue.due(["slow"], 10))[0]
        assert await runner.run_task(task, deps) == "queued"
        doc = await deps.db.get("tasks", tid)
        assert doc is not None and "TimeoutError" in doc["error"]
    finally:
        del runner.STAGES["slow"]


async def test_a_task_someone_else_claimed_is_skipped(deps: Deps) -> None:
    deps.extractor = FakeExtractor([GOOD])
    await seed(deps)
    task = (await deps.queue.due(["extract"], 10))[0]
    assert await deps.queue.claim(task["id"]) is not None
    assert await runner.run_task(task, deps) == "skipped"
```

`tests/http/test_tick.py`:
```python
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.deps import Deps
from tests.fakes.fake_agents import FakeExtractor

SAMPLE = json.loads((Path(__file__).parents[1] / "fixtures" / "fathom_webhook_sample.json").read_text())
GOOD = {"decisions": [], "open_questions": [],
        "action_items": [{"title": "t", "evidence": [{"quote": "I can have that done by next Friday"}]}]}


def test_tick_without_the_token_is_rejected(client: TestClient) -> None:
    assert client.post("/tick").status_code == 401
    assert client.post("/tick", headers={"X-Tick-Token": "wrong"}).status_code == 401


async def test_tick_runs_due_tasks_and_reports_outcomes(client: TestClient, deps: Deps) -> None:
    deps.extractor = FakeExtractor([GOOD])
    event_id = await deps.events.record(provider="fathom", provider_event_id="m", payload=SAMPLE,
                                        project_id="acme")
    await deps.queue.enqueue(kind="extract", project_id="acme", payload={"event_id": event_id},
                             reason="t", root_event_id=event_id)
    r = client.post("/tick", headers={"X-Tick-Token": "tick-secret"})
    assert r.status_code == 200
    assert r.json() == {"processed": 1, "outcomes": ["done"]}
    r = client.post("/tick", headers={"X-Tick-Token": "tick-secret"})
    assert r.json()["processed"] == 0  # reconcile is queued but has no handler yet
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/stages/test_runner.py tests/http/test_tick.py -q
```
Expected: FAIL with `ModuleNotFoundError: No module named 'app.stages.runner'`.

- [ ] **Step 3: Write `app/stages/runner.py`**

```python
"""Claim → run → complete-or-fail. The only code that both runs a stage and touches the queue."""

from __future__ import annotations

import asyncio

from app.core.redact import redact
from app.deps import Deps
from app.stages import extract
from app.stages.base import StageHandler
from app.store.db import Doc

STAGES: dict[str, StageHandler] = {
    "extract": extract.run,
}


async def run_task(task: Doc, deps: Deps) -> str:
    """Returns the task's status after this attempt: done, queued (retry), failed, or skipped."""
    claimed = await deps.queue.claim(task["id"])
    if claimed is None:
        return "skipped"
    handler = STAGES.get(claimed["kind"])
    if handler is None:
        return await deps.queue.fail(claimed, f"no handler for kind {claimed['kind']!r}")
    try:
        outcome = await asyncio.wait_for(
            handler(claimed, deps), timeout=deps.settings.stage_timeout_seconds
        )
    except Exception as exc:  # noqa: BLE001 — the queue owns retry policy; we only classify
        return await deps.queue.fail(claimed, redact(f"{type(exc).__name__}: {exc}"))
    await deps.queue.complete(claimed, outcome.result, outcome.children)
    return "done"
```

- [ ] **Step 4: Write `app/http/tick.py` and include it in `main.py`**

`app/http/tick.py`:
```python
"""The heartbeat. Cloud Scheduler POSTs here once a minute with the shared token; we run every
due task whose kind we know how to handle, sequentially, oldest first."""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.deps import Deps
from app.stages.runner import STAGES, run_task

router = APIRouter()


@router.post("/tick")
async def tick(request: Request) -> dict[str, Any]:
    deps: Deps = request.app.state.deps
    expected = deps.settings.tick_token
    given = request.headers.get("x-tick-token", "")
    if not expected or not hmac.compare_digest(given, expected):
        raise HTTPException(status_code=401, detail="bad tick token")
    due = await deps.queue.due(list(STAGES), deps.settings.tick_batch)
    outcomes = [await run_task(task, deps) for task in due]
    return {"processed": len(outcomes), "outcomes": outcomes}
```

In `app/main.py`, change the import and router lines:
```python
from app.http import tick, webhooks
...
    app.include_router(webhooks.router)
    app.include_router(tick.router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest -q && uv run mypy app && uv run lint-imports && uv run ruff check .
```
Expected: all pass (live tests skipped).

- [ ] **Step 6: Commit**

```bash
git add app/stages/runner.py app/http/tick.py app/main.py tests/stages/test_runner.py tests/http/test_tick.py
git commit -m "feat: stage runner with timeout and retry classification; /tick heartbeat"
```

---

### Task 12: `agents/adk_runner.py`, `agents/extractor.py`, real wiring in `main.py`

**Files:**
- Create: `app/agents/adk_runner.py`, `app/agents/extractor.py`
- Modify: `app/main.py` (add `build_deps`, `create_default_app`)
- Test: `tests/agents/test_extractor_live.py`

**Interfaces:**
- Produces: `async def run_agent_once(agent: LlmAgent, message: str, *, state: dict | None = None) -> str`; `class GeminiExtractor(model: str)` implementing `Extractor`; `EXTRACTOR_INSTRUCTION: str`; `def build_deps(settings: Settings | None = None) -> Deps`; `def create_default_app() -> FastAPI`.

- [ ] **Step 1: Write the live test (skipped without a key)**

`tests/agents/test_extractor_live.py`:
```python
"""Hits Gemini. Skipped unless GOOGLE_API_KEY is set. This is the one place we check that the
real model, the schema and the evidence gate agree on a real transcript."""

import os
from pathlib import Path

import pytest

from app.agents.extractor import GeminiExtractor
from app.agents.schemas import ExtractResult
from app.config import Settings
from app.verify.evidence import check_evidence, normalize, quote_in_transcript

pytestmark = pytest.mark.live
live = pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="no GOOGLE_API_KEY")
SCRIPT = Path(__file__).parents[2] / "fixtures" / "transcripts" / "01-q3-planning.md"


def script_as_transcript() -> tuple[str, str]:
    """The rehearsal script doubles as a transcript: '**Name:** text' lines → segments."""
    rendered, plain = [], []
    for i, line in enumerate(SCRIPT.read_text().splitlines()):
        if line.startswith("**") and ":**" in line:
            name, text = line[2:].split(":**", 1)
            ts = f"00:{i // 60:02d}:{i % 60:02d}"
            rendered.append(f"[{ts}] {name.strip()}: {text.strip()}")
            plain.append(text.strip())
    return "\n".join(rendered), " ".join(plain)


@live
async def test_the_real_extractor_returns_schema_valid_items_with_verbatim_quotes() -> None:
    transcript, plain = script_as_transcript()
    extractor = GeminiExtractor(Settings.for_tests().model_fast)
    raw = await extractor.run({"transcript": transcript,
                               "roster_names": ["Maya Chen", "Nodir Rahimov", "Priya Nair", "Tom Alvarez"],
                               "feedback": None})
    result = ExtractResult.model_validate(raw).model_dump()
    assert result["decisions"], "expected at least one decision from the planning call"
    assert result["action_items"], "expected at least one action item"
    verdict = check_evidence(result["action_items"], plain)
    assert len(verdict.kept) >= len(result["action_items"]) // 2, verdict.dropped
    assert any(quote_in_transcript(e["quote"], normalize(plain))
               for d in result["decisions"] for e in d["evidence"])
```

- [ ] **Step 2: Write `app/agents/adk_runner.py`**

```python
"""One-shot ADK execution: fresh in-memory session per call, return the final text. Firestore
is the source of truth for everything durable; ADK session state is scratch."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

APP_NAME = "pm-agent"
USER_ID = "harness"


async def run_agent_once(agent: LlmAgent, message: str, *, state: dict[str, Any] | None = None) -> str:
    sessions = InMemorySessionService()
    session = await sessions.create_session(app_name=APP_NAME, user_id=USER_ID, state=state or {})
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=sessions)
    content = types.Content(role="user", parts=[types.Part(text=message)])
    final = ""
    async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=content):
        if event.is_final_response() and event.content and event.content.parts:
            final = "".join(part.text or "" for part in event.content.parts)
    return final
```

If the installed ADK's `create_session` is synchronous (older releases), remove the `await` on that one line; the live test in Step 1 is what tells you.

- [ ] **Step 3: Write `app/agents/extractor.py`**

```python
"""The extractor agent: reads a transcript, returns ExtractResult. No tools — it only reads."""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents import LlmAgent
from google.genai import types

from app.agents.adk_runner import run_agent_once
from app.agents.schemas import ExtractResult

EXTRACTOR_INSTRUCTION = """You are the extraction step of an autonomous product-manager agent.

You receive JSON with:
- "transcript": lines formatted "[HH:MM:SS] Speaker: words"
- "roster_names": the people on this project
- "feedback": null, or a note about items that were rejected on a previous attempt

Extract three kinds of items and return ONLY the JSON schema you were given:
1. decisions — things the group settled on. Include options that were explicitly considered and
   rejected in rejected_options.
2. action_items — concrete work someone should do. title is imperative and under 80 characters.
   owner_name must be EXACTLY one of roster_names, or null if the person named is not on the
   roster or nobody was named. due_hint and priority_hint repeat the speaker's words verbatim
   (e.g. "by next Friday", "this is urgent"); null when nothing was said.
3. open_questions — questions raised and left unanswered.

EVIDENCE RULES (these are checked mechanically; items that fail are discarded):
- Every item MUST include at least one evidence entry.
- evidence.quote MUST be copied verbatim from the transcript: same words, same order, at least
  12 characters. Do not paraphrase, do not fix grammar, do not merge two sentences.
- Fill timestamp and speaker from the line the quote came from.

Do not invent names, dates or identifiers. If the transcript contains no decisions or action
items, return empty lists. Prefer fewer, well-supported items over many weak ones."""


class GeminiExtractor:
    def __init__(self, model: str) -> None:
        self._agent = LlmAgent(
            name="extractor",
            model=model,
            instruction=EXTRACTOR_INSTRUCTION,
            output_schema=ExtractResult,
            include_contents="none",
            generate_content_config=types.GenerateContentConfig(
                temperature=0.1, max_output_tokens=8192
            ),
        )

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = await run_agent_once(self._agent, json.dumps(payload, ensure_ascii=False))
        parsed: dict[str, Any] = json.loads(text)
        return parsed
```

- [ ] **Step 4: Add real wiring to `app/main.py`**

Append to `app/main.py`:
```python
from app.agents.extractor import GeminiExtractor
from app.agents.triage import PassthroughTriage
from app.config import Settings
from app.core.clock import SystemClock
from app.store.decisions import DecisionStore
from app.store.events import EventStore
from app.store.firestore import FirestoreDb
from app.store.projects import ProjectStore
from app.store.tasks import TaskQueue


def build_deps(settings: Settings | None = None) -> Deps:
    """Real clients. Called once per process, never at import time."""
    s = settings or Settings()
    db = FirestoreDb(s.gcp_project, s.firestore_database)
    clock = SystemClock()
    return Deps(
        settings=s,
        db=db,
        clock=clock,
        queue=TaskQueue(db, clock, lease_minutes=s.lease_minutes),
        events=EventStore(db, clock),
        projects=ProjectStore(db, default_slug=s.default_project_slug),
        decisions=DecisionStore(db, clock),
        extractor=GeminiExtractor(s.model_fast),
        triage=PassthroughTriage(),
    )


def create_default_app() -> FastAPI:
    """uvicorn entry point: `uvicorn app.main:create_default_app --factory`."""
    return create_app(build_deps())
```
(Move these imports to the top of the file with the others; ruff `I` will insist.)

- [ ] **Step 5: Run the gates, then the live test once**

```bash
uv run ruff check . && uv run mypy app && uv run lint-imports && uv run pytest -q
GOOGLE_API_KEY=$GOOGLE_API_KEY GOOGLE_GENAI_USE_VERTEXAI=FALSE uv run pytest tests/agents/test_extractor_live.py -q -m live
```
Expected: gates green; the live test passes once Task 13's transcript script exists (run it again after Task 13 if you reach this first). If the model returns prose around the JSON, ADK's `output_schema` is not being honoured for this model id — switch `model_fast` to `gemini-3.5-flash` and re-run; record the outcome in the README.

- [ ] **Step 6: Commit**

```bash
git add app/agents/adk_runner.py app/agents/extractor.py app/main.py tests/agents/test_extractor_live.py
git commit -m "feat(agents): Gemini extractor on ADK with fixed output schema; real wiring"
```

---

### Task 13: Fixtures — the fake company

**Files:**
- Create: `fixtures/acme-invoicing/README.md`, `fixtures/acme-invoicing/acme/__init__.py`, `fixtures/acme-invoicing/acme/config.py`, `fixtures/acme-invoicing/acme/flags.py`, `fixtures/acme-invoicing/acme/models.py`, `fixtures/acme-invoicing/acme/reminders/__init__.py`, `fixtures/acme-invoicing/acme/reminders/scheduler.py`, `fixtures/acme-invoicing/acme/invoices/__init__.py`, `fixtures/acme-invoicing/acme/invoices/export.py`, `fixtures/transcripts/01-q3-planning.md`, `fixtures/roster.json`, `fixtures/projects/acme.json`, `scripts/seed_project.py`

**Interfaces:**
- Produces: a greppable repo whose behaviour contradicts the Notion spec and the call in known ways; a call script with six planted moments; `scripts/seed_project.py` writing the `projects/acme` document.

- [ ] **Step 1: Write the fake product**

`fixtures/acme-invoicing/README.md`:
```markdown
# Acme Invoicing

Small invoicing SaaS used as the demo company for pm-agent. Customers, invoices, payments and a
reminders module. Deliberately contains: a feature flag, a dead code path, a config override,
and a reminder window (7 days) that disagrees with the PRD (5 days) and with the Q3 planning
call (3 days).
```

`fixtures/acme-invoicing/acme/__init__.py`: empty.

`fixtures/acme-invoicing/acme/config.py`:
```python
"""Runtime configuration. Environment overrides win over defaults."""

import os

# Days after an invoice's due date before the first payment reminder is sent.
REMINDER_DAYS = int(os.environ.get("ACME_REMINDER_DAYS", "7"))

# Days between subsequent reminders.
REMINDER_REPEAT_DAYS = int(os.environ.get("ACME_REMINDER_REPEAT_DAYS", "7"))

LATE_FEE_PERCENT = float(os.environ.get("ACME_LATE_FEE_PERCENT", "0"))
```

`fixtures/acme-invoicing/acme/flags.py`:
```python
"""Feature flags. Flipped per environment at deploy time."""

FLAGS = {
    "auto_reminders": True,        # send reminders without a human clicking
    "invoice_export_csv": False,   # CSV export of invoices (in development)
    "late_fees": False,            # charge late fees (not decided)
    "sms_reminders": False,        # never shipped
}


def enabled(name: str) -> bool:
    return FLAGS.get(name, False)
```

`fixtures/acme-invoicing/acme/models.py`:
```python
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Customer:
    id: str
    name: str
    email: str


@dataclass
class Invoice:
    id: str
    customer_id: str
    amount_cents: int
    issued_on: date
    due_on: date
    paid_on: date | None = None
    reminders_sent: list[date] = field(default_factory=list)

    @property
    def is_paid(self) -> bool:
        return self.paid_on is not None
```

`fixtures/acme-invoicing/acme/reminders/__init__.py`: empty.

`fixtures/acme-invoicing/acme/reminders/scheduler.py`:
```python
"""Decides which unpaid invoices get a payment reminder today."""

from datetime import date, timedelta

from acme.config import REMINDER_DAYS, REMINDER_REPEAT_DAYS
from acme.flags import enabled
from acme.models import Invoice


def due_for_reminder(invoice: Invoice, today: date) -> bool:
    """First reminder REMINDER_DAYS after due_on, then every REMINDER_REPEAT_DAYS."""
    if invoice.is_paid or not enabled("auto_reminders"):
        return False
    first = invoice.due_on + timedelta(days=REMINDER_DAYS)
    if today < first:
        return False
    if not invoice.reminders_sent:
        return True
    return today >= invoice.reminders_sent[-1] + timedelta(days=REMINDER_REPEAT_DAYS)


def legacy_reminder_window() -> int:
    """Pre-v0.3 behaviour: reminders went out 14 days after due. Unused since the scheduler
    moved to REMINDER_DAYS; kept for the data migration that still imports it."""
    return 14


def select(invoices: list[Invoice], today: date) -> list[Invoice]:
    return [inv for inv in invoices if due_for_reminder(inv, today)]
```

`fixtures/acme-invoicing/acme/invoices/__init__.py`: empty.

`fixtures/acme-invoicing/acme/invoices/export.py`:
```python
"""Invoice export. CSV is behind the invoice_export_csv flag and currently omits payments."""

import csv
import io

from acme.flags import enabled
from acme.models import Invoice

COLUMNS = ["id", "customer_id", "amount_cents", "issued_on", "due_on"]


def to_csv(invoices: list[Invoice]) -> str:
    if not enabled("invoice_export_csv"):
        raise PermissionError("invoice_export_csv is disabled")
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(COLUMNS)
    for inv in invoices:
        writer.writerow([inv.id, inv.customer_id, inv.amount_cents, inv.issued_on, inv.due_on])
    return buf.getvalue()
```

- [ ] **Step 2: Write the call script**

`fixtures/transcripts/01-q3-planning.md`:
```markdown
# Call 1 — Q3 Billing planning (≈5 minutes, four voices)

Read naturally; small deviations are fine. Planted moments are marked in the margin comments
(do not read those aloud). Speakers: Maya (PM), Nodir (backend), Priya (frontend), Tom (support).

**Maya Chen:** Okay, let's get going. Agenda is reminders, the export request from Northwind, the overdue dashboard, and whatever Tom has from support.

**Tom Alvarez:** Support first then, since it's short. We had eleven tickets last week about people not noticing their invoice was overdue until a week after. They want the nudge sooner.

**Maya Chen:** Right. Today the first reminder goes out seven days after the due date. The PRD says five. So we're already off spec.
<!-- planted: spec says 5, code says 7 -->

**Nodir Rahimov:** The seven is just the default in config. It's one constant.

**Maya Chen:** Then let's move payment reminders to three days after the due date. Nodir, can you own that?
<!-- planted decision + owner: reminders → 3 days, Nodir -->

**Nodir Rahimov:** Sure, I can have that done by next Friday.
<!-- planted due date said aloud -->

**Priya Nair:** Should we also do SMS reminders? Two customers asked.

**Maya Chen:** We considered SMS reminders last quarter — decided no for now, email only until we have a provider we trust.
<!-- planted rejected option -->

**Tom Alvarez:** Fine by me. Second thing: Northwind is blocked on the CSV export. They can't close their books without it.

**Maya Chen:** This is urgent, a customer is blocked. Priya, can you take the invoice CSV export and get it behind the flag this week?
<!-- planted escalation → priority may leave the band; owner Priya -->

**Priya Nair:** Yes. One question — the spec says the export includes payments. The current code only writes the invoice columns.
<!-- planted code-vs-spec conflict on export -->

**Maya Chen:** Noted, let's keep that as an open question for now and ship the invoice columns first.

**Nodir Rahimov:** Also, Sam should look at the Stripe webhook retries. We dropped two events on Tuesday.
<!-- planted roster miss: Sam is not on the roster -->

**Maya Chen:** Sam's on the platform side, I'll ping them. Third: the overdue dashboard. Where are we?

**Priya Nair:** We need the overdue dashboard for the finance team. I think there's already a ticket from last quarter.
<!-- planted near-duplicate of a seeded issue (Plan 2) -->

**Maya Chen:** Probably. Let's check before we open another one. Last thing — do we charge late fees? Finance asked again.

**Tom Alvarez:** We've never decided that.

**Maya Chen:** Then it stays an open question. Need to check with finance before anything goes in the product.
<!-- planted open question -->

**Maya Chen:** That's it. Thanks all.
```

- [ ] **Step 3: Write roster and project seed data**

`fixtures/roster.json`:
```json
[
  {"name": "Maya Chen", "aliases": ["Maya"], "role": "pm", "email": "maya@acme-invoicing.test",
   "linear_user_id": "", "slack_id": ""},
  {"name": "Nodir Rahimov", "aliases": ["Nodir"], "role": "backend", "email": "nodir@acme-invoicing.test",
   "linear_user_id": "", "slack_id": ""},
  {"name": "Priya Nair", "aliases": ["Priya"], "role": "frontend", "email": "priya@acme-invoicing.test",
   "linear_user_id": "", "slack_id": ""},
  {"name": "Tom Alvarez", "aliases": ["Tom"], "role": "support", "email": "tom@acme-invoicing.test",
   "linear_user_id": "", "slack_id": ""}
]
```

`fixtures/projects/acme.json` (ids filled from your workspaces; empty until then):
```json
{
  "slug": "acme",
  "name": "Q3 Billing",
  "linear_team_id": "",
  "linear_project_id": "",
  "notion_root_page_id": "",
  "slack_channel_id": "",
  "code_repo": "fixtures/acme-invoicing",
  "timezone": "America/Los_Angeles",
  "policy": {
    "max_depth": 4,
    "max_children": 5,
    "daily_write_cap": 40,
    "daily_ping_cap": 10,
    "quiet_hours": ["20:00", "08:00"],
    "priority_band": [2, 4],
    "escalation_phrases": ["urgent", "blocker", "blocked", "p0", "asap"],
    "followup_offsets": ["-1d", "0d", "+3d"],
    "daily_model_budget_usd": 5.0
  }
}
```

`scripts/seed_project.py`:
```python
"""Write fixtures/projects/acme.json + fixtures/roster.json into Firestore as projects/acme.
Idempotent; re-run whenever the ids change. Requires ADC and PM_GCP_PROJECT."""

import asyncio
import json
from pathlib import Path

from app.config import Settings
from app.store.firestore import FirestoreDb
from app.store.projects import ProjectStore

ROOT = Path(__file__).parents[1] / "fixtures"


async def main() -> None:
    settings = Settings()
    project = json.loads((ROOT / "projects" / "acme.json").read_text())
    project["roster"] = json.loads((ROOT / "roster.json").read_text())
    db = FirestoreDb(settings.gcp_project, settings.firestore_database)
    await ProjectStore(db, settings.default_project_slug).upsert(project["slug"], project)
    print(f"seeded projects/{project['slug']} with {len(project['roster'])} roster members")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Check the fixture repo runs, seed the project, run the live extractor test**

```bash
cd fixtures/acme-invoicing && python3 -c "
from datetime import date
from acme.models import Invoice
from acme.reminders.scheduler import select
inv = Invoice('I1','C1',1000,date(2026,8,1),date(2026,8,15))
print('reminder on day 6:', select([inv], date(2026,8,21)))
print('reminder on day 7:', select([inv], date(2026,8,22)))" && cd ../..
PM_GCP_PROJECT=pm-agent-hack-2026 uv run python scripts/seed_project.py
GOOGLE_API_KEY=$GOOGLE_API_KEY GOOGLE_GENAI_USE_VERTEXAI=FALSE uv run pytest tests/agents/test_extractor_live.py -q -m live
uv run ruff check . && uv run mypy app && uv run lint-imports && uv run pytest -q
```
Expected: day 6 → `[]`, day 7 → `[Invoice(...)]`; `seeded projects/acme with 4 roster members`; live extractor test passes; gates green.

- [ ] **Step 5: Commit**

```bash
git add fixtures/acme-invoicing fixtures/transcripts/01-q3-planning.md fixtures/roster.json \
  fixtures/projects/acme.json scripts/seed_project.py
git commit -m "feat(fixtures): Acme Invoicing repo, Q3 planning call script, roster and project seed"
```

---

### Task 14: Deploy to Cloud Run, wire Cloud Scheduler, create the Fathom webhook, fire a real call

**Files:**
- Create: `deploy/Dockerfile`, `deploy/deploy.sh`, `deploy/scheduler.sh`, `deploy/secrets.md`
- Modify: `tests/fixtures/fathom_webhook_sample.json` (replace with a real capture, PII-free — it's our own fake company)

**Interfaces:**
- Produces: a public `https://pm-agent-….run.app` with `/healthz`, `/webhooks/fathom`, `/tick`; a Scheduler job hitting `/tick` every minute; a Fathom webhook pointing at the service.

- [ ] **Step 1: Write `deploy/Dockerfile`**

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /srv
ENV UV_PROJECT_ENVIRONMENT=/srv/.venv PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
COPY fixtures ./fixtures
RUN uv sync --frozen --no-dev
ENV PATH="/srv/.venv/bin:$PATH" PORT=8080
CMD ["sh", "-c", "uvicorn app.main:create_default_app --factory --host 0.0.0.0 --port ${PORT}"]
```

- [ ] **Step 2: Write `deploy/deploy.sh`**

```bash
#!/usr/bin/env bash
# Build from source and deploy. Secrets come from Secret Manager; nothing sensitive is passed here.
set -euo pipefail
PROJECT="${PM_GCP_PROJECT:-pm-agent-hack-2026}"
REGION="${PM_REGION:-us-central1}"
SERVICE="pm-agent"

gcloud run deploy "$SERVICE" \
  --project "$PROJECT" --region "$REGION" \
  --source . \
  --allow-unauthenticated \
  --timeout 900 --concurrency 4 --min-instances 0 --max-instances 2 \
  --set-env-vars "PM_GCP_PROJECT=$PROJECT,PM_DEFAULT_PROJECT_SLUG=acme,GOOGLE_GENAI_USE_VERTEXAI=FALSE" \
  --set-secrets "PM_TICK_TOKEN=pm-tick-token:latest,GOOGLE_API_KEY=pm-google-api-key:latest${PM_WITH_FATHOM:+,PM_FATHOM_WEBHOOK_SECRET=pm-fathom-webhook-secret:latest}"

gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.url)'
```

Add `.dockerignore`:
```
.venv
.git
tests
docs
.mypy_cache
.ruff_cache
.pytest_cache
__pycache__
.env
```

- [ ] **Step 3: Write `deploy/scheduler.sh`**

```bash
#!/usr/bin/env bash
# Create (or update) the one-minute tick. Reads the token from Secret Manager at creation time
# only; it is stored inside the Scheduler job, which is IAM-protected.
set -euo pipefail
PROJECT="${PM_GCP_PROJECT:-pm-agent-hack-2026}"
REGION="${PM_REGION:-us-central1}"
URL="$(gcloud run services describe pm-agent --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
TOKEN="$(gcloud secrets versions access latest --secret pm-tick-token --project "$PROJECT")"

if gcloud scheduler jobs describe pm-tick --project "$PROJECT" --location "$REGION" >/dev/null 2>&1; then
  VERB=update
else
  VERB=create
fi
gcloud scheduler jobs "$VERB" http pm-tick \
  --project "$PROJECT" --location "$REGION" \
  --schedule "* * * * *" --time-zone "Etc/UTC" \
  --uri "$URL/tick" --http-method POST \
  --headers "X-Tick-Token=$TOKEN" \
  --attempt-deadline 600s
echo "tick → $URL/tick every minute"
```

- [ ] **Step 4: Write `deploy/secrets.md`**

```markdown
# Secrets and one-time setup

Values live only in Secret Manager and your shell. Never in files, never in argv you paste
into a chat.

| Secret | Created by | Consumed by |
|---|---|---|
| `pm-tick-token` | Task 0 step 3 | Cloud Run env `PM_TICK_TOKEN`; Scheduler header |
| `pm-google-api-key` | Task 0 step 3 | Cloud Run env `GOOGLE_API_KEY` (ADK / google-genai) |
| `pm-fathom-webhook-secret` | Task 14 step 6 (returned by Fathom) | Cloud Run env `PM_FATHOM_WEBHOOK_SECRET` |

Rotate any of them with `gcloud secrets versions add <name> --data-file=-` and redeploy.

Order of operations on first deploy: deploy without Fathom → create the Fathom webhook (needs the
URL) → store its secret → redeploy with `PM_WITH_FATHOM=1`.
```

- [ ] **Step 5: First deploy (without Fathom), scheduler, health**

```bash
chmod +x deploy/deploy.sh deploy/scheduler.sh
URL=$(./deploy/deploy.sh | tail -1); echo "$URL"
curl -s "$URL/healthz"
./deploy/scheduler.sh
sleep 70; gcloud logging read 'resource.type="cloud_run_revision" AND httpRequest.requestUrl:"/tick"' --limit 3 --format='value(httpRequest.status)'
```
Expected: `{"ok":true}`; scheduler created; at least one `200` for `/tick`.

- [ ] **Step 6: Create the Fathom webhook and store its secret**

```bash
curl -s -X POST https://api.fathom.ai/external/v1/webhooks \
  -H "X-Api-Key: $FATHOM_API_KEY" -H "Content-Type: application/json" \
  -d "{\"destination_url\": \"$URL/webhooks/fathom\", \"triggered_for\": [\"my_recordings\"], \"include_transcript\": true, \"include_summary\": true, \"include_action_items\": true}" \
  | tee /dev/stderr | python3 -c 'import json,sys; print(json.load(sys.stdin)["secret"])' \
  | gcloud secrets create pm-fathom-webhook-secret --data-file=-
PM_WITH_FATHOM=1 ./deploy/deploy.sh
```
If Fathom rejects `triggered_for`, its docs list the allowed values on the create-webhook page (the field is required); use the value meaning "my own recordings".

- [ ] **Step 7: Fire a real call (the day-1 spike from spec §19)**

Start a Google Meet with Fathom recording, read the first four exchanges of `fixtures/transcripts/01-q3-planning.md`, end the call. Within a few minutes:

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND httpRequest.requestUrl:"/webhooks/fathom"' --limit 3 --format='value(httpRequest.status,timestamp)'
gcloud firestore documents list events --project pm-agent-hack-2026 2>/dev/null || echo "use the console: Firestore → events"
```
Expected: a `200` on `/webhooks/fathom`; an `events/fathom:…` document; within a minute a `tasks` document with `kind: extract` moving `queued → leased → done`; `decisions` documents with quotes. Open the Firestore console and screenshot the `tasks` doc with `status: done` — that is today's demo.

- [ ] **Step 8: Replace the sample payload with the real capture**

Copy the `payload` field of the stored `events/fathom:…` document into `tests/fixtures/fathom_webhook_sample.json` (it is our fake company; no real PII). If any field name differs from the documented shape, `parse_meeting` in `app/clients/fathom.py` is the one place to adapt; `tests/clients/test_fathom.py::test_parse_meeting_normalises_the_documented_shape` must be updated to the real names in the same commit.

```bash
uv run pytest -q
```
Expected: all green against the real payload shape.

- [ ] **Step 9: Commit**

```bash
git add deploy/Dockerfile deploy/deploy.sh deploy/scheduler.sh deploy/secrets.md .dockerignore \
  tests/fixtures/fathom_webhook_sample.json app/clients/fathom.py tests/clients/test_fathom.py
git commit -m "feat(deploy): Cloud Run service, one-minute Scheduler tick, Fathom webhook; real payload captured"
```

---

## Self-review against the spec

**Coverage (day-1 scope):** §4 architecture (Cloud Run + Firestore + Scheduler; no bus) — Tasks 6, 11, 14. §5 data model — `events`, `tasks`, `decisions`, `projects` created (Tasks 6, 8, 10); `actions`, `corrections` arrive with Act and corrections in Plans 2–3 by design. §6 queue — Task 6 implements enqueue/tick/lease/lineage-in-transaction/backoff/deferral plus dependencies (`blocked`, promotion, `on_dep_failed`, cascade cancel), plan materialisation with key resolution and `supersedes`; caps gate deferral is Plan 2 (needs Act). §7.4 plan gate and §7.5 kinds registry (schemas, no executors) — Task 6b. §7.1 extract with evidence gate and one bounce — Tasks 9–10; Gemma pre-filter is Plan 4, `PassthroughTriage` stands in. §8 extractor agent, sessions ephemeral, output schema — Task 12; tracing is Plan 3. §10 failure rows for webhook/redelivery/no-transcript/model failure/schema/gate/timeout/poison — Tasks 6, 8, 11 (Slack notice for no-transcript deferred to Plan 2, noted in code). §11 secrets in Secret Manager, signature verification — Tasks 0, 7, 14. §13 fixtures — Task 13 (Linear seed and Notion pages are Plan 2 / manual). §15 layout and layering — Task 1 (independence contract deferred until a second stage exists, as the plan header states). §16 testing — every task.

**Placeholders:** none of "TBD/TODO/implement later"; the only user-specific values (workspace ids) are empty strings in fixture JSON with the seed script documenting when they are filled. Model ids are config with a verification step.

**Type consistency:** `Db` methods (incl. `cas(..., creates, updates)` and `array_contains`) and `FakeDb` match (Task 4 ↔ 6, 8, 10). `TaskQueue.complete(task, result, children, *, supersedes=())` returns `list[str]` and is called with three positional args in `runner.run_task` (Task 11). `check_plan` consumes `KINDS`/`validate_params` from Task 6b and emits tasks whose keys (`kind, params, due_at, depends_on, on_unmet, on_dep_failed, context, key, reason, payload`) are exactly the child-spec keys `TaskQueue.complete` accepts. `StageResult(result, children)` shape matches `extract.run` and `runner`. `Deps` fields match `conftest.py` and `build_deps`. `Extractor.run(payload) -> dict` matches `GeminiExtractor` and `FakeExtractor`. `check_evidence(items, transcript_text) -> EvidenceVerdict(kept, dropped)` matches its use in `extract._gate`. Test-only helper `seed_event_and_task` is local to its test module.

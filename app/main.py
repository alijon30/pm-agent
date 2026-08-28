"""App factory. create_app(deps) is what tests and the server both use; build_deps() is the
only place real connectors are constructed.

Wiring happens in two steps because part of it needs the database: connectors come from env in
build_deps(), and everything that depends on the project document — the roster behind the id
gate, the tools the agents may call — is finished by the startup hook, which is also why a
missing project makes the service boot loudly degraded instead of crashing."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from app.agents.base.tools import make_read_tools
from app.agents.extractor import GeminiExtractor
from app.agents.planner import GeminiPlanner
from app.agents.reconciler import GeminiReconciler
from app.agents.triage import PassthroughTriage
from app.config import Settings
from app.harness.connectors.code import CodeSearch
from app.harness.connectors.github import GitHubClient
from app.harness.connectors.linear import LinearClient
from app.harness.connectors.notion import NotionClient
from app.harness.connectors.slack import SlackClient
from app.harness.core.clock import SystemClock
from app.harness.deps import Deps
from app.harness.http import slack, tick, webhooks
from app.harness.store.actions import ActionStore
from app.harness.store.corrections import CorrectionStore
from app.harness.store.decisions import DecisionStore
from app.harness.store.events import EventStore
from app.harness.store.firestore import FirestoreDb
from app.harness.store.projects import ProjectStore
from app.harness.store.tasks import TaskQueue
from app.harness.verify.ids import IdGate

log = logging.getLogger(__name__)


async def finish_wiring(deps: Deps) -> None:
    """The part of the wiring that needs the database: the project's roster and workspace ids.
    Test deps (wire_on_startup=False) build their own agents and gates and never come here."""
    if not deps.wire_on_startup:
        return
    project = await deps.projects.get(deps.settings.default_project_slug)
    if project is None:
        log.warning(
            "project %r is not seeded; the service is up but no agent can run "
            "(scripts/seed_project.py fixes this)",
            deps.settings.default_project_slug,
        )
        return

    roster: list[dict[str, Any]] = list(project.get("roster") or [])
    if project.get("code_repo"):
        deps.code = CodeSearch(Path(project["code_repo"]))

    async def known_meeting(meeting_id: str) -> bool:
        rows = await deps.db.query("events", [("provider", "==", "fathom")], limit=50)
        return any(
            str((r.get("payload") or {}).get("recording_id")) == meeting_id for r in rows
        )

    deps.ids = IdGate(
        linear=deps.linear, notion=deps.notion, code=deps.code, roster=roster,
        db=deps.db, known_meeting=known_meeting,
    )
    tools = make_read_tools(
        linear=deps.linear, team_id=str(project.get("linear_team_id") or ""),
        notion=deps.notion, code=deps.code, roster=roster,
    )
    deps.reconciler = GeminiReconciler(deps.settings.model_strong, tools)
    deps.planner = GeminiPlanner(deps.settings.model_strong, tools)
    log.info("wired for project %r: %d roster member(s), %d tool(s)",
             project.get("slug"), len(roster), len(tools))


def create_app(deps: Deps) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await finish_wiring(deps)
        yield

    app = FastAPI(title="pm-agent", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.deps = deps
    app.include_router(webhooks.router)
    app.include_router(tick.router)
    app.include_router(slack.router)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"ok": True, "wired": deps.reconciler is not None}

    return app


def build_deps(settings: Settings | None = None) -> Deps:
    """Real connectors, from env. An absent credential disables that connector — the stages
    that need it fail closed with a reason instead of the process failing to boot."""
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
        actions=ActionStore(db, clock),
        corrections=CorrectionStore(db, clock),
        linear=LinearClient(s.linear_api_key) if s.linear_api_key else None,
        notion=NotionClient(s.notion_token) if s.notion_token else None,
        slack=SlackClient(s.slack_bot_token) if s.slack_bot_token else None,
        github=GitHubClient(s.github_token, s.github_repo)
        if s.github_token and s.github_repo else None,
        wire_on_startup=True,
    )


def create_default_app() -> FastAPI:
    """uvicorn entry point: `uvicorn app.main:create_default_app --factory`."""
    return create_app(build_deps())

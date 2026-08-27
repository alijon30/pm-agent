"""App factory. create_app(deps) is what tests and the server both use; build_deps() is the
only place real connectors are constructed."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from app.agents.extractor import GeminiExtractor
from app.agents.triage import PassthroughTriage
from app.config import Settings
from app.harness.core.clock import SystemClock
from app.harness.deps import Deps
from app.harness.http import tick, webhooks
from app.harness.store.decisions import DecisionStore
from app.harness.store.events import EventStore
from app.harness.store.firestore import FirestoreDb
from app.harness.store.projects import ProjectStore
from app.harness.store.tasks import TaskQueue


def create_app(deps: Deps) -> FastAPI:
    app = FastAPI(title="pm-agent", docs_url=None, redoc_url=None)
    app.state.deps = deps
    app.include_router(webhooks.router)
    app.include_router(tick.router)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"ok": True}

    return app


def build_deps(settings: Settings | None = None) -> Deps:
    """Real connectors. Called once per process, never at import time."""
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

"""App factory. create_app(deps) is what tests and the server both use; build_deps() is the
only place real connectors are constructed."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from app.harness.deps import Deps
from app.harness.http import tick, webhooks


def create_app(deps: Deps) -> FastAPI:
    app = FastAPI(title="pm-agent", docs_url=None, redoc_url=None)
    app.state.deps = deps
    app.include_router(webhooks.router)
    app.include_router(tick.router)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"ok": True}

    return app

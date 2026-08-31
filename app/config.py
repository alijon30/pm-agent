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
    slack_signing_secret: str = ""
    slack_bot_token: str = ""
    linear_api_key: str = ""
    notion_token: str = ""
    github_token: str = ""
    github_repo: str = ""
    linear_webhook_secret: str = ""

    default_project_slug: str = "acme"

    # Verified against models.list() on day 1 (scripts/list_models.py).
    model_fast: str = "gemini-3.5-flash-lite"
    model_strong: str = "gemini-3.5-flash"
    # Gemma, not Gemini: triage is a classifier. Verified with scripts/list_models.py.
    model_triage: str = "gemma-4-31b-it"

    stage_timeout_seconds: int = 600
    tick_budget_seconds: int = 480
    lease_minutes: int = 15
    tick_batch: int = 10

    @classmethod
    def for_tests(cls, **overrides: Any) -> Settings:
        """Ignore any local .env so tests never depend on the developer's machine."""
        return cls(_env_file=None, **overrides)  # type: ignore[call-arg]

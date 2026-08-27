# pm-agent

Autonomous product-manager agent. A product call ends; the agent extracts decisions and action
items, reconciles them against Linear, Notion and the codebase, files cited issues, and schedules
its own follow-ups. Built for the All Things Agentic Hackathon 2026 (The Taskmaster).

Design: `docs/superpowers/specs/2026-08-26-pm-agent-design.md`.

    uv sync --dev
    uv run ruff check . && uv run mypy app && uv run lint-imports && uv run pytest -q
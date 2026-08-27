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

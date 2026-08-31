

def test_thinking_is_an_environment_posture_not_an_agent_trait(monkeypatch) -> None:
    """PM_THINKING_BUDGET > 0 gives every agent a deliberation budget; unset leaves it off."""
    from app.agents.base.spec import _content_config, AgentSpec
    from app.agents.base.schemas import Plan

    spec = AgentSpec(name="t", model="gemini-3.5-flash", instruction="x", output_schema=Plan)
    monkeypatch.delenv("PM_THINKING_BUDGET", raising=False)
    assert _content_config(spec).thinking_config is None
    monkeypatch.setenv("PM_THINKING_BUDGET", "1024")
    assert _content_config(spec).thinking_config.thinking_budget == 1024

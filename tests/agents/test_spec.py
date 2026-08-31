

def test_thinking_is_an_environment_posture_not_an_agent_trait(monkeypatch) -> None:
    """PM_THINKING_BUDGET > 0 gives every agent a deliberation budget; unset leaves it off."""
    from app.agents.base.schemas import Plan
    from app.agents.base.spec import AgentSpec, _content_config

    spec = AgentSpec(name="t", model="gemini-3.5-flash", instruction="x", output_schema=Plan)
    monkeypatch.delenv("PM_THINKING_BUDGET", raising=False)
    assert _content_config(spec).thinking_config is None
    monkeypatch.setenv("PM_THINKING_BUDGET", "1024")
    assert _content_config(spec).thinking_config.thinking_budget == 1024


def test_an_agent_may_opt_out_of_thinking(monkeypatch) -> None:
    """The planner's structured output broke under thinking on Vertex, so a spec can decline
    the budget even when the environment grants one."""
    from app.agents.base.schemas import Plan
    from app.agents.base.spec import AgentSpec, _content_config
    from app.agents.planner import build_planner

    spec = AgentSpec(
        name="t", model="gemini-3.5-flash", instruction="x", output_schema=Plan, thinking=False
    )
    monkeypatch.setenv("PM_THINKING_BUDGET", "1024")
    assert _content_config(spec).thinking_config is None
    assert build_planner("gemini-3.5-flash", []).thinking is False

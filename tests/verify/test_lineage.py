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

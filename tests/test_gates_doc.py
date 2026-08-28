"""GATES.md is the document a reader is asked to believe about this system's guarantees, so the
one thing it must never be is out of date. It is generated from the code it describes; this is
the test that notices when the code moved and the document did not."""

from pathlib import Path

from app.harness.kinds.registry import KINDS
from app.harness.verify import caps, lineage
from scripts.gen_gates import TARGET, kinds_table, render

REGENERATE = "uv run python scripts/gen_gates.py"


def test_the_document_on_disk_is_what_the_code_says_it_is() -> None:
    assert TARGET.exists(), f"GATES.md is missing — {REGENERATE}"
    assert TARGET.read_text() == render(), f"GATES.md is stale — {REGENERATE}"


def test_generating_it_twice_produces_the_same_bytes() -> None:
    """No timestamps, no set iteration, nothing that makes a clean checkout look dirty."""
    assert render() == render()


def test_every_kind_the_agent_has_appears_in_the_table() -> None:
    """The table is the whitelist. A capability that exists in code and not in the document is
    exactly the drift this file was written to prevent."""
    table = kinds_table()

    for kind, spec in KINDS.items():
        assert f"| `{kind}` |" in table
        assert spec.description in table
        for action in spec.unmet_actions:
            assert f"`{action}`" in table


def test_the_numbers_are_read_from_the_code_and_not_typed_in() -> None:
    """If someone changes a limit, the document has to change with it or the test above fails.
    These assertions prove the values came from the modules rather than from a copy."""
    document = render()

    assert str(lineage.DEFAULT_POLICY["max_depth"]) in document
    assert str(lineage.DEFAULT_POLICY["max_children"]) in document
    assert caps.DEFAULT_QUIET[0] in document and caps.DEFAULT_QUIET[1] in document


def test_a_changed_limit_makes_the_document_stale(monkeypatch: object) -> None:
    """The guard is only worth having if it actually catches a change."""
    import scripts.gen_gates as generator

    before = render()
    original = dict(lineage.DEFAULT_POLICY)
    try:
        lineage.DEFAULT_POLICY["max_depth"] = 99
        assert generator.render() != before
        assert "99" in generator.render()
    finally:
        lineage.DEFAULT_POLICY.clear()
        lineage.DEFAULT_POLICY.update(original)

    assert render() == before


def test_the_document_says_how_to_regenerate_itself() -> None:
    document = Path(TARGET).read_text()

    assert REGENERATE in document
    assert "scripts/gen_gates.py" in document
    assert "tests/test_gates_doc.py" in document

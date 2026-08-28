"""The citation gate is the last thing between a confident sentence and a team lead who
believes it, so these tests are mostly about what it refuses to let through."""

from typing import Any

import pytest
from app.harness.core.errors import SourceUnavailable
from app.harness.verify.citations import check_citations
from app.harness.verify.ids import IdGate

from tests.fakes.fake_db import FakeDb
from tests.fakes.fake_linear import FakeLinear

ISSUE = {"id": "u-143", "identifier": "INV-143", "title": "Move reminders", "description": "",
         "state": "In Review", "priority": 3, "assignee": None, "due_date": None, "url": "",
         "updated_at": ""}


async def gate() -> IdGate:
    db = FakeDb()
    await db.set("decisions", "dec-1", {"statement": "Reminders move to three days"})
    return IdGate(linear=FakeLinear(issues=[ISSUE]), db=db)


def report(*claims: dict[str, Any], section: str = "shipped") -> dict[str, Any]:
    return {"headline": "One sprint, told honestly.",
            "sections": [{"name": section, "claims": list(claims)}]}


async def test_a_report_whose_every_claim_checks_out_passes_through_untouched() -> None:
    original = report(
        {"text": "INV-143 is in review.", "refs": ["linear:INV-143"]},
        {"text": "Reminders move to three days.", "refs": ["decision:dec-1"]},
    )
    verdict = await check_citations(original, await gate())

    assert verdict.ok is True and verdict.removed == []
    assert verdict.report == original


async def test_a_claim_that_cites_an_issue_nobody_filed_is_removed_with_its_reason() -> None:
    verdict = await check_citations(
        report({"text": "INV-143 is in review.", "refs": ["linear:INV-143"]},
               {"text": "INV-999 shipped.", "refs": ["linear:INV-999"]}),
        await gate(),
    )

    assert verdict.ok is False
    assert [c["text"] for c in verdict.report["sections"][0]["claims"]] == ["INV-143 is in review."]
    assert verdict.removed == [
        {"section": "shipped", "text": "INV-999 shipped.",
         "reason": "unknown reference(s): linear:INV-999"}
    ]


async def test_a_claim_with_no_reference_at_all_is_removed() -> None:
    verdict = await check_citations(report({"text": "Morale is high.", "refs": []}), await gate())

    assert verdict.ok is False and verdict.report["sections"] == []
    assert verdict.removed[0]["reason"] == "no reference"


async def test_a_claim_needs_every_one_of_its_references_to_exist() -> None:
    verdict = await check_citations(
        report({"text": "INV-143 implements dec-1.", "refs": ["linear:INV-143", "decision:nope"]}),
        await gate(),
    )

    assert verdict.ok is False
    assert "decision:nope" in verdict.removed[0]["reason"]


async def test_a_section_emptied_by_removals_is_dropped_rather_than_shown_empty() -> None:
    original = {"headline": "h", "sections": [
        {"name": "shipped", "claims": [{"text": "INV-999 shipped.", "refs": ["linear:INV-999"]}]},
        {"name": "blocked", "claims": [{"text": "INV-143 is stuck.", "refs": ["linear:INV-143"]}]},
    ]}
    verdict = await check_citations(original, await gate())

    assert [s["name"] for s in verdict.report["sections"]] == ["blocked"]


async def test_the_headline_survives_even_when_every_claim_is_removed() -> None:
    verdict = await check_citations(report({"text": "made up", "refs": []}), await gate())

    assert verdict.report["headline"] == "One sprint, told honestly."


async def test_an_unreachable_tracker_is_not_reported_as_a_fake_citation() -> None:
    linear = FakeLinear(issues=[ISSUE])

    async def down(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
        raise SourceUnavailable("linear", "HTTP 503")

    linear.get_issue = down  # type: ignore[method-assign]
    ids = IdGate(linear=linear, db=FakeDb())

    with pytest.raises(SourceUnavailable):
        await check_citations(report({"text": "t", "refs": ["linear:INV-143"]}), ids)

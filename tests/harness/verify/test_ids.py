from app.harness.verify.ids import IdGate


async def test_a_brain_citation_names_a_page_and_an_entry_on_it() -> None:
    """The page is the document that can be re-fetched, and pages are stored per project —
    a gate that looked up the bare slug dropped every real brain citation."""
    class Pages:
        async def get(self, collection: str, doc_id: str) -> dict[str, str] | None:
            return {"id": doc_id} if (collection, doc_id) == ("wiki_pages", "acme:ownership") else None

    gate = IdGate(db=Pages(), project_id="acme")

    assert await gate.ref_exists("wiki:ownership#abc123")
    assert await gate.ref_exists("wiki:ownership")
    assert not await gate.ref_exists("wiki:invented#abc123")


async def test_an_unscoped_gate_still_checks_the_bare_slug() -> None:
    class Pages:
        async def get(self, collection: str, doc_id: str) -> dict[str, str] | None:
            return {"id": doc_id} if doc_id == "ownership" else None

    assert await IdGate(db=Pages()).ref_exists("wiki:ownership#abc123")

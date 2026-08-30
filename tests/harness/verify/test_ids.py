from app.harness.verify.ids import IdGate


async def test_a_brain_citation_names_a_page_and_an_entry_on_it() -> None:
    """The page is the document that can be re-fetched, so that is what the gate checks."""
    class Pages:
        async def get(self, collection: str, doc_id: str) -> dict[str, str] | None:
            return {"id": doc_id} if (collection, doc_id) == ("wiki_pages", "ownership") else None

    gate = IdGate(db=Pages())

    assert await gate.ref_exists("wiki:ownership#abc123")
    assert await gate.ref_exists("wiki:ownership")
    assert not await gate.ref_exists("wiki:invented#abc123")

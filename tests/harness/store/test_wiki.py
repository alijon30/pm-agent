"""The company brain.

The thing this store exists to prevent is a team having to say something twice. Everything
below is about that: an instruction sticks, a later one supersedes it without erasing it, and
nothing is remembered that cannot be traced to whoever said it."""

from typing import Any

from app.harness.deps import Deps
from app.harness.store.wiki import WikiStore, keywords, topic_slug


def brain(deps: Deps) -> WikiStore:
    return WikiStore(deps.db, deps.clock)


def entry(text: str, *, source: str, person: str | None = None,
          said_by: str = "Maya Chen", subject: list[str] | None = None) -> dict[str, Any]:
    return {"text": text, "source": source, "person": person, "said_by": said_by,
            "subject": subject or keywords(text)}


# --- what makes a thing worth matching on ---------------------------------------------------

def test_the_words_that_decide_relevance_are_the_ones_that_carry_meaning() -> None:
    assert keywords("Assign billing and statements to Nodir from now on") == [
        "assign", "billing", "nodir", "statements"]
    assert "always" not in keywords("Always check with Priya before merging")
    assert "please" not in keywords("Please remember the invoice export")


def test_facts_are_filed_by_topic_so_a_page_stays_readable() -> None:
    assert topic_slug("Line-item rates allow six decimal places").startswith("facts-")
    assert topic_slug("") == "facts-general"


# --- remembering ------------------------------------------------------------------------------

async def test_an_instruction_is_remembered_with_who_said_it_and_when(deps: Deps) -> None:
    wiki = brain(deps)

    where = await wiki.add_entry("acme", "ownership", entry(
        "Billing and statements go to Nodir", source="slack:C1:171.1", person="Nodir Rahimov"))

    assert where is not None
    slug, entry_id = where
    assert slug == "ownership"
    pages = await wiki.pages("acme")
    kept = pages[0]["entries"][0]
    assert kept["id"] == entry_id
    assert kept["person"] == "Nodir Rahimov"
    assert kept["said_by"] == "Maya Chen"
    assert kept["created_at"]


async def test_nothing_is_remembered_that_cannot_be_traced(deps: Deps) -> None:
    """An entry with no source is a rumour, and a rumour is not something to act on later."""
    wiki = brain(deps)

    assert await wiki.add_entry("acme", "fact", {"text": "rates allow six decimals"}) is None
    assert await wiki.add_entry("acme", "fact", {"text": "", "source": "slack:C1:1"}) is None
    assert await wiki.pages("acme") == []


async def test_the_same_message_replayed_is_not_a_second_memory(deps: Deps) -> None:
    wiki = brain(deps)
    first = await wiki.add_entry("acme", "preference", entry(
        "Never nudge anyone before ten", source="slack:C1:171.1"))

    again = await wiki.add_entry("acme", "preference", entry(
        "Never nudge anyone before ten", source="slack:C1:171.1"))

    assert first is not None and again is None
    assert len((await wiki.pages("acme"))[0]["entries"]) == 1


async def test_a_kind_this_store_does_not_keep_is_refused(deps: Deps) -> None:
    assert await brain(deps).add_entry("acme", "gossip", entry("x", source="slack:C1:1")) is None


# --- changing its mind --------------------------------------------------------------------------

async def test_naming_a_new_owner_retires_the_old_claim_without_erasing_it(deps: Deps) -> None:
    """The page has to be able to answer "since when, and what changed"."""
    wiki = brain(deps)
    await wiki.add_entry("acme", "ownership", entry(
        "Billing and statements go to Nodir", source="slack:C1:1", person="Nodir Rahimov"))

    await wiki.add_entry("acme", "ownership", entry(
        "Billing and statements go to Priya", source="slack:C1:2", person="Priya Nair"))

    entries = (await wiki.pages("acme"))[0]["entries"]
    assert len(entries) == 2, "history is kept"
    assert entries[0]["retired_at"], "the older claim is retired"
    assert not entries[1]["retired_at"]
    live = await wiki.relevant("acme", "billing statements", kinds=("ownership",))
    assert [e["person"] for e in live] == ["Priya Nair"]


async def test_two_opinions_about_the_same_thing_are_both_kept(deps: Deps) -> None:
    """People hold several preferences about billing; only ownership is exclusive."""
    wiki = brain(deps)
    await wiki.add_entry("acme", "preference", entry(
        "Always mention the billing owner in the summary", source="slack:C1:1"))
    await wiki.add_entry("acme", "preference", entry(
        "Never nudge about billing on a Friday", source="slack:C1:2"))

    live = await wiki.relevant("acme", "billing", kinds=("preference",))

    assert len(live) == 2


# --- being asked ----------------------------------------------------------------------------------

async def test_only_what_bears_on_the_situation_comes_back(deps: Deps) -> None:
    wiki = brain(deps)
    await wiki.add_entry("acme", "ownership", entry(
        "Billing and statements go to Nodir", source="slack:C1:1", person="Nodir Rahimov"))
    await wiki.add_entry("acme", "ownership", entry(
        "Onboarding emails go to Priya", source="slack:C1:2", person="Priya Nair"))

    found = await wiki.relevant("acme", "the statements page is wrong")

    assert [e["person"] for e in found] == ["Nodir Rahimov"]


async def test_an_entry_with_nothing_specific_to_match_on_always_applies(deps: Deps) -> None:
    """"Always cc the channel" is not about billing; it is about everything."""
    wiki = brain(deps)
    await wiki.add_entry("acme", "preference",
                         {"text": "cc the channel", "source": "slack:C1:1", "subject": []})

    assert len(await wiki.relevant("acme", "anything at all")) == 1


async def test_an_entry_carries_the_reference_a_citation_would_use(deps: Deps) -> None:
    wiki = brain(deps)
    where = await wiki.add_entry("acme", "ownership", entry(
        "Billing goes to Nodir", source="slack:C1:1", person="Nodir Rahimov"))
    assert where is not None

    found = await wiki.relevant("acme", "billing")

    assert found[0]["ref"] == f"wiki:ownership#{where[1]}"
    assert found[0]["kind"] == "ownership"


async def test_the_brain_handed_to_a_model_is_capped(deps: Deps) -> None:
    """A prompt carrying the whole brain carries none of it."""
    wiki = brain(deps)
    for n in range(14):
        await wiki.add_entry("acme", "fact", entry(
            f"billing statements detail number {n}", source=f"slack:C1:{n}"))

    assert len(await wiki.relevant("acme", "billing statements")) == 8


async def test_one_project_never_reads_another_ones_brain(deps: Deps) -> None:
    wiki = brain(deps)
    await wiki.add_entry("acme", "ownership", entry(
        "Billing goes to Nodir", source="slack:C1:1", person="Nodir Rahimov"))

    assert await wiki.relevant("other", "billing") == []

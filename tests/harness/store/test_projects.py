import pytest
from app.harness.core.errors import PmError
from app.harness.store.projects import ProjectStore

from tests.fakes.fake_db import FakeDb


async def test_default_project_is_looked_up_by_slug() -> None:
    db = FakeDb()
    store = ProjectStore(db, default_slug="acme")
    await store.upsert("acme", {"slug": "acme", "roster": [], "policy": {}})
    proj = await store.default()
    assert proj["id"] == "acme" and proj["slug"] == "acme"


async def test_a_missing_default_project_fails_closed() -> None:
    store = ProjectStore(FakeDb(), default_slug="acme")
    with pytest.raises(PmError):
        await store.default()

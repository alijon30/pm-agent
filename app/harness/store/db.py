"""The tiny document-store surface the harness needs. FirestoreDb implements it for real;
tests use FakeDb. Nothing outside store/ imports google.cloud.firestore."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol

Doc = dict[str, Any]
Filter = tuple[str, str, Any]
Predicate = Callable[[Doc], bool]
Updater = Callable[[Doc], dict[str, Any]]
Create = tuple[str, str, dict[str, Any]]
Update = tuple[str, str, dict[str, Any]]

OPS = ("==", "<", "<=", ">", ">=", "in", "array_contains")


class Db(Protocol):
    async def get(self, collection: str, doc_id: str) -> Doc | None: ...

    async def create(self, collection: str, doc_id: str, data: dict[str, Any]) -> bool:
        """Create only if absent. False when the doc already exists — the idempotency primitive."""
        ...

    async def set(self, collection: str, doc_id: str, data: dict[str, Any]) -> None: ...

    async def update(self, collection: str, doc_id: str, fields: dict[str, Any]) -> None: ...

    async def delete(self, collection: str, doc_id: str) -> None:
        """Remove a document; deleting one that does not exist is a no-op."""
        ...

    async def query(
        self,
        collection: str,
        filters: Sequence[Filter],
        *,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[Doc]: ...

    async def count(self, collection: str, filters: Sequence[Filter]) -> int: ...

    async def cas(
        self,
        collection: str,
        doc_id: str,
        predicate: Predicate,
        updater: Updater,
        creates: Sequence[Create] = (),
        updates: Sequence[Update] = (),
    ) -> bool:
        """Compare-and-set in one transaction: read the doc, and if predicate(doc) holds, apply
        updater(doc), create every doc in `creates`, and update every doc in `updates`. False
        (and no writes at all) otherwise."""
        ...

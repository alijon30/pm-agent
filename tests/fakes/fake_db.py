"""In-memory Db. Single-threaded, so cas() is trivially atomic. Mirrors the semantics the
FirestoreDb tests in tests/store/test_firestore_live.py check against the real service."""

from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any

from app.harness.store.db import Create, Doc, Filter, Predicate, Update, Updater


def _matches(doc: dict[str, Any], filters: Sequence[Filter]) -> bool:
    for field, op, value in filters:
        actual = doc.get(field)
        if op == "==":
            ok = actual == value
        elif op == "<":
            ok = actual is not None and actual < value
        elif op == "<=":
            ok = actual is not None and actual <= value
        elif op == ">":
            ok = actual is not None and actual > value
        elif op == ">=":
            ok = actual is not None and actual >= value
        elif op == "in":
            ok = actual in value
        elif op == "array_contains":
            ok = isinstance(actual, list) and value in actual
        else:
            raise ValueError(f"unsupported op {op!r}")
        if not ok:
            return False
    return True


class FakeDb:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, dict[str, Any]]] = {}

    def _col(self, collection: str) -> dict[str, dict[str, Any]]:
        return self._data.setdefault(collection, {})

    async def get(self, collection: str, doc_id: str) -> Doc | None:
        raw = self._col(collection).get(doc_id)
        return None if raw is None else {"id": doc_id, **copy.deepcopy(raw)}

    async def create(self, collection: str, doc_id: str, data: dict[str, Any]) -> bool:
        col = self._col(collection)
        if doc_id in col:
            return False
        col[doc_id] = copy.deepcopy(data)
        return True

    async def set(self, collection: str, doc_id: str, data: dict[str, Any]) -> None:
        self._col(collection)[doc_id] = copy.deepcopy(data)

    async def update(self, collection: str, doc_id: str, fields: dict[str, Any]) -> None:
        self._col(collection)[doc_id].update(copy.deepcopy(fields))

    async def delete(self, collection: str, doc_id: str) -> None:
        self._col(collection).pop(doc_id, None)

    async def query(
        self,
        collection: str,
        filters: Sequence[Filter],
        *,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[Doc]:
        rows = [
            {"id": doc_id, **copy.deepcopy(raw)}
            for doc_id, raw in self._col(collection).items()
            if _matches(raw, filters)
        ]
        if order_by:
            rows.sort(key=lambda r: (r.get(order_by) is None, r.get(order_by)))
        return rows[:limit] if limit is not None else rows

    async def count(self, collection: str, filters: Sequence[Filter]) -> int:
        return sum(1 for raw in self._col(collection).values() if _matches(raw, filters))

    async def cas(
        self,
        collection: str,
        doc_id: str,
        predicate: Predicate,
        updater: Updater,
        creates: Sequence[Create] = (),
        updates: Sequence[Update] = (),
    ) -> bool:
        current = await self.get(collection, doc_id)
        if current is None or not predicate(current):
            return False
        await self.update(collection, doc_id, updater(current))
        for c_col, c_id, c_data in creates:
            await self.set(c_col, c_id, c_data)
        for u_col, u_id, u_fields in updates:
            await self.update(u_col, u_id, u_fields)
        return True

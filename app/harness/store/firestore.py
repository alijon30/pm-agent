"""Db on Firestore (native mode), async client. The only module that imports google.cloud."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from google.api_core import exceptions as gexc
from google.cloud import firestore
from google.cloud.firestore_v1.async_transaction import AsyncTransaction, async_transactional
from google.cloud.firestore_v1.base_query import FieldFilter

from app.harness.store.db import Create, Doc, Filter, Predicate, Update, Updater


class FirestoreDb:
    def __init__(self, project: str, database: str = "(default)") -> None:
        self._client = firestore.AsyncClient(project=project or None, database=database)

    def _ref(self, collection: str, doc_id: str) -> Any:
        return self._client.collection(collection).document(doc_id)

    async def get(self, collection: str, doc_id: str) -> Doc | None:
        snap = await self._ref(collection, doc_id).get()
        if not snap.exists:
            return None
        return {"id": doc_id, **(snap.to_dict() or {})}

    async def create(self, collection: str, doc_id: str, data: dict[str, Any]) -> bool:
        try:
            await self._ref(collection, doc_id).create(data)
        except gexc.AlreadyExists:
            return False
        return True

    async def set(self, collection: str, doc_id: str, data: dict[str, Any]) -> None:
        await self._ref(collection, doc_id).set(data)

    async def update(self, collection: str, doc_id: str, fields: dict[str, Any]) -> None:
        await self._ref(collection, doc_id).update(fields)

    async def delete(self, collection: str, doc_id: str) -> None:
        await self._ref(collection, doc_id).delete()

    def _filtered(self, collection: str, filters: Sequence[Filter]) -> Any:
        q: Any = self._client.collection(collection)
        for field, op, value in filters:
            q = q.where(filter=FieldFilter(field, op, value))
        return q

    async def query(
        self,
        collection: str,
        filters: Sequence[Filter],
        *,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[Doc]:
        q = self._filtered(collection, filters)
        if order_by:
            q = q.order_by(order_by)
        if limit is not None:
            q = q.limit(limit)
        return [{"id": snap.id, **(snap.to_dict() or {})} async for snap in q.stream()]

    async def count(self, collection: str, filters: Sequence[Filter]) -> int:
        result = await self._filtered(collection, filters).count().get()
        return int(result[0][0].value)

    async def cas(
        self,
        collection: str,
        doc_id: str,
        predicate: Predicate,
        updater: Updater,
        creates: Sequence[Create] = (),
        updates: Sequence[Update] = (),
    ) -> bool:
        ref = self._ref(collection, doc_id)
        client = self._client

        @async_transactional
        async def _run(tx: AsyncTransaction) -> bool:
            snap = await ref.get(transaction=tx)
            if not snap.exists:
                return False
            current: Doc = {"id": doc_id, **(snap.to_dict() or {})}
            if not predicate(current):
                return False
            tx.update(ref, updater(current))
            for c_col, c_id, c_data in creates:
                tx.create(client.collection(c_col).document(c_id), c_data)
            for u_col, u_id, u_fields in updates:
                tx.update(client.collection(u_col).document(u_id), u_fields)
            return True

        return bool(await _run(client.transaction()))

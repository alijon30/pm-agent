"""Identifiers. Deterministic where idempotency depends on it, random otherwise."""

from __future__ import annotations

import hashlib
import re
import uuid


def new_id() -> str:
    return uuid.uuid4().hex


def event_doc_id(provider: str, provider_event_id: str) -> str:
    """Doc id for an inbound event. Creating it twice fails the second time, which is how a
    redelivered webhook becomes a no-op without any extra bookkeeping."""
    return f"{provider}:{provider_event_id}"


def idempotency_key(root_event_id: str, item_index: int, kind: str) -> str:
    """Stable per (call, item, action kind). Stamped into the Linear issue so a retried Act can
    recognise its own earlier write."""
    raw = f"{root_event_id}|{item_index}|{kind}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


RETRY_SUFFIX = re.compile(r"#retry\d+$")


def origin(event_id: str) -> str:
    """An event id with a replay's suffix taken off.

    A webhook replayed through the replay script carries `#retry2`. It is the same call, and
    counting or grouping by the raw id turns one conversation into two."""
    return RETRY_SUFFIX.sub("", str(event_id or "").strip())

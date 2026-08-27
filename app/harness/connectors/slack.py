"""Slack Web API, plus request-signature verification for the inbound side.

Two directions live here on purpose: the signing secret and the bot token are both Slack
protocol knowledge, and keeping them together means http/slack.py stays about routing."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from typing import Any

import httpx

from app.harness.core.errors import SourceUnavailable
from app.harness.core.redact import redact

API = "https://slack.com/api"
SIGNATURE_VERSION = "v0"
TOLERANCE_SECONDS = 300


def verify_slack_signature(
    signing_secret: str,
    headers: Mapping[str, str],
    raw_body: bytes,
    now_epoch: int,
    *,
    tolerance_seconds: int = TOLERANCE_SECONDS,
) -> bool:
    """HMAC-SHA256 over "v0:<timestamp>:<body>". Fails closed on a missing secret, a missing
    header, or a timestamp outside the replay window."""
    if not signing_secret:
        return False
    timestamp = headers.get("x-slack-request-timestamp") or headers.get(
        "X-Slack-Request-Timestamp"
    ) or ""
    given = headers.get("x-slack-signature") or headers.get("X-Slack-Signature") or ""
    if not timestamp or not given:
        return False
    try:
        sent_at = int(timestamp)
    except ValueError:
        return False
    if abs(now_epoch - sent_at) > tolerance_seconds:
        return False
    basestring = f"{SIGNATURE_VERSION}:{timestamp}:".encode() + raw_body
    digest = hmac.new(signing_secret.encode(), basestring, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"{SIGNATURE_VERSION}={digest}", given)


class SlackClient:
    def __init__(
        self, bot_token: str, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        self._transport = transport

    async def _call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Slack answers 200 with {"ok": false, "error": "..."} for application errors, so the
        status code alone is never enough."""
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=20) as client:
                resp = await client.post(
                    f"{API}/{method}", headers=self._headers, json=payload
                )
        except httpx.HTTPError as exc:
            raise SourceUnavailable("slack", redact(str(exc))) from exc
        if resp.status_code >= 400:
            raise SourceUnavailable("slack", f"HTTP {resp.status_code}")
        data: dict[str, Any] = resp.json()
        if not data.get("ok"):
            raise SourceUnavailable("slack", redact(str(data.get("error") or "unknown error")))
        return data

    async def post(
        self,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        *,
        thread_ts: str | None = None,
    ) -> str:
        """Returns the message ts, which is how a later edit or revert finds this message.
        `text` is the notification fallback and must always be set."""
        payload: dict[str, Any] = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts
        data = await self._call("chat.postMessage", payload)
        return str(data.get("ts") or "")

    async def update(
        self, channel: str, ts: str, text: str, blocks: list[dict[str, Any]] | None = None
    ) -> None:
        payload: dict[str, Any] = {"channel": channel, "ts": ts, "text": text}
        if blocks is not None:
            payload["blocks"] = blocks
        await self._call("chat.update", payload)

    async def open_modal(self, trigger_id: str, view: dict[str, Any]) -> None:
        await self._call("views.open", {"trigger_id": trigger_id, "view": view})

    async def user_info(self, user_id: str) -> dict[str, Any] | None:
        """None for an unknown user; an outage still raises. Used to map a clicker to a person."""
        try:
            data = await self._call("users.info", {"user": user_id})
        except SourceUnavailable as exc:
            if "user_not_found" in str(exc):
                return None
            raise
        user = data.get("user") or {}
        return {
            "id": user.get("id") or user_id,
            "name": user.get("real_name") or user.get("name") or "",
            "email": (user.get("profile") or {}).get("email") or "",
        }

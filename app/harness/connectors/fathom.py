"""Fathom webhook verification and payload normalisation."""

from __future__ import annotations

import base64
import hashlib
import hmac
from collections.abc import Mapping
from typing import Any


def _header(headers: Mapping[str, str], name: str) -> str:
    return headers.get(name) or headers.get(name.lower()) or headers.get(name.title()) or ""


def verify_signature(
    secret: str,
    headers: Mapping[str, str],
    raw_body: bytes,
    now_epoch: int,
    *,
    tolerance_seconds: int = 300,
) -> bool:
    """Standard-Webhooks style: HMAC-SHA256 over "<id>.<timestamp>.<body>" with the base64 secret
    after the whsec_ prefix. Fails closed on any missing piece or a stale timestamp."""
    if not secret or "_" not in secret:
        return False
    msg_id = _header(headers, "webhook-id")
    ts_raw = _header(headers, "webhook-timestamp")
    sig_header = _header(headers, "webhook-signature")
    if not (msg_id and ts_raw and sig_header):
        return False
    try:
        ts = int(ts_raw)
        key = base64.b64decode(secret.split("_", 1)[1])
    except ValueError:
        return False
    if abs(now_epoch - ts) > tolerance_seconds:
        return False
    signed = f"{msg_id}.{ts_raw}.".encode() + raw_body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    candidates = [part.split(",", 1)[1] if "," in part else part for part in sig_header.split()]
    return any(hmac.compare_digest(expected, c) for c in candidates)


def parse_meeting(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalise a Fathom meeting object (webhook body or /meetings item) into the shape the
    stages use. Every field is optional upstream; nothing here raises on a missing section."""
    invitees = [
        {"name": i.get("name"), "email": i.get("email")}
        for i in payload.get("calendar_invitees") or []
    ]
    transcript = []
    for seg in payload.get("transcript") or []:
        speaker = seg.get("speaker") or {}
        transcript.append({
            "speaker": speaker.get("display_name") or "Unknown",
            "email": speaker.get("matched_calendar_invitee_email"),
            "text": seg.get("text") or "",
            "timestamp": seg.get("timestamp") or "",
        })
    action_items = [
        {
            "description": a.get("description") or "",
            "timestamp": a.get("recording_timestamp") or "",
            "assignee_name": (a.get("assignee") or {}).get("name"),
        }
        for a in payload.get("action_items") or []
    ]
    return {
        "meeting_id": str(payload.get("recording_id") or payload.get("id") or ""),
        "title": payload.get("title") or payload.get("meeting_title") or "",
        "url": payload.get("share_url") or payload.get("url") or "",
        "recorded_at": payload.get("recording_start_time") or payload.get("created_at") or "",
        "invitees": invitees,
        "transcript": transcript,
        "summary_md": (payload.get("default_summary") or {}).get("markdown_formatted") or "",
        "action_items": action_items,
    }


def render_transcript(segments: list[dict[str, Any]]) -> str:
    """What the model reads: one line per segment with its timestamp and speaker."""
    return "\n".join(f"[{s['timestamp']}] {s['speaker']}: {s['text']}" for s in segments)


def transcript_plain(meeting: dict[str, Any]) -> str:
    """What the evidence gate matches against: spoken words only, no timestamps or names, so a
    quote is judged on the words actually said."""
    return " ".join(s["text"] for s in meeting["transcript"])

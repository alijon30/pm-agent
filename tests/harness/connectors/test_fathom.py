import base64
import hashlib
import hmac
import json
from pathlib import Path

from app.harness.connectors.fathom import (
    parse_meeting,
    render_transcript,
    transcript_plain,
    verify_signature,
)

SAMPLE = Path(__file__).parents[2] / "fixtures" / "fathom_webhook_sample.json"
SECRET_BYTES = b"0123456789abcdef0123456789abcdef"
SECRET = "whsec_" + base64.b64encode(SECRET_BYTES).decode()


def sign(body: bytes, msg_id: str, ts: int) -> str:
    signed = f"{msg_id}.{ts}.".encode() + body
    return base64.b64encode(hmac.new(SECRET_BYTES, signed, hashlib.sha256).digest()).decode()


def test_a_correctly_signed_fresh_webhook_verifies() -> None:
    body = b'{"recording_id": 1}'
    ts = 1_800_000_000
    headers = {"webhook-id": "msg_1", "webhook-timestamp": str(ts),
               "webhook-signature": f"v1,{sign(body, 'msg_1', ts)}"}
    assert verify_signature(SECRET, headers, body, now_epoch=ts + 10) is True


def test_a_tampered_body_or_wrong_secret_fails() -> None:
    body = b'{"recording_id": 1}'
    ts = 1_800_000_000
    headers = {"webhook-id": "msg_1", "webhook-timestamp": str(ts),
               "webhook-signature": f"v1,{sign(body, 'msg_1', ts)}"}
    assert verify_signature(SECRET, headers, b'{"recording_id": 2}', now_epoch=ts) is False
    other = "whsec_" + base64.b64encode(b"x" * 32).decode()
    assert verify_signature(other, headers, body, now_epoch=ts) is False


def test_a_stale_timestamp_is_rejected_even_with_a_valid_signature() -> None:
    body = b"{}"
    ts = 1_800_000_000
    headers = {"webhook-id": "m", "webhook-timestamp": str(ts),
               "webhook-signature": f"v1,{sign(body, 'm', ts)}"}
    assert verify_signature(SECRET, headers, body, now_epoch=ts + 301) is False


def test_missing_headers_or_empty_secret_never_verify() -> None:
    assert verify_signature(SECRET, {}, b"{}", now_epoch=0) is False
    assert verify_signature("", {"webhook-id": "m", "webhook-timestamp": "0",
                                 "webhook-signature": "v1,x"}, b"{}", now_epoch=0) is False


def test_parse_meeting_normalises_the_documented_shape() -> None:
    meeting = parse_meeting(json.loads(SAMPLE.read_text()))
    assert meeting["meeting_id"] == "8841201"
    assert meeting["title"] == "Q3 Billing planning"
    assert meeting["url"] == "https://fathom.video/share/abc123"
    assert meeting["recorded_at"] == "2026-08-27T09:00:12Z"
    assert meeting["invitees"][0] == {"name": "Maya Chen", "email": "maya@acme-invoicing.test"}
    seg = meeting["transcript"][0]
    assert seg == {"speaker": "Maya Chen", "email": "maya@acme-invoicing.test",
                   "text": "Let's move payment reminders to three days after the due date. "
                           "Nodir, can you own that?", "timestamp": "00:01:42"}
    assert meeting["summary_md"].startswith("- Reminders")
    assert meeting["action_items"][0] == {"description": "Move payment reminders to 3 days",
                                          "timestamp": "00:01:42", "assignee_name": "Nodir Rahimov"}


def test_parse_meeting_tolerates_missing_optional_sections() -> None:
    meeting = parse_meeting({"recording_id": 5, "title": "x"})
    assert meeting["transcript"] == [] and meeting["action_items"] == []
    assert meeting["summary_md"] == "" and meeting["invitees"] == []


def test_transcript_renderings() -> None:
    meeting = parse_meeting(json.loads(SAMPLE.read_text()))
    assert render_transcript(meeting["transcript"]).splitlines()[0].startswith(
        "[00:01:42] Maya Chen: Let's move payment reminders")
    assert "Sure, I can have that done by next Friday." in transcript_plain(meeting)
    assert "[00:01:42]" not in transcript_plain(meeting)

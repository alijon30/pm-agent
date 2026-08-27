import base64
import hashlib
import hmac
import json
from pathlib import Path

from app.harness.deps import Deps
from fastapi.testclient import TestClient

SAMPLE = (Path(__file__).parents[2] / "fixtures" / "fathom_webhook_sample.json").read_bytes()
SECRET_BYTES = b"0123456789abcdef0123456789abcdef"
SECRET = "whsec_" + base64.b64encode(SECRET_BYTES).decode()
TS = 1_787_821_200  # 2026-08-27T09:00:00Z, matches conftest T0


def signed_headers(body: bytes, msg_id: str = "msg_1") -> dict[str, str]:
    signed = f"{msg_id}.{TS}.".encode() + body
    sig = base64.b64encode(hmac.new(SECRET_BYTES, signed, hashlib.sha256).digest()).decode()
    return {"webhook-id": msg_id, "webhook-timestamp": str(TS), "webhook-signature": f"v1,{sig}"}


def test_an_unsigned_webhook_is_rejected_and_nothing_is_stored(client: TestClient, deps: Deps) -> None:
    deps.settings.fathom_webhook_secret = SECRET
    r = client.post("/webhooks/fathom", content=SAMPLE)
    assert r.status_code == 401


def test_a_webhook_with_no_secret_configured_is_rejected(client: TestClient) -> None:
    r = client.post("/webhooks/fathom", content=SAMPLE, headers=signed_headers(SAMPLE))
    assert r.status_code == 401


async def test_a_signed_webhook_stores_the_event_and_enqueues_extract(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.fathom_webhook_secret = SECRET
    r = client.post("/webhooks/fathom", content=SAMPLE, headers=signed_headers(SAMPLE))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued"
    task = await deps.db.get("tasks", body["task_id"])
    assert task is not None
    assert task["kind"] == "extract" and task["payload"] == {"event_id": "fathom:msg_1"}
    assert task["root_event_id"] == "fathom:msg_1" and task["project_id"] == "acme"
    assert "Q3 Billing planning" in task["reason"]


async def test_a_redelivered_webhook_is_a_no_op(client: TestClient, deps: Deps) -> None:
    deps.settings.fathom_webhook_secret = SECRET
    client.post("/webhooks/fathom", content=SAMPLE, headers=signed_headers(SAMPLE))
    r = client.post("/webhooks/fathom", content=SAMPLE, headers=signed_headers(SAMPLE))
    assert r.json() == {"status": "duplicate"}
    assert await deps.db.count("tasks", []) == 1


async def test_a_call_without_a_transcript_is_recorded_but_not_queued(
    client: TestClient, deps: Deps
) -> None:
    deps.settings.fathom_webhook_secret = SECRET
    payload = json.loads(SAMPLE)
    payload["transcript"] = []
    body = json.dumps(payload).encode()
    r = client.post("/webhooks/fathom", content=body, headers=signed_headers(body, "msg_2"))
    assert r.json() == {"status": "no_transcript"}
    event = await deps.events.get("fathom:msg_2")
    assert event is not None and event["notes"] == ["no transcript in payload"]
    assert await deps.db.count("tasks", []) == 0

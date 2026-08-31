"""Fire a fixture transcript at the Fathom webhook as if the call just ended.

The webhook payload carries the transcript itself, so a demo call does not need Fathom to
host it — this signs a Standard-Webhooks request exactly the way Fathom does and posts it.
The pipeline that runs is the production pipeline; nothing downstream knows the difference,
which is the point.

    uv run --env-file .env python scripts/send_call.py \\
        fixtures/transcripts/02-sprint1-kickoff.md \\
        --title "Sprint 1 kickoff sync" --recording-id call_s1_kickoff_20260828
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import time
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

DEFAULT_URL = "https://pm-agent-999960779013.us-central1.run.app/webhooks/fathom"
SEGMENT = re.compile(r"^\[(\d\d:\d\d)\] ([^:]+): (.*)$")
BOLD = re.compile(r"^\*\*([^:*]+):\*\* (.*)$")


def parse_segments(text: str) -> list[dict[str, str]]:
    """The fixture's `[MM:SS] Name: words` lines, with wrapped lines folded back in.
    Everything above the `---` separator is stage direction for the humans recording it."""
    _, _, body = text.partition("\n---\n")
    segments: list[dict[str, str]] = []
    for line in (body or text).splitlines():
        if line.startswith("<!--"):
            continue  # stage directions for the humans recording it
        match = SEGMENT.match(line)
        bold = BOLD.match(line) if not match else None
        if match:
            segments.append({
                "timestamp": match.group(1),
                "speaker": match.group(2).strip(),
                "text": match.group(3).strip(),
            })
        elif bold:
            # The older fixture format: `**Name:** words`, no spoken timestamps. Twenty
            # seconds a turn is close enough for a citation to point at the right moment.
            n = len(segments)
            segments.append({
                "timestamp": f"{n // 3:02d}:{(n * 20) % 60:02d}",
                "speaker": bold.group(1).strip(),
                "text": bold.group(2).strip(),
            })
        elif line.strip() and segments:
            segments[-1]["text"] += " " + line.strip()
    return segments


def payload_for(
    segments: list[dict[str, str]], roster: list[dict], title: str, recording_id: str
) -> dict:
    emails = {person["name"]: person["email"] for person in roster}
    started = datetime.now(UTC) - timedelta(hours=1)
    return {
        "recording_id": recording_id,
        "title": title,
        "recording_start_time": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "calendar_invitees": [
            {"name": person["name"], "email": person["email"]} for person in roster
        ],
        "transcript": [
            {
                "speaker": {
                    "display_name": segment["speaker"],
                    "matched_calendar_invitee_email": emails.get(segment["speaker"]),
                },
                "text": segment["text"],
                "timestamp": segment["timestamp"],
            }
            for segment in segments
        ],
    }


def signed_headers(secret: str, msg_id: str, body: bytes) -> dict[str, str]:
    ts = str(int(time.time()))
    key = base64.b64decode(secret.split("_", 1)[1])
    digest = hmac.new(key, f"{msg_id}.{ts}.".encode() + body, hashlib.sha256).digest()
    return {
        "content-type": "application/json",
        "webhook-id": msg_id,
        "webhook-timestamp": ts,
        "webhook-signature": "v1," + base64.b64encode(digest).decode(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--recording-id", required=True)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--roster", type=Path, default=Path("fixtures/roster.json"))
    args = parser.parse_args()

    secret = os.environ["PM_FATHOM_WEBHOOK_SECRET"]
    segments = parse_segments(args.transcript.read_text())
    if not segments:
        raise SystemExit("no [MM:SS] Speaker: lines found in the transcript")
    roster = json.loads(args.roster.read_text())
    body = json.dumps(payload_for(segments, roster, args.title, args.recording_id)).encode()

    request = urllib.request.Request(
        args.url, data=body, headers=signed_headers(secret, args.recording_id, body)
    )
    with urllib.request.urlopen(request) as response:
        print(response.status, response.read().decode())
    print(f"{len(segments)} segments sent; the next tick drains the pipeline")


if __name__ == "__main__":
    main()

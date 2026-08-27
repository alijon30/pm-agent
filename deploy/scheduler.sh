#!/usr/bin/env bash
# Create (or update) the one-minute tick. Reads the token from Secret Manager at creation time
# only; it is stored inside the Scheduler job, which is IAM-protected.
set -euo pipefail
PROJECT="${PM_GCP_PROJECT:-pm-agent-hack-2026}"
REGION="${PM_REGION:-us-central1}"
URL="$(gcloud run services describe pm-agent --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
TOKEN="$(gcloud secrets versions access latest --secret pm-tick-token --project "$PROJECT")"

if gcloud scheduler jobs describe pm-tick --project "$PROJECT" --location "$REGION" >/dev/null 2>&1; then
  VERB=update
else
  VERB=create
fi
gcloud scheduler jobs "$VERB" http pm-tick \
  --project "$PROJECT" --location "$REGION" \
  --schedule "* * * * *" --time-zone "Etc/UTC" \
  --uri "$URL/tick" --http-method POST \
  --headers "X-Tick-Token=$TOKEN" \
  --attempt-deadline 600s
echo "tick → $URL/tick every minute"

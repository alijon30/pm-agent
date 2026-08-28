#!/usr/bin/env bash
# Create (or update) the one-minute tick. Reads the token from Secret Manager at creation time
# only; it is stored inside the Scheduler job, which is IAM-protected.
set -euo pipefail
PROJECT="${PM_GCP_PROJECT:-pm-agent-hackathon-26}"
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

# The morning review: the same endpoint with one extra header, so there is one door into the
# system rather than two. 16:00 UTC is 09:00 Pacific. The endpoint is idempotent per day, so a
# Scheduler retry costs nothing.
if gcloud scheduler jobs describe pm-daily-review --project "$PROJECT" --location "$REGION" >/dev/null 2>&1; then
  VERB=update
else
  VERB=create
fi
gcloud scheduler jobs "$VERB" http pm-daily-review \
  --project "$PROJECT" --location "$REGION" \
  --schedule "0 16 * * *" --time-zone "Etc/UTC" \
  --uri "$URL/tick" --http-method POST \
  --headers "^|^X-Tick-Token=$TOKEN|X-Tick-Kind=daily_review" \
  --attempt-deadline 600s
echo "daily review → $URL/tick at 16:00 UTC (09:00 PT)"

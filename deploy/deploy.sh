#!/usr/bin/env bash
# Build from source and deploy. Secrets come from Secret Manager; nothing sensitive is passed here.
# Usage: ./deploy/deploy.sh            (first deploy, before the Fathom webhook exists)
#        PM_WITH_FATHOM=1 ./deploy/deploy.sh   (once pm-fathom-webhook-secret exists)
set -euo pipefail
PROJECT="${PM_GCP_PROJECT:-pm-agent-hack-2026}"
REGION="${PM_REGION:-us-central1}"
SERVICE="pm-agent"

SECRETS="PM_TICK_TOKEN=pm-tick-token:latest,GOOGLE_API_KEY=pm-google-api-key:latest"
if [ -n "${PM_WITH_FATHOM:-}" ]; then
  SECRETS="$SECRETS,PM_FATHOM_WEBHOOK_SECRET=pm-fathom-webhook-secret:latest"
fi

gcloud run deploy "$SERVICE" \
  --project "$PROJECT" --region "$REGION" \
  --source . \
  --allow-unauthenticated \
  --timeout 900 --concurrency 4 --min-instances 0 --max-instances 2 \
  --set-env-vars "PM_GCP_PROJECT=$PROJECT,PM_DEFAULT_PROJECT_SLUG=acme,GOOGLE_GENAI_USE_VERTEXAI=FALSE" \
  --set-secrets "$SECRETS"

gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" \
  --format='value(status.url)'

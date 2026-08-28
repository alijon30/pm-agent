#!/usr/bin/env bash
# Build from source and deploy. Secrets come from Secret Manager; nothing sensitive is passed
# here. Every optional secret that exists in Secret Manager is mounted; absent ones simply
# leave their feature disabled, mirroring how config.py treats an empty value.
set -euo pipefail
PROJECT="${PM_GCP_PROJECT:-pm-agent-hackathon-26}"
REGION="${PM_REGION:-us-central1}"
SERVICE="pm-agent"

SECRETS="PM_TICK_TOKEN=pm-tick-token:latest,GOOGLE_API_KEY=pm-google-api-key:latest"
declare -a OPTIONAL=(
  "PM_FATHOM_WEBHOOK_SECRET=pm-fathom-webhook-secret"
  "PM_SLACK_BOT_TOKEN=pm-slack-bot-token"
  "PM_SLACK_SIGNING_SECRET=pm-slack-signing-secret"
  "PM_LINEAR_API_KEY=pm-linear-api-key"
  "PM_LINEAR_WEBHOOK_SECRET=pm-linear-webhook-secret"
  "PM_NOTION_TOKEN=pm-notion-token"
  "PM_GITHUB_TOKEN=pm-github-token"
)
for pair in "${OPTIONAL[@]}"; do
  secret="${pair#*=}"
  if gcloud secrets describe "$secret" --project "$PROJECT" >/dev/null 2>&1; then
    SECRETS="$SECRETS,${pair}:latest"
  fi
done

ENV_VARS="PM_GCP_PROJECT=$PROJECT,PM_DEFAULT_PROJECT_SLUG=acme,GOOGLE_GENAI_USE_VERTEXAI=FALSE"
if [ -n "${PM_GITHUB_REPO:-}" ]; then
  ENV_VARS="$ENV_VARS,PM_GITHUB_REPO=$PM_GITHUB_REPO"
fi

gcloud run deploy "$SERVICE" \
  --project "$PROJECT" --region "$REGION" \
  --source . \
  --allow-unauthenticated \
  --timeout 900 --concurrency 4 --min-instances 0 --max-instances 2 \
  --set-env-vars "$ENV_VARS" \
  --set-secrets "$SECRETS"

gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" \
  --format='value(status.url)'

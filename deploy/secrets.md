# Secrets and one-time setup

Values live only in Secret Manager and your shell. Never in files, never in argv you paste
into a chat.

| Secret | Created by | Consumed by |
|---|---|---|
| `pm-tick-token` | setup step 3 | Cloud Run env `PM_TICK_TOKEN`; Scheduler header |
| `pm-google-api-key` | setup step 3 | Cloud Run env `GOOGLE_API_KEY` (ADK / google-genai) |
| `pm-fathom-webhook-secret` | after the webhook exists (Fathom returns the secret) | Cloud Run env `PM_FATHOM_WEBHOOK_SECRET` |

Rotate any of them with `gcloud secrets versions add <name> --data-file=-` and redeploy.

## Order of operations on first deploy

1. `./deploy/deploy.sh` — without Fathom; gives you the service URL.
2. `./deploy/scheduler.sh` — the one-minute tick.
3. Create the Fathom webhook pointing at `<url>/webhooks/fathom`; store its `secret` as
   `pm-fathom-webhook-secret`.
4. `PM_WITH_FATHOM=1 ./deploy/deploy.sh` — redeploy with the webhook secret mounted.
5. `PM_GCP_PROJECT=<project> uv run python scripts/seed_project.py` — the `projects/acme` doc.
6. Record a call with Fathom on. Watch `events`, `tasks`, `decisions` in the Firestore console.

## Setup steps (once)

```bash
gcloud auth login
gcloud projects create pm-agent-hack-2026 --name="pm-agent"
gcloud config set project pm-agent-hack-2026
gcloud billing projects link pm-agent-hack-2026 --billing-account=XXXXXX-XXXXXX-XXXXXX
gcloud services enable run.googleapis.com firestore.googleapis.com cloudscheduler.googleapis.com \
  secretmanager.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  cloudtrace.googleapis.com
gcloud firestore databases create --location=us-central1 --type=firestore-native
gcloud auth application-default login

# step 3 — secrets
python3 -c 'import secrets; print(secrets.token_urlsafe(32))' | gcloud secrets create pm-tick-token --data-file=-
printf '%s' "$GOOGLE_API_KEY" | gcloud secrets create pm-google-api-key --data-file=-
```

The Fathom webhook (needs `FATHOM_API_KEY` in your shell and the service URL):

```bash
curl -s -X POST https://api.fathom.ai/external/v1/webhooks \
  -H "X-Api-Key: $FATHOM_API_KEY" -H "Content-Type: application/json" \
  -d "{\"destination_url\": \"$URL/webhooks/fathom\", \"triggered_for\": [\"my_recordings\"], \"include_transcript\": true, \"include_summary\": true, \"include_action_items\": true}" \
  | tee /dev/stderr | python3 -c 'import json,sys; print(json.load(sys.stdin)["secret"])' \
  | gcloud secrets create pm-fathom-webhook-secret --data-file=-
```

If Fathom rejects `triggered_for`, its create-webhook docs list the allowed values; use the one
meaning "my own recordings".

## Firestore composite indexes

Queries that filter on one field and order by another need these (single-field queries are
auto-indexed). Created once per project:

```bash
for spec in "tasks:status,due_at" "tasks:status,lease_until" \
            "actions:idempotency_key,created_at" "actions:project_id,created_at" \
            "_contract:status,due_at" "_contract:status,lease_until"; do
  col="${spec%%:*}"; fields="${spec#*:}"; f1="${fields%%,*}"; f2="${fields#*,}"
  gcloud firestore indexes composite create --collection-group="$col" \
    --field-config="field-path=$f1,order=ascending" \
    --field-config="field-path=$f2,order=ascending" --async
done
```

`_contract` exists only for the live Db contract test, which uses the same query shapes as the
real queue.

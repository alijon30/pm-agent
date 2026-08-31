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
for spec in "tasks:status,due_at" "tasks:status,lease_until" "tasks:project_id,created_at" \
            "actions:idempotency_key,created_at" "actions:project_id,created_at" \
            "decisions:project_id,created_at" "corrections:project_id,created_at" \
            "evals:project_id,created_at" "events:project_id,received_at" \
            "_contract:status,due_at" "_contract:status,lease_until"; do
  col="${spec%%:*}"; fields="${spec#*:}"; f1="${fields%%,*}"; f2="${fields#*,}"
  gcloud firestore indexes composite create --collection-group="$col" \
    --field-config="field-path=$f1,order=ascending" \
    --field-config="field-path=$f2,order=ascending" --async
done
```

`_contract` exists only for the live Db contract test, which uses the same query shapes as the
real queue.

## If a deploy hangs

`deploy.sh` builds through the us-central1 Cloud Build pool, which can jam
(builds sit QUEUED indefinitely — seen 2026-08-28, three builds stuck 45+ min).
If a deploy stalls after "Uploading sources... done":

    gcloud builds list --project pm-agent-hackathon-26 --region us-central1 --limit 3
    # QUEUED and not moving? Cancel them, then build through us-east1 and
    # deploy the image directly (preserves env and secrets):
    gcloud builds submit --project pm-agent-hackathon-26 --region us-east1 \
      --tag us-central1-docker.pkg.dev/pm-agent-hackathon-26/cloud-run-source-deploy/pm-agent/redesign:<tag> .
    gcloud run deploy pm-agent --region us-central1 --project pm-agent-hackathon-26 \
      --image us-central1-docker.pkg.dev/pm-agent-hackathon-26/cloud-run-source-deploy/pm-agent/redesign:<tag> --quiet


## Gemini API key and tiers (learned 2026-08-31)

The Gemini API tier follows the KEY's project, not the gcloud account. The original AI Studio
key lived in an auto-created unbilled project: free tier (flash: 20 requests/day). A key minted
on pm-agent-hackathon-26 (`gcloud services api-keys create --api-target
service=generativelanguage.googleapis.com`) attaches to the billed project — but that project
is prepay-gated: until billing is set up for the Gemini API in AI Studio
(https://ai.studio/projects → project → billing; see
https://ai.google.dev/gemini-api/docs/billing#prepay), EVERY model returns "prepayment credits
are depleted", including the ones that are free elsewhere.

Secret versions: v1 = old free-tier key (works, small quota), v2 = project-bound key (works
only after AI Studio billing). The service is PINNED to `pm-google-api-key:1` — env-var
secrets referencing `latest` resolve at instance start, so on a scale-to-zero service a bad
`latest` takes production down at the next cold start. After AI Studio billing is confirmed
(probe with a burst of 15 flash calls), unpin with:

    gcloud run services update pm-agent --region us-central1 \
      --update-secrets GOOGLE_API_KEY=pm-google-api-key:latest

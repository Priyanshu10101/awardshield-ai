#!/usr/bin/env bash
# deploy.sh - one-time setup + deploy of AwardShield on Google Cloud.
#
#   PROJECT_ID=my-project ./deploy/deploy.sh          (run from the repository root, after `gcloud auth login`)
#
# Creates (if missing): the APIs, a Cloud Storage bucket with the PDFs, a Firestore database, a service
# account, an Artifact Registry repo. Then builds one image and deploys:
#   - Cloud Run SERVICE  awardshield       the API + UI (reads results from Firestore)
#   - Cloud Run JOB      awardshield-run   the AI pipeline: Vertex AI Gemini reads PDFs from GCS,
#                                          results are saved to Firestore
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-asia-south1}"                      # Cloud Run / Firestore / bucket region
VERTEX_LOCATION="${VERTEX_LOCATION:-global}"         # Gemini 3 models are served from "global"
BUCKET="${BUCKET:-${PROJECT_ID}-awardshield-docs}"
SA_NAME="awardshield-run"
SA="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
REPO="awardshield"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/awardshield:$(date +%Y%m%d-%H%M%S)"
CASE="${CASE:-IN-CRUT-EBUS}"

gcloud config set project "$PROJECT_ID"

echo "== APIs"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  aiplatform.googleapis.com firestore.googleapis.com storage.googleapis.com

echo "== Cloud Storage: gs://${BUCKET}/assets"
gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1 || \
  gcloud storage buckets create "gs://${BUCKET}" --location="$REGION" --uniform-bucket-level-access
# same layout as the local assets/ folder: assets/rfp/*.pdf, assets/Bids/*.pdf
gcloud storage cp -r assets/* "gs://${BUCKET}/assets/"

echo "== Firestore (Native mode)"
gcloud firestore databases describe --database="(default)" >/dev/null 2>&1 || \
  gcloud firestore databases create --database="(default)" --location="$REGION" --type=firestore-native

echo "== Service account + roles"
gcloud iam service-accounts describe "$SA" >/dev/null 2>&1 || \
  gcloud iam service-accounts create "$SA_NAME" --display-name="AwardShield Cloud Run"
for role in roles/aiplatform.user roles/datastore.user; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${SA}" --role="$role" \
    --condition=None >/dev/null
done
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${SA}" --role=roles/storage.objectViewer >/dev/null

echo "== Build image"
gcloud artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "$REPO" --repository-format=docker --location="$REGION"
gcloud builds submit --tag "$IMAGE" .

ENV_VARS="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${VERTEX_LOCATION},TRUECOST_VERTEX=true,AWARDSHIELD_FIRESTORE=true,AWARDSHIELD_ASSETS_URI=gs://${BUCKET}/assets,TRUECOST_CASE=${CASE}"

echo "== Cloud Run service (API + UI)"
gcloud run deploy awardshield --image "$IMAGE" --region "$REGION" --service-account "$SA" \
  --set-env-vars "$ENV_VARS" --memory 1Gi --cpu 1 --allow-unauthenticated

echo "== Cloud Run job (AI pipeline)"
gcloud run jobs deploy awardshield-run --image "$IMAGE" --region "$REGION" --service-account "$SA" \
  --set-env-vars "$ENV_VARS" --memory 2Gi --cpu 2 --task-timeout 60m --max-retries 1 \
  --command /app/deploy/run_pipeline.sh --args "$CASE"

echo
echo "Done. Run the pipeline:   gcloud run jobs execute awardshield-run --region $REGION --wait"
echo "Open the app:             $(gcloud run services describe awardshield --region "$REGION" --format='value(status.url)')"

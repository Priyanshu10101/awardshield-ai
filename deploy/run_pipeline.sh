#!/bin/sh
# Cloud Run job entrypoint: TrueCost (Vertex AI reads the PDFs from Cloud Storage) then RedSeal.
# Each runner pulls earlier results from Firestore first and saves its results to Firestore at the end.
# Usage: run_pipeline.sh [CASE_ID] [extra truecost args, e.g. --fresh | --answers-only]
set -e
CASE="${1:-${TRUECOST_CASE:-IN-CRUT-EBUS}}"
[ $# -gt 0 ] && shift
cd /app/awardshield-agent
python -m truecost_ai.runner "$CASE" "$@"
python -m redseal_ai.runner "$CASE"

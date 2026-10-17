# AwardShield on Cloud Run: one image for both the web service (API + UI) and the pipeline job.

# ---- 1. build the Angular UI ------------------------------------------------
FROM node:24-slim AS ui
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npx ng build

# ---- 2. Python runtime ------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8080
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# the workspace layout settings.py expects (ROOT = /app)
COPY awardshield-agent/ awardshield-agent/
COPY config/ config/
COPY project/ project/
COPY output/ output/
COPY data/ data/
COPY deploy/run_pipeline.sh deploy/run_pipeline.sh
COPY --from=ui /ui/dist/awardshield-ui/browser ui/dist/awardshield-ui/browser
# PDFs are NOT in the image: they come from Cloud Storage (AWARDSHIELD_ASSETS_URI)

WORKDIR /app/awardshield-agent
# web service by default; the Cloud Run job overrides the command with deploy/run_pipeline.sh
CMD exec uvicorn api.app:app --host 0.0.0.0 --port ${PORT}

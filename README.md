# AwardShield

**Live app: https://awardshield-gpxovcd6kq-el.a.run.app/** (Google Cloud Run)

**The cheapest bid is not always the cheapest.** Evaluation committees compare multi-year supplier
contracts by reading long tenders and every bid by hand, retyping rates into spreadsheets and checking
price-adjustment formulas and fine print: days of work, where one missed clause can pick the wrong
supplier. AwardShield does it with **two AI agents, TrueCost AI and RedSeal AI**:

- **TrueCost AI** reads the tender and every bid (PDFs) with Gemini agents and builds each bidder's
  lifetime cost model: rates, price-adjustment formulas and official price indices, every value with
  a verbatim quote and page.
- A **deterministic engine** (plain Python, no AI) projects every bid month by month over the whole
  contract, applies each bidder's own escalation formula and discounts every payment to today.
- **RedSeal AI** then tries to *disprove* the result. AI challengers propose corrections; a deterministic
  prover verifies each quote in the documents, re-runs the engine and decides the verdict by fixed
  rules: `CERTIFIED_ROBUST`, `UNDERSTATED` or `OVERTURNED`.

> The AI builds the inputs. Code decides. No model ever types a total, a ranking or the verdict.

Nothing in the prompts, schemas or engine is specific to buses, India or one tender: a case is a
manifest of PDFs, and the agents extract whatever quantities, rates and index formulas the documents
contain. The Odisha e-bus tender below is the test case.

### Built with Google

- **Gemini on Vertex AI**: 17 sub-agents (14 in TrueCost AI, 3 in RedSeal AI) read the PDFs natively and
  answer in strict JSON schemas.
- **Google ADK**: both agent trees (`SequentialAgent`, `ParallelAgent`, one pipeline per bidder in
  parallel), with callbacks that keep each bidder's documents away from the other bidders' agents.
- **Cloud Run**: a service (UI, API, live what-if engine) and a job (the agent pipeline).
- **Cloud Storage** holds the tender and bid PDFs; **Firestore** holds the results and buyer answers.

## The demo case: IN-CRUT-EBUS

A real public tender (CRUT 1376, Odisha, India, 108 pages): operation of 200 electric buses for
10 + 2 years, paid per kilometre, with a price-adjustment clause and conflicting rules on amounts in
figures and words. Three synthetic bids respond to it (`generate_bids.py`, see *Scope and assumptions*).

| | GreenMetro | MetroLink | UrbanDrive |
|---|---|---|---|
| Quoted rate (₹/km) | 63.00 *(words: "Sixty Six")* | **61.00** | 65.50 |
| Price indexed to inflation | 36 % | 70 % | 45 % |
| 12-year cost, today's money | **₹549.02 cr** | ₹562.64 cr | ₹575.23 cr |

1. **On paper** MetroLink is the cheapest.
2. **TrueCost AI + engine:** over 12 years MetroLink's price rises fastest, so GreenMetro is ₹13.61 cr cheaper.
3. **RedSeal AI:** GreenMetro wrote ₹63.00 in figures but "Sixty Six" in words, and the tender says words
   prevail. Re-run at ₹66: MetroLink wins (₹562.64 vs ₹575.17 cr). Verdict: **OVERTURNED (contested)**,
   because another tender clause says the lower amount counts. The buyer must decide before signing.

## Scope and assumptions

- **Award rule vs lifetime cost.** This tender formally awards on the lowest *Aggregate Bus Operation
  Cost for Year One* (RFP s.7 iii); on that metric MetroLink is lowest (₹79.92 cr vs GreenMetro ₹81.95 cr).
  AwardShield adds the 12-year lifetime cost as decision support and RedSeal AI reports when the two
  disagree (`CH_AWARD_METRIC` in the proof pack). `OVERTURNED` refers to the lifetime ranking: it tells
  the committee that the tender's own rules and its long-term cost point to different suppliers.
- **Synthetic bids.** Real commercial bids are confidential, so the three bids are generated from public
  data (CAG Delhi DTC audit and CESL award rates, LBNL/WRI India e-bus costs) with known, deliberate
  traps. That gives a ground truth to test the agents against: they must find the traps themselves.
- **Recorded run.** A full run takes about 13 minutes (TrueCost AI 12.4 min, RedSeal AI 43 s), so the UI
  replays a recorded real run instead of making visitors wait; new runs execute as the Cloud Run job.
- **Cost model.** Price revisions follow each bid's formula and timing (every 6 months from month 6);
  the 4 % change trigger and re-basing on the previous revision date are not modelled. Future index
  growth is projected from recent official data. The discount rate and index window are buyer policy
  settings, and the state electricity tariff uses the national WPI electricity series as a proxy
  (recorded in the output).
- **Strict evidence.** The prover accepts a quote only if its words appear in the PDF text in order. By
  design: a paraphrase or an invented clause never counts as evidence, even if it sounds right.
- **Public demo.** The live app has no login because the bids are synthetic; real tenders would need
  access control on the Cloud Run service.

## On Google Cloud

```
Buyer ──HTTPS──▶ Cloud Run service "awardshield"   Angular UI + FastAPI + engine (live what-ifs)
                        ▲ results
                    Firestore                      awardshield_cases/{case}: verdict, cost models,
                        ▲ results                  proof pack, run recordings, buyer answers
                 Cloud Run job "awardshield-run"   TrueCost AI, then RedSeal AI (Google ADK agents)
                   │            │            │
           Cloud Storage   Gemini on      official index publishers (India)
           tender + bid    Vertex AI      Labour Bureau CPI-IW, Economic Adviser WPI
           PDFs
```

- **Cloud Run service** (`awardshield`): the API and the built UI from one image ([Dockerfile](Dockerfile)).
  It loads the results from Firestore, since a new instance starts with an empty disk.
- **Cloud Run job** (`awardshield-run`): the AI pipeline ([deploy/run_pipeline.sh](deploy/run_pipeline.sh)).
  The agents call Gemini on **Vertex AI** through the job's service account (no API key). They read the
  PDFs from **Cloud Storage** and save every result to **Firestore**.
- Without Google Cloud settings, everything runs on local files and a Gemini API key
  ([truecost_ai/cloud.py](awardshield-agent/truecost_ai/cloud.py)).

Deploy (from the repository root, after `gcloud auth login`):

```bash
PROJECT_ID=my-project ./deploy/deploy.sh
```

[deploy/deploy.sh](deploy/deploy.sh) enables the APIs, uploads `assets/` to a bucket, creates the Firestore
database, a service account (Vertex AI user, Firestore user, bucket reader) and the Artifact Registry repo,
builds the image and deploys the service and the job (region `asia-south1`, Vertex AI location `global`).

Run the agents on Cloud Run (about 13 minutes for the demo case):

```bash
gcloud run jobs execute awardshield-run --region asia-south1 --wait
```

## Repository layout

```
awardshield-agent/
  truecost_ai/        TrueCost: ADK agent tree, runner, finalizer (link checks), settings
    engine/           the deterministic NPV / award engine (no AI, no network)
    tests/            engine tests
  redseal_ai/         RedSeal: challengers, prover, narrator, runner
    tests/            RedSeal tests
  api/app.py          FastAPI: case data, live engine what-ifs, serves the built UI
ui/                   Angular 22 UI (decision brief, evidence, engine, challenges, run replay)
deploy/               deploy.sh (Google Cloud setup + deploy), run_pipeline.sh (Cloud Run job)
Dockerfile            one image for the Cloud Run service and job
config/               truecost.json (models, retries, search), buyer_policy.json,
                      rfp_basis.json (buyer evaluation rules), known_sources.json (official index pages)
project/IND/          case manifests (tender + bid PDFs per case)
output/IN-CRUT-EBUS/  results: cost_model.json, proof_pack.json, frozen index series, run recordings
data/state/           buyer answers (checkpoints are local only)
generate_bids.py      generates the three synthetic bid PDFs
```

The results in `output/IN-CRUT-EBUS/` are committed, so the engine, the API and the UI work without
an API key. The tender and bid PDFs are in `assets/` (on Google Cloud they are read from Cloud Storage).

## Setup

Python 3.12+ and, for the UI, Node.js 24.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in the repository root. For Gemini on Vertex AI (as on Cloud Run), set your project and
log in once with `gcloud auth application-default login`:

```
GOOGLE_CLOUD_PROJECT=my-project
GOOGLE_CLOUD_LOCATION=global
```

Or, without Google Cloud, a Gemini API key: `GOOGLE_API_KEY=...`

Settings live in `config/truecost.json`: the model per step, retries, the web-search tool
(`google_search`, `enterprise_web_search` or `none`), the default case. An environment variable
overrides a value for one run (see `truecost_ai/settings.py`).

## Run

From `awardshield-agent/` (with the virtualenv active):

```bash
# 1. TrueCost - read the PDFs, build the cost models, ask the buyer's open questions (~8 min)
python -m truecost_ai.runner IN-CRUT-EBUS
python -m truecost_ai.runner IN-CRUT-EBUS --answers-only   # re-apply stored answers, no PDF reading
python -m truecost_ai.runner IN-CRUT-EBUS --fresh          # ignore checkpoints, read everything again

# 2. Engine - lifetime cost and winner; what-ifs never change the saved model
python -m truecost_ai.engine.cli IN-CRUT-EBUS
python -m truecost_ai.engine.cli IN-CRUT-EBUS --set GreenMetro.gm_rate_1=66 --set discount_rate=0.10

# 3. RedSeal - challenge the award, write proof_pack.json (~1 min)
python -m redseal_ai.runner IN-CRUT-EBUS

# 4. Tests (engine + RedSeal, no model calls)
python -m pytest truecost_ai/tests redseal_ai/tests -q
```

A TrueCost run that stops (rate limit, network) resumes from the last finished step when started
again. Rate parameter ids (e.g. `gm_rate_1`) are chosen by the model; the engine prints them.

To regenerate the synthetic bids: `python generate_bids.py` (from the repository root).

## UI

```bash
cd ui && npm install && npx ng build          # once, and after changing UI code
cd ../awardshield-agent && uvicorn api.app:app --port 8900
```

Open http://127.0.0.1:8900/. For UI development, `npx ng serve` (in `ui/`) hot-reloads on
http://localhost:4200 and forwards `/api` to the server on port 8900.

| Page | Shows |
|---|---|
| Home | the three steps: price on paper, TrueCost's 12-year cost, RedSeal's catch |
| Decision | the verdict, what each reading of the tender means for the winner, the bids |
| TrueCost | every extracted figure with its quote and page; official index sources; buyer questions |
| Engine | yearly payments and price-adjustment curves; live sliders that re-run the engine |
| RedSeal | the challenge ledger with evidence and engine re-runs; flip thresholds; sensitivity |
| Agent run | a time-coded replay of the recorded TrueCost and RedSeal runs |

## API

`uvicorn api.app:app --port 8900` (from `awardshield-agent/`):

| Method | Path | Returns |
|---|---|---|
| GET | `/api/cases` | the cases with a cost model |
| GET | `/api/cases/{id}` | overview: bidders, the three acts, verdict |
| GET | `/api/cases/{id}/truecost` | volume, supplier records, official indices, report, buyer answers |
| GET | `/api/cases/{id}/engine` | parameters, rate ids, full engine result, award |
| POST | `/api/cases/{id}/evaluate` | re-runs the engine with `{"overrides": {...}}` |
| GET | `/api/cases/{id}/redseal` | the proof pack |
| GET | `/api/cases/{id}/runs` | recorded agent runs |
| GET | `/api/cases/{id}/documents/{name}` | one of the case's PDFs |

"""app.py - the AwardShield API: serves the case files and live engine what-ifs to the UI.

    uvicorn api.app:app --port 8900        (from awardshield-agent/)

Read-only over <output_dir>/<rfq_id>/ (written by TrueCost and RedSeal). The only computation is
TrueCost's engine.evaluate - deterministic, no model calls. A built UI (<workspace>/ui/dist/
awardshield-ui/browser) is served at / when it exists.

    GET  /api/cases                         list of cases
    GET  /api/cases/{id}                    overview: bidders, the three acts, verdict
    GET  /api/cases/{id}/truecost           volume, per-supplier records, official indices, report, answers
    GET  /api/cases/{id}/engine             parameters, rates, full result, award, indices, policy, buyer rules
    POST /api/cases/{id}/evaluate           {"overrides": {...}} -> re-runs the engine (what-if)
    GET  /api/cases/{id}/redseal            proof_pack.json
    GET  /api/cases/{id}/runs               recorded runs (truecost / truecost_answers / redseal)
    GET  /api/cases/{id}/documents/{name}   one of the case's PDFs (tender or bid)
"""

import json
import sys
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # awardshield-agent/

from truecost_ai.doc_reader import Case  # noqa: E402
from truecost_ai.engine import award, evaluate, load_case  # noqa: E402
from truecost_ai.engine.indices import rate_for  # noqa: E402
from truecost_ai.finalizer import _slug  # noqa: E402
from truecost_ai.settings import BUYER_POLICY, CONFIG_DIR, OUTPUT_DIR, ROOT, STATE_DIR  # noqa: E402

RFP_BASIS = ROOT / "config" / "rfp_basis.json"
UI = ROOT / "ui" / "dist" / "awardshield-ui" / "browser"
CRORE = 1e7

app = FastAPI(title="AwardShield API")


def _json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def _out(case_id: str) -> Path:
    out = OUTPUT_DIR / case_id
    if "/" in case_id or ".." in case_id or not (out / "cost_model.json").exists():
        raise HTTPException(404, f"no cost model for {case_id} - run TrueCost first")
    return out


@lru_cache(maxsize=8)
def _model(case_id: str, mtime: float):
    return load_case(_out(case_id), _json(BUYER_POLICY) or {})


def model(case_id: str):
    """(EngineModel, histories), reloaded when cost_model.json changes."""
    return _model(case_id, (_out(case_id) / "cost_model.json").stat().st_mtime)


def _manifest(case_id: str) -> dict:
    """The case manifest under project/ whose rfq_id is case_id ({} when none)."""
    for f in CONFIG_DIR.rglob("*.json"):
        try:
            m = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if m.get("rfq_id") == case_id:
            return m
    return {}


def _award(r: dict, metric: str = "tco_esc"):
    try:
        return award(r, metric)
    except ValueError as e:  # no supplier with a complete cost model
        raise HTTPException(409, str(e))


def _rate(m, supplier: str) -> tuple[str, float]:
    """The supplier's priced rate: the first p: factor of its lines that is a supplier parameter."""
    sup = m.suppliers[supplier]
    for ln in sup.lines:
        for f in ln.factors:
            if f.startswith("p:") and f[2:] in sup.parameters:
                return f[2:], float(sup.parameters[f[2:]].value)
    return "", 0.0


def _year_one(result: dict) -> dict:
    """Escalated cost of the first 12 months per supplier (the tender's own award metric)."""
    out = {}
    m0 = int(result["start"][5:7])
    for n, v in result["suppliers"].items():
        ys = sorted(v["yearly"])
        if not ys:
            continue
        rest = 12 - (13 - m0)
        out[n] = v["yearly"][ys[0]]["tco_esc"] + (
            v["yearly"][ys[1]]["tco_esc"] * rest / 12 if rest > 0 and len(ys) > 1 else 0.0)
    return out


@app.get("/api/cases")
def cases():
    if not OUTPUT_DIR.exists():
        return []
    return [{"id": p.name, "title": _manifest(p.name).get("title", p.name),
             "has_verdict": (p / "proof_pack.json").exists()}
            for p in sorted(OUTPUT_DIR.iterdir()) if (p / "cost_model.json").exists()]


@app.get("/api/cases/{case_id}")
def case(case_id: str):
    m, h = model(case_id)
    out = _out(case_id)
    r = evaluate(m, h)
    life, sticker = _award(r), _award(r, "tco")
    y1 = _year_one(r)
    bidders = []
    for n in m.suppliers:
        param, rate = _rate(m, n)
        esc = r["suppliers"][n]["escalators"]
        last = list(next(iter(esc.values()))["by_year"].values())[-1] if esc else 1.0
        folder = out / "suppliers" / _slug(n)
        com = _json(folder / "commercial.json") or {}
        unit = next((t for t in com.get("terms", []) if t.get("kind") == "unit_rate"), {})
        fx = next(iter((_json(folder / "escalation.json") or {}).get("formulae", [])), {})
        bidders.append({"name": n, "status": m.suppliers[n].status, "rate": rate, "rate_param": param,
                        "amount_in_words": unit.get("amount_in_words", ""),
                        "sticker_cr": dict(sticker.ranking).get(n), "lifetime_cr": dict(life.ranking).get(n),
                        "year_one_cr": y1[n] / CRORE if n in y1 else None, "factor_end": last,
                        "fixed": fx.get("fixed_weight"),
                        "terms": [(t["symbol"], t["weight"]) for t in fx.get("terms", [])]})
    proof = _json(out / "proof_pack.json")
    after = None
    if proof:
        flip = next((c for c in proof["challenges"]
                     if c.get("rerun") and c["rerun"]["winner"] != proof["original_winner"]), None)
        if flip:
            after = {"ranking": flip["rerun"]["ranking"], "winner": flip["rerun"]["winner"],
                     "challenge": flip["challenge_id"],
                     "change": f"{flip['target']}: {flip['original_value']} -> {flip['corrected_value']}"}
    man = _manifest(case_id)
    vol = _json(out / "volume.json") or {}
    verdict = None
    if proof:
        verdict = {k: proof.get(k) for k in ("status", "contested", "original_winner", "final_winner",
                                             "summary", "fragile")}
        verdict["narrative"] = proof.get("narrative")
    return {"id": case_id, "title": man.get("title", ""), "buyer": man.get("buyer", ""),
            "country": man.get("country", ""), "currency": man.get("currency", "INR"),
            "start": r["start"], "months": r["months"], "discount": r["discount"], "base_year": r["base_year"],
            "volume": [{"id": d["driver_id"], "label": d.get("label", ""), "build": d.get("build_rule", ""),
                        "components": [(c["name"], c["value"], c["unit"]) for c in d.get("components", [])]}
                       for d in vol.get("drivers", []) if d.get("primary", True)],
            "bidders": bidders,
            "acts": {"sticker": {"ranking": sticker.ranking, "winner": sticker.winner},
                     "lifetime": {"ranking": life.ranking, "winner": life.winner, "margin_cr": life.margin_cr},
                     "after": after,
                     "year_one_winner": min(y1, key=y1.get) if y1 else None},
            "verdict": verdict}


@app.get("/api/cases/{case_id}/truecost")
def truecost(case_id: str):
    out = _out(case_id)
    m, _ = model(case_id)
    sups = {}
    for n in m.suppliers:
        d = out / "suppliers" / _slug(n)
        sups[n] = {k: _json(d / f"{k}.json") for k in ("commercial", "escalation", "index_resolutions",
                                                       "open_questions")}
    idx = {}
    for f in sorted((out / "frozen_indices").glob("*.json")):
        j = _json(f) or {}
        idx[f.stem] = {k: j.get(k) for k in ("symbol", "label", "annual_values", "url", "official", "downloaded_at",
                                             "sha256", "step", "proxy", "partial_years", "frequency")}
    return {"volume": _json(out / "volume.json"), "suppliers": sups, "indices": idx,
            "report": _json(out / "report.json"), "answers": _json(STATE_DIR / case_id / "answers.json"),
            "questions": _json(STATE_DIR / case_id / "questions.json")}


def _index_rate(h: tuple, spec) -> float | None:
    try:
        return rate_for(h, spec.method, spec.rate, spec.years) if spec.method != "path" else None
    except ValueError:
        return None


@app.get("/api/cases/{case_id}/engine")
def engine(case_id: str):
    m, h = model(case_id)
    r = evaluate(m, h)
    return {"result": r, "award": _award(r).model_dump(), "sticker": _award(r, "tco").model_dump(),
            "indices": {s: {"method": spec.method, "years": spec.years, "history": dict(h.get(s, ())),
                            "rate": _index_rate(h.get(s, ()), spec)}
                        for s, spec in m.indices.items()},
            "parameters": {k: p.model_dump() for k, p in m.parameters.items()},
            "rates": {n: dict(zip(("param", "value"), _rate(m, n))) for n in m.suppliers},
            "policy": _json(BUYER_POLICY), "rfp_basis": _json(RFP_BASIS)}


class WhatIf(BaseModel):
    overrides: dict = {}


@app.post("/api/cases/{case_id}/evaluate")
def what_if(case_id: str, body: WhatIf):
    """Re-run the engine with overrides: <Supplier>.<param>, discount_rate, horizon_months, base_year,
    monthly_rate_method, index:<series>, driver_scale. Unknown keys are ignored - use the ids from /engine."""
    m, h = model(case_id)
    try:
        r = evaluate(m, h, body.overrides)
    except (KeyError, ValueError, TypeError) as e:
        raise HTTPException(400, f"bad override: {e}")
    return {"award": _award(r).model_dump(), "sticker": _award(r, "tco").model_dump(),
            "yearly": {n: {y: v["tco_esc"] for y, v in s["yearly"].items()} for n, s in r["suppliers"].items()},
            "factors": {n: next(iter(s["escalators"].values()))["by_year"] if s["escalators"] else {}
                        for n, s in r["suppliers"].items()},
            "discount": r["discount"], "months": r["months"], "start": r["start"]}


@app.get("/api/cases/{case_id}/redseal")
def redseal(case_id: str):
    p = _json(_out(case_id) / "proof_pack.json")
    if p is None:
        raise HTTPException(404, "RedSeal has not run for this case")
    return p


@app.get("/api/cases/{case_id}/runs")
def runs(case_id: str):
    d = _out(case_id) / "runs"
    return {f.stem: _json(f) for f in sorted(d.glob("*.json"))} if d.exists() else {}


@app.get("/api/cases/{case_id}/documents/{name}")
def document(case_id: str, name: str):
    """Only the case's own documents (tender + bids, from its manifest) - never an arbitrary path."""
    try:
        docs = Case.load(case_id).documents
    except (SystemExit, ValueError):
        raise HTTPException(404, f"no manifest for {case_id}")
    for d in docs:
        if d.path.name == name and d.path.is_file():
            return FileResponse(d.path, media_type="application/pdf")
    raise HTTPException(404, name)


if UI.exists():
    app.mount("/", StaticFiles(directory=UI, html=True), name="ui")

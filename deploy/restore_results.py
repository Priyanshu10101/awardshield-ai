"""restore_results.py - replace a case's results in Firestore with the ones in this repo's output/ folder.

Use it when an AI run on Cloud Run left a bidder incomplete (for example an unanswered buyer question)
and you want the website to show the committed, complete results again.

    pip install --user google-cloud-firestore
    python3 deploy/restore_results.py PROJECT_ID [CASE_ID]

Run it from the repository root. It deletes the case's result files in Firestore, then uploads every
output/<case>/**.json plus data/state/<case>/answers.json and questions.json, in the same layout the
app uses (see awardshield-agent/truecost_ai/cloud.py). Afterwards, restart the Cloud Run service so
its disk is refreshed from Firestore.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import firestore

COLLECTION = "awardshield_cases"
ROOT = Path(__file__).resolve().parents[1]


def has_nested_list(x) -> bool:
    if isinstance(x, dict):
        return any(has_nested_list(v) for v in x.values())
    if isinstance(x, list):
        return any(isinstance(v, list) or has_nested_list(v) for v in x)
    return False


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: python3 deploy/restore_results.py PROJECT_ID [CASE_ID]")
    project, case = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "IN-CRUT-EBUS")
    out, state = ROOT / "output" / case, ROOT / "data" / "state" / case
    if not (out / "cost_model.json").exists():
        sys.exit(f"no results in {out} - run this from the repository root")

    files = [("output", p.relative_to(out).as_posix(), p) for p in sorted(out.rglob("*.json"))]
    files += [("state", n, state / n) for n in ("answers.json", "questions.json") if (state / n).exists()]

    db = firestore.Client(project=project)
    case_ref = db.collection(COLLECTION).document(case)

    old = list(case_ref.collection("files").stream())
    batch = db.batch()
    for d in old:
        batch.delete(d.reference)
    batch.commit()
    print(f"removed {len(old)} old result file(s) from Firestore")

    now = datetime.now(timezone.utc)
    batch, n = db.batch(), 0
    for area, rel, path in files:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        doc = {"area": area, "path": rel, "json": text, "sha256": hashlib.sha256(raw).hexdigest(),
               "updated_at": now}
        data = json.loads(text)
        if isinstance(data, dict) and not has_nested_list(data) and len(raw) < 450_000:
            doc["data"] = data
        batch.set(case_ref.collection("files").document(f"{area}__{rel.replace('/', '__')}"), doc)
        n += 1
        if n % 400 == 0:
            batch.commit()
            batch = db.batch()

    summary = {"rfq_id": case, "updated_at": now}
    for m in (ROOT / "project").rglob("*.json"):
        try:
            man = json.loads(m.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if man.get("rfq_id") == case:
            summary["title"] = man.get("title", "")
    report = json.loads((out / "report.json").read_text()) if (out / "report.json").exists() else {}
    proof = json.loads((out / "proof_pack.json").read_text()) if (out / "proof_pack.json").exists() else {}
    summary["ready_for_evaluation"] = report.get("ready_for_evaluation")
    summary["truecost_summary"] = report.get("summary")
    if proof:
        summary["verdict"] = proof.get("status")
        for k in ("contested", "original_winner", "final_winner"):
            summary[f"verdict_{k}"] = proof.get(k)
    batch.set(case_ref, summary)
    batch.commit()
    print(f"uploaded {n} result file(s) for {case}; ready bidders: {summary['ready_for_evaluation']}; "
          f"verdict: {summary.get('verdict')}")


if __name__ == "__main__":
    main()

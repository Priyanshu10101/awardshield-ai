"""cli.py - print the award for one tender.

    python -m truecost_ai.engine.cli IN-CRUT-EBUS
    python -m truecost_ai.engine.cli IN-CRUT-EBUS --set GreenMetro.rate_1=66 --set discount_rate=0.10
    python -m truecost_ai.engine.cli IN-CRUT-EBUS --index-years 5 --json

Reads <output_dir>/<rfq_id>/cost_model.json + frozen_indices/ and config/buyer_policy.json.
output_dir: TRUECOST_OUTPUT_DIR, else 'output_dir' in config/truecost.json, else <root>/output -
the same folder TrueCost's runner writes to.
"""

import argparse
import json
import os
from pathlib import Path

from . import award, evaluate, explain_escalator, load_case

ROOT = Path(__file__).resolve().parents[3]  # the workspace (awardshield-agent/truecost_ai/engine/cli.py)


def output_dir() -> Path:
    settings = ROOT / "config" / "truecost.json"
    configured = json.loads(settings.read_text()).get("output_dir") if settings.exists() else None
    return ROOT / (os.getenv("TRUECOST_OUTPUT_DIR") or configured or "output")


def parse_value(v: str):
    try:
        return float(v)
    except ValueError:
        return v


def main() -> None:
    ap = argparse.ArgumentParser(description="TrueCost engine: lifetime cost and award for one tender.")
    ap.add_argument("case", help="RFQ id (folder under the output directory)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override, e.g. GreenMetro.rate_1=66, discount_rate=0.10, rfq.contract.start=2026-01")
    ap.add_argument("--index-years", type=int, help="index window for every series (mean_yoy N points)")
    ap.add_argument("--json", action="store_true", help="print the full evaluate() result as JSON")
    args = ap.parse_args()

    policy_file = ROOT / "config" / "buyer_policy.json"
    policy = json.loads(policy_file.read_text()) if policy_file.exists() else {}
    model, histories = load_case(output_dir() / args.case, policy)
    overrides = {k.strip(): parse_value(v.strip()) for k, _, v in (s.partition("=") for s in args.set)}
    if args.index_years:
        overrides.update({f"index:{s}": {"method": "mean_yoy", "years": args.index_years}
                          for s in model.indices})

    result = evaluate(model, histories, overrides)
    if args.json:
        print(json.dumps(result, indent=1))
        return
    sticker, lifetime = award(result, "tco", "STICKER"), award(result, "tco_esc", "LIFETIME")
    d = result["discount"]
    print(f"{model.rfp_id}: {result['months']} months from {result['start']}, base year {result['base_year']}, "
          f"discount {d['annual']:.1%} ({d['method']})" + (f", overrides {overrides}" if overrides else ""))
    print(f"\n {'supplier':12} {'sticker NPV':>12} {'lifetime NPV':>13} {'escalation':>11}  factor at end")
    last_year = int(result["start"][:4]) * 12 + int(result["start"][5:7]) - 1 + result["months"] - 1
    for name, npv in lifetime.ranking:
        s = result["suppliers"][name]
        esc = next(iter(model.suppliers[name].escalators), None)
        end = explain_escalator(model, histories, name, esc.id, last_year // 12, overrides)["value"] if esc else 1.0
        print(f" {name:12} {s['npv']['tco'] / 1e7:9.2f} Cr {npv:10.2f} Cr {npv / (s['npv']['tco'] / 1e7) - 1:+10.1%}"
              f"   x{end:.4f}")
    print(f"\n cheapest sticker : {sticker.winner} (by {sticker.margin_cr:.2f} Cr)")
    print(f" lifetime winner  : {lifetime.winner} (by {lifetime.margin_cr:.2f} Cr, {lifetime.margin_pct:.2f}%)")
    if lifetime.excluded:
        print(f" not ranked (cost model incomplete): {lifetime.excluded}")
        for name in lifetime.excluded:
            if err := result["suppliers"][name].get("error"):
                print(f"   {name}: {err}")


if __name__ == "__main__":
    main()

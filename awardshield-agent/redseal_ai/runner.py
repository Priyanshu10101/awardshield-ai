"""runner.py - run RedSeal on a tender TrueCost has already built, and write the Proof Pack.

    python -m redseal_ai.runner IN-CRUT-EBUS
    python -m redseal_ai.runner IN-CRUT-EBUS --output IN-CRUT-EBUS-ROBUST   # audit a variant cost model

Needs <output_dir>/<rfq_id>/cost_model.json (+ frozen_indices, suppliers/*) from TrueCost. Writes
<output_dir>/<rfq_id>/proof_pack.json and prints the verdict.
"""

import argparse
import asyncio
import json
import logging
import time

from google.adk.runners import InMemoryRunner
from google.genai import types

from truecost_ai.doc_reader import Case, pack
from truecost_ai.settings import CASE, OUTPUT_DIR

from .agent import build_root

APP, USER = "redseal", "buyer"


async def run(case_id: str, output: str = "") -> dict:
    case = Case.load(case_id)
    runner = InMemoryRunner(agent=build_root(case_id, output), app_name=APP)
    session = await runner.session_service.create_session(app_name=APP, user_id=USER, state={})
    intro = types.Part(text=f"Tender {case.rfq_id}: {case.title}. Documents follow.")
    t0 = time.time()
    async for e in runner.run_async(user_id=USER, session_id=session.id,
                                    new_message=types.Content(role="user", parts=[intro, *pack(case.documents)])):
        if e.is_final_response() and e.content and e.content.parts:  # not the narrator check's state update
            print(f"[{time.time() - t0:5.0f}s] {e.author}: done", flush=True)

    st = (await runner.session_service.get_session(app_name=APP, user_id=USER, session_id=session.id)).state
    pack_ = {**st["verdict"], "narrative": st.get("narrative"), "narrative_check": st.get("narrative_check"),
             "challenger_raw": {"extraction": st.get("extraction"), "assumptions": st.get("assumptions")}}
    path = OUTPUT_DIR / (output or case.rfq_id) / "proof_pack.json"
    path.write_text(json.dumps(pack_, indent=1, ensure_ascii=False))
    print_verdict(pack_)
    print(f"\nproof pack: {path} ({time.time() - t0:.0f}s)")
    return pack_


def print_verdict(p: dict) -> None:
    print(f"\n{'=' * 78}\nREDSEAL VERDICT {p['rfq_id']}: {p['status']}{' (contested)' if p['contested'] else ''}"
          f"    {p['original_winner']} -> {p['final_winner']}\n{'=' * 78}")
    b = p["baseline"]
    print(" baseline: " + ", ".join(f"{n} {v:.2f} Cr" for n, v in b["ranking"]) + f" (margin {b['margin_cr']:.2f} Cr)")
    for c in p["challenges"]:
        print(f"\n [{c['status']:9}] {c['challenge_id']} ({c['target']}: {c['original_value']} -> {c['corrected_value']})")
        if c["effect"]:
            print(f"             {c['effect']}")
        print(f"             check: {c['checks'][-1]}")
    print("\n flip thresholds:")
    for t in p["flip_thresholds"]:
        print(f"    {t['supplier']:11} {t['param']} {t['current']:g} -> {t['threshold']:.2f} ({t['change_pct']:+.1f} %) "
              f"vs {t['against']}{'  PLAUSIBLE' if t['plausible'] else ''}")
    print(" sensitivity:")
    for r in p["sensitivity"]:
        print(f"    {r['driver']:14} {r['low_label']:>11}: {r['winner_low']:11} {r['high_label']:>11}: {r['winner_high']:11}"
              f" {'FLIPS' if r['flips'] else ''}")
    n = p.get("narrative")
    if n:
        print(f"\n {n['headline']}")
        for f in n["findings"]:
            print(f" - {f}")
        print(f" {n['recommendation']}")
    elif p.get("narrative_check"):
        print(f"\n (narrative dropped - numbers not in the proof: {p['narrative_check']['numbers_not_in_proof']})")


def main():
    parser = argparse.ArgumentParser(description="RedSeal: try to disprove a TrueCost award and write the Proof Pack.")
    parser.add_argument("case", nargs="?", default=CASE,
                        help="RFQ id (TrueCost must have run for it; default: 'case' in config/truecost.json)")
    parser.add_argument("--output", default="", help="audit <output_dir>/<OUTPUT> instead of <output_dir>/<rfq_id>")
    args = parser.parse_args()
    asyncio.run(run(args.case, args.output))
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)


if __name__ == "__main__":
    main()

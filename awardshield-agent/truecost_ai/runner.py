"""runner.py - run TrueCost for one tender from the command line,

    python -m truecost_ai.runner                         # the 'case' in config/truecost.json
    python -m truecost_ai.runner IN-CRUT-EBUS            # full run, then ask the buyer
    python -m truecost_ai.runner IN-CRUT-EBUS --answers-only   # re-apply stored answers (no document reading)
    python -m truecost_ai.runner IN-CRUT-EBUS --fresh    # ignore saved steps, read everything again
    python -m truecost_ai.runner IN-CRUT-EBUS --set rfq.contract.start=2026-04 --set rfq.index.base_year=2025

Round 1 runs the whole agent tree (agent.build_root): tender volume, every bidder in parallel, merged report. The buyer then answers the report's questions in the terminal (Enter = accept the suggestion, 'skip' = leave open); answers are stored in data/state/<rfq_id>/answers.json and reused on every later run. Rounds 2+ run only build_answers_root: each bidder's cost model + finalizer, then the orchestrator. - the extraction records are reused, so no document is read again.

Resume: every model step's answer is saved under data/state/<rfq_id>/checkpoints/ as it finishes
(checkpoint.py), so a run that stopped (503, quota) continues from the failed step when started again.
"""

import argparse
import asyncio
import json
import logging
import shutil
import sys
import time

from google.adk.agents import ParallelAgent, SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from .agent import bidder_key, build_root, make_orchestrator
from .checkpoint import RESTORED
from .recorder import Recorder
from .doc_reader import Case, docs_hash, pack
from .finalizer import _slug, make_finalizer
from .settings import CASE, MAX_QUESTION_ROUNDS, OUTPUT_DIR, STATE_DIR
from .subagents.cost_model import make_cost_model

APP, USER = "truecost", "buyer"

# ------------------------------------------------------------------------
# buyer answers (stored outside output/, reused on every run)
# ------------------------------------------------------------------------
def answers_path(case: Case):
    return STATE_DIR / case.rfq_id / "answers.json"

def load_answers(case: Case) -> dict:
    p = answers_path(case)
    return json.loads(p.read_text()) if p.exists() else {}

def save_answers(case: Case, answers: dict) -> None:
    p = answers_path(case)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(answers, indent=1, ensure_ascii=False))

def ask(questions: list[dict], known: dict) -> dict:
    """Ask every open question once in the terminal. Enter = the suggestion, a number = that option,
    'skip' = leave it open, anything else = your answer. No terminal -> nothing is asked."""
    todo = [q for q in questions if q["key"] not in known]
    if not todo or not sys.stdin.isatty():
        return {}
    print(f"\n{'-' * 78}\n{len(todo)} question(s) for you - Enter accepts the suggestion, 'skip' leaves it open\n"
          f"{'-' * 78}")
    answers = {}
    for i, q in enumerate(todo, 1):
        print(f"\n{i}. [{q['key']}] {q['question']}")
        if q.get("why"):
            print(f"   why: {q['why'][:300]}")
        opts = q.get("options") or []
        for n, o in enumerate(opts, 1):
            print(f"   {n}. {o}")
        if q.get("suggestion"):
            print(f"   suggested: {q['suggestion']}")
        raw = input("   answer > ").strip()
        if raw.lower() == "skip" or (not raw and not q.get("suggestion")):
            continue
        answers[q["key"]] = (q["suggestion"] if not raw else
                             opts[int(raw) - 1] if raw.isdigit() and 1 <= int(raw) <= len(opts) else raw)

    return answers

# ------------------------------------------------------------------------
# agent trees
# ------------------------------------------------------------------------
def build_answers_root(case: Case) -> SequentialAgent:
    """Rounds 2+: re-link each bidder's cost model with the buyer's answers, re-check, re-report."""
    relinks = [SequentialAgent(name=f"relink_{bidder_key(s)}", description=f"{s} : cost model with answers.",
                               sub_agents=[make_cost_model(s, bidder_key(s)),
                                           make_finalizer(s, bidder_key(s))])
               for s in case.supplier_names]
    return SequentialAgent(name="truecost_answers", description="Apply the buyer's answers to every cost model.",
                           sub_agents=[ParallelAgent(name="relink",
                               description="Every bidder at once.",
                               sub_agents=relinks),
                               make_orchestrator(case)])

def records_from_disk(case: Case) -> dict:
    """The extraction records a previous full run saved, as session state (for --answers-only)."""
    out = OUTPUT_DIR / case.rfq_id
    state = {"volume": json.loads((out / "volume.json").read_text())}
    for s in case.supplier_names:
        folder, k = out / "suppliers" / _slug(s), bidder_key(s)
        for name in ("commercial", "escalation", "index_resolutions"):
            state[f"{name}_{k}"] = json.loads((folder / f"{name}.json").read_text())
    return state

async def run_tree(agent, state: dict, parts: list[types.Part], t0: float, rec: Recorder | None = None) -> dict:
    """Run one agent tree in a fresh session; print each sub-agent as it finishes; return the final state.
    rec: a Recorder that keeps a time-coded copy of every event for the UI's run replay."""
    runner = InMemoryRunner(agent=agent, app_name=APP)
    session = await runner.session_service.create_session(app_name=APP, user_id=USER, state=state)
    async for e in runner.run_async(user_id=USER, session_id=session.id,
                                    new_message=types.Content(role="user",
                                    parts=parts)):
        if rec is not None:
            rec.event(e)
        if e.is_final_response() and e.content and e.content.parts:
            text = (e.content.parts[0].text or "").strip()
            restored = (e.actions.state_delta or {}).get(RESTORED) == e.author
            shown = text if e.author.startswith("finalizer") else "restored from checkpoint" if restored else "done"
            print(f"[{time.time() - t0:5.0f}s] {e.author}: {shown}",
                  flush=True)
    return (await runner.session_service.get_session(app_name=APP, user_id=USER, session_id=session.id)).state

# ------------------------------------------------------------------------
# the run
# ------------------------------------------------------------------------
def print_report(report: dict) -> None:
    print(f"\n{'-' * 78}\nTRUECOST REPORT {report['rfq_id']}\n{'-' * 78}")
    for b in report["bidders"]:
        print(f" {b['supplier']:<14} {b['status']:<14} {b['quoted_price']:<26} {b['escalation']}")
        for p in b.get("problems", []):
            print(f"   unresolved: {p}")
    print(f"\n ready for evaluation: {report['ready_for_evaluation'] or 'none yet'}")
    print(f" {report['summary']}")

def checkpoint_dir(case: Case, fresh: bool):
    """<state_dir>/<rfq_id>/checkpoints/<hash of the documents>; --fresh empties it first."""
    root = STATE_DIR / case.rfq_id / "checkpoints"
    if fresh and root.exists():
        shutil.rmtree(root)
    return root / docs_hash(case.documents)

async def main(case_id: str, sets: list[str], answers_only: bool, fresh: bool = False) -> None:
    case = Case.load(case_id)
    answers = load_answers(case)
    for item in sets:
        k, _, v = item.partition("=")
        answers[k.strip()] = v.strip()
        save_answers(case, answers)

    t0 = time.time()
    base = {"rfq_id": case.rfq_id, "country": case.country, "answers": answers,
            "checkpoint_dir": str(checkpoint_dir(case, fresh))}
    print(f"{case.rfq_id}: {len(case.documents)} documents, bidders {case.supplier_names}"
          f"{' - answers only, no document reading' if answers_only else ''}",
          flush=True)
    rec = Recorder("truecost_answers" if answers_only else "truecost", case.rfq_id)
    if answers_only:
        st = await run_tree(build_answers_root(case), {**base, **records_from_disk(case)},
                            [types.Part(text="Apply the buyer's answers.")], t0, rec)
    else:
        intro = types.Part(text=f"Tender {case.rfq_id}: {case.title}. Documents follow.")
        st = await run_tree(build_root(case), base, [intro, *pack(case.documents)], t0, rec)
    rec.save({"bidders": case.supplier_names})

    for _ in range(MAX_QUESTION_ROUNDS):
        print_report(st["report"])
        questions = st["report"]["questions"]
        q_path = STATE_DIR / case.rfq_id / "questions.json"  # the open questions, for the UI
        q_path.parent.mkdir(parents=True, exist_ok=True)
        q_path.write_text(json.dumps(questions, indent=1, ensure_ascii=False))
        new = ask(questions, answers)
        if not new:
            break
        answers.update(new)
        save_answers(case, answers)
        print(f"\nAnswers stored in {answers_path(case)} - re-linking the cost models ...", flush=True)
        rec = Recorder("truecost_answers", case.rfq_id)
        st = await run_tree(build_answers_root(case), {**st, "answers": answers},
                            [types.Part(text="Apply the buyer's answers.")], t0, rec)
        rec.save({"bidders": case.supplier_names})

    out = OUTPUT_DIR / case.rfq_id
    (out / "report.json").write_text(json.dumps(st["report"], indent=1, ensure_ascii=False))
    print(f"\ncost model: {out / 'cost_model.json'}\nreport: {out / 'report.json'} ({time.time() - t0:.0f}s)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run TrueCost for one tender.")
    ap.add_argument("case", nargs="?", default=CASE,
                    help="RFQ id or manifest path (default: 'case' in config/truecost.json)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="store a buyer answer")
    ap.add_argument("--answers-only", action="store_true",
                    help="skip document reading; re-link the cost models with the stored answers")
    ap.add_argument("--fresh", action="store_true",
                    help="delete the saved steps of this tender and run every step again")
    args = ap.parse_args()
    asyncio.run(main(args.case, args.set, args.answers_only, args.fresh))
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)  # silence SSL close noise at interpreter exit

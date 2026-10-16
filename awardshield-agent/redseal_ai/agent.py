"""agent.py - the RedSeal agent tree: AI challengers propose, Python proves.

    redseal = SequentialAgent "redseal"
    ├ load_case               BaseAgent  engine baseline + the facts the challengers need -> state
    ├ ParallelAgent "challengers"
    │   ├ extraction_challenger  LlmAgent  re-reads every bid (+ tender rules) -> state['extraction']
    │   └ assumption_challenger  LlmAgent  reads the tender + policy + buyer rules -> state['assumptions']
    ├ prover                  BaseAgent  verify, engine re-runs, flip thresholds, sensitivity, verdict
    │                                    -> state['verdict'] (NO model call)
    └ narrator                LlmAgent   plain-words story from the proof only -> state['narrative']
                                         (Python drops it if it adds a number; the verdict stands without it)

One session per tender. The user message holds every document; each challenger sees only what it needs
(only_documents from TrueCost's doc_reader). RedSeal audits what TrueCost wrote to <output>/<rfq_id>/ and
re-runs TrueCost's engine; it never edits TrueCost's files.
"""

import json
import re
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types

from truecost_ai.doc_reader import Case, only_documents, read_pdf_text
from truecost_ai.engine import award, evaluate, load_case
from truecost_ai.finalizer import _slug
from truecost_ai.settings import BUYER_POLICY, OUTPUT_DIR, ROOT, apply_vertex_env, generate_config, model_for

from . import prompts
from .prover import prove
from .schemas import AssumptionChallengeRecord, ExtractionChallengeRecord, Narrative, Verdict

apply_vertex_env()  # Gemini API key / Vertex project for every model call

RFP_BASIS = ROOT / "config" / "rfp_basis.json"  # the buyer's evaluation rules RedSeal audits against


def _read_json(path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _inputs(case_id: str, output: str):
    """(case, output folder, policy, buyer rules, engine model, histories) - shared by load_case and prover."""
    case = Case.load(case_id)
    out = OUTPUT_DIR / (output or case.rfq_id)
    policy = _read_json(BUYER_POLICY)
    model, histories = load_case(out, policy)
    return case, out, policy, _read_json(RFP_BASIS), model, histories


# -----------------------------------------------------------------------------
# 1. load_case: engine baseline + facts for the prompts
# -----------------------------------------------------------------------------

class LoadCase(BaseAgent):
    case_id: str
    output: str = ""  # <output_dir>/<output>; default = the case's rfq_id

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        case, out, policy, basis, model, histories = _inputs(self.case_id, self.output)
        base = award(evaluate(model, histories))

        values, terms = [], []
        for name, sup in model.suppliers.items():
            values.append(f"{name}: " + "; ".join(f"{k} = {p.value} ({p.source})" for k, p in sup.parameters.items()))
            com = _read_json(out / "suppliers" / _slug(name) / "commercial.json")
            for t in com.get("terms", []):
                if t.get("kind") == "unit_rate":
                    ev = t.get("evidence") or {}
                    terms.append(f"{name}: {t.get('amount')} {t.get('unit', '')} | words: {t.get('amount_in_words', '')} | "
                                 f"quote: {ev.get('quote', '')} ({ev.get('document', '')} p.{ev.get('page', '')})")

        settings = [f"{k} = {p.value} ({p.source})" for k, p in model.parameters.items()]
        settings += [f"index {s}: {i.method} {i.years}" for s, i in model.indices.items()]
        settings.append(f"monthly rate method: {model.monthly_rate_method}; award ranks on lifetime escalated NPV")

        delta = {
            "rfq_id": case.rfq_id, "country": case.country,
            "baseline_text": f"winner {base.winner}, margin {base.margin_cr:.2f} Cr; ranking: "
                             + ", ".join(f"{n} {v:.2f} Cr" for n, v in base.ranking),
            "model_values": "\n".join(values),
            "extracted_terms": "\n".join(terms) or "(none)",
            "model_settings": "\n".join(settings),
            "policy_text": "\n".join(f"{k}: {v}" for k, v in policy.items() if not k.startswith("_")),
            "rfp_basis_text": "\n".join(f"{k}: {v}" for k, v in basis.items() if not k.startswith("_")),
        }
        yield Event(author=self.name, invocation_id=ctx.invocation_id,
                    content=types.Content(role="model", parts=[types.Part(text=delta["baseline_text"])]),
                    actions=EventActions(state_delta=delta))


# -----------------------------------------------------------------------------
# 2. challengers
# -----------------------------------------------------------------------------

def make_extraction_challenger() -> LlmAgent:
    """Sees the tender and EVERY bid (it audits all bidders), so no document filter."""
    return LlmAgent(
        name="extraction_challenger", model=model_for("extraction_challenger"),
        description="Re-reads every bid adversarially and proposes numeric corrections with evidence.",
        instruction=prompts.EXTRACTION,
        output_schema=ExtractionChallengeRecord,
        output_key="extraction",
        generate_content_config=generate_config(),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )


def make_assumption_challenger() -> LlmAgent:
    return LlmAgent(
        name="assumption_challenger", model=model_for("assumption_challenger"),
        description="Challenges the evaluation basis against the tender and the buyer's rules.",
        instruction=prompts.ASSUMPTION,
        output_schema=AssumptionChallengeRecord,
        output_key="assumptions",
        before_model_callback=only_documents(tender=True),
        generate_content_config=generate_config(),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )


# -----------------------------------------------------------------------------
# 3. prover (no AI)
# -----------------------------------------------------------------------------

class Prover(BaseAgent):
    case_id: str
    output: str = ""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        st = ctx.session.state
        case, out, policy, basis, model, histories = _inputs(self.case_id, self.output)
        documents = {d.path.name: read_pdf_text(d.path) for d in case.documents}
        tender = "\n".join(documents[d.path.name] for d in case.documents if not d.supplier)
        v = prove(model, histories, st.get("extraction"), st.get("assumptions"), documents, basis, policy, tender)
        yield Event(author=self.name, invocation_id=ctx.invocation_id,
                    content=types.Content(role="model", parts=[types.Part(text=v.summary)]),
                    actions=EventActions(state_delta={"verdict": v.model_dump(),
                                                      "proof_text": v.summary + "\n" + _proof_details(v)}))


def _proof_details(v: Verdict) -> str:
    lines = []
    for t in v.flip_thresholds:
        lines.append(f"flip threshold: {t.supplier} {t.param} {t.current:g} -> {t.threshold:.2f} ({t.change_pct:+.1f} %) "
                     f"vs {t.against}{' - plausible' if t.plausible else ''}")
    for r in v.sensitivity:
        lines.append(f"sensitivity {r.driver}: {r.low_label} -> winner {r.winner_low}; {r.high_label} -> winner "
                     f"{r.winner_high}{' (FLIPS)' if r.flips else ''}")
    for p in v.challenges:
        if p.status != "rejected" and p.evidence_against:
            lines.append(f"{p.challenge_id} evidence against: " + " / ".join(e["quote"] for e in p.evidence_against))
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# 4. narrator (+ number check)
# -----------------------------------------------------------------------------

NUMBER = re.compile(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?")


def numbers_not_in(text: str, source: str) -> list[str]:
    allowed = {n.replace(",", "").rstrip(".") for n in NUMBER.findall(source)}
    return [n for n in NUMBER.findall(text) if n.replace(",", "").rstrip(".") not in allowed]


def _check_narrative(callback_context: CallbackContext) -> None:
    """after_agent_callback: a narrative with a number the proof does not contain is dropped (the verdict
    and the deterministic summary stand on their own)."""
    st = callback_context.state
    n = st.get("narrative")
    if not n:
        return None
    text = " ".join([n.get("headline", ""), *n.get("findings", []), n.get("recommendation", "")])
    bad = numbers_not_in(text, st.get("proof_text", ""))
    st["narrative_check"] = {"ok": not bad, "numbers_not_in_proof": bad}
    if bad:
        st["narrative"] = None
    return None


def make_narrator() -> LlmAgent:
    return LlmAgent(
        name="narrator", model=model_for("narrator"),
        description="Explains the proven verdict in plain words; may not introduce numbers.",
        instruction=prompts.NARRATOR,
        output_schema=Narrative,
        output_key="narrative",
        include_contents="none",
        after_agent_callback=_check_narrative,
        generate_content_config=generate_config(),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )


# -----------------------------------------------------------------------------
# the tree
# -----------------------------------------------------------------------------

def build_root(case_id: str, output: str = "") -> SequentialAgent:
    """output: audit <output_dir>/<output> instead of <output_dir>/<rfq_id> (same documents)."""
    return SequentialAgent(
        name="redseal",
        description="RedSeal: try to disprove the award; prove every challenge with the engine.",
        sub_agents=[
            LoadCase(name="load_case", case_id=case_id, output=output),
            ParallelAgent(name="challengers", description="Both challengers at once.",
                          sub_agents=[make_extraction_challenger(), make_assumption_challenger()]),
            Prover(name="prover", case_id=case_id, output=output),
            make_narrator(),
        ],
    )

AwardShield - RedSeal Build 

Self-contained. Do the steps in order; each ends with a check. Built and verified on the server first; the expected outputs below are from that run. Prerequisites: ENGINE_BUILD.md is done (the engine/ package and agent/truecost/ layout exist) and TrueCost has produced data/output/IN-CRUT-EBUS/.

What RedSeal is: a second, independent agent whose job is to DISPROVE TrueCost's award. AI sub-agents
propose challenges; a deterministic prover verifies every one against the documents and proves its effect by
re-running the engine; fixed rules decide the verdict. No model ever types a ranking, a total or the verdict.

0. Architecture

redseal (SequentialAgent, one session per tender; the user message holds every document)
├── load_case BaseAgent engine baseline + the facts the prompts need -> state
├── challengers ParallelAgent
│   ├── extraction_challenger LlmAgent re-reads every bid + tender price rules
│   |               -> state['extraction'] (ExtractionChallengeRecord)
│   └── assumption_challenger LlmAgent tender + company policy + buyer rules
│       |               -> state['assumptions'] (AssumptionChallengeRecord)
├── prover BaseAgent NO AI: verify -> engine reruns
-> flip thresholds -> sensitivity -> verdict
│                                        -> state['verdict']
└── narrator LlmAgent plain words from the proof only; a Python check drops it if it adds a number
│                                        -> state['narrative']
-> data/output/<rfq>/proof_pack.json

step	AI?	why
load_case	no	reads files, runs the engine baseline
extraction_challenger	yes	adversarial re-reading needs judgement
assumption_challenger	yes	matching tender clauses to evaluation settings needs judgement
prover	no	proof must be deterministic: same challenges -> same verdict
narrator	yes	readable story; cannot add numbers

How the AI is kept honest (prover rules):

1. A quote must be printed in the cited document (read_pdf_text), else rejected.

2. A figure-vs-words claim must parse (words.py) to the corrected value, else rejected.

3. The challenged parameter must hold the claimed value and be used by a cost line, else rejected.

4. An assumption citing the tender must quote a clause printed in the tender, else rejected.

5. A verified challenge whose evidence_against cites a printed clause -> contested (still proven).

6. Only engine.rerun() produces numbers.

Verdict rules (prover.prove):

⚬ OVERTURNED: a verified or contested challenge changes the winner (contested=True when the deciding one is contested).

⚬ UNDERSTATED: the winner holds, but the award is fragile (a flip threshold within +-5 % of a priced rate,
or a sensitivity flip), or a challenge raises the winner's NPV > 1 % or cuts the margin > 1 %.

⚬ CERTIFIED_ROBUST: none of the above.

1. Files, in build order

Create agent/redseal/ and copy each file exactly. No new packages
(uses google-adk, pydantic, numpy, pypdf).

R1. config/rfp_basis.json

The buyer's evaluation rules RedSeal audits the cost model against.
Honestly labelled: the CRUT tender itself prescribes no discount rate
or index window (it awards on year-one cost).

[json]
{
  "_note": "The BUYER'S evaluation rules RedSeal checks the cost model against. The CRUT tender itself prescribes no discount rate or index window (it awards on 'Lowest Aggregate Bus Operation Cost for Year One', L1 per package): these values are the procurement team's evaluation standard for multi-year GCC contracts and must be confirmed by the buyer. Company policy (config/buyer_policy.json) departs from them.",
  "discount_rate": 0.10,
  "index_method": {"method": "mean_yoy", "years": 5},
  "source": "Buyer evaluation standard (AwardShield spec section 8), confirmed for multi-year GCC evaluations",
  "tender_award_metric": "year_one",
  "_tender_award_metric_note": "What the tender itself awards on: 'The bidder quoting the lowest Aggregate Bus Operation Cost for Year One ... shall be the Preferred Bidder' (RFP s.7 iii). RedSeal reports when the lifetime winner differs from this year-one L1."
}


R2. agent/redseal/__init__.py

Package marker.

[python]
"""RedSeal - the adversarial auditor: AI challengers propose, the engine proves, fixed rules decide."""


R3. agent/redseal/schemas.py

Challenger outputs (what the AI proposes) and prover outputs (what Python proves). Lists with ids, no free-key dicts.

[python]
"""schemas.py - what the RedSeal sub-agents return and what the prover writes.

Challengers PROPOSE (LLM output, lists with ids - no free-key dicts).
The prover VERIFIES and PROVES
(Python). Every challenge is a concrete numeric correction the engine
can re-run.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    document: str = Field(description="File name exactly as in its DOCUMENT header.")
    page: str = Field("", description="Page number where it is printed.")
    quote: str = Field(description="The printed sentence or table row, copied verbatim.")


# ---------------------------------------------------------------------------
# challenger
# outputs
# ---------------------------------------------------------------------------

class ExtractionChallenge(BaseModel):
    challenge_id: str = Field(description="Short unique id, e.g. 'greenmetro_rate_words'.")
    supplier: str = Field(description="Bidder name exactly as in the case.")
    param: str = Field(description="The cost-model parameter id challenged (from the parameter list you were given).")
    kind: Literal["figure_vs_words", "misread", "wrong_term", "wrong_weight"] = Field(
        description="figure_vs_words = the printed figure and the amount in words disagree; misread = the "
                    "document prints a different value than the model holds; wrong_weight = an escalation "
                    "weight / fixed share differs from the printed formula; wrong_term = the model used a "
                    "different term than the one the bid prices.")
    extracted_value: float = Field(description="The value the cost model holds now.")
    corrected_value: float = Field(description="The value you claim the document actually establishes.")
    amount_in_words: str = Field("", description="For figure_vs_words: the words exactly as printed.")
    evidence_for: list[Evidence] = Field(description="Where the corrected value is printed / the rule that makes it "
                                                   "prevail (bid page, tender clause).")
    evidence_against: list[Evidence] = Field(default_factory=list,
                                             description="Any printed clause or figure that supports the extracted "
                                                         "value instead. Never omit one you saw.")
    reasoning: str = Field(description="Two or three plain sentences: what is wrong and why the correction holds.")


class ExtractionChallengeRecord(BaseModel):
    challenges: list[ExtractionChallenge] = Field(default_factory=list)
    checked: list[str] = Field(default_factory=list,
                               description="What you checked and found correct, one line each.")


class AssumptionChallenge(BaseModel):
    challenge_id: str
    setting: Literal["discount_rate", "index_window", "contract_months", "base_year", "award_metric", "other"] = Field(
        description="Which evaluation setting is challenged.")
    used_value: str = Field(description="The value the cost model / company policy uses now.")
    should_be: str = Field(description="The value the governing rule prescribes (a number, or 'year_one' for the "
                                       "award metric).")
    rule_source: Literal["tender", "buyer_rules"] = Field(
        description="tender = a clause of the tender document; "
                    "buyer_rules = the buyer's evaluation rules given to you.")
    rule_quote: str = Field(description="The governing clause / rule, verbatim.")
    rule_document: str = Field("", description="Tender file name when rule_source is 'tender'.")
    reasoning: str = Field(description="Two or three plain sentences.")


class AssumptionChallengeRecord(BaseModel):
    challenges: list[AssumptionChallenge] = Field(default_factory=list)
    checked: list[str] = Field(default_factory=list)


class Narrative(BaseModel):
    headline: str = Field(description="One sentence: the verdict and the reason.")
    findings: list[str] = Field(description="One plain sentence per verified challenge, with its proven effect.")
    recommendation: str = Field(description="What the buyer must do before signing, in two or three sentences.")


# ---------------------------------------------------------------------------
# prover outputs
# (Python)
# ---------------------------------------------------------------------------

class Rerun(BaseModel):
    label: str
    ranking: list[tuple[str, float]]  # (supplier, NPV crore) cheapest first
    winner: str
    margin_cr: float
    margin_pct: float


class ProvenChallenge(BaseModel):
    challenge_id: str
    agent: Literal["extraction_challenger", "assumption_challenger"]
    kind: str
    target: str  # parameter or setting
    challenged: str = ""
    supplier: str = ""
    original_value: str
    corrected_value: str
    status: Literal["verified", "contested", "rejected", "finding"]
    checks: list[str]  # what the prover verified, one line each
    evidence: list[dict] = []
    evidence_against: list[dict] = []
    reasoning: str = ""
    overrides: dict = {}
    rerun: Optional[Rerun] = None
    effect: str = ""  # winner changed / cost moved, in words built from numbers


class FlipThreshold(BaseModel):
    supplier: str
    param: str
    current: float
    threshold: float  # value at which this supplier's rank vs the challenger flips
    change_pct: float
    against: str  # the supplier it flips with
    plausible: bool  # |change| <= the plausible band


class SensitivityRow(BaseModel):
    driver: str
    low_label: str
    high_label: str
    winner_low: str
    winner_high: str
    swing_cr: float  # winner's NPV high - low
    flips: bool


class Verdict(BaseModel):
    rfqid: str
    status: Literal["OVERTURNED", "UNDERSTATED", "CERTIFIED_ROBUST"]
    contested: bool = False  # the deciding challenge rests on a disputed rule
    original_winner: str
    final_winner: str
    baseline: Rerun
    challenges: list[ProvenChallenge]
    flip_thresholds: list[FlipThreshold]
    sensitivity: list[SensitivityRow]
    fragile: bool
    summary: str  # deterministic one-paragraph summary
    narrative: Optional[Narrative] = None


R4. agent/redseal/words.py

Amount in words -> number (Indian lakh/crore and paise). Lets the prover verify a figure-vs-words claim WITHOUT trusting the model.

[python]
"""words.py - an amount written in words -> a number (Indian and international usage). Pure Python.

words_to_number("Rupees Sixty Six only per kilometre") -> 66.0
words_to_number("Rupees Sixty Four and Fifty paise per kilometre") -> 64.5
words_to_number("Rupees One Crore Twenty Lakh") -> 12000000.0

Used by the prover to VERIFY a figure-vs-words challenge without trusting the model's reading.
"""

import re

UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
         "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
         "thirteen": 13, "fourteen": 14, "fifteen": 15,
         "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fourty": 40,
        "fifty": 50, "sixty": 60, "seventy": 70,
        "eighty": 80, "ninety": 90}
SCALES = {"hundred": 100, "thousand": 1_000, "lakh": 100_000,
          "lakhs": 100_000, "lac": 100_000,
          "crore": 10_000_000, "crores": 10_000_000, "million":
          1_000_000, "billion": 1_000_000_000}
SUBUNIT = ("paise", "paisa", "cents", "cent")


def _integer(tokens: list[str]) -> int | None:
    total, current, seen = 0, 0, False
    for t in tokens:
        if t in UNITS:
            current += UNITS[t]
        elif t in TENS:
            current += TENS[t]
        elif t == "hundred":
            current = (current or 1) * 100
        elif t in SCALES:
            total += (current or 1) * SCALES[t]
            current = 0
        else:
            continue
        seen = True
    return total + current if seen else None


def words_to_number(text: str) -> float | None:
    """The amount in `text`, or None when no number word is found. A sub-unit (paise / cents) is the part
    after the LAST 'and' that ends with the sub-unit word: '<main> and <n> paise'."""
    t = re.sub(r"[^a-z ]+", " ", text.lower())
    t = re.sub(r"\b(rupees?|rs|inr|only|per|kilomet(re|er)s?|km|a)\b", " ", t)
    words = t.split()
    sub = next((i for i, w in enumerate(words) if w in SUBUNIT), None)
    if sub is not None and "and" in words[:sub]:
        cut = len(words[:sub]) - 1 - words[:sub][::-1].index("and")
        main, frac = words[:cut], words[cut + 1:sub]
    else:
        main, frac = words[:sub] if sub is not None else words, []
    main = [w for w in main if w != "and"]
    whole = _integer(main)
    if whole is None:
        return None
    cents = _integer(frac) if frac else 0
    return round(whole + (cents or 0) / 100, 2)


R5. agent/redseal/prover.py

The deterministic core (no AI): verify each challenge, prove it with engine.rerun, exact flip thresholds, sensitivity sweep, verdict by fixed rules.

[python]
"""prover.py - RedSeal's deterministic core: VERIFY each challenge, PROVE it with the engine, decide the
verdict by fixed rules. No model calls. Same challenges + same cost model -> same verdict.

verdict = prove(model, histories, extraction, assumptions, documents, rfp_basis, tender_text)

1. verify - a quote must be printed in the cited document; a figure-vs-words claim must parse
           (words_to_number) to the corrected value; an assumption must cite a rule found in the
           tender text or the buyer's rules. Unverifiable -> 'rejected' (reported, never used).
           A verified challenge whose evidence_against cites a printed clause -> 'contested'.
2. prove - every verified / contested challenge -> engine overrides -> rank.rerun().
3. counterfactual - the exact flip threshold of every bidder's priced rate against the winner (NPV is
                    linear in the rate).
4. sensitivity - sweep discount, index growth, demand, contract term; does the winner ever change?
5. verdict - OVERTURNED: a verified/contested challenge changes the winner.
             UNDERSTATED: winner unchanged, but the award is fragile (a plausible flip threshold or a
             sensitivity flip) or a challenge raises the winner's NPV > 1 % / cuts the margin > 1 %.
             CERTIFIED_ROBUST: nothing flips it, nothing plausible would, and no challenge moves the
             winner's cost materially. (A rule change that raises EVERY bidder's cost but keeps the
             ranking robust is reported as a finding, and the award is still certified only if the
             winner's own NPV moves <= 1 %.)
"""

import re

from engine import award, evaluate
from engine.model import EngineModel
from engine.rank import CRORE, Award

from .schemas import (AssumptionChallengeRecord, ExtractionChallengeRecord,
                      FlipThreshold, ProvenChallenge, Rerun, SensitivityRow, Verdict)
from .words import words_to_number

UNDERSTATED_PCT = 1.0       # winner's NPV rises by more than this % -> material
PLAUSIBLE_BAND = 0.05       # a flip within +-5 % of a priced rate counts as plausible (fragile award)
TOLERANCE = 0.005           # numbers compared to this absolute tolerance


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower().replace("x", "x")).strip()


def _printed(quote: str, text: str) -> bool:
    """A quote counts as printed if its words appear in order in the text (cells joined by '|' or '...'
    are checked piece by piece)."""
    pieces = [p for p in re.split(r"\s*(?:\||\.|\.\.|\…)\s*", quote) if p.strip()]
    t = _norm(text)
    return bool(pieces) and all(_norm(p)[:80] in t for p in pieces)


def _rerun(model: EngineModel, histories: dict, overrides: dict, label: str) -> Rerun:
    a = award(evaluate(model, histories, overrides), label=label)
    return Rerun(label=label, ranking=a.ranking, winner=a.winner,
                 margin_cr=a.margin_cr, margin_pct=a.margin_pct)


def _priced_param(model: EngineModel, supplier: str) -> str | None:
    """The supplier's priced rate: the first p: factor of its first line that is a supplier parameter."""
    sup = model.suppliers[supplier]
    for ln in sup.lines:
        for f in ln.factors:
            if f.startswith("p:") and f[2:] in sup.parameters:
                return f[2:]
    return None


# ---------------------------------------------------------------------------
# 1. verify
# ---------------------------------------------------------------------------


def verify_extraction(c, model: EngineModel, documents: dict[str, str]) -> tuple[str, list[str]]:
    checks = []
    if c.supplier not in model.suppliers:
        return "rejected", [f"{c.supplier} is not a bidder of this case"]
    params = model.suppliers[c.supplier].parameters
    if c.param not in params:
        return "rejected", [f"{c.param} is not a parameter of {c.supplier}: {sorted(params)}"]
    held = float(params[c.param].value)
    if abs(held - c.extracted_value) > TOLERANCE:
        return "rejected", [f"the model holds {held:g}, not the claimed {c.extracted_value:g}"]
    checks.append(f"the cost model holds {c.param} = {held:g}")
    sup = model.suppliers[c.supplier]
    used = any(f"p:{c.param}" in f or f"1-p:{c.param}" in f for ln in sup.lines for f in ln.factors)
    if not used:
        return "rejected", checks + [f"{c.param} is not used by any cost line - changing it cannot move the award "
                                     f"(escalation weights live in the escalator, which mirrors the bid's printed formula)"]
    if abs(c.corrected_value - held) <= TOLERANCE:
        return "rejected", checks + ["the corrected value equals the extracted value - nothing to correct"]
    for e in c.evidence_for:
        text = documents.get(e.document)
        if text is None:
            return "rejected", checks + [f"cites '{e.document}', which is not a document of this case"]
        if not _printed(e.quote, text):
            return "rejected", checks + [f"quote not found in {e.document}: '{e.quote[:90]}'"]
        checks.append(f"quote verified in {e.document} p.{e.page}")
    if c.kind == "figure_vs_words":
        parsed = words_to_number(c.amount_in_words)
        if parsed is None or abs(parsed - c.corrected_value) > TOLERANCE:
            return "rejected", checks + [f"'{c.amount_in_words}' parses to {parsed}, not {c.corrected_value:g}"]
        checks.append(f"'{c.amount_in_words}' parses to {parsed:g} (independent words-to-number check)")
    against = [e for e in c.evidence_against if (t := documents.get(e.document)) and _printed(e.quote, t)]
    if against:
        checks.append(f"{len(against)} printed clause(s) support the extracted value -> contested")
        return "contested", checks
    return "verified", checks


def verify_assumption(c, rfp_basis: dict, policy: dict, tender_text: str) -> tuple[str, list[str], dict]:
    """(status, checks, overrides)."""
    checks = []
    if c.rule_source == "tender":
        if not _printed(c.rule_quote, tender_text):
            return "rejected", [f"tender clause not found: '{c.rule_quote[:90]}'"], {}
        checks.append("rule verified in the tender text")
    else:
        checks.append("rule taken from the buyer's evaluation rules (config/rfp_basis.json)")
    if c.setting == "discount_rate":
        want = float(rfp_basis.get("discount_rate")) if c.rule_source == "buyer_rules" else _num(c.should_be)
        if want is None or abs(want - _num(c.should_be, want)) > TOLERANCE:
            return "rejected", checks + [f"should_be {c.should_be} does not match the rule ({want})"], {}
        return "verified", checks + [f"discount rate {c.used_value} -> {want:g}"], {"discount_rate": want}
    if c.setting == "index_window":
        rule = rfp_basis.get("index_method", {})
        years = int(rule.get("years")) if c.rule_source == "buyer_rules" else int(_num(c.should_be) or 0)
        if not years:
            return "rejected", checks + ["no index window in the rule"], {}
        return "verified", checks + [f"index window -> {years} years"], {"index_method": {"method": rule.get("method", "mean_yoy"), "years": years}, "__index_all__": {"method": rule.get("method", "mean_yoy"), "years": years}}
    if c.setting == "contract_months":
        months = _num(c.should_be)
        if not months:
            return "rejected", checks + [f"'{c.should_be}' is not a number of months"], {}
        return "verified", checks + [f"contract term -> {months:g} months"], {"horizon_months": int(months)}
    if c.setting == "base_year":
        year = _num(c.should_be)
        if not year or not 1990 <= year <= 2100:
            return "rejected", checks + [f"'{c.should_be}' is not a year"], {}
        return "verified", checks + [f"index base year -> {int(year)}"], {"base_year": int(year)}
    if c.setting == "award_metric":
        return "finding", checks + ["the award metric is not an engine input: reported as a finding"], {}
    return "rejected", checks + [f"setting '{c.setting}' cannot be re-run by the engine"], {}


def _num(text, default=None):
    m = re.search(r"-?\d+(?:\.\d+)?", str(text))
    if not m:
        return default
    v = float(m.group())
    return v / 100 if "%" in str(text) and v > 1 else v


# ---------------------------------------------------------------------------
# 2-4. prove, counterfactual, sensitivity
# ---------------------------------------------------------------------------


def _expand(overrides: dict, model: EngineModel) -> dict:
    ov = dict(overrides)
    if spec := ov.pop("__index_all__", None):
        ov.update({f"index:{s}": spec for s in model.indices})
    return ov


def flip_thresholds(model: EngineModel, histories: dict, base: Award) -> list[FlipThreshold]:
    """For each bidder: the priced rate at which it swaps places with the winner (or, for the winner, with
    the runner-up). NPV is linear in the rate, so threshold = rate x NPV_other / NPV_self."""
    npv = {n: v for n, v in base.ranking}
    out = []
    for name, _ in base.ranking:
        param = _priced_param(model, name)
        if param is None:
            continue
        other = base.runner_up if name == base.winner else base.winner
        if not other:
            continue
        rate = float(model.suppliers[name].parameters[param].value)
        threshold = rate * npv[other] / npv[name]
        change = threshold / rate - 1
        out.append(FlipThreshold(supplier=name, param=param, current=rate, threshold=round(threshold, 4),
                                   change_pct=round(change * 100, 2), against=other,
                                   plausible=abs(change) <= PLAUSIBLE_BAND))
    return out


def sensitivity(model: EngineModel, histories: dict) -> list[SensitivityRow]:
    base_rate = {s: None for s in model.indices}
    from engine.indices import rate_for
    for s, spec in model.indices.items():
        try:
            base_rate[s] = rate_for(histories[s], spec.method, spec.rate, spec.years) if spec.method != "path" else 0.0
        except ValueError:
            base_rate[s] = 0.0
    idx = lambda d: {f"index:{s}": {"method": "fixed", "rate": r + d, "years": None} for s, r in base_rate.items()}
    sweeps = [("discount rate", "8 %", {"discount_rate": 0.08}, "14 %", {"discount_rate": 0.14}),
              ("index growth", "-2 pts/yr", idx(-0.02), "+2 pts/yr", idx(0.02)),
              ("demand", "-20 %", {"driver_scale": 0.8}, "+20 %", {"driver_scale": 1.2}),
              ("contract term", "120 months", {"horizon_months": 120}, "144 months", {"horizon_months": 144})]
    rows = []
    for driver, lo_l, lo, hi_l, hi in sweeps:
        a, b = award(evaluate(model, histories, lo)), award(evaluate(model, histories, hi))
        wl, wh = a.winner, b.winner
        swing = dict(b.ranking)[wh] - dict(a.ranking)[wl]
        base_w = award(evaluate(model, histories, {})).winner
        rows.append(SensitivityRow(driver=driver, low_label=lo_l, high_label=hi_l, winner_low=wl, winner_high=wh,
                                   swing_cr=round(swing, 2), flips=(wl != base_w or wh != base_w)))
    return rows


# ---------------------------------------------------------------------------
# 5. the whole proof
# ---------------------------------------------------------------------------


def prove(model: EngineModel, histories: dict, extraction: dict | None, assumptions: dict | None,
          documents: dict[str, str], rfp_basis: dict, policy: dict, tender_text: str) -> Verdict:
    base_award = award(evaluate(model, histories))
    baseline = Rerun(label="BASELINE", ranking=base_award.ranking, winner=base_award.winner,
                     margin_cr=base_award.margin_cr, margin_pct=base_award.margin_pct)
    base_npv = dict(baseline.ranking)
    proven: list[ProvenChallenge] = []

    for c in ExtractionChallengeRecord.model_validate(extraction or {}).challenges:
        status, checks = verify_extraction(c, model, documents)
        pc = ProvenChallenge(challenge_id=c.challenge_id, agent="extraction_challenger", kind=c.kind,
                             target=f"{c.supplier}.{c.param}", supplier=c.supplier,
                             original_value=f"{c.extracted_value:g}", corrected_value=f"{c.corrected_value:g}",
                             status=status, checks=checks, reasoning=c.reasoning,
                             evidence=[e.model_dump() for e in c.evidence_for],
                             evidence_against=[e.model_dump() for e in c.evidence_against])
        if status in ("verified", "contested"):
            pc.overrides = {f"{c.supplier}.{c.param}": c.corrected_value}
            pc.rerun = _rerun(model, histories, pc.overrides, c.challenge_id)
        proven.append(pc)

    for c in AssumptionChallengeRecord.model_validate(assumptions or {}).challenges:
        status, checks, ov = verify_assumption(c, rfp_basis, policy, tender_text)
        pc = ProvenChallenge(challenge_id=c.challenge_id, agent="assumption_challenger", kind=c.setting,
                             target=c.setting, original_value=c.used_value, corrected_value=c.should_be,
                             status=status, checks=checks, reasoning=c.reasoning,
                             evidence=[{"document": c.rule_document or c.rule_source, "quote": c.rule_quote}])
        if status == "verified":
            pc.overrides = ov
            pc.rerun = _rerun(model, histories, _expand(ov, model), c.challenge_id)
        if status == "finding" and c.setting == "award_metric":
            pc.effect = _year_one_finding(model, histories, baseline.winner)
        proven.append(pc)

    # the combined 'governing basis' rerun: every verified assumption override at once
    combined = {k: v for p in proven if p.agent == "assumption_challenger" and p.status == "verified"
                for k, v in p.overrides.items()}
    if len([p for p in proven if p.agent == "assumption_challenger" and p.status == "verified"]) > 1:
        pc = ProvenChallenge(challenge_id="all_assumptions", agent="assumption_challenger", kind="combined",
                             target="evaluation basis", original_value="company policy",
                             corrected_value="buyer evaluation rules", status="verified",
                             checks=["every verified assumption challenge applied together"],
                             overrides=combined,
                             rerun=_rerun(model, histories, _expand(combined, model), "all_assumptions"))
        proven.append(pc)

    for p in proven:
        if p.rerun and not p.effect:
            p.effect = _effect(baseline, p.rerun, base_npv)

    thresholds = flip_thresholds(model, histories, base_award)
    sens = sensitivity(model, histories)
    fragile = any(t.plausible for t in thresholds) or any(r.flips for r in sens)

    flips = [p for p in proven if p.rerun and p.rerun.winner != baseline.winner]
    understated = [p for p in proven if p.rerun and p.rerun.winner == baseline.winner and
                   (dict(p.rerun.ranking)[baseline.winner] / base_npv[baseline.winner] - 1) * 100 > UNDERSTATED_PCT]
    shrinks = [p for p in proven if p.rerun and p.rerun.winner == baseline.winner and
               p.rerun.margin_cr < baseline.margin_cr * (1 - UNDERSTATED_PCT / 100)]

    if flips:
        decider = next((p for p in flips if p.status == "verified"), flips[0])
        status, final, contested = "OVERTURNED", decider.rerun.winner, decider.status == "contested"
    elif fragile:
        status, final, contested = "UNDERSTATED", baseline.winner, False
    elif understated or shrinks:
        status, final, contested = "UNDERSTATED", baseline.winner, False
    else:
        status, final, contested = "CERTIFIED_ROBUST", baseline.winner, False

    v = Verdict(rfq_id=model.rfq_id, status=status, contested=contested, original_winner=baseline.winner,
                final_winner=final, baseline=baseline, challenges=proven, flip_thresholds=thresholds,
                sensitivity=sens, fragile=fragile, summary="")
    v.summary = summary(v)
    return v


def _effect(base: Rerun, r: Rerun, base_npv: dict) -> str:
    w = base.winner
    if r.winner != w:
        return (f"award flips: {r.winner} becomes L1 at {dict(r.ranking)[r.winner]:.2f} Cr, "
                f"{w} falls to {dict(r.ranking)[w]:.2f} Cr")
    delta = dict(r.ranking)[w] - base_npv[w]
    return (f"{w} stays L1; its lifetime NPV moves {delta:+.2f} Cr ({delta / base_npv[w]:+.1%}); "
            f"margin {base.margin_cr:.2f} -> {r.margin_cr:.2f} Cr")


def _year_one_finding(model: EngineModel, histories: dict, lifetime_winner: str) -> str:
    r = evaluate(model, histories)
    first12 = {}
    for n, v in r["suppliers"].items():
        first12[n] = _first_months(v, r["start"], 12)
    l1 = min(first12, key=first12.get)
    rows = ", ".join(f"{n} {x / CRORE:.2f} Cr" for n, x in sorted(first12.items(), key=lambda x: x[1]))
    same = "the same as" if l1 == lifetime_winner else "DIFFERENT from"
    return f"tender metric (first 12 months of operation): L1 = {l1} ({rows}); {same} the lifetime winner {lifetime_winner}"


def _first_months(sup_result: dict, start: str, n: int) -> float:
    """Escalated cost of the first n months, from the yearly totals (months in the first calendar year counted
    exactly, the rest pro rata of the next year)."""
    years = sorted(sup_result["yearly"])
    m0 = int(start[5:7])
    in_first = 13 - m0
    first = sup_result["yearly"][years[0]]["tco_esc"]
    rest = n - in_first
    nxt = sup_result["yearly"][years[1]]["tco_esc"] * rest / 12 if rest > 0 and len(years) > 1 else 0.0
    return first + nxt


def summary(v: Verdict) -> str:
    """One deterministic paragraph (the narrator rewrites it in plain words; it may not add numbers)."""
    b = v.baseline
    parts = [f"Baseline: {b.winner} is L1 at {dict(b.ranking)[b.winner]:.2f} Cr (margin {b.margin_cr:.2f} Cr)."]
    for p in v.challenges:
        if p.status == "rejected":
            continue
        parts.append(f"[{p.status}] {p.challenge_id} ({p.target}: {p.original_value} -> {p.corrected_value}): {p.effect}.")
    parts.append(f"Verdict: {v.status}{' (contested)' if v.contested else ''}; final winner {v.final_winner}.")
    return " ".join(parts)


R6. agent/redseal/prompts.py

Instructions of the two challengers and the narrator (generic: any tender).

[python]
"""prompts.py - the instructions of RedSeal's AI sub-agents (generic: any tender, any product).

The output shape is each agent's output_schema (schemas.py). ADK fills {name} from session state;
never write any other literal {word} in these texts.
"""

AUDITOR = """\
You are a RedSeal red-team auditor. Your job is to DISPROVE the recommended award of a public tender.
Do not accept any value at face value. You never compute a total or a ranking: a deterministic engine
re-runs every correction you propose and decides whether it matters.
So every challenge must be a concrete numeric correction with verbatim evidence; a challenge
without printed evidence is worthless
and will be rejected. Report evidence AGAINST your own challenge too - hiding it gets the whole
challenge rejected. When you find nothing wrong, say what you checked.
"""

EXTRACTION = AUDITOR + """
TASK - re-read the documents and find values the cost model got WRONG.

The documents are in this conversation, each after a header '--- DOCUMENT (<whose>, <kind>): <file> ---'.

Baseline award (computed by the engine):
{baseline_text}

The values the cost model holds, per bidder (parameter id = value, source):
{model_values}

What TrueCost recorded for each bidder's priced terms (figure, amount in words, quote):
{extracted_terms}

For EVERY bidder, re-read its priced rate, its escalation formula and
the tender's rules about prices:
X1. FIGURE vs WORDS: when a price is printed both as a figure and in
words and they disagree, that is a
    challenge (kind 'figure_vs_words'): extracted = the figure the
    model holds, corrected = the amount in
    words, amount_in_words = the words exactly as printed. Cite the
    bid row in evidence_for AND every
    tender clause that says which one prevails: a clause that favours
    the words goes in evidence_for, a
    clause that favours the figure or the lower amount goes in
    evidence_against.
X2. MISREAD: the document prints a different value than the model
holds (a digit, a decimal, a unit).
X3. WRONG WEIGHT: the model's escalation weight / fixed share differs
from the formula THE BID prints.
    A bid formula that differs from the tender's model formula is NOT
    a misread - it is the bidder's
    offer (a commercial deviation for the buyer to accept or reject),
    so never 'correct' a bid's weights
    to the tender's.
X4. WRONG TERM: the model priced a different item / option / case
than the bid's priced offer.
Use only parameter ids from the list above. Quote the printed row
exactly (cells may be joined with ' | ').
"""

ASSUMPTION = AUDITOR + """
TASK - challenge the EVALUATION BASIS: the settings the cost model
was evaluated with.

The tender documents are in this conversation, each after a header
'--- DOCUMENT (TENDER / RFP): <file> ---'.

Baseline award (computed by the engine):
{baseline_text}

Settings the cost model used (and where each came from):
{model_settings}

Company policy (the company's defaults - these are what you are
auditing):
{policy_text}

The buyer's evaluation rules (rule_source 'buyer_rules'):
{rfp_basis_text}

Find every setting that departs from the governing rule:
A1. discount_rate, index_window: compare with the buyer's evaluation
rules; if they differ, challenge with
    rule_source 'buyer_rules', should_be = the rule's value (discount
    as a fraction, index window as the
    number of points), rule_quote = the rule as given.
A2. contract_months, base_year: compare with what the TENDER prints
(term options, the index base date);
    challenge only when the tender clearly prescribes a different
    value; quote the clause verbatim with
    rule_source 'tender' and rule_document = the tender file name. A
    firm term with an optional extension
    IS a challenge when the model includes the extension: should_be =
    the firm term (the extension is
    the authority's option, not a commitment).
A3. award_metric: what does the tender itself award on (e.g. lowest
first-year cost, lowest quoted rate,
    lowest lifetime cost)? If it is not the lifetime cost the model
    ranks on, raise ONE award_metric
    challenge quoting the clause (should_be = 'year_one' for a
    first-year metric, otherwise the metric
    in a few words).
Never invent a rule: a buyer rule must be one given above; a tender
rule must be printed in the tender.
"""

NARRATOR = """\
You are the RedSeal narrator. You explain a finished audit to a
procurement committee in plain words.
You do NOT compute anything and you may NOT introduce any number:
every number you write must appear in
the proof below, written the same way. Prefer words over numbers when
in doubt.

THE PROOF (computed by the deterministic engine and prover):
{proof_text}

Write:
- headline: one sentence - the verdict and why.
- findings: one sentence per non-rejected challenge, in order of
impact: what was wrong, what the engine
proved it changes. Say 'contested' plainly when the tender itself
is ambiguous and quote both sides in
words. Mention the tender's own award metric when it differs from
the lifetime winner.
- recommendation: two or three sentences - what the buyer must
resolve or confirm before signing.
"""


R7. agent/redseal/agent.py

The agent tree: load_case -> ParallelAgent(extraction_challenger, assumption_challenger) -> prover -> narrator (+ number check).

[python]
"""agent.py - the RedSeal agent tree: AI challengers propose, Python proves.

root_agent = SequentialAgent "redseal"
├── load_case BaseAgent engine baseline + the facts the challengers need -> state
├── ParallelAgent "challengers"
│   ├── extraction_challenger LlmAgent re-reads every bid (+ tender rules) -> state['extraction']
│   └── assumption_challenger LlmAgent reads the tender + policy + buyer rules -> state['assumptions']
├── prover BaseAgent verify, engine re-runs, flip thresholds, sensitivity, verdict -> state['verdict'] (NO model call)
└── narrator LlmAgent plain-words story from the proof only -> state['narrative'] (Python rejects any number not in the proof; the verdict stands without it)

One session per tender. The user message holds every document; each challenger sees only what it needs (only_documents from the TrueCost doc_reader).
"""

import json
import re
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from pydantic import PrivateAttr

from engine import award, evaluate, load_case
from engine.model import EngineModel

from ..truecost.doc_reader import Case, only_documents, read_pdf_text
from ..truecost.settings import CONFIG_DIR, MODEL, OUTPUT_DIR, apply_vertex_env, generate_config
from . import prompts
from .prover import prove
from .schemas import AssumptionChallengeRecord, ExtractionChallengeRecord, Narrative, Verdict

apply_vertex_env()          # Vertex project / location for every model call


def _read_json(path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


# ---------------------------------------------------------------------------
# 1. load_case: engine baseline + facts for the prompts
# ---------------------------------------------------------------------------


class LoadCase(BaseAgent):
    case_id: str
    output: str = ""        # data/output/<output>; default = the case's rfq_id
    _model: EngineModel | None = PrivateAttr(default=None)
    _histories: dict = PrivateAttr(default_factory=dict)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        case = Case.load(self.case_id)
        out = OUTPUT_DIR / (self.output or case.rfq_id)
        policy = _read_json(CONFIG_DIR / "buyer_policy.json")
        basis = _read_json(CONFIG_DIR / "rfp_basis.json")
        model, histories = load_case(out, policy)
        base = award(evaluate(model, histories))

        values, terms = [], []
        for name, sup in model.suppliers.items():
            values.append(f"{name}: " + "; ".join(f"{k} = {p.value} ({p.source})" for k, p in sup.parameters.items()))
            com = _read_json(out / "suppliers" / name / "commercial.json")
            for t in com.get("terms", []):
                if t.get("kind") == "unit_rate":
                    terms.append(f"{name}: {t.get('amount')} {t.get('unit', '')} | words: {t.get('amount_in_words', '')} | "
                                 f"quote: {t['evidence']['quote']} ({t['evidence']['document']} p.{t['evidence'].get('page', '')})")

        settings = [f"{k} = {p.value} ({p.source})" for k, p in model.parameters.items()]
        settings += [f"index {s}: {i.method} {i.years}" for s, i in model.indices.items()]
        settings.append(f"monthly rate method: {model.monthly_rate_method}; award ranks on lifetime escalated NPV")

        delta = {
            "rfq_id": case.rfq_id, "country": case.country,
            "baseline_text": f"winner {base.winner}, margin {base.margin_cr:.2f} Cr; ranking: " +
                             ", ".join(f"{n} {v:.2f} Cr" for n, v in base.ranking),
            "model_values": "\n".join(values), "extracted_terms": "\n".join(terms) or "(none)",
            "model_settings": "\n".join(settings),
            "policy_text": "\n".join(f"{k}: {v}" for k, v in policy.items() if not k.startswith("_")),
            "rfp_basis_text": "\n".join(f"{k}: {v}" for k, v in basis.items() if not k.startswith("_"))
        }
        yield Event(author=self.name, invocation_id=ctx.invocation_id,
                    content=types.Content(role="model", parts=[types.Part(text=delta["baseline_text"])]),
                    actions=EventActions(state_delta=delta))


# ---------------------------------------------------------------------------
# 2. challengers
# ---------------------------------------------------------------------------


def make_extraction_challenger() -> LlmAgent:
    """Sees the tender and EVERY bid (it audits all bidders), so no document filter."""
    return LlmAgent(
        name="extraction_challenger", model=MODEL,
        description="Re-reads every bid adversarially and proposes numeric corrections with evidence.",
        instruction=prompts.EXTRACTION,
        output_schema=ExtractionChallengeRecord,
        output_key="extraction",
        generate_content_config=generate_config(),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True
    )


def make_assumption_challenger() -> LlmAgent:
    return LlmAgent(
        name="assumption_challenger", model=MODEL,
        description="Challenges the evaluation basis against the tender and the buyer's rules.",
        instruction=prompts.ASSUMPTION,
        output_schema=AssumptionChallengeRecord,
        output_key="assumptions",
        before_model_callback=only_documents(tender=True),
        generate_content_config=generate_config(),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True
    )


# ---------------------------------------------------------------------------
# 3. prover (no AI)
# ---------------------------------------------------------------------------


class Prover(BaseAgent):
    case_id: str
    output: str = ""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        st = ctx.session.state
        case = Case.load(self.case_id)
        out = OUTPUT_DIR / (self.output or case.rfq_id)
        policy = _read_json(CONFIG_DIR / "buyer_policy.json")
        basis = _read_json(CONFIG_DIR / "rfp_basis.json")
        model, histories = load_case(out, policy)
        documents = {d.path.name: read_pdf_text(d.path) for d in case.documents}
        tender = "\n".join(t for d, t in zip(case.documents, documents.values()) if not d.supplier)
        v = prove(model, histories, st.get("extraction"), st.get("assumptions"), documents, basis, policy, tender)
        yield Event(author=self.name, invocation_id=ctx.invocation_id,
                    content=types.Content(role="model", parts=[types.Part(text=v.summary)]),
                    actions=EventActions(state_delta={"verdict": v.model_dump(), "proof_text": v.summary + "\n" + _proof_details(v)}))


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


# ---------------------------------------------------------------------------
# 4. narrator (+ number check)
# ---------------------------------------------------------------------------


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
        name="narrator", model=MODEL,
        description="Explains the proven verdict in plain words; may not introduce numbers.",
        instruction=prompts.NARRATOR, output_schema=Narrative,
        output_key="narrative",
        include_contents="none",
        after_agent_callback=_check_narrative,
        generate_content_config=generate_config(),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True
    )


# ---------------------------------------------------------------------------
# the tree
# ---------------------------------------------------------------------------


def build_root(case_id: str, output: str = "") -> SequentialAgent:
    """output: audit data/output/<output> instead of data/output/<rfq_id> (same documents)."""
    return SequentialAgent(
        name="redseal",
        description="RedSeal: try to disprove the award; prove every challenge with the engine.",
        sub_agents=[LoadCase(name="load_case", case_id=case_id, output=output),
                    ParallelAgent(name="challengers",
                                  description="Both challengers at once.",
                                  sub_agents=
                                  [make_extraction_challenger(),
                                   make_assumption_challenger()]),
                    Prover(name="prover", case_id=case_id, output=output),
                    make_narrator()]
    )


R8. agent/redseal/runner.py

CLI: runs the tree, writes proof_pack.json, prints the verdict.

[python]
"""runner.py - run RedSeal on a tender TrueCost has already built, and write the Proof Pack.

python -m agent.redseal.runner IN-CRUT-EBUS
python -m agent.redseal.runner IN-CRUT-EBUS --output IN-CRUT-EBUS-ROBUST # audit a variant cost model

Needs data/output/<rfq_id>/cost_model.json (+ frozen_indices, suppliers/*) from TrueCost. Writes
data/output/<rfq_id>/proof_pack.json and prints the verdict.
"""

import argparse
import asyncio
import json
import logging
import time

from google.adk.runners import InMemoryRunner
from google.genai import types

from ..truecost.doc_reader import Case, pack
from ..truecost.settings import OUTPUT_DIR
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
        if e.is_final_response():
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
    print(f"\n{'=' * 78}\nREDSEAL VERDICT {p['rfq_id']}: {p['status']}{' (contested)' if p['contested'] else ''}\n"
          f"     {p['original_winner']} -> {p['final_winner']}\n{'=' * 78}")
    b = p["baseline"]
    print(" baseline: " + ", ".join(f"{n} {v:.2f} Cr" for n, v in b["ranking"]) + f" (margin {b['margin_cr']:.2f} Cr)")
    for c in p["challenges"]:
        print(f"\n [{c['status']:9}] {c['challenge_id']} ({c['target']}: {c['original_value']} -> {c['corrected_value']})")
        if c["effect"]:
            print(f"                     {c['effect']}")
        print(f"                     check: {c['checks'][-1]}")
    print("\n flip thresholds:")
    for t in p["flip_thresholds"]:
        print(f"    {t['supplier']:11} {t['param']} {t['current']:g} -> {t['threshold']:.2f} ({t['change_pct']:+.1f} %) "
              f"vs {t['against']}{' PLAUSIBLE' if t['plausible'] else ''}")
    print(" sensitivity:")
    for r in p["sensitivity"]:
        print(f"    {r['driver']:14} {r['low_label']:>11}: {r['winner_low']:10} {r['high_label']:>11}: {r['winner_high']:10}"
              f"    {['', 'FLIPS'][r['flips']]}")
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
    parser.add_argument("case", help="RFQ id (TrueCost must have run for it)")
    parser.add_argument("--output", default="", help="audit data/output/<OUTPUT> instead of data/output/<rfq_id>")
    args = parser.parse_args()
    asyncio.run(run(args.case, args.output))
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)


if __name__ == "__main__":
    main()


R9. tests/test_redseal.py

19 tests, no model calls: words parser, verification (incl. invented evidence rejected), exact flip threshold, the three verdicts, determinism, narrator number check.

[python]
"""RedSeal tests - the deterministic parts only (no model calls):
words parser, challenge verification, engine proof, flip thresholds, the three verdicts, the narrator's
number check.
"""

import pytest

from agent.redseal.agent import numbers_not_in
from agent.redseal.prover import flip_thresholds, prove
from agent.redseal.words import words_to_number
from engine import award, evaluate
from engine.model import Driver, EngineModel, Escalator, IndexSpec, Line, Param, Supplier, Term


# ---------------------------------------------------------------------------
# words -> number
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text, expect", [
    ("Rupees Sixty Six only per kilometre", 66.0),
    ("Rupees Sixty Four and Fifty paise per kilometre", 64.5),
    ("Rupees Sixty Three and Five paise", 63.05),
    ("Rupees Two Hundred and Five only", 205.0),
    ("Rupees One Crore Twenty Lakh", 12_000_000.0),
    ("One Lakh Twenty Five Thousand Three Hundred", 125_300.0),
    ("no number here", None),
])
def test_words_to_number(text, expect):
    assert words_to_number(text) == expect


# ---------------------------------------------------------------------------
# a three-bidder model: A wins on lifetime, B is the cheapest sticker
# ---------------------------------------------------------------------------


def model(rate_a=63.0) -> EngineModel:
    def sup(name, rate, fixed):
        return Supplier(name=name, parameters={"unit_rate": Param(value=rate, source=f"term:{name}")},
                        drivers={"d": Driver(id="d", per_month=1000)},
                        escalators=[Escalator(id="e", kind="index_formula", fixed=fixed,
                                              terms=[Term(series="IDX", weight=1 - fixed)],
                                              first="p:start+6", every="c:6", source="formula:f")],
                        lines=[Line(id="L", factors=["p:unit_rate", "d:d"], start="p:start", escalators=["e"])])
    return EngineModel(rfq_id="T", horizon_start="p:start", horizon_months="c:144", base_year="c:2025",
                       discount_rate="p:disc", monthly_rate_method="compound",
                       parameters={"start": Param(value="2026-01", kind="month", source="decision:start"),
                                   "disc": Param(value=0.12, source="policy:disc")},
                       indices={"IDX": IndexSpec(series="IDX", method="mean_yoy", years=3)},
                       suppliers={"A": sup("A", rate_a, 0.64), "B": sup("B", 61.0, 0.30), "C": sup("C", 66.0, 0.55)})


H = {"IDX": ((2021, 100.0), (2022, 104.0), (2023, 108.5), (2024, 112.0), (2025, 116.0))}  # ~3.5 %/yr
DOCS = {"bid_A.pdf": "Per-kilometre rate | Rs 63.00 / km | (rate in words) Rupees Sixty Six only per kilometre",
        "tender.pdf": "if the Authority finds a discrepancy between words and figures quoted, then the amount "
                      "written in words shall prevail. ... in the event of discrepancy in numeric and "
                      "alphabetical manner, the lower of both shall be considered."}
TENDER = DOCS["tender.pdf"]
BASIS = {"discount_rate": 0.10, "index_method": {"method": "mean_yoy", "years": 5}}


def words_challenge(against=True, words="Rupees Sixty Six only per kilometre", corrected=66.0, quote=None):
    c = {"challenge_id": "a_words", "supplier": "A", "param": "unit_rate", "kind": "figure_vs_words",
         "extracted_value": 63.0, "corrected_value": corrected, "amount_in_words": words,
         "evidence_for": [{"document": "bid_A.pdf", "page": "1",
                           "quote": quote or "Rs 63.00 / km | Rupees Sixty Six only per kilometre"}],
         "reasoning": "figure and words disagree"}
    if against:
        c["evidence_against"] = [{"document": "tender.pdf", "page": "42",
                                  "quote": "the lower of both shall be considered"}]
    return {"challenges": [c]}


def test_baseline_shape():
    a = award(evaluate(model(), H))
    assert award(evaluate(model(), H), "tco").winner == "B"  # cheapest sticker
    assert a.winner == "A"                                    # lifetime winner


def test_verified_flip_is_overturned():
    v = prove(model(), H, words_challenge(against=False), {}, DOCS, BASIS, {}, TENDER)
    c = v.challenges[0]
    assert c.status == "verified" and c.rerun.winner == "B"
    assert v.status == "OVERTURNED" and not v.contested and v.final_winner == "B"
    assert any("parses to 66" in x for x in c.checks)


def test_contested_flip():
    v = prove(model(), H, words_challenge(against=True), {}, DOCS, BASIS, {}, TENDER)
    assert v.challenges[0].status == "contested"
    assert v.status == "OVERTURNED" and v.contested


@pytest.mark.parametrize("kw, reason", [
    ({"quote": "Rs 58.00 / km"}, "quote not found"),  # invented evidence
    ({"words": "Rupees Sixty Five only", "corrected": 66.0}, "parses to 65"),  # words do not say 66
])
def test_unverifiable_challenges_are_rejected(kw, reason):
    v = prove(model(), H, words_challenge(against=False, **kw), {}, DOCS, BASIS, {}, TENDER)
    assert v.challenges[0].status == "rejected" and reason in v.challenges[0].checks[-1]
    assert v.challenges[0].rerun is None and v.final_winner == "A"


def test_wrong_extracted_value_rejected():
    ch = words_challenge(against=False)
    ch["challenges"][0]["extracted_value"] = 62.0
    v = prove(model(), H, ch, {}, DOCS, BASIS, {}, TENDER)
    assert v.challenges[0].status == "rejected"


def test_assumption_challenges_and_combined():
    asm = {"challenges": [
        {"challenge_id": "d", "setting": "discount_rate", "used_value": "0.12", "should_be": "0.10",
         "rule_source": "buyer_rules", "rule_quote": "discount 10 %", "reasoning": "x"},
        {"challenge_id": "i", "setting": "index_window", "used_value": "3", "should_be": "5",
         "rule_source": "buyer_rules", "rule_quote": "mean_yoy 5", "reasoning": "x"},
        {"challenge_id": "t", "setting": "contract_months", "used_value": "144", "should_be": "120",
         "rule_source": "tender", "rule_quote": "invented clause not in the tender", "reasoning": "x"}]}
    v = prove(model(), H, {}, asm, DOCS, BASIS, {}, TENDER)
    by = {c.challenge_id: c for c in v.challenges}
    assert by["d"].status == "verified" and by["d"].overrides == {"discount_rate": 0.10}
    assert by["t"].status == "rejected"                                 # tender clause not printed
    assert by["all_assumptions"].rerun is not None
    assert dict(by["d"].rerun.ranking)["A"] > dict(v.baseline.ranking)["A"]  # lower discount -> higher NPV


def test_flip_threshold_is_exact():
    m = model()
    base = award(evaluate(m, H))
    t = next(x for x in flip_thresholds(m, H, base) if x.supplier == "A")
    assert award(evaluate(m, H, {"A.unit_rate": t.threshold - 0.01})).winner == "A"
    assert award(evaluate(m, H, {"A.unit_rate": t.threshold + 0.01})).winner == "B"


def test_certified_robust_when_nothing_moves_it():
    v = prove(model(rate_a=50.0), H, {}, {}, DOCS, BASIS, {}, TENDER)
    assert v.status == "CERTIFIED_ROBUST" and not v.fragile


def test_understated_when_cost_moves_but_winner_holds():
    asm = {"challenges": [{"challenge_id": "d", "setting": "discount_rate", "used_value": "0.12",
                           "should_be": "0.10", "rule_source": "buyer_rules", "rule_quote": "x", "reasoning": "x"}]}
    v = prove(model(rate_a=50.0), H, {}, asm, DOCS, BASIS, {}, TENDER)
    assert v.status == "UNDERSTATED" and v.final_winner == "A"


def test_deterministic():
    a = prove(model(), H, words_challenge(), {}, DOCS, BASIS, {}, TENDER)
    b = prove(model(), H, words_challenge(), {}, DOCS, BASIS, {}, TENDER)
    assert a.model_dump() == b.model_dump()


def test_narrator_number_check():
    proof = "MetroLink becomes L1 at 562.64 Cr; rate 63 -> 66"
    assert numbers_not_in("MetroLink wins at 562.64 Cr after 63 becomes 66", proof) == []
    assert numbers_not_in("GreenMetro saves 14 Cr", proof) == ["14"]


2. Verification (run once, in order)

[bash]
python -m pytest tests -q
# expect: 36 passed  (17 engine + 19 RedSeal)

python -m agent.redseal.runner IN-CRUT-EBUS    # about 2 minutes


Expected (server run on the regenerated bids, start 2026-04, base year 2025, 144 months, 12 %):

[text]
==============================================================================
REDSEAL VERDICT IN-CRUT-EBUS: OVERTURNED (contested)    GreenMetro -> MetroLink
==============================================================================
 baseline: GreenMetro 549.02 Cr, MetroLink 562.64 Cr, UrbanDrive 575.23 Cr (margin 13.61 Cr)

 [contested] ..._figure_vs_words (GreenMetro.unit_rate: 63 -> 66)
                     award flips: MetroLink becomes L1 at 562.64 Cr, GreenMetro falls to 575.17 Cr
                     check: 1 printed clause(s) support the extracted value -> contested
 [verified ] discount_rate: 0.12 -> 0.1                    GreenMetro stays L1; +50.58 Cr (+9.2%)
 [verified ] index_window: 3 -> 5                          GreenMetro stays L1; +37.92 Cr (+6.9%)
 [verified ] contract_months: 144 -> 120                   GreenMetro stays L1; -50.20 Cr; margin 13.61 -> 8.65 Cr
 [finding  ] award_metric -> year_one                      tender L1 (first 12 months) = MetroLink - DIFFERENT from lifetime winner
 [verified ] all_assumptions                               GreenMetro stays L1; +22.33 Cr; margin 13.61 -> 21.68 Cr

 flip thresholds:
    GreenMetro  unit_rate   63 -> 64.56 (+2.5 %) vs MetroLink PLAUSIBLE
 sensitivity:
    discount rate 8 %     : GreenMetro MetroLink    FLIPS
    index growth  -2 pts/yr: GreenMetro MetroLink    FLIPS

The challengers are LLMs, so challenge ids and wording vary per run; the proven numbers and the verdict are
deterministic for the same challenges. Check `proof_pack.json` -> `narrative_check.ok` is `true`.

CERTIFIED_ROBUST (spec 9.4) - proven in `tests/test_redseal.py::test_certified_robust_when_nothing_moves_it`
(a bidder clearly cheapest, nothing plausible moves it). The same rule applied to the real case:
```python
import json

from agent.redseal.prover import prove
from engine import load_case

m, h = load_case("data/output/IN-CRUT-EBUS", json.load(open("config/buyer_policy.json")))
gm = m.suppliers["GreenMetro"]
gm.parameters["unit_rate"] = gm.parameters["unit_rate"].model_copy(update={"value": 55.0})
print(
    prove(
        m,
        h,
        {},
        {},
        {},
        json.load(open("config/rfp_basis.json")),
        {},
        "",
    ).status
)  # CERTIFIED_ROBUST


To audit a variant cost model against the same documents: python -m agent.redseal.runner IN-CRUT-EBUS --output <folder>.

3. What the demo shows (3 acts)

act	agent	proof
1. Escalation flip	TrueCost + engine	MetroLink is the cheapest sticker; GreenMetro wins the 12-year lifetime NPV by 13.61 Cr
2. OVERTURNED (contested)	RedSeal extraction challenger	GreenMetro's figure 63.00 vs words "Sixty Six"; the tender says words prevail (ITB 20.vii) but ALSO "the lower of both shall be considered" (p.42). At 66.00 MetroLink wins. RedSeal proves the flip AND flags that the authority must resolve its own contradictory clauses before signing.
3. UNDERSTATED + findings	RedSeal assumption challenger	buyer rules (10 %, 5-point index) raise every NPV; the firm 10-year term cuts the margin to 8.65 Cr; the tender's own year-one metric picks MetroLink

4. Notes for the builder

⚬ Run TrueCost first (python -m agent.truecost.runner IN-CRUT-EBUS): RedSeal audits data/output/<rfq>/.

⚬ RedSeal calls apply_vertex_env() in agent/redseal/agent.py (without it: "No API key was provided").

⚬ The extraction challenger sees EVERY bid (it audits all bidders); the assumption challenger sees only the tender (only_documents(tender=True)); the narrator sees no documents (include_contents="none").

⚬ Escalation weights are not challengeable as parameters: the engine's escalator mirrors the bid's printed formula. A bid formula that differs from the tender's model formula is a commercial deviation, not a misread (the prompt says so; the prover rejects challenges on parameters no cost line uses).

⚬ config/rfp_basis.json is the BUYER'S rules, not the tender's. Change it there, not in code.

Backend status

With this file the backend is complete: TrueCost (extraction) -> engine (deterministic award) -> RedSeal (adversarial audit + proof pack). Run end to end:

[bash]
python -m agent.truecost.runner IN-CRUT-EBUS --set rfq.contract.start=2026-04 --set rfq.index.base_year=2025 --set rfq.contract.months=144
python -m engine.cli IN-CRUT-EBUS
python -m agent.redseal.runner IN-CRUT-EBUS
python -m pytest tests -q


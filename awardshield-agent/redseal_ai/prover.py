"""prover.py - RedSeal's deterministic core: VERIFY each challenge, PROVE it with the engine, decide the
verdict by fixed rules. No model calls. Same challenges + same cost model -> same verdict.

    verdict = prove(model, histories, extraction, assumptions, documents, rfp_basis, policy, tender_text)

1. verify          a quote must be printed in the cited document; a figure-vs-words claim must parse
                   (words_to_number) to the corrected value; an assumption must cite a rule found in the
                   tender text or the buyer's rules. Unverifiable -> 'rejected' (reported, never used).
                   A verified challenge whose evidence_against cites a printed clause -> 'contested'.
2. prove           every verified / contested challenge -> engine overrides -> rerun.
3. counterfactual  the exact flip threshold of every bidder's priced rate against the winner (NPV is
                   linear in the rate).
4. sensitivity     sweep discount, index growth, demand, contract term; does the winner ever change?
5. verdict         OVERTURNED: a verified/contested challenge changes the winner.
                   UNDERSTATED: winner unchanged, but the award is fragile (a plausible flip threshold or a
                   sensitivity flip) or a challenge raises the winner's NPV > 1 % / cuts the margin > 1 %.
                   CERTIFIED_ROBUST: nothing flips it, nothing plausible would, and no challenge moves the
                   winner's cost materially.
"""

import re

from truecost_ai.engine import award, evaluate
from truecost_ai.engine.indices import rate_for
from truecost_ai.engine.model import EngineModel
from truecost_ai.engine.rank import CRORE, Award

from .schemas import (AssumptionChallengeRecord, ExtractionChallengeRecord, FlipThreshold, ProvenChallenge,
                      Rerun, SensitivityRow, Verdict)
from .words import words_to_number

UNDERSTATED_PCT = 1.0  # winner's NPV rises by more than this % -> material
PLAUSIBLE_BAND = 0.05  # a flip within +-5 % of a priced rate counts as plausible (fragile award)
TOLERANCE = 0.005  # numbers compared to this absolute tolerance


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _printed(quote: str, text: str) -> bool:
    """A quote counts as printed if its words appear in order in the text (cells joined by '|' or '...'
    are checked piece by piece)."""
    pieces = [p for p in re.split(r"\s*(?:\||\.\.\.|…|\.)\s*", quote) if p.strip()]
    t = _norm(text)
    return bool(pieces) and all(_norm(p)[:80] in t for p in pieces)


def _rerun(model: EngineModel, histories: dict, overrides: dict, label: str) -> Rerun:
    a = award(evaluate(model, histories, overrides), label=label)
    return Rerun(label=label, ranking=a.ranking, winner=a.winner, margin_cr=a.margin_cr, margin_pct=a.margin_pct)


def _priced_param(model: EngineModel, supplier: str) -> str | None:
    """The supplier's priced rate: the first p: factor of its first line that is a supplier parameter."""
    sup = model.suppliers[supplier]
    for ln in sup.lines:
        for f in ln.factors:
            if f.startswith("p:") and f[2:] in sup.parameters:
                return f[2:]
    return None


def _num(text, default=None):
    m = re.search(r"-?\d+(?:\.\d+)?", str(text))
    if not m:
        return default
    v = float(m.group())
    return v / 100 if "%" in str(text) and v > 1 else v


# -----------------------------------------------------------------------------
# 1. verify
# -----------------------------------------------------------------------------

def verify_extraction(c, model: EngineModel, documents: dict[str, str]) -> tuple[str, list[str]]:
    checks = []
    if c.supplier not in model.suppliers:
        return "rejected", [f"{c.supplier} is not a bidder of this case"]
    sup = model.suppliers[c.supplier]
    if c.param not in sup.parameters:
        return "rejected", [f"{c.param} is not a parameter of {c.supplier}: {sorted(sup.parameters)}"]
    try:
        held = float(sup.parameters[c.param].value)
    except (TypeError, ValueError):
        return "rejected", [f"{c.param} is not a number ({sup.parameters[c.param].value})"]
    if abs(held - c.extracted_value) > TOLERANCE:
        return "rejected", [f"the model holds {held:g}, not the claimed {c.extracted_value:g}"]
    checks.append(f"the cost model holds {c.param} = {held:g}")
    used = any(f in (f"p:{c.param}", f"1-p:{c.param}") for ln in sup.lines for f in ln.factors)
    if not used:
        return "rejected", checks + [f"{c.param} is not used by any cost line - changing it cannot move the award "
                                     f"(escalation weights live in the escalator, which mirrors the bid's printed formula)"]
    if abs(c.corrected_value - held) <= TOLERANCE:
        return "rejected", checks + ["the corrected value equals the extracted value - nothing to correct"]
    if not c.evidence_for:
        return "rejected", checks + ["no evidence cited"]
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
        want = rfp_basis.get("discount_rate") if c.rule_source == "buyer_rules" else _num(c.should_be)
        if want is None:
            return "rejected", checks + ["no discount rate in the rule"], {}
        want = float(want)
        if abs(want - _num(c.should_be, want)) > TOLERANCE:
            return "rejected", checks + [f"should_be {c.should_be} does not match the rule ({want:g})"], {}
        return "verified", checks + [f"discount rate {c.used_value} -> {want:g}"], {"discount_rate": want}
    if c.setting == "index_window":
        rule = rfp_basis.get("index_method") or {}
        years = int(rule.get("years") or 0) if c.rule_source == "buyer_rules" else int(_num(c.should_be) or 0)
        if not years:
            return "rejected", checks + ["no index window in the rule"], {}
        spec = {"method": rule.get("method", "mean_yoy"), "years": years}
        return "verified", checks + [f"index window -> {years} years"], {"__index_all__": spec}
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


# -----------------------------------------------------------------------------
# 2-4. prove, counterfactual, sensitivity
# -----------------------------------------------------------------------------

def _expand(overrides: dict, model: EngineModel) -> dict:
    ov = dict(overrides)
    if spec := ov.pop("__index_all__", None):
        ov.update({f"index:{s}": spec for s in model.indices})
    return ov


def flip_thresholds(model: EngineModel, histories: dict, base: Award) -> list[FlipThreshold]:
    """For each bidder: the priced rate at which it swaps places with the winner (or, for the winner, with
    the runner-up). NPV is linear in the rate, so threshold = rate x NPV_other / NPV_self."""
    npv = dict(base.ranking)
    out = []
    for name, _ in base.ranking:
        param = _priced_param(model, name)
        other = base.runner_up if name == base.winner else base.winner
        if param is None or not other:
            continue
        rate = float(model.suppliers[name].parameters[param].value)
        threshold = rate * npv[other] / npv[name]
        change = threshold / rate - 1
        out.append(FlipThreshold(supplier=name, param=param, current=rate, threshold=round(threshold, 4),
                                 change_pct=round(change * 100, 2), against=other,
                                 plausible=abs(change) <= PLAUSIBLE_BAND))
    return out


def sensitivity(model: EngineModel, histories: dict) -> list[SensitivityRow]:
    base_rate = {}
    for s, spec in model.indices.items():
        try:
            base_rate[s] = 0.0 if spec.method == "path" else rate_for(histories.get(s, ()), spec.method,
                                                                      spec.rate, spec.years)
        except ValueError:
            base_rate[s] = 0.0
    idx = lambda d: {f"index:{s}": {"method": "fixed", "rate": r + d, "years": None} for s, r in base_rate.items()}
    sweeps = [("discount rate", "8 %", {"discount_rate": 0.08}, "14 %", {"discount_rate": 0.14}),
              ("index growth", "-2 pts/yr", idx(-0.02), "+2 pts/yr", idx(0.02)),
              ("demand", "-20 %", {"driver_scale": 0.8}, "+20 %", {"driver_scale": 1.2}),
              ("contract term", "120 months", {"horizon_months": 120}, "144 months", {"horizon_months": 144})]
    base_w = award(evaluate(model, histories)).winner
    rows = []
    for driver, lo_l, lo, hi_l, hi in sweeps:
        a, b = award(evaluate(model, histories, lo)), award(evaluate(model, histories, hi))
        swing = dict(b.ranking)[b.winner] - dict(a.ranking)[a.winner]
        rows.append(SensitivityRow(driver=driver, low_label=lo_l, high_label=hi_l, winner_low=a.winner,
                                   winner_high=b.winner, swing_cr=round(swing, 2),
                                   flips=(a.winner != base_w or b.winner != base_w)))
    return rows


# -----------------------------------------------------------------------------
# 5. the whole proof
# -----------------------------------------------------------------------------

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
    verified_assumptions = [p for p in proven if p.agent == "assumption_challenger" and p.status == "verified"]
    if len(verified_assumptions) > 1:
        combined = {k: v for p in verified_assumptions for k, v in p.overrides.items()}
        proven.append(ProvenChallenge(challenge_id="all_assumptions", agent="assumption_challenger", kind="combined",
                                      target="evaluation basis", original_value="company policy",
                                      corrected_value="buyer evaluation rules", status="verified",
                                      checks=["every verified assumption challenge applied together"],
                                      overrides=combined,
                                      rerun=_rerun(model, histories, _expand(combined, model), "all_assumptions")))

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
    elif fragile or understated or shrinks:
        status, final, contested = "UNDERSTATED", baseline.winner, False
    else:
        status, final, contested = "CERTIFIED_ROBUST", baseline.winner, False

    v = Verdict(rfq_id=model.rfp_id, status=status, contested=contested, original_winner=baseline.winner,
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
    first12 = {n: _first_months(v, r["start"], 12) for n, v in r["suppliers"].items() if v.get("yearly")}
    if not first12:
        return "tender metric (first 12 months): no supplier could be evaluated"
    l1 = min(first12, key=first12.get)
    rows = ", ".join(f"{n} {x / CRORE:.2f} Cr" for n, x in sorted(first12.items(), key=lambda x: x[1]))
    same = "the same as" if l1 == lifetime_winner else "DIFFERENT from"
    return f"tender metric (first 12 months of operation): L1 = {l1} ({rows}); {same} the lifetime winner {lifetime_winner}"


def _first_months(sup_result: dict, start: str, n: int) -> float:
    """Escalated cost of the first n months, from the yearly totals (months in the first calendar year counted
    exactly, the rest pro rata of the next year)."""
    years = sorted(sup_result["yearly"])
    in_first = 13 - int(start[5:7])
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

"""RedSeal tests - the deterministic parts only (no model calls): words parser, challenge verification,
engine proof, flip thresholds, the three verdicts, the narrator's number check.
"""

import pytest

from redseal_ai.agent import numbers_not_in
from redseal_ai.prover import flip_thresholds, prove
from redseal_ai.words import words_to_number
from truecost_ai.engine import award, evaluate
from truecost_ai.engine.model import Driver, EngineModel, Escalator, IndexSpec, Line, Param, Supplier, Term


# -----------------------------------------------------------------------------
# words -> number
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# a three-bidder model: A wins on lifetime, B is the cheapest sticker
# -----------------------------------------------------------------------------

def model(rate_a=63.0) -> EngineModel:
    def sup(name, rate, fixed):
        return Supplier(name=name, parameters={"unit_rate": Param(value=rate, source=f"term:{name}")},
                        drivers={"d": Driver(id="d", per_month=1000)},
                        escalators=[Escalator(id="e", kind="index_formula", fixed=fixed,
                                              terms=[Term(series="IDX", weight=1 - fixed)],
                                              first="p:start+6", every="c:6", source="formula:f")],
                        lines=[Line(id="L", factors=["p:unit_rate", "d:d"], start="p:start", escalators=["e"])])
    return EngineModel(rfp_id="T", horizon_start="p:start", horizon_months="c:144", base_year="c:2025",
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
    assert award(evaluate(model(), H), "tco").winner == "B"  # cheapest sticker
    assert award(evaluate(model(), H)).winner == "A"  # lifetime winner


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
    assert by["t"].status == "rejected"  # tender clause not printed
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

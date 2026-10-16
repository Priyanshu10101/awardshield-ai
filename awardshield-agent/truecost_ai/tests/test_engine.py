"""Engine tests: index maths (spec 9.3 numbers), a hand-calculated model, determinism, overrides,
explain == evaluate, ranking. No files, no network, no model calls."""

import pytest

from truecost_ai.engine import award, evaluate, explain_escalator, explain_index, explain_npv, rerun
from truecost_ai.engine.explain import check_consistency
from truecost_ai.engine.indices import levels, rate_for
from truecost_ai.engine.model import Driver, EngineModel, Escalator, IndexSpec, Line, Param, Supplier, Term

CPI = ((2021, 122.025), (2022, 129.225), (2023, 136.4), (2024, 141.5833), (2025, 145.5417))
WPI = ((2021, 131.7), (2022, 142.1), (2023, 140.6), (2024, 141.6), (2025, 144.8167))


# -----------------------------------------------------------------------------------------
# indices
# -----------------------------------------------------------------------------------------
@pytest.mark.parametrize("hist, years, expect",
                         [(CPI, 3, 0.0330), (CPI, 5, 0.0451), (WPI, 3, 0.0149), (WPI, 5, 0.0246)])
def test_mean_yoy_matches_spec(hist, years, expect):
    """spec 9.3: window = last N points (3 points -> 2 yearly changes)."""
    assert rate_for(hist, "mean_yoy", None, years) == pytest.approx(expect, abs=5e-5)


def test_window_changes_the_rate():
    assert rate_for(CPI, "mean_yoy", None, 3) != rate_for(CPI, "mean_yoy", None, 5)


def test_levels_base_year_is_one_and_compounds():
    lv = levels("fixed", (), 2025, range(2024, 2028), rate=0.10)
    assert lv[2025] == 1.0
    assert lv[2027] == pytest.approx(1.21)
    assert lv[2024] == pytest.approx(1 / 1.1)


def test_cagr_and_short_history():
    assert rate_for(CPI, "cagr", None, 5) == pytest.approx((145.5417 / 122.025) ** 0.25 - 1)
    with pytest.raises(ValueError):
        rate_for(((2024, 1.0),), "mean_yoy", None, 3)


# -----------------------------------------------------------------------------------------
# a model small enough to compute by hand
# -----------------------------------------------------------------------------------------
def tiny(rate_a=100.0, rate_b=95.0, fixed_b=0.2) -> EngineModel:
    """Two suppliers, 1 line each: rate x 10 units/month, 24 months from 2026-01, index fixed 10%/yr,
    first adjustment 2026-07 then every 6 months, 12% simple discount."""
    def sup(name, rate, fixed):
        return Supplier(name=name, parameters={"rate": Param(value=rate, source=f"term:{name}")},
                        drivers={"d": Driver(id="d", per_month=10)},
                        escalators=[Escalator(id="e", kind="index_formula", fixed=fixed,
                                              terms=[Term(series="IDX", weight=1 - fixed)],
                                              first="p:start+6", every="c:6", source="formula:f")],
                        lines=[Line(id="L", factors=["p:rate", "d:d"], start="p:start", escalators=["e"])])
    return EngineModel(rfp_id="T", horizon_start="p:start", horizon_months="c:24", base_year="c:2025",
                       discount_rate="c:0.12", monthly_rate_method="simple",
                       parameters={"start": Param(value="2026-01", kind="month", source="decision:start")},
                       indices={"IDX": IndexSpec(series="IDX", method="fixed", years=None, rate=0.10)},
                       suppliers={"A": sup("A", rate_a, 0.5), "B": sup("B", rate_b, fixed_b)})


H = {"IDX": ()}


def test_hand_calculation():
    r = evaluate(tiny(), H)["suppliers"]["A"]
    # factor: 1.0 for 2026-01..06; 0.5+0.5*1.1 = 1.05 for 2026-07..12; 0.5+0.5*1.21 = 1.105 for 2027
    f = [1.0] * 6 + [1.05] * 6 + [1.105] * 12
    cash = [1000 * x for x in f]
    assert r["totals"]["tco"] == pytest.approx(24000)
    assert r["totals"]["tco_esc"] == pytest.approx(sum(cash))
    assert r["npv"]["tco_esc"] == pytest.approx(sum(c / (1 + 0.01) ** (t + 1) for t, c in enumerate(cash)))
    assert r["escalators"]["e"]["by_year"] == {"2026": pytest.approx(1.05), "2027": pytest.approx(1.105)}


def test_deterministic():
    assert evaluate(tiny(), H) == evaluate(tiny(), H)


def test_overrides_do_not_mutate_model():
    m = tiny()
    before = m.model_dump()
    evaluate(m, H, {"rate": 1.0, "discount_rate": 0.05, "index:IDX": {"rate": 0.2}})
    assert m.model_dump() == before


def test_parameter_override_scopes():
    base = evaluate(tiny(), H)["suppliers"]
    both = evaluate(tiny(), H, {"rate": 50.0})["suppliers"]
    only_a = evaluate(tiny(), H, {"A.rate": 50.0})["suppliers"]
    assert both["A"]["npv"]["tco"] == pytest.approx(base["A"]["npv"]["tco"] / 2)
    assert both["B"]["npv"]["tco"] == pytest.approx(base["B"]["npv"]["tco"] * 50 / 95)
    assert only_a["B"]["npv"]["tco"] == pytest.approx(base["B"]["npv"]["tco"])


def test_index_and_discount_overrides_move_npv():
    base = evaluate(tiny(), H)["suppliers"]["A"]["npv"]["tco_esc"]
    assert evaluate(tiny(), H, {"index:IDX": {"rate": 0.0}})["suppliers"]["A"]["npv"]["tco_esc"] < base
    assert evaluate(tiny(), H, {"discount_rate": 0.0})["suppliers"]["A"]["npv"]["tco_esc"] > base


def test_compound_monthly_rate():
    r = evaluate(tiny(), H, {"monthly_rate_method": "compound"})
    assert r["discount"]["monthly"] == pytest.approx(1.12 ** (1 / 12) - 1)


# -----------------------------------------------------------------------------------------
# explain == evaluate
# -----------------------------------------------------------------------------------------
def test_explain_npv_reproduces_evaluate():
    assert check_consistency(tiny(), H)
    assert check_consistency(tiny(), H, {"discount_rate": 0.07, "A.rate": 80.0})


def test_explain_escalator_and_index():
    e = explain_escalator(tiny(), H, "A", "e", 2027)
    assert e["value"] == pytest.approx(1.105) and e["index_year"] == 2027
    assert e["fixed"] + sum(t["contribution"] for t in e["terms"]) == pytest.approx(e["value"])
    i = explain_index(tiny(), H, "IDX", 2027)
    assert i["value"] == pytest.approx(1.21)
    assert explain_npv(tiny(), H, "A")["undiscounted"] == pytest.approx(
        evaluate(tiny(), H)["suppliers"]["A"]["totals"]["tco_esc"])


# -----------------------------------------------------------------------------------------
# award / escalation flip
# -----------------------------------------------------------------------------------------
def test_escalation_flip_and_rerun():
    """B is cheaper on the sticker (99 < 100) but fully indexed; with 10%/yr inflation A wins lifetime."""
    m = tiny(rate_b=99.0, fixed_b=0.0)
    r = evaluate(m, H)
    sticker = award(r, "tco", label="STICKER")
    lifetime = award(r, "tco_esc", label="LIFETIME")
    assert sticker.winner == "B"
    assert lifetime.winner == "A"
    # A's lifetime NPV is linear in its rate: the flip point is where it equals B's
    npv = {n: v["npv"]["tco_esc"] for n, v in r["suppliers"].items()}
    flip = 100.0 * npv["B"] / npv["A"]
    assert rerun(m, H, {"A.rate": flip - 0.01}, "below").winner == "A"
    flipped = rerun(m, H, {"A.rate": flip + 0.01}, "A corrected")
    assert flipped.winner == "B" and flipped.label == "A corrected"


def test_award_skips_incomplete():
    m = tiny()
    m.suppliers["B"].status = "needs_answers"
    a = award(evaluate(m, H))
    assert a.winner == "A" and a.excluded == ["B"] and a.runner_up == ""

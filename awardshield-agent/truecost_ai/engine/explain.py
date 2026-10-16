"""explain.py - how a number was computed, using the SAME functions as evaluate() (so it reproduces
evaluate's numbers exactly). Pure; no files.

    explain_npv(model, histories, supplier, overrides)                  NPV: cash, discount, by year
    explain_escalator(model, histories, supplier, esc_id, year, ov)     factor in a year, term by term
    explain_index(model, histories, series, year, overrides)            rate (method + history) -> level
"""

import numpy as np

from .evaluate import (MONTHLY_RATE, Context, escalator_factor, evaluate, horizon, index_levels,
                       line_vectors, month_label)
from .indices import METHODS, rate_for
from .model import EngineModel, IndexSpec


def _setup(model: EngineModel, histories: dict, overrides: dict | None) -> tuple:
    ov = dict(overrides or {})
    start, n, base_year = horizon(model, ov)
    months = np.arange(start, start + n)
    years = range(min(base_year, start // 12), int(months[-1]) // 12 + 1)
    lev = index_levels(model, histories, ov, base_year, years)
    return ov, start, n, base_year, months, lev


def explain_npv(model: EngineModel, histories: dict, supplier: str, overrides: dict | None = None) -> dict:
    ov, start, n, base_year, months, lev = _setup(model, histories, overrides)
    sup = model.suppliers[supplier]
    ctx = Context(model, sup, ov)
    annual = float(ov.get("discount_rate", Context(model, None, ov).num(model.discount_rate)))
    method = ov.get("monthly_rate_method", model.monthly_rate_method)
    r_m = MONTHLY_RATE[method](annual)
    disc = 1 / (1 + r_m) ** np.arange(1, n + 1)
    esc = {e.id: escalator_factor(e, ctx, lev, months, base_year) for e in sup.escalators}
    _, escd = line_vectors(sup, ctx, months, start, n, esc, float(ov.get("driver_scale", 1.0)))

    cash = sum(escd.values(), np.zeros(n))
    pv = cash * disc
    by_year = {}
    for i, m in enumerate(months):
        y = by_year.setdefault(str(int(m) // 12), {"cash": 0.0, "pv": 0.0})
        y["cash"] += float(cash[i])
        y["pv"] += float(pv[i])
    return {"supplier": supplier, "value": float(pv.sum()), "undiscounted": float(cash.sum()),
            "annual_rate": annual, "method": method, "monthly_rate": r_m, "months": n,
            "first": {"month": month_label(start), "cash": float(cash[0]), "factor": float(disc[0])},
            "last": {"month": month_label(int(months[-1])), "cash": float(cash[-1]),
                     "factor": float(disc[-1])},
            "how": f"sum over {n} months of cash(t) / (1 + {r_m:.6f})^t, t = 1..{n}",
            "by_year": by_year}


def explain_escalator(model: EngineModel, histories: dict, supplier: str, escalator: str,
                      year: int, overrides: dict | None = None) -> dict:
    ov, start, n, base_year, months, lev = _setup(model, histories, overrides)
    sup = model.suppliers[supplier]
    e = next(x for x in sup.escalators if x.id == escalator)
    ctx = Context(model, sup, ov)
    vec = escalator_factor(e, ctx, lev, months, base_year)
    idx = np.nonzero(months // 12 == year)[0]
    if not len(idx):
        raise ValueError(f"{year} is outside the contract")
    i = int(idx[-1])
    first, every = ctx.month(e.first), int(ctx.num(e.every))
    out = {"supplier": supplier, "escalator": e.id, "source": e.source, "year": year,
           "month": month_label(int(months[i])), "value": float(vec[i]), "first": month_label(first),
           "every_months": every}
    if months[i] < first:
        out["how"] = f"before the first adjustment ({month_label(first)}): factor 1"
        return out
    steps = (int(months[i]) - first) // every
    index_year = (first + steps * every) // 12
    terms = [{"series": t.series, "weight": t.weight,
              "ratio": lev[t.series][index_year] / lev[t.series][base_year],
              "contribution": t.weight * lev[t.series][index_year] / lev[t.series][base_year]}
             for t in e.terms]
    out.update(index_year=index_year, fixed=e.fixed, terms=terms,
               how=f"{e.fixed:g}" + "".join(f" + {t['weight']:g} x {t['series']} [{index_year}/{base_year}]"
                                           f" = {t['ratio']:.4f}" for t in terms) + f" -> {vec[i]:.4f}")
    return out


def explain_index(model: EngineModel, histories: dict, series: str, year: int,
                  overrides: dict | None = None) -> dict:
    ov, start, n, base_year, months, lev = _setup(model, histories, overrides)
    spec = IndexSpec(**{**model.indices[series].model_dump(), **ov.get(f"index:{series}", {})})
    h = histories.get(series, ())
    out = {"series": series, "year": year, "base_year": base_year, "value": lev[series][year],
           "method": spec.method, "method_label": METHODS[spec.method]["label"], "window": spec.years,
           "history": [{"year": y, "value": v} for y, v in h]}
    if spec.method == "path":
        out["how"] = f"explicit level for {year}"
        return out
    r = rate_for(h, spec.method, spec.rate, spec.years)
    out["rate"] = r
    if spec.method == "mean_yoy":
        pts = h[-spec.years:]
        steps = [(b[0], b[1] / a[1] - 1) for a, b in zip(pts, pts[1:])]
        out["rate_how"] = "average of " + ", ".join(f"{y}: {c:+.2%}" for y, c in steps) + f" = {r:+.4%}"
    out["how"] = f"(1 + {r:+.4%}) ^ ({year} - {base_year}) = {lev[series][year]:.4f}"
    return out


def check_consistency(model: EngineModel, histories: dict, overrides: dict | None = None) -> bool:
    """explain_npv reproduces evaluate() for every supplier (used by the tests)."""
    r = evaluate(model, histories, overrides)
    return all(abs(explain_npv(model, histories, s, overrides)["value"] - v["npv"]["tco_esc"]) < 1e-6
               for s, v in r["suppliers"].items() if "error" not in v)

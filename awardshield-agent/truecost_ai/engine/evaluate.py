"""evaluate.py - the deterministic TCO / NPV engine. Pure arithmetic over numpy month vectors:
no files, no documents, no model calls. Same model + histories + overrides -> identical numbers.

    result = evaluate(model, histories, overrides=None)

overrides (what RedSeal / a simulation changes; the model itself is never modified):
    "<param id>": value                 e.g. "unit_rate": 63.0 (any supplier's param)
    "<supplier>.<param id>": value      only that supplier's parameter
    "discount_rate" / "monthly_rate_method" / "base_year" / "horizon_months": value
    "index:<series>": {"method", "years", "rate", "path"}   e.g. {"method": "mean_yoy", "years": 5}
    "driver_scale": factor              every driver x factor (demand shock)

Algorithm per supplier (spec 4.2):
    1. months = horizon_months months from horizon_start.
    2. index levels per year: level(base_year) = 1.0, compounding with the method's rate.
    3. each line: base amount per month = product of its factors, inside its window [start, end).
    4. escalated amount = base x product of its escalators. index_formula factor at month m:
       fixed + sum(weight x level(year of the last adjustment) / level(base_year)); it is 1.0 before
       'first' and changes only every 'every' months. compound factor = (1 + rate) ** adjustments.
    5. NPV: month t (1..n) discounted by 1 / (1 + r_m) ** t, r_m = annual/12 (simple) or
       (1 + annual) ** (1/12) - 1 (compound).
    6. tco = sum of every line (all lines are costs); tco_esc = escalated. Award metric: npv.tco_esc.

A supplier whose status is not 'ok' never stops the evaluation: if its numbers cannot be computed
(a missing parameter, an index without history) it gets an 'error' and zero cost - rank.py never
ranks it anyway. For an 'ok' supplier the same failure is raised.
"""

import re

import numpy as np

from .indices import levels
from .model import EngineModel, IndexSpec, Supplier

MONTHLY_RATE = {
    "simple": lambda a: a / 12,
    "compound": lambda a: (1 + a) ** (1 / 12) - 1,
}


def month_index(ym: str) -> int:
    """'YYYY-MM' -> months since year 0."""
    y, m = str(ym).split("-")[:2]
    return int(y) * 12 + int(m) - 1


def month_label(i: int) -> str:
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


# -----------------------------------------------------------------------------------------
# token resolution
# -----------------------------------------------------------------------------------------
class Context:
    """Parameter values for ONE supplier (shared + own + overrides) and token resolution."""

    def __init__(self, model: EngineModel, supplier: Supplier | None, overrides: dict):
        self.p = {k: v.value for k, v in model.parameters.items()}
        if supplier is not None:
            self.p.update({k: v.value for k, v in supplier.parameters.items()})
            prefix = supplier.name + "."
            self.p.update({k[len(prefix):]: v for k, v in overrides.items() if k.startswith(prefix)})
        self.p.update({k: v for k, v in overrides.items() if k in self.p})

    def _get(self, ref: str):
        if ref not in self.p:
            raise ValueError(f"parameter '{ref}' has no value")
        return self.p[ref]

    def num(self, tok: str) -> float:
        kind, _, ref = tok.partition(":")
        if kind == "c":
            return float(ref)
        if kind in ("p", "1-p"):
            v = float(self._get(ref))
            return 1 - v if kind == "1-p" else v
        raise ValueError(f"not a number token: {tok}")

    def month(self, tok: str) -> int:
        kind, _, ref = tok.partition(":")
        off = 0
        m = re.fullmatch(r"(.+?)([+-]\d+)", ref)
        if m and ((kind == "p" and m.group(1) in self.p)
                  or (kind == "c" and re.fullmatch(r"\d{4}-\d{2}", m.group(1)))):
            ref, off = m.group(1), int(m.group(2))
        value = self._get(ref) if kind == "p" else ref
        return month_index(str(value)) + off

    def active(self, when: str) -> bool:
        for cond in filter(None, (c.strip() for c in (when or "").split(";"))):
            pid, _, want = cond.partition("=")
            have = self.p.get(pid.strip())
            try:
                if abs(float(have) - float(want)) > 1e-9:
                    return False
            except (TypeError, ValueError):
                if str(have).strip().lower() != want.strip().lower():
                    return False
        return True


# -----------------------------------------------------------------------------------------
# pieces
# -----------------------------------------------------------------------------------------
class Levels(dict):
    """{series: {year: level}}; a series that could not be projected raises when it is used."""

    def __init__(self, ok: dict, errors: dict):
        super().__init__(ok)
        self.errors = errors

    def __missing__(self, series):
        raise ValueError(f"index '{series}': {self.errors.get(series, 'not in the model')}")


def index_levels(model: EngineModel, histories: dict, overrides: dict, base_year: int,
                 years: range) -> Levels:
    ok, errors = {}, {}
    for series, spec in model.indices.items():
        s = IndexSpec(**{**spec.model_dump(), **overrides.get(f"index:{series}", {})})
        try:
            ok[series] = levels(s.method, histories.get(series, ()), base_year, years,
                                rate=s.rate, window=s.years, path=s.path)
        except (ValueError, KeyError, TypeError) as e:
            errors[series] = str(e)
    return Levels(ok, errors)


def escalator_factor(e, ctx: Context, lev: dict, months: np.ndarray, base_year: int) -> np.ndarray:
    """Factor per month for one escalator (1.0 before the first adjustment)."""
    first, every = ctx.month(e.first), int(ctx.num(e.every))
    started = months >= first
    steps = np.where(started, (months - first) // every, 0)
    if e.kind == "compound":
        return np.where(started, (1 + ctx.num(e.rate)) ** (steps + 1), 1.0)
    year = (first + steps * every) // 12  # index year in force at each month
    value = lambda y: e.fixed + sum(t.weight * lev[t.series][int(y)] / lev[t.series][base_year]
                                    for t in e.terms)
    return np.where(started, np.array([value(y) for y in year]), 1.0)


def line_vectors(sup: Supplier, ctx: Context, months: np.ndarray, start: int, n: int,
                 esc: dict, driver_scale: float) -> tuple[dict, dict]:
    """(base, escalated) monthly vector per line."""
    base, escd = {}, {}
    for ln in sup.lines:
        if not ctx.active(ln.when):
            v = np.zeros(len(months))
        else:
            a = ctx.month(ln.start)
            b = ctx.month(ln.end) if ln.end else start + n
            v = ((months >= a) & (months < b)).astype(float)
        for f in ln.factors:
            if f.startswith("d:"):
                v = v * sup.drivers[f[2:]].per_month * driver_scale
            else:
                v = v * ctx.num(f)
        e = v.copy()
        for eid in ln.escalators:
            e = e * esc[eid]
        base[ln.id], escd[ln.id] = v, e
    return base, escd


def _supplier_result(sup: Supplier, ctx: Context, lev, months, horizon_start, n, base_year,
                     driver_scale, disc, year_of) -> dict:
    esc = {e.id: escalator_factor(e, ctx, lev, months, base_year) for e in sup.escalators}
    base, escd = line_vectors(sup, ctx, months, horizon_start, n, esc, driver_scale)
    total = sum(base.values(), np.zeros(n))
    total_esc = sum(escd.values(), np.zeros(n))
    by_role = {}
    for ln in sup.lines:
        by_role[ln.role] = by_role.get(ln.role, 0.0) + float(escd[ln.id] @ disc)
    years = np.unique(year_of)
    return {
        "status": sup.status,
        "totals": {"tco": float(total.sum()), "tco_esc": float(total_esc.sum())},
        "npv": {"tco": float(total @ disc), "tco_esc": float(total_esc @ disc)},
        "npv_by_role": by_role,
        "yearly": {str(int(y)): {"tco": float(total[year_of == y].sum()),
                                 "tco_esc": float(total_esc[year_of == y].sum())} for y in years},
        "escalators": {e.id: {"source": e.source,
                              "by_year": {str(int(y)): float(esc[e.id][year_of == y][-1]) for y in years}}
                       for e in sup.escalators},
        "lines": {ln.id: {"role": ln.role, "base": float(base[ln.id].sum()),
                          "escalated": float(escd[ln.id].sum()), "npv_esc": float(escd[ln.id] @ disc)}
                  for ln in sup.lines},
    }


# -----------------------------------------------------------------------------------------
# evaluate
# -----------------------------------------------------------------------------------------
def horizon(model: EngineModel, ov: dict) -> tuple[int, int, int]:
    """(first month index, number of months, base year) after overrides. An override may be a token
    or a plain value ('2026-01', 144, 2025)."""
    shared = Context(model, None, ov)
    start = ov.get("horizon_start", model.horizon_start)
    start = f"c:{start}" if re.fullmatch(r"\d{4}-\d{2}", str(start)) else start
    return (shared.month(start),
            int(ov.get("horizon_months", shared.num(model.horizon_months))),
            int(ov.get("base_year", shared.num(model.base_year))))


def evaluate(model: EngineModel, histories: dict[str, tuple], overrides: dict | None = None) -> dict:
    ov = dict(overrides or {})
    shared = Context(model, None, ov)
    horizon_start, n, base_year = horizon(model, ov)
    annual = float(ov.get("discount_rate", shared.num(model.discount_rate)))
    method = ov.get("monthly_rate_method", model.monthly_rate_method)
    driver_scale = float(ov.get("driver_scale", 1.0))

    months = np.arange(horizon_start, horizon_start + n)
    years = range(min(base_year, horizon_start // 12), int(months[-1]) // 12 + 1)
    lev = index_levels(model, histories, ov, base_year, years)
    r_m = MONTHLY_RATE[method](annual)
    disc = 1 / (1 + r_m) ** np.arange(1, n + 1)
    year_of = months // 12

    out = {}
    for name, sup in model.suppliers.items():
        ctx = Context(model, sup, ov)
        try:
            out[name] = _supplier_result(sup, ctx, lev, months, horizon_start, n, base_year,
                                         driver_scale, disc, year_of)
        except (ValueError, KeyError) as e:
            if sup.status == "ok":
                raise ValueError(f"{name}: {e}") from e
            zero = {"tco": 0.0, "tco_esc": 0.0}
            out[name] = {"status": sup.status, "error": str(e), "totals": dict(zero), "npv": dict(zero),
                         "npv_by_role": {}, "yearly": {}, "escalators": {}, "lines": {}}

    return {"rfp_id": model.rfp_id, "currency": model.currency, "start": month_label(horizon_start),
            "months": n, "base_year": base_year,
            "discount": {"annual": annual, "monthly": r_m, "method": method},
            "index_levels": {s: {str(y): v for y, v in lv.items()} for s, lv in lev.items()},
            "suppliers": out}

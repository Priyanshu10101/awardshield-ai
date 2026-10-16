trustcost_ai - Engine Build + Agent Changes (for the laptop coding agent)

This file is self-contained. Do the steps in order. Every step ends with a check
until it passes. Everything here was built and verified on the server first; the expected
outputs are the real
ones from that run.

Rule: the AI builds the inputs (TrueCost writes cost_model.json); this deterministic
engine decides. No LLM,
no network inside engine/. Same inputs -> byte-identical numbers.

0. Final project layout (after this file)

[python]
truecost_ai/
├── agent/                  # AI agents (TrueCost now, RedSeal later)
│   ├── __init__.py
│   └── truecost/           # MOVED from trustcost_ai/truecost/ (step A1)
│       ├── settings.py doc_reader.py schemas.py prompts.py fetchers.py
│       ├── finalizer.py agent.py runner.py
│       └── subagents/ volume.py commercial.py escalation.py index_resolver.py cost_model.py web_search.py
├── engine/                 # NEW - deterministic TCO / NPV engine (steps E1-E8)
│   └── __init__.py model.py indices.py load.py evaluate.py rank.py explain.py cli.py
├── tests/                  # NEW - 17 tests
│   └── test_engine.py
├── config/ buyer_policy.json known_sources.json projects/IN/IN-CRUT-EBUS.manifest.json
├── assets/ rfp/ bids/      # bids REGENERATED (step B)
├── data/ output/<rfp>/ state/<rfp>/
└── generate_bids.py        # UPDATED (step B)


Commands after this file:

[bash]
python -m agent.truecost.runner IN-CRUT-EBUS                                        # AI extraction (was: python truecost.runner)
python -m agent.truecost.runner IN-CRUT-EBUS --answers-only                           # re-link with stored answers, no PDF reading
python -m engine.cli IN-CRUT-EBUS                                                   # deterministic award
python -m pytest tests -q                                                           # 17 engine tests


A. Agent changes (do these first)

A1. Move the package: truecost/ -> agent/truecost/

[bash]
cd trustcost_ai
mkdir -p agent
mv truecost agent/truecost
printf """agent - trustcost_ai AI agents (TrueCost now, RedSeal next). Agents build inputs;
engine decides."""\n > agent/__init__.py
find agent -name __pycache__ -exec rm -rf {} +


In agent/truecost/settings.py change the ROOT line (the package is now one level deeper):

[python]
ROOT = Path(__file__).resolve().parent.parent.parent                          # /trustcost_ai (agent/truecost/
settings.py)


In agent/truecost/runner.py docstring: python -m truecost.runner -> python -m agent.truecost.runner
(3 lines). All other imports inside the package are relative (from .x import, from ..x import) and need
no change.

Check:

[bash]
python -c "from agent.truecost.settings import ROOT; from agent.truecost.agent import
root_agent; print(ROOT.name, root_agent.name)"
# expect: trustcost_ai truecost


A2. Alternative / option volumes are never part of the base cost

Found on the server: MetroLink's cost model added the tender's optional "+25 % buses"
volumes as extra lines
(primary=false drivers). An option the buyer MAY order is not part of the bid's base cost.

agent/truecost/prompts.py - in COST_MODEL, K3, replace the first sentence with:

K3. DRIVERS - one per tender volume driver that this bidder prices: source
'volume:<driver_id>' of
that stream's PRIMARY driver (a driver with primary=false is an option / alternative - e.
g. extra
units the buyer MAY order - and is never part of the base cost: no driver, no line for
it); scale
from the policy's buffer rule ($1.0 =$ as printed; without a $8\%$ buffer $= 1/(1+B/100)$).
Leave points
empty - Python fills them.

agent/truecost/finalizer.py - in link_problems, replace the start of the drivers
loop with:

[python]
primary = {d.driver_id for d in volume.drivers if d.primary}
for d in draft.drivers:
    if d.source.removeprefix("volume:") not in volume_ids:
        problems.append(f"driver {d.id}: source '{d.source}' is not a tender volume
driver")
    elif d.source.removeprefix("volume:") not in primary:
        problems.append(f"driver {d.id}: '{d.source}' is an ALTERNATIVE (non-primary)
tender volume - an
                        f"option or scenario is not part of the base cost; use the
primary driver only")


(keep the two scale / scale_source checks that follow).

A3. Earlier agent fixes (only if your laptop does not have them yet)

These were given in the chat before; listed here so nothing is missed:

⚬ config/known_sources.json: each entry has a fixed series_key (in_cpi_iw_all_india,
in_wpi_all_commodities, in_wpi_electricity); known_source() returns status: "reused" when that file is
already frozen. -> one download per series per tender,

⚬ prompts.py COMMERCIAL C5: "ESCALATION IS NOT A COMMERCIAL TERM ...",

⚬ prompts.py COST_MODEL K6: a unit price is ONE line, never split by the formula's fixed
share.

⚬ schemas.py DriverDraft.scale_source; finalizer.py checks scale_source and flags a
split unit price.

⚬ schemas.py ParamDraft: value: Optional[float], month, choice.

B. New synthetic bids (decision 1B: GreenMetro wins the lifetime award as extracted)

The old bids ($64.50 / 61.00 / 64.00$) were tuned for a different volume. Calibrated with THIS
engine on the real
tender ($2 \times 100$ buses $\times$ 64,800 km/yr, 144 months, live CPI-IW / WPI / WPI-Electricity,
mean_yoy 3, 12 %):

| bidder | figure printed | in words | formula (fixed +

CPI-IW + WPI + Elec)
GreenMetro
MetroLink
UrbanDrive

The planted error: GreenMetro's figure cell reads 63.00 while the amount in words is
Sixty Six. The tender
itself says words prevail (ITB 20.vii, "if the Authority finds a discrepancy between words
and figures quoted,
then the amount written in words shall prevail"). TrueCost takes the figure (63.00) and
raises an open question;
RedSeal will apply the words (66.00) and prove the flip.

Edits in generate_bids.py:

1. common_header: tender number 1072/CRUT -> 1376/CRUT; the row ["Assured kilometres", ...] ->
["Assured kilometres", "64,800 km / bus / year (as per RFP)"].

2. bid_greenmetro: price rows -> ["Per-kilometre Gross Cost Rate (AC MIDI, 9 m)", "Rs 63. 00 / km"] and
["     (rate in words)", "Rupees Sixty Six only per kilometre"]; DELETE the grey "
[Document note: ... planted
error ...]" paragraph and the Spacer(1, 2) before it (a real bid would not announce its
error).

3. bid_metrolink: escalation_clause(story, WC=0.40, WW=0.20, WE=0.10, note="Note: MetroLink's headline rate is the lowest, but 70% of the fee is indexed (CPI-IW 0.40, WPI 0. 20, Electricity 0.10) and escalates with inflation over the 12-year term.")

4. bid_urbandrive: price rows -> "Rs 65.50 / km" and "Rupees Sixty Five and Fifty paise per kilometre".

5. Update the module docstring to describe the 3 acts (see section D).

Then:

[bash]
pip install reportlab
python generate_bids.py
rm -rf data/output/IN-CRUT-EBUS                                               # the old extraction is for the old PDFs
python -m agent.truecost.runner IN-CRUT-EBUS --set rfq.contract.start=2026-04 --set rfq.
index.base_year=2025 --set rfq.contract.months=144


(about 8 min; accept the suggestions or answer as before - volume = the tender's, formula =
the bidder's own).
TrueCost should end with all 3 bidders ok and the rates 63.0 / 61.0 / 65.5.

E. The engine, file by file

Create engine/ and tests/ and copy each file below exactly. Install: pip install numpy pydantic pytest.

How the pieces fit:

cost_model.json + frozen_indices/ --load.py--> EngineModel + histories
EngineModel + histories + overrides --evaluate.py--> result {suppliers: {npv, totals,
yearly, escalators, lines}}
result --rank.py--> Award (ranking in crore, winner, margin)                      # RedSeal calls rerun
() per challenge
explain.py = the same maths, step by step, for the pitch / audit


E1. engine/model.py

[python]
"""model.py - the EngineModel: the clean, validated input of evaluate().

load.py builds it from TrueCost's cost_model.json (+ frozen index files). Every line is a
COST.

Tokens used in lines / escalators / horizon:
    p:<param>       value of a parameter                 1-p:<param>   one minus it
    c:<number>      a constant                           d:<driver>    the driver's value that
month
Month tokens: 'p:<param>' or 'c:YYYY-MM', optional '+N' / '-N' months offset.
Windows are half-open: start <= month < end ('' end = end of the horizon).
"""

from typing import Literal

from pydantic import BaseModel, Field


class Param(BaseModel):
    value: float | str                                  # a number, or 'YYYY-MM' for a month, or a
choice
    kind: Literal["number", "month", "choice"] = "number"
    unit: str = ""
    source: str
    source_kind: str = ""
    quote: str = ""


class IndexSpec(BaseModel):
    series: str
    method: Literal["fixed", "mean_yoy", "cagr", "trend", "path"] = "mean_yoy"
    years: int | None = 3
    rate: float | None = None
    path: dict[int, float] | None = None


class Driver(BaseModel):
    id: str
    per_month: float                                    # volume per month (already scaled)
    source: str = ""
    built_as: str = ""


class Term(BaseModel):
    series: str
    weight: float


class Escalator(BaseModel):
    id: str
    kind: Literal["index_formula", "compound"]
    fixed: float = 0.0
    terms: list[Term] = []
    rate: str = ""                                      # number token (compound)
    first: str = ""                                     # month token of the first adjustment
    every: str = ""                                     # number token: months between adjustments
    source: str = ""


class Line(BaseModel):
    id: str
    role: str = "cost"                                  # display grouping only; every line is a c
    factors: list[str]
    start: str
    end: str = ""
    escalators: list[str] = []
    when: str = ""                                      # '<param>=<value>[;...]' : counts only in th
scenario


class Supplier(BaseModel):
    name: str
    status: str = "ok"
    parameters: dict[str, Param] = Field(default_factory=dict)  # this supplier's own
    drivers: dict[str, Driver] = {}
    escalators: list[Escalator] = []
    lines: list[Line]
    indices: dict[str, IndexSpec] = Field(default_factory=dict)


class EngineModel(BaseModel):
    rfp_id: str
    currency: str = "INR"
    horizon_start: str                                  # month token
    horizon_months: str                                 # number token
    base_year: str                                      # number token (index level 1.0 in this year)
    discount_rate: str                                  # number token (annual fraction)
    monthly_rate_method: Literal["simple", "compound"] = "compound"
    parameters: dict[str, Param]                        # shared rfq.* parameters
    indices: dict[str, IndexSpec]                       # one per published series, shared by sup
    suppliers: dict[str, Supplier]


E2. engine/indices.py

Index projection. Window N = the last N annual POINTS (spec 4.1: 3 points -> 2 changes).
Verified against spec 9.3: CPI $3.30\ \% / 4.51\ \%$, WPI $1.49\ \% / 2.46\ \%$.

[python]
"""indices.py - index projection: a series' annual history -> a yearly growth rate -> inde
levels.

Levels are relative to the base year (level(base_year) = 1.0) and compound with the method'
rate:
    level(y) = (1 + r) ** (y - base_year)
'path' gives explicit levels instead. Pure functions; no files.

History = tuple of (year, value) sorted by year (a tuple so rate_for can be cached).
Window N = the last N annual POINTS (trustcost_ai spec 4.1: 3 points -> 2 yearly changes).
"""

from functools import lru_cache


def _yoy(h: tuple, n: int) -> list[float]:
    """Year-on-year changes among the last n points (n points -> n-1 changes)."""
    ys = [v for _, v in h[-n:]]
    return [b / a - 1 for a, b in zip(ys, ys[1:]) if a]


def mean_yoy(h: tuple, years: int, **_) -> float:
    """Average yearly change among the last `years` points."""
    r = _yoy(h, years)
    if len(h) < years or not r:
        raise ValueError(f"mean_yoy {years}: history too short ({len(h)} points)")
    return sum(r) / len(r)


def cagr(h: tuple, years: int, **_) -> float:
    """Compound growth between the first and last of the last `years` points."""
    if len(h) < years or years < 2:
        raise ValueError(f"cagr {years}: history too short ({len(h)} points)")
    a, b = h[-years][1], h[-1][1]
    return (b / a) ** (1 / (years - 1)) - 1


def trend(h: tuple, years: int, **_) -> float:
    """Least-squares slope over the last `years` points, divided by the last value."""
    pts = h[-years:]
    if len(pts) < 2:
        raise ValueError(f"trend {years}: history too short ({len(h)} points)")
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return slope / ys[-1]


def fixed(h: tuple, rate: float, **_) -> float:
    """A stated yearly rate (history ignored)."""
    return float(rate)


METHODS = {
    "fixed": {"label": "fixed rate per year", "fn": fixed},
    "mean_yoy": {"label": "average of the last N yearly changes", "fn": mean_yoy},
    "cagr": {"label": "compound growth over the last N years", "fn": cagr},
    "trend": {"label": "linear trend over the last N years (slope / last value)", "fn":
trend},
    "path": {"label": "explicit yearly levels", "fn": None},
}


@lru_cache(maxsize=4096)
def rate_for(history: tuple, method: str, rate: float | None, years: int | None) -> float:
    if method not in METHODS or METHODS[method]["fn"] is None:
        raise ValueError(f"no rate for method '{method}'")
    return METHODS[method]["fn"](history, rate=rate, years=years)


def levels(method: str, history: tuple, base_year: int, years: range, *, rate: float | None
= None,
           window: int | None = None, path: dict[int, float] | None = None) -> dict[int,
float]:
    """{year: level} with level(base_year) = 1.0."""
    if method == "path":
        return {y: float(path[y]) for y in years}
    r = rate_for(history, method, rate, window)
    return {y: (1 + r) ** (y - base_year) for y in years}


E3. engine/load.py

The ONLY file that reads disk. Adapts TrueCost's cost_model.json (number / month / choic
in separate fields, a year written as text, shared rfp.* parameters) + frozen_indices/ json into an EngineModel + histories.

[python]
"""load.py - TrueCost output -> EngineModel + index histories (the only file that reads
disk).

Model, histories = load_case(output_dir)                                      # output_dir = data/output/<rfp_id>

Adapts TrueCost's cost_model.json to the engine:
    - a parameter's number / month / choice (stored in separate fields) -> one typed value;
    - a year written as text ('2025') or a month written as number -> normalised;
    - shared rfq.* parameters stay shared; supplier parameters stay with their supplier;
    - drivers: TrueCost's per_month volume (already scaled);
    - every series a supplier escalates with gets ONE IndexSpec (method from the supplier's
spec, else
      the company policy default) and its history from frozen_indices/<series>.json.
"""

import json
import re
from pathlib import Path

from .model import Driver, EngineModel, Escalator, IndexSpec, Line, Param, Supplier

MONTH = re.compile(r"^\d{4}-\d{2}$")
YEAR = re.compile(r"^\d{4}$")


def _param(raw: dict) -> Param:
    """TrueCost parameter -> Param with exactly one typed value."""
    value, month, choice = raw.get("value"), (raw.get("month") or "").strip(), (raw.
"choice") or "").strip()
    if value is not None:
        p = Param(value=float(value), kind="number", **_meta(raw))
    elif MONTH.match(month):
        p = Param(value=month, kind="month", **_meta(raw))
    elif YEAR.match(month):
        p = Param(value=float(month), kind="number", **_meta(raw))            # a year stored as a month string
    elif choice:
        p = Param(value=choice, kind="choice", **_meta(raw))
    else:
        raise ValueError(f"parameter has no value, month or choice: {raw}")
    return p


def _meta(raw: dict) -> dict:
    return {k: raw.get(k, "") or "" for k in ("unit", "source", "source_kind", "quote")}


def _history(path: Path) -> tuple:
    data = json.loads(path.read_text())
    return tuple(sorted((int(y), float(v)) for y, v in data["annual_values"].items()))


def default_method(policy: dict) -> IndexSpec:
    """Company default 'mean_yoy 3' / 'fixed 2.5' -> a template IndexSpec."""
    text = str(policy.get("index.default_method", "mean_yoy 3")).split()
    method, arg = text[0], (float(text[1]) if len(text) > 1 else 3)
    if method == "fixed":
        return IndexSpec(series="", method="fixed", years=None, rate=arg / 100)
    return IndexSpec(series="", method=method, years=int(arg))


def load_case(output_dir: str | Path, policy: dict | None = None) -> tuple[EngineModel, di
[str, tuple]]:
    out = Path(output_dir)
    cm = json.loads((out / "cost_model.json").read_text())
    template = default_method(policy or {})

    shared = {k: _param(v) for k, v in cm["shared_parameters"].items()}
    suppliers, indices = {}, {}
    for name, s in cm["suppliers"].items():
        for series, spec in (s.get("indices") or {}).items():
            indices.setdefault(series, IndexSpec(**{**template.model_dump(), **spec,
"series": series}))
        for e in s.get("escalators", []):
            for t in e.get("terms", []):
                indices.setdefault(t["series"], template.model_copy(update={"series": t
["series"]}))
        suppliers[name] = Supplier(
            name=name, status=s.get("status", "ok"),
            parameters={k: _param(v) for k, v in s.get("parameters", {}).items()},
            drivers={k: Driver(id=k, per_month=d["per_month"], source=d.get("source", ""),
                               built_as=d.get("built_as", "")) for k, d in s["drivers"].items()},
            escalators=[Escalator(**{k: v for k, v in e.items() if k in Escalator.
model_fields})
                        for e in s.get("escalators", [])],
            lines=[Line(**{k: v for k, v in ln.items() if k in Line.model_fields}) for ln
in
                   s["lines"]],
        )

    h = cm["horizon"]
    model = EngineModel(rfp_id=cm["rfp_id"], horizon_start=h["start"], horizon_months=h
["months"],
                        base_year=h["base_year"], discount_rate=h["discount_rate"],
                        monthly_rate_method=str((policy or {}).get("finance.
monthly_rate_method", "compound")),
                        parameters=shared, indices=indices, suppliers=suppliers)

    histories = {}
    for series in indices:
        f = out / "frozen_indices" / f"{series}.json"
        if not f.exists():
            raise FileNotFoundError(f"index series '{series}' is used but not frozen: {f}")
        histories[series] = _history(f)
    return model, histories


E4. engine/evaluate.py

The deterministic engine (spec 4.2). numpy month vectors; overrides never mutate the model
Verified to the cent against a hand calculation.

[python]
"""evaluate.py - the deterministic TCO / NPV engine. Pure arithmetic over numpy month
vectors:
no files, no documents, no model calls. Same model + histories + overrides -> identical
numbers.

    result = evaluate(model, histories, overrides=None)

overrides (what RedSeal / a simulation changes; the model itself is never modified):
    "<param id>": value                                             e.g. "unit_rate": 63.0  (any
supplier's param)
    "<supplier>.<param id>": value                                  only that supplier's parameter
    "discount_rate" / "monthly_rate_method" / "base_year" / "horizon_months": value
    "index:<series>": {"method", "years", "rate", "path"} e.g. {"method": "mean_yoy",
"years": 5}
    "driver_scale": factor                                          every driver x factor (demand
shock)

Algorithm per supplier (trustcost_ai spec 4.2):
    1. months = horizon_months months from horizon_start.
    2. index levels per year: level(base_year) = 1.0, compounding with the method's rate.
    3. each line: base amount per month = product of its factors, inside its window [start,
end).
    4. escalated amount = base x product of its escalators. index_formula factor at month m:
       fixed + sum(weight x level(year of the last adjustment) / level(base_year)); it is 1.0
before
       'first' and changes only every 'every' months. compound factor = (1 + rate) **
adjustments.
    5. NPV: month t (1..n) discounted by 1 / (1 + r_m) ** t, r_m = annual/12 (simple) or
       (1 + annual) ** (1/12) - 1 (compound).
    6. tco = sum of every line (all lines are costs); tco_esc = escalated. award metric: npv.
tco_esc.
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
    y, m = ym.split("-")
    return int(y) * 12 + int(m) - 1


def month_label(i: int) -> str:
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


# --------------------------------------------------------------------------------------
# token resolution
# --------------------------------------------------------------------------------------
class Context:
    """Parameter values for ONE supplier (shared + own + overrides) and token resolution."""

    def __init__(self, model: EngineModel, supplier: Supplier | None, overrides: dict):
        self.p = {k: v.value for k, v in model.parameters.items()}
        if supplier is not None:
            self.p.update({k: v.value for k, v in supplier.parameters.items()})
            prefix = supplier.name + "."
            self.p.update({k[len(prefix):]: v for k, v in overrides.items() if k.startswith
(prefix)})
        self.p.update({k: v for k, v in overrides.items() if k in self.p})

    def num(self, tok: str) -> float:
        kind, _, ref = tok.partition(":")
        if kind == "c":
            return float(ref)
        if kind in ("p", "1-p"):
            v = float(self.p[ref])
            return 1 - v if kind == "1-p" else v
        raise ValueError(f"not a number token: {tok}")

    def month(self, tok: str) -> int:
        kind, _, ref = tok.partition(":")
        off = 0
        m = re.fullmatch(r"(.+?)([+-]\d+)", ref)
        if m and (kind == "p" and m.group(1) in self.p or kind == "c" and re.fullmatch(r"^\d
{4}-\d{2}$", m.group(1))):
            ref, off = m.group(1), int(m.group(2))
        value = self.p[ref] if kind == "p" else ref
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


# --------------------------------------------------------------------------------------
# pieces
# --------------------------------------------------------------------------------------
def index_levels(model: EngineModel, histories: dict, overrides: dict, base_year: int,
                 years: range) -> dict[str, dict[int, float]]:
    out = {}
    for series, spec in model.indices.items():
        s = IndexSpec(**{**spec.model_dump(), **overrides.get(f"index:{series}", {})})
        out[series] = levels(s.method, histories.get(series, ()), base_year, years,
                             rate=s.rate, window=s.years, path=s.path)
    return out


def escalator_factor(e, ctx: Context, lev: dict, months: np.ndarray, base_year: int) -> np.
ndarray:
    """Factor per month for one escalator (1.0 before the first adjustment)."""
    first, every = ctx.month(e.first), int(ctx.num(e.every))
    started = months >= first
    steps = np.where(started, (months - first) // every, 0)
    if e.kind == "compound":
        return np.where(started, (1 + ctx.num(e.rate)) ** (steps + 1), 1.0)
    year = (first + steps * every) // 12                                        # index year in force at each
month
    value = lambda y: e.fixed + sum(t.weight * lev[t.series][int(y)] / lev[t.series]
[base_year] for t in e.terms)
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


# --------------------------------------------------------------------------------------
# evaluate
# --------------------------------------------------------------------------------------
def evaluate(model: EngineModel, histories: dict[str, tuple], overrides: dict | None = None
) -> dict:
    ov = dict(overrides or {})
    shared = Context(model, None, ov)
    horizon_start = shared.month(ov.get("horizon_start", model.horizon_start))
    n = int(ov.get("horizon_months", shared.num(model.horizon_months)))
    base_year = int(ov.get("base_year", shared.num(model.base_year)))
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
        esc = {e.id: escalator_factor(e, ctx, lev, months, base_year) for e in sup.
escalators}
        base, escd = line_vectors(sup, ctx, months, horizon_start, n, esc, driver_scale)
        total = sum(base.values(), np.zeros(n))
        total_esc = sum(escd.values(), np.zeros(n))
        by_role = {}
        for ln in sup.lines:
            by_role[ln.role] = by_role.get(ln.role, 0.0) + float(escd[ln.id] @ disc)
        out[name] = {
            "status": sup.status,
            "totals": {"tco": float(total.sum()), "tco_esc": float(total_esc.sum())},
            "npv": {"tco": float(total @ disc), "tco_esc": float(total_esc @ disc)},
            "npv_by_role": by_role,
            "yearly": {str(int(y)): {"tco": float(total[year_of == y].sum()),
                                     "tco_esc": float(total_esc[year_of == y].sum())}
                       for y in np.unique(year_of)},
            "escalators": {e.id: {"source": e.source,
                                  "by_year": {str(int(y)): float(esc[e.id][year_of == y][-1])
                                              for y in np.unique(year_of)}}
                           for e in sup.escalators},
            "lines": {ln.id: {"role": ln.role, "base": float(base[ln.id].sum()),
                              "escalated": float(escd[ln.id].sum()), "npv_esc": float(escd
[ln.id] @ disc)}
                      for ln in sup.lines}
        }

    return {"rfp_id": model.rfp_id, "currency": model.currency, "start": month_label
(horizon_start),
            "months": n, "base_year": base_year,
            "discount": {"annual": annual, "monthly": r_m, "method": method},
            "index_levels": {s: {str(y): v for y, v in lv.items()} for s, lv in lev.items()},
            "suppliers": out}


E5. engine/rank.py

Award = ranking (crore), winner, runner-up, margin. rerun() is what RedSeal calls for
every challenge. Only status 'ok' bidders are ranked.

[python]
"""rank.py - turn an evaluate() result into the award: ranking, winner, margin. Pure
functions.

    award(result)                                                   -> Award(ranking=[(supplier, npv_cr)], winner, runner_up,
margin_cr, margin_pct)
    award(result, metric="tco")                                     -> the same on the unescalated NPV (the 'sticker' view)
    rerun(model, histories, overrides, label)                       -> Award for one what-if (RedSeal uses this)

Only suppliers whose cost model is complete (status 'ok') are ranked unless
include_incomplete=True.
Amounts are reported in crore (1 crore = 1e7) - the engine itself works in base currency
units.
"""

from pydantic import BaseModel

from .evaluate import evaluate


CRORE = 1e7


class Award(BaseModel):
    label: str = "BASELINE"
    metric: str = "tco_esc"
    ranking: list[tuple[str, float]]                                # (supplier, NPV in crore), cheapest first
    winner: str
    runner_up: str = ""
    margin_cr: float = 0.0
    margin_pct: float = 0.0
    excluded: list[str] = []                                        # suppliers not ranked (incomplete cost model)


def award(result: dict, metric: str = "tco_esc", label: str = "BASELINE",
          include_incomplete: bool = False) -> Award:
    sup = result["suppliers"]
    ranked = [n, v for n, v in sup.items() if include_incomplete or v["status"] == "ok"]
    if not ranked:
        raise ValueError("no supplier with a complete cost model to rank")
    rows = sorted(((n, sup[n]["npv"][metric] / CRORE) for n in ranked), key=lambda x: (x[1],
x[0]))
    margin = rows[1][1] - rows[0][1] if len(rows) > 1 else 0.0
    return Award(label=label, metric=metric, ranking=rows, winner=rows[0][0],
                 runner_up=rows[1][0] if len(rows) > 1 else "", margin_cr=margin,
                 margin_pct=margin / rows[0][1] * 100 if rows[0][1] else 0.0,
                 excluded=sorted(set(sup) - set(ranked)))


def rerun(model: EngineModel, histories: dict, overrides: dict | None, label: str = "RERUN"
,
          metric: str = "tco_esc") -> Award:
    return award(evaluate(model, histories, overrides), metric=metric, label=label)


E6. engine/explain.py

'How was this number made' - uses the same functions as evaluate, so it reproduces evaluate
exactly (tested).

[python]
"""explain.py - how a number was computed, using the SAME functions as evaluate() (so it
reproduces
evaluate's numbers exactly). Pure; no files.

    explain_npv(model, histories, supplier, overrides)              NPV: cash, discount, by
year
    explain_escalator(model, histories, supplier, esc_id, year, ov) factor in a year, term
by term
    explain_index(model, histories, series, year, overrides)        rate (method + history)
-> level
"""

import numpy as np

from .evaluate import MONTHLY_RATE, Context, escalator_factor, index_levels, line_vectors
from .indices import METHODS, rate_for
from .model import EngineModel, IndexSpec


def _setup(model: EngineModel, histories: dict, overrides: dict | None) -> tuple:
    ov = dict(overrides or {})
    shared = Context(model, None, ov)
    start = shared.month(ov.get("horizon_start", model.horizon_start))
    n = int(ov.get("horizon_months", shared.num(model.horizon_months)))
    base_year = int(ov.get("base_year", shared.num(model.base_year)))
    months = np.arange(start, start + n)
    years = range(min(base_year, start // 12), int(months[-1]) // 12 + 1)
    lev = index_levels(model, histories, ov, base_year, years)
    return ov, start, n, base_year, months, lev


def explain_npv(model: EngineModel, histories: dict, supplier: str, overrides: dict | None =
None) -> dict:
    ov, start, n, base_year, months, lev = _setup(model, histories, overrides)
    sup = model.suppliers[supplier]
    ctx = Context(model, sup, ov)
    annual = float(ov.get("discount_rate", Context(model, None, ov).num(model.
discount_rate)))
    method = ov.get("monthly_rate_method", model.monthly_rate_method)
    r_m = MONTHLY_RATE[method](annual)
    disc = 1 / (1 + r_m) ** np.arange(1, n + 1)
    esc = {e.id: escalator_factor(e, ctx, lev, months, base_year) for e in sup.
escalators}
    _, escd = line_vectors(sup, ctx, months, start, n, esc, float(ov.get("driver_scale", 1.
0)))

    cash = sum(escd.values(), np.zeros(n))
    pv = cash * disc
    by_year = {}
    for i, m in enumerate(months):
        y = by_year.setdefault(str(int(m) // 12), {"cash": 0.0, "pv": 0.0})
        y["cash"] += float(cash[i])
        y["pv"] += float(pv[i])
    return {"supplier": supplier, "value": float(pv.sum()), "undiscounted": float(cash.sum
()),
            "annual_rate": annual, "method": method, "monthly_rate": r_m, "months": n,
            "first": {"month": month_label(start), "cash": float(cash[0]), "factor": float
(disc[0])},
            "last": {"month": month_label(int(months[-1])), "cash": float(cash[-1]),
                     "factor": float(disc[-1])},
            "how": f"sum over {n} months of cash(t) / (1 + {r_m:.6f})^t, t = 1..{n}",
            "by_year": by_year}


def explain_escalator(model: EngineModel, histories: dict, supplier: str, escalator: str,
                      year: int) -> dict:
    ov, start, n, base_year, months, lev = _setup(model, histories, None)
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
           "month": month_label(int(months[i])), "value": float(vec[i]), "first": month_label
(first),
           "every_months": every}
    if months[i] < first:
        out["how"] = f"before the first adjustment ({month_label(first)}): factor 1"
        return out
    steps = (int(months[i]) - first) // every
    index_year = (first + steps * every) // 12
    terms = [{"series": t.series, "weight": t.weight,
              "ratio": lev[t.series][index_year] / lev[t.series][base_year],
              "contribution": t.weight * lev[t.series][index_year] / lev[t.series]
[base_year]} for t in e.terms]
    out.update(index_year=index_year, fixed=e.fixed, terms=terms,
               how=f"{e.fixed:g}" + "".join(f" + {t['weight']:g} x {t['series']} "
                                            f"[{index_year}/{base_year}]"
                                            f" = {t['ratio']:.4f}" for t in terms) + f" = {vec[i]:.4f}")
    return out


def explain_index(model: EngineModel, histories: dict, series: str, year: int,
                  overrides: dict | None = None) -> dict:
    ov, start, n, base_year, months, lev = _setup(model, histories, overrides)
    spec = IndexSpec(**{**model.indices[series].model_dump(), **ov.get(f"index:{series}",
{})})
    h = histories.get(series, ())
    out = {"series": series, "year": year, "base_year": base_year, "value": lev[series]
[year],
           "method": spec.method, "method_label": METHODS[spec.method]["label"], "window":
spec.years,
           "history": [{"year": y, "value": v} for y, v in h]}
    if spec.method == "path":
        out["how"] = f"explicit level for {year}"
        return out
    r = rate_for(h, spec.method, spec.rate, spec.years)
    out["rate"] = r
    if spec.method == "mean_yoy":
        pts = h[-spec.years:]
        steps = [(b[0], b[1] / a[1] - 1) for a, b in zip(pts, pts[1:])]
        out["rate_how"] = "average of " + ", ".join(f"{y}: {c:+.2%}" for y, c in steps) + " "
= {r:+.4%}"
    out["how"] = f"(1 + {r:+.4%}) ^ ({year} - {base_year}) = {lev[series][year]:.4f}"
    return out


def check_consistency(model: EngineModel, histories: dict, overrides: dict | None = None) ->
bool:
    """explain_npv reproduces evaluate() for every supplier (used by the tests)."""
    r = evaluate(model, histories, overrides)
    return all(abs(explain_npv(model, histories, s, overrides)["value"] - v["npv"]
["tco_esc"]) < 1e-6
               for s, v in r["suppliers"].items())


E7. engine/cli.py

python -m engine.cli IN-CRUT-EBUS prints sticker vs lifetime NPV and the winner; --set /
--index-years for what-ifs.

[python]
"""cli.py - print the award for one tender.

    python -m engine.cli IN-CRUT-EBUS
    python -m engine.cli IN-CRUT-EBUS --set GreenMetro.unit_rate=66 --set discount_rate=0.10
    python -m engine.cli IN-CRUT-EBUS --index-years 5 --json

Reads data/output/<rfp_id>/cost_model.json + frozen_indices/ and config/buyer_policy.json.
"""

import argparse
import json
from pathlib import Path

from . import award, evaluate, explain_escalator, load_case

ROOT = Path(__file__).resolve().parent.parent


def parse_value(v: str):
    try:
        return float(v)
    except ValueError:
        return v


def main() -> None:
    ap = argparse.ArgumentParser(description="trustcost_ai engine: lifetime cost and award
for one tender.")
    ap.add_argument("case", help="RFQ id (folder under data/output/)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override, e.g. GreenMetro.unit_rate=66, discount_rate=0.10, rfq.
contract.start=2026-01")
    ap.add_argument("--index-years", type=int, help="index window for every series (mean_yoy
N points)")
    ap.add_argument("--json", action="store_true", help="print the full evaluate() result as
JSON")
    args = ap.parse_args()

    policy = json.loads((ROOT / "config" / "buyer_policy.json").read_text())
    model, histories = load_case(ROOT / "data" / "output" / args.case, policy)
    overrides = {k: parse_value(v) for k, _, v in (s.partition("=") for s in args.set)}
    if args.index_years:
        overrides.update({f"index:{s}": {"method": "mean_yoy", "years": args.index_years}
                          for s in model.indices})

    result = evaluate(model, histories, overrides)
    if args.json:
        print(json.dumps(result, indent=1))
        return
    sticker, lifetime = award(result, "tco", "STICKER"), award(result, "tco_esc", "LIFETIME")
    d = result["discount"]
    print(f"{model.rfp_id}: {result['months']} months from {result['start']}, base year
{result['base_year']}, "
          f"discount {d['annual']:.1%} ({d['method']})" + (f", overrides {overrides}" if
overrides else ""))
    print(f"\n {'supplier':12} {'sticker NPV':>12} {'lifetime NPV':>13}
{'escalation':>11} factor at end")
    for name, npv in lifetime.ranking:
        s = result["suppliers"][name]
        esc = next(iter(model.suppliers[name].escalators), None)
        end = explain_escalator(model, histories, name, esc.id, int(result["start"][:4]) +
result["months"] // 12 - 1,
                                overrides)["value"] if esc else 1.0
        print(f" {name:12} {s['npv']['tco'] / 1e7:10.2f} Cr {npv:11.2f} Cr {npv / (s['npv']
['tco'] / 1e7) - 1:+10.1%}"
              f"  x{end:.4f}")
    print(f"\n cheapest sticker : {sticker.winner} (by {sticker.margin_cr:.2f} Cr)")
    print(f" lifetime winner  : {lifetime.winner} (by {lifetime.margin_cr:.2f} Cr,
{lifetime.margin_pct:.2f}%)")
    if lifetime.excluded:
        print(f" not ranked (cost model incomplete): {lifetime.excluded}")


if __name__ == "__main__":
    main()


E8. engine/__init__.py

Public API: load_case, evaluate, award, rerun, explain_*.

[python]
"""engine - trustcost_ai's deterministic TCO / NPV engine (no AI, no network).

The AI builds the inputs (TrueCost's cost_model.json); this code decides. Same inputs ->
same numbers.
"""

    from engine import load_case, evaluate, award
    model, histories = load_case("data/output/IN-CRUT-EBUS", policy) # overrides={} = the baseline
    result = evaluate(model, histories, evaluations)                 # ranking, winner, margin (crore)
    print(award(result))
"""

from .evaluate import evaluate
from .explain import explain_escalator, explain_index, explain_npv
from .load import load_case
from .rank import Award, award, rerun

__all__ = ["evaluate", "load_case", "award", "rerun", "Award", "explain_npv",
           "explain_escalator", "explain_index"]


E9. tests/test_engine.py

17 tests, no network: spec index rates, hand calculation, determinism, override scopes,
explain == evaluate, escalation flip, incomplete bidders.

[python]
"""Engine tests: index maths (spec 9.3 numbers), a hand-calculated model, determinism,
overrides,
explain == evaluate, ranking. No files, no network, no model calls."""

import pytest

from engine import award, evaluate, explain_escalator, explain_index, explain_npv, rerun
from engine.explain import check_consistency
from engine.indices import levels, rate_for
from engine.model import Driver, EngineModel, Escalator, IndexSpec, Line, Param, Supplier,
Term

CPI = ((2021, 122.025), (2022, 129.225), (2023, 136.4), (2024, 141.5833), (2025, 145.5417))
WPI = ((2021, 131.7), (2022, 142.1), (2023, 140.6), (2024, 141.6), (2025, 144.8167))

# --------------------------------------------------------------------------------------
# indices
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("hist, years, expect", [(CPI, 3, 0.0330), (CPI, 5, 0.0451), (WPI,
3, 0.0149), (WPI, 5, 0.0246)])
def test_mean_yoy_matches_spec(hist, years, expect):
    """trustcost_ai spec 9.3: window = last N points (3 points -> 2 yearly changes)."""
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

# --------------------------------------------------------------------------------------
# a model small enough to compute by hand
# --------------------------------------------------------------------------------------
def tiny(rate_a=100.0, rate_b=95.0, fixed_b=0.2) -> EngineModel:
    """Two suppliers, 1 line each: rate x 10 units/month, 24 months from 2026-01, index
fixed 10%/yr,
    first adjustment 2026-07 then every 6 months, 12% simple discount."""
    def sup(name, rate, fixed):
        return Supplier(name=name, parameters={"rate": Param(value=rate, source=f"term:{name}")},
                        drivers={"d": Driver(id="d", per_month=10)},
                        escalators=[Escalator(id="e", kind="index_formula", fixed=fixed,
                                              terms=[Term(series="IDX", weight=1 - fixed)],
                                              first="p:start+6", every="c:6",
                                              source="formula:f")],
                        lines=[Line(id="L", factors=["p:rate", "d:d"], start="p:start",
                                    escalators=["e"])])
    return EngineModel(rfp_id="T", horizon_start="p:start", horizon_months="c:24",
                       base_year="c:2025",
                       discount_rate="c:0.12", monthly_rate_method="simple",
                       parameters={"start": Param(value="2026-01", kind="month",
                                                  source="decision:start")},
                       indices={"IDX": IndexSpec(series="IDX", method="fixed", years=None,
                                                 rate=0.10)},
                       suppliers={"A": sup("A", rate_a, 0.5), "B": sup("B", rate_b,
fixed_b)})


H = {"IDX": ()}


def test_hand_calculation():
    r = evaluate(tiny(), H)["suppliers"]["A"]
    # factor: 1.0 for 2026-01..06; 0.5+0.5*1.1 = 1.05 for 2026-07..12; 0.5+0.5*1.21 = 1.105
for 2027
    f = [1.0] * 6 + [1.05] * 6 + [1.105] * 12
    cash = [1000 * x for x in f]
    assert r["totals"]["tco"] == pytest.approx(24000)
    assert r["totals"]["tco_esc"] == pytest.approx(sum(cash))
    assert r["npv"]["tco_esc"] == pytest.approx(sum(c / (1 + 0.01) ** (t + 1) for t, c in
enumerate(cash)))
    assert r["escalators"]["e"]["by_year"] == {"2026": pytest.approx(1.05), "2027": pytest.
approx(1.105)}


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
    assert evaluate(tiny(), H, {"index:IDX": {"rate": 0.0}})["suppliers"]["A"]["npv"]
["tco_esc"] < base
    assert evaluate(tiny(), H, {"discount_rate": 0.0})["suppliers"]["A"]["npv"]["tco_esc"] >
base


def test_compound_monthly_rate():
    r = evaluate(tiny(), H, {"monthly_rate_method": "compound"})
    assert r["discount"]["monthly"] == pytest.approx(1.12 ** (1 / 12) - 1)

# --------------------------------------------------------------------------------------
# explain == evaluate
# --------------------------------------------------------------------------------------
def test_explain_npv_reproduces_evaluate():
    assert check_consistency(tiny(), H)
    assert check_consistency(tiny(), H, {"discount_rate": 0.07, "A.rate": 80.0})


def test_explain_escalator_and_index():
    e = explain_escalator(tiny(), H, "A", "e", 2027)
    assert e["value"] == pytest.approx(1.105) and e["index_year"] == 2027
    assert e["fixed"] + sum(t["contribution"] for t in e["terms"]) == pytest.approx(e
["value"])
    i = explain_index(tiny(), H, "IDX", 2027)
    assert i["value"] == pytest.approx(1.21)
    assert explain_npv(tiny(), H, "A")["undiscounted"] == pytest.approx(evaluate(tiny(), H)
["suppliers"]["A"]["totals"]["tco_esc"])

# --------------------------------------------------------------------------------------
# award / escalation flip
# --------------------------------------------------------------------------------------
def test_escalation_flip_and_rerun():
    """B is cheaper on the sticker (95 < 100) but fully indexed; with 10%/yr inflation A
wins lifetime."""
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
    a = evaluate(m, H)
    assert a.winner == "A" and a.excluded == ["B"] and a.runner_up == ""


C. Verification (run once, in this order)

[bash]
python -m pytest tests -q
# expect: 17 passed
python -m engine.cli IN-CRUT-EBUS


Expected (server run, rates 63.0 / 61.0 / 65.5, start 2026-04, base year 2025, 144 months,
12 % compound):

--------------------------------------------------------------------------------------
supplier        sticker NPV   lifetime NPV   escalation   factor at end
GreenMetro        533.01 Cr      549.02 Cr       +3.0%    x1.0760
MetroLink         516.09 Cr      562.64 Cr       +9.0%    x1.2287
UrbanDrive        554.16 Cr      575.23 Cr       +3.8%    x1.0962

cheapest sticker : MetroLink (by 16.92 Cr)
lifetime winner  : GreenMetro (by 13.61 Cr, 2.48%)
--------------------------------------------------------------------------------------


Small differences are expected if your live index downloads include a newer month (CPI-IW
2025 is a partial
year); the winners must be the same.

What-ifs (these are exactly what RedSeal will run):

[bash]
python -m engine.cli IN-CRUT-EBUS --set GreenMetro.unit_rate=66                   <- the words-vs-figure correction
#    lifetime winner  : MetroLink (by 12.53 Cr)
flips the award
python -m engine.cli IN-CRUT-EBUS --set discount_rate=0.10 --index-years 5
#    GreenMetro 642.82 / MetroLink 674.23 / UrbanDrive 683.71 -> every bidder ~+94..112 Cr
(understated)


Index check (python -c or a REPL):

[python]
import json
from engine import load_case, explain_index
m, h = load_case("data/output/IN-CRUT-EBUS", json.load(open("config/buyer_policy.json")))
print(explain_index(m, h, "in_cpi_iw_all_india", 2030)["rate_how"])
# average of 2024: +4.07%, 2025: +2.95% = +3.5066%


D. The demo story this produces (for RedSeal, next)

act	engine	evidence
1. Escalation flip (TrueCost)	MetroLink is the cheapest sticker (61.00) but 70 % indexed; GreenMetro (fixed 0.64) wins the 12-year lifetime NPV	sticker winner MetroLink by 16.92 Cr; lifetime winner GreenMetro by 13.61 Cr
2. RedSeal extraction flip -> OVERTURNED	GreenMetro's figure 63.00 vs words Sixty Six; tender: words prevail. Override GreenMetro.unit_rate=66	lifetime winner flips to MetroLink (by 12.53 Cr)
3. RedSeal assumption check -> UNDERSTATED	policy 12 % / 3-point index vs the tender-style basis 10 % / 5-point	every NPV rises ~94-112 Cr, winner unchanged

Robustness (checked on the server): acts 1 and 2 hold in 18/18 scenarios - base year 2024/
2025 x start
2026-01/04/07 x discount 10/12/14 %.

Notes for the builder

⚬ Do NOT put any LLM call or network access in engine/. load.py is the only file that
reads disk.

⚬ Overrides never mutate the model (tested). Keys: "<param>" (any supplier), "<Supplier>.<param>" (one
supplier), "discount_rate", "monthly_rate_method", "base_year", "horizon_months",
"driver_scale",
"index:<series>": {"method", "years", "rate"}. This is what makes the spec numbers match.

⚬ Index window = last N POINTS (not N changes). This is what makes the spec numbers match.

⚬ rank.award() ranks only bidders with status ok; others go to excluded.

⚬ Amounts inside the engine are in base currency (INR); rank.py converts to crore (/1e7)
for display only.

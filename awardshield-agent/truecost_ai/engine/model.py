"""model.py - the EngineModel: the clean, validated input of evaluate().

load.py builds it from TrueCost's cost_model.json (+ frozen index files). Every line is a COST.

Tokens used in lines / escalators / horizon:
    p:<param>       value of a parameter                 1-p:<param>   one minus it
    c:<number>      a constant                           d:<driver>    the driver's value that month
Month tokens: 'p:<param>' or 'c:YYYY-MM', optional '+N' / '-N' months offset.
Windows are half-open: start <= month < end ('' end = end of the horizon).
"""

from typing import Literal

from pydantic import BaseModel, Field


class Param(BaseModel):
    value: float | str  # a number, or 'YYYY-MM' for a month, or a choice
    kind: Literal["number", "month", "choice"] = "number"
    unit: str = ""
    source: str = ""
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
    per_month: float  # volume per month (already scaled)
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
    rate: str = ""  # number token (compound)
    first: str = ""  # month token of the first adjustment
    every: str = ""  # number token: months between adjustments
    source: str = ""


class Line(BaseModel):
    id: str
    role: str = "cost"  # display grouping only; every line is a cost
    factors: list[str]
    start: str
    end: str = ""
    escalators: list[str] = []
    when: str = ""  # '<param>=<value>[;...]': counts only in that scenario


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
    horizon_start: str  # month token
    horizon_months: str  # number token
    base_year: str  # number token (index level 1.0 in this year)
    discount_rate: str  # number token (annual fraction)
    monthly_rate_method: Literal["simple", "compound"] = "compound"
    parameters: dict[str, Param]  # shared rfq.* parameters
    indices: dict[str, IndexSpec]  # one per published series, shared by suppliers
    suppliers: dict[str, Supplier]

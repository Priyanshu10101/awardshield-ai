"""load.py - TrueCost output -> EngineModel + index histories (the only file that reads disk).

    model, histories = load_case(output_dir, policy)        # output_dir = <output_dir>/<rfq_id>

Adapts TrueCost's cost_model.json to the engine:
    - a parameter's number / month / choice (stored in separate fields) -> one typed value;
      a parameter with none of them is left out (a token that needs it fails in evaluate());
    - a year written as text ('2025') or a month written as number -> normalised;
    - shared rfq.* parameters stay shared; supplier parameters stay with their supplier;
    - drivers: TrueCost's per_month volume x the driver's scale (TrueCost stores them apart);
    - every series a supplier escalates with gets ONE IndexSpec (method from the supplier's spec,
      else the company policy default) and its history from frozen_indices/<series>.json;
    - a supplier that is not 'ok' and cannot be loaded is kept with no lines (never ranked).
"""

import json
import re
from pathlib import Path

from .model import Driver, EngineModel, Escalator, IndexSpec, Line, Param, Supplier

MONTH = re.compile(r"^\d{4}-\d{2}$")
YEAR = re.compile(r"^\d{4}$")


def _meta(raw: dict) -> dict:
    return {k: raw.get(k, "") or "" for k in ("unit", "source", "source_kind", "quote")}


def _param(raw: dict) -> Param | None:
    """TrueCost parameter -> Param with exactly one typed value (None when it has none)."""
    value = raw.get("value")
    month = str(raw.get("month") or "").strip()
    choice = str(raw.get("choice") or "").strip()
    if value is not None:
        return Param(value=float(value), kind="number", **_meta(raw))
    if MONTH.match(month):
        return Param(value=month, kind="month", **_meta(raw))
    if YEAR.match(month):  # a year stored as a month string
        return Param(value=float(month), kind="number", **_meta(raw))
    if choice:
        return Param(value=choice, kind="choice", **_meta(raw))
    return None


def _params(raw: dict) -> dict[str, Param]:
    return {k: p for k, v in raw.items() if (p := _param(v)) is not None}


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


def _supplier(name: str, s: dict) -> Supplier:
    drivers = {}
    for k, d in s["drivers"].items():
        if d.get("per_month") is None:
            raise ValueError(f"driver '{k}' has no monthly volume ({d.get('built_as', '')})")
        drivers[k] = Driver(id=k, per_month=float(d["per_month"]) * float(d.get("scale", 1.0) or 1.0),
                            source=d.get("source", ""), built_as=d.get("built_as", ""))
    return Supplier(
        name=name,
        status=s.get("status", "ok"),
        parameters=_params(s.get("parameters", {})),
        drivers=drivers,
        escalators=[Escalator(**{k: v for k, v in e.items() if k in Escalator.model_fields})
                    for e in s.get("escalators", [])],
        lines=[Line(**{k: v for k, v in ln.items() if k in Line.model_fields}) for ln in s["lines"]],
    )


def load_case(output_dir: str | Path, policy: dict | None = None) -> tuple[EngineModel, dict[str, tuple]]:
    out = Path(output_dir)
    cm = json.loads((out / "cost_model.json").read_text())
    template = default_method(policy or {})

    suppliers, indices = {}, {}
    for name, s in cm["suppliers"].items():
        try:
            suppliers[name] = _supplier(name, s)
        except (ValueError, KeyError, TypeError) as e:
            if s.get("status", "ok") == "ok":
                raise ValueError(f"{name}: {e}") from e
            suppliers[name] = Supplier(name=name, status=f"{s.get('status')} (not loadable: {e})", lines=[])
            continue
        for series, spec in (s.get("indices") or {}).items():
            spec = {k: v for k, v in spec.items() if v is not None}
            indices.setdefault(series, IndexSpec(**{**template.model_dump(), **spec, "series": series}))
        for e in s.get("escalators", []):
            for t in e.get("terms", []):
                indices.setdefault(t["series"], template.model_copy(update={"series": t["series"]}))

    h = cm["horizon"]
    model = EngineModel(
        rfp_id=cm.get("rfp_id") or cm["rfq_id"],
        currency=cm.get("currency", "INR"),
        horizon_start=h["start"], horizon_months=h["months"],
        base_year=h["base_year"], discount_rate=h["discount_rate"],
        monthly_rate_method=str((policy or {}).get("finance.monthly_rate_method", "compound")),
        parameters=_params(cm["shared_parameters"]),
        indices=indices,
        suppliers=suppliers,
    )

    # a missing frozen file is an empty history: evaluate() fails only if that series is needed
    histories = {}
    for series in indices:
        f = out / "frozen_indices" / f"{series}.json"
        histories[series] = _history(f) if f.exists() else ()
    return model, histories

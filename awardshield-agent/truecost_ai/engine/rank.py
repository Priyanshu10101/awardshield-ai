"""rank.py - turn an evaluate() result into the award: ranking, winner, margin. Pure functions.

    award(result)                               -> Award(ranking=[(supplier, npv_cr)], winner, runner_up,
                                                         margin_cr, margin_pct)
    award(result, metric="tco")                 -> the same on the unescalated NPV (the 'sticker' view)
    rerun(model, histories, overrides, label)   -> Award for one what-if (RedSeal uses this)

Only suppliers whose cost model is complete (status 'ok') are ranked unless include_incomplete=True.
Amounts are reported in crore (1 crore = 1e7) - the engine itself works in base currency units.
"""

from pydantic import BaseModel

from .evaluate import evaluate
from .model import EngineModel

CRORE = 1e7


class Award(BaseModel):
    label: str = "BASELINE"
    metric: str = "tco_esc"
    ranking: list[tuple[str, float]]  # (supplier, NPV in crore), cheapest first
    winner: str
    runner_up: str = ""
    margin_cr: float = 0.0
    margin_pct: float = 0.0
    excluded: list[str] = []  # suppliers not ranked (incomplete cost model)


def award(result: dict, metric: str = "tco_esc", label: str = "BASELINE",
          include_incomplete: bool = False) -> Award:
    sup = result["suppliers"]
    ranked = [n for n, v in sup.items() if include_incomplete or v["status"] == "ok"]
    if not ranked:
        raise ValueError("no supplier with a complete cost model to rank")
    rows = sorted(((n, sup[n]["npv"][metric] / CRORE) for n in ranked), key=lambda x: (x[1], x[0]))
    margin = rows[1][1] - rows[0][1] if len(rows) > 1 else 0.0
    return Award(label=label, metric=metric, ranking=rows, winner=rows[0][0],
                 runner_up=rows[1][0] if len(rows) > 1 else "", margin_cr=margin,
                 margin_pct=margin / rows[0][1] * 100 if rows[0][1] else 0.0,
                 excluded=sorted(set(sup) - set(ranked)))


def rerun(model: EngineModel, histories: dict, overrides: dict | None, label: str = "RERUN",
          metric: str = "tco_esc") -> Award:
    return award(evaluate(model, histories, overrides), metric=metric, label=label)

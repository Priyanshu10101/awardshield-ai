"""truecost_ai.engine - TrueCost's deterministic TCO / NPV engine (no AI, no network).

TrueCost's agents build the inputs (cost_model.json); this code decides. Same inputs -> same numbers.

    from truecost_ai.engine import load_case, evaluate, award
    model, histories = load_case("../output/IN-CRUT-EBUS", policy)
    result = evaluate(model, histories)          # overrides={} = the baseline
    print(award(result))                         # ranking, winner, margin (crore)
"""

from .evaluate import evaluate
from .explain import explain_escalator, explain_index, explain_npv
from .load import load_case
from .rank import Award, award, rerun

__all__ = ["evaluate", "load_case", "award", "rerun", "Award", "explain_npv",
           "explain_escalator", "explain_index"]

"""schemas.py - what the RedSeal sub-agents return and what the prover writes.

Challengers PROPOSE (LLM output, lists with ids - no free-key dicts). The prover VERIFIES and PROVES
(Python). Every challenge is a concrete numeric correction the engine can re-run.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    document: str = Field(description="File name exactly as in its DOCUMENT header.")
    page: str = Field("", description="Page number where it is printed.")
    quote: str = Field(description="The printed sentence or table row, copied verbatim.")


# -----------------------------------------------------------------------------
# challenger outputs
# -----------------------------------------------------------------------------

class ExtractionChallenge(BaseModel):
    challenge_id: str = Field(description="Short unique id, e.g. 'greenmetro_rate_words'.")
    supplier: str = Field(description="Bidder name exactly as in the case.")
    param: str = Field(description="The cost-model parameter id challenged (from the parameter list you were given).")
    kind: Literal["figure_vs_words", "misread", "wrong_term", "wrong_weight"] = Field(
        description="figure_vs_words = the printed figure and the amount in words disagree; misread = the "
                    "document prints a different value than the model holds; wrong_weight = an escalation "
                    "weight / fixed share differs from the printed formula; wrong_term = the model used a "
                    "different term than the one the bid prices.")
    extracted_value: float = Field(description="The value the cost model holds now.")
    corrected_value: float = Field(description="The value you claim the document actually establishes.")
    amount_in_words: str = Field("", description="For figure_vs_words: the words exactly as printed.")
    evidence_for: list[Evidence] = Field(description="Where the corrected value is printed / the rule that makes it "
                                                     "prevail (bid page, tender clause).")
    evidence_against: list[Evidence] = Field(default_factory=list,
                                             description="Any printed clause or figure that supports the extracted "
                                                         "value instead. Never omit one you saw.")
    reasoning: str = Field(description="Two or three plain sentences: what is wrong and why the correction holds.")


class ExtractionChallengeRecord(BaseModel):
    challenges: list[ExtractionChallenge] = Field(default_factory=list)
    checked: list[str] = Field(default_factory=list, description="What you checked and found correct, one line each.")


class AssumptionChallenge(BaseModel):
    challenge_id: str
    setting: Literal["discount_rate", "index_window", "contract_months", "base_year", "award_metric", "other"] = Field(
        description="Which evaluation setting is challenged.")
    used_value: str = Field(description="The value the cost model / company policy uses now.")
    should_be: str = Field(description="The value the governing rule prescribes (a number, or 'year_one' for the "
                                       "award metric).")
    rule_source: Literal["tender", "buyer_rules"] = Field(
        description="tender = a clause of the tender document; buyer_rules = the buyer's evaluation rules given to you.")
    rule_quote: str = Field(description="The governing clause / rule, verbatim.")
    rule_document: str = Field("", description="Tender file name when rule_source is 'tender'.")
    reasoning: str = Field(description="Two or three plain sentences.")


class AssumptionChallengeRecord(BaseModel):
    challenges: list[AssumptionChallenge] = Field(default_factory=list)
    checked: list[str] = Field(default_factory=list)


class Narrative(BaseModel):
    headline: str = Field(description="One sentence: the verdict and the reason.")
    findings: list[str] = Field(description="One plain sentence per verified challenge, with its proven effect.")
    recommendation: str = Field(description="What the buyer must do before signing, in two or three sentences.")


# -----------------------------------------------------------------------------
# prover outputs (Python)
# -----------------------------------------------------------------------------

class Rerun(BaseModel):
    label: str
    ranking: list[tuple[str, float]]  # (supplier, NPV crore) cheapest first
    winner: str
    margin_cr: float
    margin_pct: float


class ProvenChallenge(BaseModel):
    challenge_id: str
    agent: Literal["extraction_challenger", "assumption_challenger"]
    kind: str
    target: str  # parameter or setting
    supplier: str = ""
    original_value: str
    corrected_value: str
    status: Literal["verified", "contested", "rejected", "finding"]
    checks: list[str]  # what the prover verified, one line each
    evidence: list[dict] = []
    evidence_against: list[dict] = []
    reasoning: str = ""
    overrides: dict = {}
    rerun: Optional[Rerun] = None
    effect: str = ""  # winner changed / cost moved, in words built from numbers


class FlipThreshold(BaseModel):
    supplier: str
    param: str
    current: float
    threshold: float  # value at which this supplier's rank vs the other flips
    change_pct: float
    against: str  # the supplier it flips with
    plausible: bool  # |change| <= the plausible band


class SensitivityRow(BaseModel):
    driver: str
    low_label: str
    high_label: str
    winner_low: str
    winner_high: str
    swing_cr: float  # winner's NPV high - low
    flips: bool


class Verdict(BaseModel):
    rfq_id: str
    status: Literal["OVERTURNED", "UNDERSTATED", "CERTIFIED_ROBUST"]
    contested: bool = False  # the deciding challenge rests on a disputed rule
    original_winner: str
    final_winner: str
    baseline: Rerun
    challenges: list[ProvenChallenge]
    flip_thresholds: list[FlipThreshold]
    sensitivity: list[SensitivityRow]
    fragile: bool
    summary: str  # deterministic one-paragraph summary
    narrative: Optional[Narrative] = None

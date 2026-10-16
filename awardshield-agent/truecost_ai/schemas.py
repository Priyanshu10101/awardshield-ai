"""schemas.py - the typed output of every TrueCost sub-agent.

Each extractor sub-agent is an LlmAgent with `output_schema=<one of the
*Record models>`:
Gemini must answer with exactly these fields, and the Python checker
validates the same model.
Every Field description is read by the model - it is part of the prompt.

Rules for models the LLM fills:
 - lists of objects with an id, never dict[str, X] (free keys break
   structured output);
 - Optional[...] = None for "not printed" - 0 means the document prints 0;
 - every value carries Evidence (document, page, verbatim quote).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

SourceKind = Literal["proposal", "clarification", "contract", "rfp"]


# -----------------------------------------------------------------------------
# shared
# -----------------------------------------------------------------------------

class Evidence(BaseModel):
    document: str = Field(
        description="Copy the exact file name of the source document shown in its document header."
    )
    page: str = Field(
        "",
        description="Give the page, sheet and cell, or section heading where the value appears.",
    )
    quote: str = Field(
        description="Copy the supporting sentence or table row verbatim. Do not paraphrase."
    )


class OpenQuestion(BaseModel):
    key: str = Field(
        description="Provide a short dotted identifier for the unresolved question."
    )
    scope: Literal["rfq", "supplier"] = Field(
        description="Use 'rfq' when the answer applies to all suppliers, or 'supplier' when it applies to one supplier."
    )
    question: str = Field(
        description="One plain-language question a procurement analyst can answer without reading a formula."
    )
    options: list[str] = Field(
        default_factory=list,
        description="List the choices printed in the source documents, if any.",
    )
    suggestion: str = Field(
        "",
        description="Give the best-supported answer for the user to confirm, or leave empty if none is supported.",
    )
    why: str = Field(
        description="Explain why the source documents do not settle the question and cite the document and location."
    )


# -----------------------------------------------------------------------------
# volume (output of volume_extractor)
# -----------------------------------------------------------------------------

class VolumeComponent(BaseModel):
    name: str = Field(
        description="Give a short label for the volume input represented by this number."
    )
    value: float = Field(
        description="The number exactly as printed. No arithmetic, no unit conversion."
    )
    unit: str = Field(
        description="Copy the unit exactly as printed, using a generic unit label where applicable."
    )
    evidence: Evidence


class VolumePoint(BaseModel):
    period: str = Field(
        description="Copy the printed period label, such as a year, date, or phase."
    )
    value: float = Field(description="Value as printed for that period.")


class VolumeDriver(BaseModel):
    driver_id: str = Field(description="Provide a short unique id for this volume driver.")
    label: str = Field(description="Copy the label used for this volume driver.")
    billing_unit: str = Field(
        description="Copy the unit the price is charged per, such as 'units' or 'per unit per day'."
    )
    components: list[VolumeComponent] = Field(
        description="Every printed number the volume is built from. Do NOT multiply them yourself; the checker does."
    )
    build_rule: str = Field(
        description="Describe in words how the printed components combine. Do not calculate or infer a different rule."
    )
    ramp: list[VolumePoint] = Field(
        default_factory=list,
        description="If volumes are printed over time, list every period in order; never extend or interpolate.",
    )
    includes_buffer_pct: Optional[float] = Field(
        None,
        description="Copy the explicitly stated percentage buffer included in the volume, or use null if none is printed.",
    )
    stream: str = Field(
        "",
        description="Name the separately priced stream, lot, or item. Use the same value for alternatives in that stream.",
    )
    primary: bool = Field(
        True,
        description="Set true for the one series the source document asks to be priced within this stream; set false for alternatives.",
    )
    choice_reason: str = Field(
        "",
        description="Explain briefly why this series is primary or an alternative, using only printed evidence.",
    )
    markers: list[str] = Field(
        default_factory=list,
        description="List printed phase or milestone markers that apply to this volume driver.",
    )
    notes: str = Field(
        "",
        description="Record relevant printed context, including both figures when a volume is stated as a percentage of capacity.",
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="List the source evidence supporting this volume driver.",
    )


class Phase(BaseModel):
    label: str = Field(description="Copy the printed label for this phase.")
    start: str = Field("", description="Copy the printed phase start, or leave empty if not stated.")
    end: str = Field("", description="Copy the printed phase end, or leave empty if not stated.")
    evidence: Evidence = Field(description="Provide the source evidence for this phase.")


class ContractFacts(BaseModel):
    term_months_options: list[int] = Field(
        description="List each allowed contract duration in months. For example, either 5 or 10 years becomes [60, 120]."
    )
    supply_start: str = Field(
        "",
        description="Give the stated start month in 'YYYY-MM' format, or leave empty if not printed.",
    )
    adjustment_frequency_months: Optional[int] = Field(
        None,
        description="Give the stated interval between price revisions in months, or null if not printed.",
    )
    first_adjustment_months: Optional[int] = Field(
        None,
        description="Give the number of months until the first price adjustment, or null if not printed. Treat 'first anniversary' as 12 months.",
    )
    adjustment_trigger: str = Field(
        "",
        description="Copy any printed threshold that triggers a revision, or leave empty if none is stated.",
    )
    base_index_date: str = Field(
        "",
        description="Copy the stated base date for the index values, or leave empty if not printed.",
    )
    evidence: list[Evidence] = Field(default_factory=list)


class VolumeRecord(BaseModel):
    drivers: list[VolumeDriver]
    contract: ContractFacts
    phases: list[Phase] = Field(
        default_factory=list,
        description="List the printed contract or delivery phases, with their dates and evidence.",
    )
    open_questions: list[OpenQuestion] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# commercial (output of commercial_extractor)
# -----------------------------------------------------------------------------

TermKind = Literal[
    "unit_rate",
    "recurring_fee",
    "one_time_fee",
    "minimum_commitment",
    "power",
    "utility",
    "capacity",
    "supply_mode",
    "demand_basis",
    "escalation_timing",
    "validity",
    "price_case",
    "cost_basis",
    "inclusion",
    "other",
]


class CommercialTerm(BaseModel):
    term_id: str = Field(
        description="Provide a short unique id for this term within the supplier's record."
    )
    kind: TermKind = Field(
        description=(
            "unit_rate: A price charged per unit.\n"
            "recurring_fee: A fee charged repeatedly.\n"
            "one_time_fee: A fee charged once.\n"
            "minimum_commitment: A required minimum purchase or payment.\n"
            "power: A stated power-related charge or basis.\n"
            "utility: A stated utility charge or basis.\n"
            "capacity: A stated capacity charge or basis.\n"
            "supply_mode: How the item or service is supplied.\n"
            "demand_basis: The stated basis used to determine demand.\n"
            "escalation_timing: When a price change applies.\n"
            "validity: The period a price or offer remains valid.\n"
            "price_case: A named price option.\n"
            "cost_basis: A supporting figure shown for information, never a price.\n"
            "inclusion: An item explicitly included in another price.\n"
            "other: A term that does not fit another kind."
        )
    )
    label: str = Field(description="The row / item name as printed.")
    amount: Optional[float] = Field(
        None,
        description="The number exactly as printed (64.50 stays 64.5). Null when the term is words only.",
    )
    unit: str = Field(
        "", description="Copy the unit exactly as printed. For example, '25 M per month' is amount 25 with unit 'M/month'."
    )
    currency: str = Field(
        "", description="Copy the currency code exactly as printed, or leave empty if no currency is stated."
    )
    text: str = Field(
        "",
        description="The statement in words when it is not one number (ranges, inclusions, conditions).",
    )
    amount_in_words: str = Field(
        "",
        description="If the document also writes the amount in words, copy it here. Used to cross-check the figure.",
    )
    case: str = Field(
        "",
        description="Price option / case name when the bid offers alternatives.",
    )
    phase: str = Field(
        "", description="Phase or period the amount applies to, if tied to one."
    )
    valid_from: str = Field(
        "", description="'YYYY-MM' when the amount starts on a printed date."
    )
    valid_to: str = Field(
        "", description="'YYYY-MM' when it ends on a printed date."
    )
    quantity: Optional[float] = Field(
        None,
        description="Copy the quantity printed next to a per-unit figure. For example, '<size> x 3 sets' gives quantity 3.",
    )
    applies_to: str = Field(
        "",
        description="Name the item or stream this term prices, or use 'shared' when it applies across items.",
    )
    scope: Optional[Literal["line_item", "total"]] = Field(
        None,
        description="Use 'line_item' for a printed line-item amount or 'total' only when the document prints a total; otherwise null.",
    )
    coverage: Optional[Literal["stated", "included_in"]] = Field(
        None,
        description="Use 'stated' when the document explicitly gives the amount, including zero or not applicable; use 'included_in' when it explicitly says the item is included in another price; otherwise null.",
    )
    source_kind: SourceKind = Field(
        description="Which kind of document it comes from."
    )
    supersedes: str = Field(
        "",
        description="If a later document replaces an earlier figure: the old figure and its document.",
    )
    evidence: Evidence


class CommercialRecord(BaseModel):
    supplier: str
    terms: list[CommercialTerm]
    not_stated: list[str] = Field(
        default_factory=list,
        description="Kinds you looked for and did not find.",
    )
    open_questions: list[OpenQuestion] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# escalation (output of escalation_extractor)
# -----------------------------------------------------------------------------

class IndexedTerm(BaseModel):
    symbol: str = Field(
        description="Copy the index symbol and remove only its timing subscript; for example, X1, Xn, or X0 becomes X."
    )
    weight: float = Field(
        description="Weight as a fraction. Nested weights are multiplied out: '0.8 + 0.2*(0.4A+0.6B) -> A 0.08, B 0.12.'"
    )


class EscalationFormula(BaseModel):
    formula_id: str = Field(
        description="Short unique id, e.g. 'rate_adjustment'."
    )
    applies_to: list[str] = Field(
        description="term_id(s) of the commercial terms this formula escalates."
    )
    formula_text: str = Field(
        description="The formula exactly as printed."
    )
    fixed_weight: float = Field(
        description="The un-indexed (fixed) part as a fraction."
    )
    terms: list[IndexedTerm]
    frequency_months: Optional[int] = Field(
        None, description="How often the price is revised, in months, as printed."
    )
    first_adjustment: str = Field(
        "",
        description="Copy when the first revision happens, using the wording printed in the source document.",
    )
    trigger: str = Field("", description="Revision threshold, verbatim, if any.")
    base_period: str = Field(
        "", description="Base date / period of the index ratios, verbatim."
    )
    applies_to_item: str = Field(
        "",
        description="Name the item this formula applies to, or use 'shared' when it applies across items.",
    )
    supersedes: str = Field(
        "",
        description="If this formula replaces an earlier one, write 'SUPERSEDES: <old formula> (<doc>)'; use 'REVIEW-TABLE ONLY' when it appears only in a review table; otherwise leave empty.",
    )
    source_kind: SourceKind
    evidence: Evidence


class IndexDefinition(BaseModel):
    kind: Literal["price", "wage", "energy", "commodity", "other"] = Field(
        "other",
        description="Classify the statistic as a price, wage, energy, commodity, or other index based on the source document.",
    )
    symbol: str = Field(
        description="Same symbol as in the formula terms."
    )
    name: str = Field(
        description="Full name as the document defines THIS symbol."
    )
    publisher: str = Field(
        "", description="Copy the publisher name as printed, or leave empty if not stated."
    )
    country: str = Field(
        "", description="Copy the country name or code stated for the statistic, or leave empty if not stated."
    )
    region: str = Field(
        "",
        description="Copy the geographic area named for this index, or leave empty if none is stated.",
    )
    printed_url: str = Field(
        "",
        description="URL printed in the document for this index, never invent one.",
    )
    evidence: Evidence


class EscalationRecord(BaseModel):
    supplier: str
    formulae: list[EscalationFormula]
    indices: list[IndexDefinition]
    open_questions: list[OpenQuestion] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# index resolution (output of index_resolver)
# -----------------------------------------------------------------------------

class IndexResolution(BaseModel):
    symbol: str = Field(description="Index symbol exactly as in the escalation record.")
    status: Literal["ok", "needs_user"]
    step: Literal["reuse", "known_source", "printed_url", "web", "user"] = Field(description="The step that resolved it: reuse = "
        "already saved for this tender; known_source = a known official page; printed_url = URL printed in the documents; "
        "web = found by search or "
        "your own knowledge; user = flagged.")
    series_key: str = Field("", description="series_key returned by the tool that saved the series.")
    url: str = Field("", description="Official URL the series was read from.")
    proxy: str = Field("", description="When an official stand-in series is used because the exact statistic "
        "is not published as a series: why (copied from the tool result). The buyer confirms it.")
    reason: str = Field("", description="When status is needs_user: what each step tried and returned.")



class IndexResolutionRecord(BaseModel):
    resolutions: list[IndexResolution]


# -----------------------------------------------------------------------------
# cost model draft (output of cost_model_extractor, ONE supplier)
# writer_agent converts it to the AwardShield CostModel (spec section 3).
# -----------------------------------------------------------------------------

ParamSourceKind = Literal[
    "SOURCE_FACT",
    "ASSUMPTION",
    "DERIVED",
    "LLM_INTERPRETATION",
    "POLICY",
    "DECISION",
]


class ParamDraft(BaseModel):
    id: str
    value: Optional[float] = Field(
        None,
        description="Numeric value (amounts, rates, counts, months of a term, years). Null for a calendar month, or for a choice that has no number.",
    )
    month: str = Field("", description="'YYYY-MM' when the parameter is a calendar month (e.g. a contract start).")
    choice: str = Field("", description="The selected option, or every allowed option, when the parameter is a choice.")
    unit: str = ""
    source: str = Field(
        description="Where the value comes from: 'term:<term_id>', 'formula:<formula_id>', 'volume:<driver_id>', 'policy:<key>', 'decision:<key>', or 'derived:<rule citing the sources above>'. Never empty."
    )
    source_kind: ParamSourceKind
    quote: str = ""


class TermDraft(BaseModel):
    series: str
    weight: float


class EscalatorDraft(BaseModel):
    id: str
    kind: Literal["index_formula", "compound"]
    fixed: float = 0.0
    terms: list[TermDraft] = Field(default_factory=list)
    first: str = Field(
        description="Month token, e.g. 'p:rfq.contract.start +6'."
    )
    every: str = Field(
        description="Frequency token, e.g. 'c:6' = every 6 months."
    )
    source: str = Field(
        description="'formula:<formula_id>' for index formulae."
    )


class LineDraft(BaseModel):
    id: str
    role: str
    factors: list[str] = Field(
        description="Tokens multiplied together: 'p:<param>', '1-p:<param>', 'c:<number>', 'd:<driver>'."
    )
    start: str = "p:rfq.contract.start"
    end: str = ""
    escalators: list[str] = Field(default_factory=list)
    when: str = ""


class IndexSpecDraft(BaseModel):
    series: str
    method: Literal["fixed", "mean_yoy", "cagr", "trend", "path"] = "mean_yoy"
    years: int = 3
    rate: Optional[float] = None


class DriverDraft(BaseModel):
    id: str
    source: str = Field(
        description="'volume:<driver_id>'. Leave points empty; Python fills them."
    )
    scale: float = 1.0


class CostModelDraft(BaseModel):
    supplier: str
    parameters: list[ParamDraft]
    escalators: list[EscalatorDraft]
    lines: list[LineDraft]
    indices: list[IndexSpecDraft]
    drivers: list[DriverDraft]
    horizon_start: str
    horizon_months: str = Field(
        description="Param token, e.g. 'p:rfq.contract.months'."
    )
    base_year: str
    discount_rate: str
    open_questions: list[OpenQuestion] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# report (output of the orchestrator: every bidder's result_<key>, merged)
# -----------------------------------------------------------------------------

class ProxyNote(BaseModel):
    symbol: str = Field(description="Index symbol that uses an official stand-in series.")
    note: str = Field(description="Why the stand-in is used, as the bidder result states it.")


class BidderResult(BaseModel):
    supplier: str = Field(description="Bidder name exactly as in its result.")
    status: Literal["ok", "needs_answers", "failed"] = Field(
        description="Copied from the bidder result."
    )
    quoted_price: str = Field("", description="Copied from the bidder result.")
    escalation: str = Field("", description="Copied from the bidder result.")
    proxies: list[ProxyNote] = Field(default_factory=list, description="Copied from the bidder result.")
    problems: list[str] = Field(default_factory=list, description="Copied from the bidder result.")
    open_questions: list[str] = Field(
        default_factory=list,
        description="The keys of the bidder result's open questions (the questions themselves are in the report's questions).",
    )


class ReportQuestion(OpenQuestion):
    suppliers: list[str] = Field(
        default_factory=list,
        description="Every bidder whose result raised this question.",
    )


class TenderReport(BaseModel):
    rfq_id: str
    title: str = ""
    bidders: list[BidderResult] = Field(description="One entry per bidder result, in the given order.")
    questions: list[ReportQuestion] = Field(
        default_factory=list,
        description="Every open question of every bidder, merged: one entry per key.",
    )
    ready_for_evaluation: list[str] = Field(
        default_factory=list,
        description="Suppliers whose status is 'ok'.",
    )
    summary: str = Field(
        description="3-6 plain sentences on where the tender stands. Never rank bidders or state a total."
    )

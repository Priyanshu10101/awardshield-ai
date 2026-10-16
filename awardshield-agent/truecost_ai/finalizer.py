"""finalizer.py - the last step of each bidder (finalizer_<key>, built by make_finalizer): check the
cost-model draft's links, fill the volumes, write the files and put the bidder's result in
state['result_<key>'] for the orchestrator. A BaseAgent - pure Python, no model call.

What it does (nothing here decides a business question):
1. LINK CHECKS - every token in lines / escalators points at
something that exists, escalator weights
equal the extracted formula's, every index series was
resolved, every parameter has a source, every
decision:<key> it cites has a buyer answer.
2. VOLUMES - drivers get a monthly value from the tender
volume record (Python multiplies the printed
components; a component stated per year becomes per
month).
3. WRITE - output/<rfq_id>/suppliers/<bidder>/
cost_model_part.json (the bidder's part), its records
next to it, and open_questions.json: the questions the
extractors raised plus every proxy index.
Parts are merged into output/<rfq_id>/cost_model.json.

A part with unresolved references is still written (status
'needs_answers') so the buyer sees exactly
what is missing; the merged cost_model.json lists which
bidders are complete.
"""

import json
import re
from datetime import date
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types

from .schemas import ContractFacts, CostModelDraft, EscalationRecord, VolumeRecord
from .settings import OUTPUT_DIR

WEIGHT_TOLERANCE = 0.005
DECISION = re.compile(r"decision:([\w.-]+)")
CONTRACT_FACT = re.compile(r"volume:contract\.(\w+)")
CONTRACT_FIELDS = set(ContractFacts.model_fields) - {"evidence"}
MONTH = re.compile(r"^(\d{4})-(\d{2})(?:-\d{2})?$")
PER_DAY = re.compile(r"(/|per\s*)(day|d)\b", re.I)
PER_HOUR = re.compile(r"(/|per\s*)(hour|hr|h)\b", re.I)
PER_YEAR = re.compile(r"(/|per\s*)(year|annum|yr)\b", re.I)


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip("_"))


#
# -----------------------------------------------------------------
# 1. link checks
#
# -----------------------------------------------------------------
#


def tidy(draft: CostModelDraft, resolutions: list[dict]) -> CostModelDraft:
    """Mechanical clean-up before any check: tokens lose whitespace ('p:x +6' -> 'p:x+6'), a bare
    number becomes a constant ('2024' -> 'c:2024'), and an
    escalator term naming an index by its symbol ('WPI') gets the series_key it was saved under."""
    keys = {r["symbol"]: r["series_key"] for r in resolutions if r.get("status") == "ok" and r.get("series_key")}
    d = draft.model_copy(deep=True)
    def squash(tok: str) -> str:
        tok = re.sub(r"\s+", "", tok)
        return f"c:{tok}" if re.fullmatch(r"-?\d+(\.\d+)?", tok) else tok  # bare '2024' -> 'c:2024'
    for line in d.lines:
        line.factors = [squash(t) for t in line.factors]
        line.start, line.end = squash(line.start), squash(line.end)
    for e in d.escalators:
        e.first, e.every = squash(e.first), squash(e.every)
        for t in e.terms:
            t.series = keys.get(t.series, t.series)
    for f in ("horizon_start", "horizon_months", "base_year", "discount_rate"):
        setattr(d, f, squash(getattr(d, f)))
    return d


def _tokens(draft: CostModelDraft) -> list[str]:
    return [
        *(t for line in draft.lines for t in (*line.factors, line.start, line.end)),
        *(t for e in draft.escalators for t in (e.first, e.every)),
        draft.horizon_start, draft.horizon_months, draft.base_year, draft.discount_rate,
    ]


def missing_parameters(draft: CostModelDraft, volume: VolumeRecord) -> dict[str, str]:
    """{parameter id: why} for every parameter nobody actually gave: no value, a tender contract fact
    the tender leaves empty (a value 'found' there was invented), or referenced but not defined."""
    missing = {}
    for p in draft.parameters:
        if p.value is None and not p.month and not p.choice:
            missing[p.id] = "the cost model found no value for it"
        for field in CONTRACT_FACT.findall(p.source):
            if field in CONTRACT_FIELDS and getattr(volume.contract, field) in (None, "", []):
                missing[p.id] = f"the tender does not state contract.{field}"
    defined = {p.id for p in draft.parameters}
    for tok in _tokens(draft):
        kind, _, name = tok.partition(":")
        name = re.sub(r"[+-]\d+$", "", name)
        if kind in ("p", "1-p") and name and name not in defined:
            missing[name] = "the cost model uses it but no document or answer gives it"
    return missing


def plausible_month(text: str) -> str:
    """A suggested month as 'YYYY-MM', or '' when it is not a month or lies in the past (a start the
    model invented before the tender existed must not be offered as the default answer)."""
    m = MONTH.match(text.strip())
    if not m:
        return ""
    month = f"{m.group(1)}-{m.group(2)}"
    return month if month >= date.today().strftime("%Y-%m") else ""


def tender_says(pid: str, volume: VolumeRecord) -> str:
    """What the tender itself states about a contract-timing parameter (e.g. 'starts at COD')."""
    if not pid.startswith("rfq.contract."):
        return ""
    said = [
        f"tender: '{ph.label}' runs from '{ph.start}' to '{ph.end}' "
        f"({ph.evidence.document} {ph.evidence.page}: \"{ph.evidence.quote[:160]}\")"
        for ph in volume.phases if ph.start or ph.end
    ]
    if volume.contract.term_months_options:
        said.append(f"allowed terms (months): {volume.contract.term_months_options}")
    return "; ".join(said)


def link_problems(
    draft: CostModelDraft,
    escalation: EscalationRecord,
    resolved: set[str],
    volume: VolumeRecord,
    answers: dict,
) -> list[str]:
    params = {p.id: p for p in draft.parameters}
    drivers = {d.id for d in draft.drivers}
    escalators = {e.id for e in draft.escalators}
    formulae = {f.formula_id: f for f in escalation.formulae}
    volume_ids = {d.driver_id for d in volume.drivers}
    problems = []

    def ref(token: str, where: str) -> None:
        kind, _, name = token.partition(":")
        name = re.sub(r"[+-]\d+$", "", name)  # month offset 'p:x+6'
        if kind in ("p", "1-p") and name not in params:
            problems.append(f"{where}: parameter '{name}' is not defined")
        elif kind in ("p", "1-p") and where.startswith("line") and params[name].value is None:
            problems.append(f"{where}: factor '{token}' needs a number, but {name} is a month / choice")
        elif kind == "d" and name not in drivers:
            problems.append(f"{where}: driver '{name}' is not defined")
        elif kind == "c":
            try:
                float(name)
            except ValueError:
                problems.append(f"{where}: '{token}' is not a number")
        elif kind not in ("p", "1-p", "d", "c"):
            problems.append(f"{where}: unknown token '{token}'")

    for p in draft.parameters:
        if not p.source.strip():
            problems.append(f"parameter {p.id}: no source")
        if p.value is None and not p.month and not p.choice:
            problems.append(f"parameter {p.id}: has no value, month or choice")
        for k in DECISION.findall(p.source):
            k = k.rstrip(".")
            if k not in answers:
                problems.append(
                    f"parameter {p.id}: cites decision:{k} but the buyer has not answered it"
                )
        for field in CONTRACT_FACT.findall(p.source):
            if field not in CONTRACT_FIELDS:
                problems.append(
                    f"parameter {p.id}: cites volume:contract.{field}, which is not a tender contract "
                    f"field (fields: {', '.join(sorted(CONTRACT_FIELDS))}) - a cost-model citation error"
                )
            elif getattr(volume.contract, field) in (None, "", []):
                problems.append(
                    f"parameter {p.id}: cites volume:contract.{field} but the tender does not state it"
                )
    primary = {d.driver_id for d in volume.drivers if d.primary}
    for d in draft.drivers:
        if d.source.removeprefix("volume:") not in volume_ids:
            problems.append(
                f"driver {d.id}: source '{d.source}' is not a tender volume driver"
            )
        elif d.source.removeprefix("volume:") not in primary:
            problems.append(
                f"driver {d.id}: '{d.source}' is an ALTERNATIVE (non-primary) tender volume - an "
                f"option or scenario is not part of the base cost; use the primary driver only"
            )
    priced = {d.source.removeprefix("volume:") for d in draft.drivers
              if any(f"d:{d.id}" in line.factors for line in draft.lines)}
    for missing in sorted(primary - priced):  # every stream the tender buys must be in the cost
        problems.append(
            f"tender volume '{missing}' is not priced: no driver / line uses it, so its cost is missing"
        )
    for line in draft.lines:
        for t in line.factors:  # multipliers: numbers only
            ref(t, f"line {line.id}")
        for t in (line.start, line.end):  # the window: a month is fine here
            if t:
                ref(t, f"window of {line.id}")
        for e in line.escalators:
            if e not in escalators:
                problems.append(f"line {line.id}: escalator '{e}' is not defined")
    for f in escalation.formulae:  # fixed + index weights of a formula always total 1
        total = f.fixed_weight + sum(t.weight for t in f.terms)
        if abs(total - 1.0) > WEIGHT_TOLERANCE:
            problems.append(
                f"formula {f.formula_id}: fixed + weights = {total:g}, not 1 - the escalation record "
                f"misread it (quote: \"{f.evidence.quote[:90]}\")"
            )
    for e in draft.escalators:
        ref(e.first, f"escalator {e.id}.first")
        ref(e.every, f"escalator {e.id}.every")
        for t in e.terms:
            if t.series not in resolved:
                problems.append(f"escalator {e.id}: series '{t.series}' was not resolved")
        f = formulae.get(e.source.removeprefix("formula:"))
        if e.kind == "index_formula":
            if f is None:
                problems.append(
                    f"escalator {e.id}: source '{e.source}' is not an extracted formula"
                )
            elif abs(e.fixed - f.fixed_weight) > WEIGHT_TOLERANCE or abs(
                sum(t.weight for t in e.terms) - sum(t.weight for t in f.terms)
            ) > WEIGHT_TOLERANCE:
                problems.append(
                    f"escalator {e.id}: weights differ from formula {f.formula_id}"
                )
    for tok in (
        draft.horizon_start,
        draft.horizon_months,
        draft.base_year,
        draft.discount_rate,
    ):
        ref(tok, "horizon")
    return sorted(set(problems))


#
# -----------------------------------------------------------------
# 2. volumes: printed components -> monthly value
#
# -----------------------------------------------------------------
#


def monthly_volume(driver_id: str, volume: VolumeRecord, hours_per_month: float = 720) -> tuple[float | None, str]:
    """(value per month, how). Product of the printed components, turned into a monthly figure by the
    component that carries the time unit: per year / 12, per day x days per month, per hour x hours
    per month (the policy's calendar.hours_per_month; 720 h = 30 days)."""
    d = next((x for x in volume.drivers if x.driver_id == driver_id), None)
    if d is None or not d.components:
        return None, "no printed components"
    value, period = 1.0, "month"
    for c in d.components:
        value *= c.value
        text = f"{c.unit} {c.name.replace('_', ' ')}"
        if PER_YEAR.search(text) or "per annum" in text:
            period = "year"
        elif PER_DAY.search(text):
            period = "day"
        elif PER_HOUR.search(text):
            period = "hour"
    how = " x ".join(f"{c.value:g} {c.unit}" for c in d.components)
    days = hours_per_month / 24
    if period == "year":
        return value / 12, f"({how}) / 12 months"
    if period == "day":
        return value * days, f"({how}) x {days:g} days/month"
    if period == "hour":
        return value * hours_per_month, f"({how}) x {hours_per_month:g} h/month"
    return value, how


#
# -----------------------------------------------------------------
# 3. draft -> part, parts -> cost_model.json
#
# -----------------------------------------------------------------
#


def to_part(draft: CostModelDraft, volume: VolumeRecord, supplier: str, hours_per_month: float = 720) -> dict:
    drivers = {}
    for d in draft.drivers:
        per_month, how = monthly_volume(d.source.removeprefix("volume:"), volume, hours_per_month)
        drivers[d.id] = {
            "id": d.id,
            "source": d.source,
            "scale": d.scale,
            "per_month": per_month,
            "built_as": how,
            "points": {},  # the engine expands per_month over the horizon
        }
    return {
        "supplier": supplier,
        "parameters": {p.id: p.model_dump(exclude={"id"}) for p in draft.parameters},
        "indices": {i.series: i.model_dump() for i in draft.indices},
        "drivers": drivers,
        "lines": [ln.model_dump() for ln in draft.lines],
        "escalators": [e.model_dump() for e in draft.escalators],
        "horizon": {
            "start": draft.horizon_start,
            "months": draft.horizon_months,
            "base_year": draft.base_year,
            "discount_rate": draft.discount_rate,
        },
    }


def merge(rfq_dir) -> dict:
    """All bidders' parts -> cost_model.json; rfq.* parameters are shared (first definition wins)."""
    parts = [
        json.loads(p.read_text())
        for p in sorted(rfq_dir.glob("suppliers/*/cost_model_part.json"))
    ]
    shared, suppliers = {}, {}
    for part in parts:
        own = {}
        for pid, p in part["parameters"].items():
            if pid.startswith("rfq."):
                shared.setdefault(pid, p)
            else:
                own[pid] = p
        suppliers[part["supplier"]] = {
            **{
                k: part[k]
                for k in ("drivers", "lines", "escalators", "indices")
            },
            "parameters": own,
            "status": part["status"],
        }
    model = {
        "rfq_id": rfq_dir.name,
        "shared_parameters": shared,
        "suppliers": suppliers,
        "horizon": parts[0]["horizon"] if parts else {},
        "complete": sorted(n for n, s in suppliers.items() if s["status"] == "ok"),
        "needs_answers": sorted(
            n for n, s in suppliers.items() if s["status"] != "ok"
        ),
    }
    (rfq_dir / "cost_model.json").write_text(
        json.dumps(model, indent=1, ensure_ascii=False)
    )
    return model


def quoted_price(commercial: dict) -> str:
    """The bid's unit rates as printed (no arithmetic), one line."""
    rates = [
        " ".join(
            x
            for x in (
                f"{t['amount']:g}" if t.get("amount") is not None else t.get("text", ""),
                t.get("currency", "") if t.get("currency", "") not in t.get("unit", "") else "",
                t.get("unit", ""),
                f"({', '.join(filter(None, (t.get('applies_to'), t.get('case'), t.get('phase'))))})"
                if any(t.get(k) for k in ("applies_to", "case", "phase"))
                else "",
            )
            if x
        )
        for t in commercial.get("terms", [])
        if t.get("kind") == "unit_rate"
    ]
    return "; ".join(rates) or "no unit rate found"


def escalation_line(escalation: EscalationRecord) -> str:
    """'F1: 0.15 fixed + 0.45 CPI + 0.4 WPI, every 12 months; ...' or 'none'."""
    out = []
    for f in escalation.formulae:
        terms = " + ".join([f"{f.fixed_weight:g} fixed", *(f"{t.weight:g} {t.symbol}" for t in f.terms)])
        every = f", every {f.frequency_months} months" if f.frequency_months else ""
        out.append(f"{f.formula_id}: {terms}{every}")
    return "; ".join(out) or "no escalation formula"


class Finalizer(BaseAgent):
    """Checks one bidder's cost-model draft, fills volumes, writes the part + open questions,
    merges, and stores the bidder's result in state['result_<key>']."""

    supplier: str
    key: str

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        st, key, supplier = ctx.session.state, self.key, self.supplier
        rfq_dir = OUTPUT_DIR / st["rfq_id"]
        out = rfq_dir / "suppliers" / _slug(supplier)
        out.mkdir(parents=True, exist_ok=True)

        commercial = st.get(f"commercial_{key}") or {}
        index_resolutions = st.get(f"index_resolutions_{key}")
        previous = st.get(f"result_{key}")  # set when this bidder already ran in the session
        volume = VolumeRecord.model_validate(st["volume"])
        escalation = EscalationRecord.model_validate(st[f"escalation_{key}"])
        draft = CostModelDraft.model_validate(st[f"cost_model_{key}"])
        resolutions = (index_resolutions or {}).get("resolutions", [])
        resolved = {r["series_key"] for r in resolutions if r.get("status") == "ok"}

        answers = st.get("answers") or {}
        draft = tidy(draft, resolutions)
        problems = link_problems(draft, escalation, resolved, volume, answers)
        hours = float((st.get("policy") or {}).get("calendar.hours_per_month", 720))
        part = to_part(draft, volume, supplier, hours)  # manifest name, not the model's spelling
        part["status"] = "ok" if not problems else "needs_answers"
        part["problems"] = problems
        part["proxies"] = {
            r["symbol"]: r["proxy"] for r in resolutions if r.get("proxy")
        }

        questions = [
            *commercial.get("open_questions", []),
            *escalation.model_dump()["open_questions"],
            *draft.model_dump()["open_questions"],
        ]
        questions = list(
            {q["key"]: q for q in questions}.values()
        )  # one per key, latest wins
        for pid, why in missing_parameters(draft, volume).items():
            if pid in answers:
                continue  # answered; a remaining problem is the cost model's, not a new question
            asked = next((q for q in questions if q["key"] == pid), None)  # the cost model's own
            invented = next((p for p in draft.parameters if p.id == pid), None)
            is_month = bool(invented and invented.month) or pid.endswith((".start", ".end", "_date"))
            guess = (asked or {}).get("suggestion") or (invented and (invented.month or invented.choice or (
                f"{invented.value:g}" if invented.value is not None else ""))) or ""
            questions = [q for q in questions if q["key"] != pid] + [{
                "key": pid,
                "scope": "rfq" if pid.startswith("rfq.") else "supplier",
                "question": (asked or {}).get("question") or (
                    f"Which month should the cost model assume for {pid} ('YYYY-MM')?" if is_month
                    else f"What value should the cost model use for {pid}?"),
                "options": (asked or {}).get("options", []),
                "suggestion": plausible_month(guess) if is_month else guess,
                "why": "; ".join(filter(None, (why, tender_says(pid, volume), (asked or {}).get("why")))),
            }]
        for sym, why in part["proxies"].items():
            if f"index.proxy.{sym}" in answers:
                continue
            questions.append(
                {
                    "key": f"index.proxy.{sym}",
                    "scope": "rfq",
                    "question": f"Index {sym} uses an official stand-in series. Accept it?",
                    "options": ["accept", "give another official source"],
                    "suggestion": "accept",
                    "why": why,
                }
            )

        for name, data in (
            ("commercial.json", commercial),
            ("escalation.json", st[f"escalation_{key}"]),
            ("index_resolutions.json", index_resolutions),
            ("cost_model_part.json", part),
            ("open_questions.json", questions),
        ):
            (out / name).write_text(json.dumps(data, indent=1, ensure_ascii=False))
        (rfq_dir / "volume.json").write_text(
            json.dumps(st["volume"], indent=1, ensure_ascii=False)
        )
        model = merge(rfq_dir)

        result = {
            "supplier": supplier,
            "status": part["status"],
            "quoted_price": quoted_price(commercial),
            "escalation": escalation_line(escalation),
            "proxies": [{"symbol": s, "note": n} for s, n in part["proxies"].items()],
            "problems": problems,
            "open_questions": questions,
        }
        was = f" (was {previous['status']})" if previous and previous.get("status") != part["status"] else ""
        summary = (
            f"{supplier}: cost model part {part['status']}{was} ({len(draft.lines)} lines, "
            f"{len(problems)} unresolved reference(s), {len(questions)} open question(s). "
            f"Merged: complete={model['complete']} needs_answers={model['needs_answers']})"
        )
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            branch=ctx.branch,
            content=types.Content(
                role="model", parts=[types.Part(text=summary)]
            ),
            actions=EventActions(state_delta={f"result_{key}": result}),
        )


def make_finalizer(supplier: str, key: str) -> Finalizer:
    return Finalizer(
        name=f"finalizer_{key}",
        description=f"Checks links, fills volumes and writes {supplier}'s cost model.",
        supplier=supplier,
        key=key,
    )

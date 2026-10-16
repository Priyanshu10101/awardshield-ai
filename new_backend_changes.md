AwardShield - new backend changes

Every backend change made during the UI work, plus the bid generator that produces the demo numbers.
Paths are relative to awardshield/. Six changes, listed below:

#	File	Change	Type
1	generate_bids.py	recalibrated synthetic bids (figure 63.00 vs words "Sixty Six", MetroLink 70 % indexed, UrbanDrive 65.50, 64,800 km/bus/yr, tender 1376/CRUT)	modified
2	agent/truecost/prompts.py	COST_MODEL rule K1: FIGURE vs WORDS	small edit
3	agent/recorder.py	time-coded event recorder for the UI's run replay -> data/output/<rfq>/runs/<name>.json	new
4	agent/truecost/runner.py	creates a Recorder("truecost"/"truecost_answers"), passes it to run_tree, which records every event	modified
5	agent/redseal/runner.py	creates a Recorder("redseal") and records every event	modified
6	api/app.py	FastAPI for the UI: case overview, truecost, engine, live what-if POST /evaluate, redseal, runs, documents, serves built UI	new/rewritten

The test suite is unchanged (python -m pytest tests -q -> 36 passed).

1. Reproduce the exact demo numbers on your laptop

[bash]
cd awardshield
pip install reportlab google-adk google-genai fastapi uvicorn  # versions used: reportlab 5.0.1, google-adk 2.9.2, google-genai 2.24.0, fastapi 0.141.1, uvicorn 0.53.0
# Gemini / Vertex credentials exactly as for the earlier TrueCost build
(GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GOOGLE_GENAI_USE_VERTEXAI=True)

# 1. synthetic bids -> assets/bids/BID_1_GreenMetro.pdf, BID_2_MetroLink.pdf, BID_3_UrbanDrive.pdf
python generate_bids.py

# 2. buyer answers: copy the answers.json shown in section 7 to data/state/IN-CRUT-EBUS/answers.json
#   (otherwise, in a terminal, the runner asks the open questions after round 1: Enter = accept suggestion;
#   # new answers are then applied with: python -m agent.truecost.runner IN-CRUT-EBUS --answers-only)

# 3. TrueCost (Gemini + ADK, ~7 min) -> data/output/IN-CRUT-EBUS/{volume,cost_model,report}.json, suppliers/*, runs/truecost.json
python -m agent.truecost.runner IN-CRUT-EBUS

# 4. deterministic engine check
python -m engine.cli IN-CRUT-EBUS
python -m engine.cli IN-CRUT-EBUS --set GreenMetro.unit_rate_base=66       # the words amount -> MetroLink wins

# 5. RedSeal (~2 min) -> proof_pack.json (status OVERTURNED), runs/redseal.json
python -m agent.redseal.runner IN-CRUT-EBUS

# 6. API + UI
(cd ui && npm install && npx ng build)
uvicorn api.app:app --port 8900     # open http://127.0.0.1:8900/


Expected engine output (144 months, 12 % compound discount, start 2026-04, base year 2025, mean_yoy 3-yr official indices):

supplier	sticker NPV	lifetime NPV	escalation	factor at end
GreenMetro	533.01 Cr	549.02 Cr	+3.0%	x1.0760
MetroLink	516.09 Cr	562.64 Cr	+9.0%	x1.2287
UrbanDrive	554.16 Cr	575.23 Cr	+3.8%	x1.0962

cheapest sticker : MetroLink (by 16.92 Cr)
lifetime winner : GreenMetro (by 13.61 Cr, 2.48%)

With GreenMetro.unit_rate_base=66, MetroLink wins at 562.64 against GreenMetro's 575.17.

Expected RedSeal result: status OVERTURNED, original_winner GreenMetro, final_winner MetroLink, figure_vs_words challenge contested, flip threshold for GreenMetro 64.56 (+2.48 %), narrative_check.ok = true.

Notes

⚬ The engine numbers are fully deterministic once cost_model.json and the frozen indices exist. The Gemini steps (3, 5) can word things differently. Parameter ids can also vary: here they came out as unit_rate_base / unit_rate_main / urbandrive.unit_rate_gcc. Check the ids with python -m engine.cli IN-CRUT-EBUS or GET /api/cases/IN-CRUT-EBUS/engine -> rates. The UI reads them from there.

⚬ Index values come from the official series downloaded during the TrueCost run (CPI-IW, WPI all commodities, WPI electricity). If those publishers add a newer month, the factors can move by a few hundredths of a crore, but the winners and flips stay the same. The calibration held in 18/18 scenarios.

⚬ POST /evaluate silently ignores unknown override keys, so a wrong param id changes nothing. Use the exact ids from /engine.

⚬ config/projects/IN-CRUT-EBUS.manifest.json still has an old note text ("1072/CRUT", "64.50 -> 63.00"). It is description only; nothing reads it for numbers.

2. Bid generator (generate_bids.py)

What changed against the original generator:

Item	Original	Now
Tender no.	1072/CRUT	1376/CRUT (the real one)
Volume	200 km/bus/day × 330 days	64,800 km/bus/year (2 packages × 100 buses)
GreenMetro rate	figure 64.50, words "Sixty Four and Fifty paise", plus a visible "planted error" note	figure Rs 63.00 / km, words "Rupees Sixty Six only"; no visible note
GreenMetro escalation	fixed 0.64	unchanged: fixed 0.64 + 0.12 CPI-IW + 0.14 WPI + 0.10 Elec
MetroLink rate	61.00	unchanged, 61.00
MetroLink escalation	CPI 0.20 / WPI 0.24 / Elec 0.20	fixed 0.30, CPI-IW 0.40, WPI 0.20, Elec 0.10 (70 % indexed)
UrbanDrive rate	64.00	65.50 ("Sixty Five and Fifty paise")

The story this produces:

⚬ ACT 1: MetroLink has the cheapest sticker price but loses the lifetime NPV to GreenMetro.

⚬ ACT 2: the tender says words prevail (ITB 20.vii), so GreenMetro's rate is really 66.00, and at 66.00 MetroLink wins. TrueCost now takes the printed figure (rule K1); RedSeal catches the words.

⚬ ACT 3: the tender's own policy basis (10 %, 5-year index window) changes the lifetime cost but does not change the ranking.

generate_bids.py (full file)

[python]
"""
Generate 3 synthetic supplier bid PDFs for the AwardShield demo.

Domain: CRUT tender 1376/CRUT (real), 200 midi electric buses in 2 packages, GCC, 10 +2 years.
These bids RESPOND to the real CRUT tender. They are SYNTHETIC but grounded in public data:
- per-km rates: CAG Delhi DTC audit real bid range (Rs 68-80/km) + CESL award (Rs 43-63/km)
- cost inputs: LBNL/WRI India e-bus TCO (capex, electricity, battery, maintenance)
- escalation: CPI-IW + WPI + electricity weighted formula (as in the CRUT tender)

CALIBRATED with the AwardShield engine (engine/evaluate.py) on the real tender volume
(2 x 100 buses x 64,800 km/yr), 144 months, live official index series (CPI-IW, WPI,
WPI Electricity, mean_yoy 3), 12 % discount. Verified in 18/18 scenarios (base year 2024/2025,
start 2026-01/04/07, discount 10/12/14 %):

ACT 1 (escalation flip): MetroLink has the LOWEST per-km rate (Rs 61.00) but HIGH escalation
(fixed 0.30, CPI-IW 0.40) and loses the 12-year lifetime NPV to GreenMetro.
ACT 2 (RedSeal extraction flip): GreenMetro's price cell is a low-contrast scan that reads
"Rs 63.00 / km; the rate IN WORDS (which the tender says prevails, ITB 20.vii)
is
"Sixty Six Rupees". TrueCost takes the figure 63.00 -> GreenMetro wins. RedSeal reads the words -> true 66.00 -> the award flips to MetroLink.
ACT 3 (RedSeal understated): the tender's own evaluation basis (10 %, 5-year index window)
raises every bidder's lifetime cost by ~100 Cr - the policy basis understates it.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak)

import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "bids")
os.makedirs(OUT, exist_ok=True)

styles = getSampleStyleSheet()
H1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=15, spaceAfter=6)
H2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=11, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle('BODY', parent=styles['BodyText'], fontSize=9, leading=12)
SMALL = ParagraphStyle('SMALL', parent=styles['BodyText'], fontSize=8, textColor=colors.grey)

EQ = ParagraphStyle('EQ', parent=styles['BodyText'], fontSize=11, leading=12,
                    alignment=1, fontName='Helvetica')
EQB = ParagraphStyle('EQB', parent=EQ, fontName='Helvetica-Bold')
EQNUM = ParagraphStyle('EQNUM', parent=styles['BodyText'], fontSize=8.5, leading=9,
                       alignment=1, fontName='Helvetica')
EQDEN = ParagraphStyle('EQDEN', parent=EQNUM, fontName='Helvetica-Bold')

def _formula_block(fixed, wC, wW, wE):
    """Clean single-line escalation equation (index names only, no fractions):
       Payable Fee = Quoted Rate x [ fixed + wC x CPI-IW + wW x WPI + wE x Elec ]
    """
    expr = ("Payable Fee&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Quoted Rate&nbsp;&nbsp;&nbsp;&nbsp;&times;&nbsp;&nbsp;&nbsp;&nbsp;"
            "[&nbsp;%.2f&nbsp;&nbsp;&nbsp;+&nbsp;&nbsp;&nbsp;%.2f&nbsp;&times;&nbsp;CPI-IW"
            "&nbsp;&nbsp;&nbsp;+&nbsp;&nbsp;&nbsp;%.2f&nbsp;&times;&nbsp;WPI"
            "&nbsp;&nbsp;&nbsp;+&nbsp;&nbsp;&nbsp;%.2f&nbsp;&times;&nbsp;Elec&nbsp;]" % (fixed, wC, wW, wE))
    eq = Paragraph(expr, ParagraphStyle('EQLINE', parent=styles['BodyText'],
                                        fontName='Helvetica-Bold', fontSize=11,
                                        leading=15, alignment=1))
    panel = Table([[eq]], colwidths=[176*mm])
    panel.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff4e0')),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#e0b060')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    return panel

def tbl(data, colw):
    t = Table(data, colWidths=colw)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f3864')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#999999')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#eef2f8')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return t

def common_header(story, supplier, reg):
    story.append(Paragraph("TECHNO-COMMERCIAL BID / PRICE PROPOSAL", H1))
    story.append(Paragraph(
        "In response to: <b>Capital Region Urban Transport (CRUT), Government of Odisha</b><br/>"
        "Tender No. 1376/CRUT &nbsp;|&nbsp; <b>Selection of Bus Operator for Procurement, "
        "Operation & Maintenance of 200 Electric Buses (MIDI) on Gross Cost Contract (GCC) "
        "basis for a period of 12 (10+2) years</b>", BODY))
    story.append(Spacer(1, 6))
    story.append(tbl([
        ["Bidder (Operator)", supplier],
        ["Company Registration", reg],
        ["Bid Reference", "GCC/200EB/2025"],
        ["Contract Term", "12 years (10 operational + 2 extension)"],
        ["Fleet", "200 x MIDI (9 m) AC electric buses"],
        ["Assured kilometres", "64,800 km / bus / year (as per RFP)"],
        ["Delivery basis", "Gross Cost Contract (operator paid per assured kilometre)"],
    ], [55*mm, 110*mm]))
    story.append(Spacer(1, 8))

def escalation_clause(story, wC, wW, wE, note=""):
    fixed = round(1 - (wC + wW + wE), 4)
    story.append(Paragraph("3. PRICE ADJUSTMENT / ESCALATION", H2))
    story.append(Paragraph(
        "In accordance with Clause 15 of the RFP, the Quoted Per-Kilometre Rate shall be "
        "revised once every six (6) months. The Payable Fee for any revision period shall be "
        "computed as per the following formula (triggered when any component index moves by "
        "more than 4% from its value on the Base Index Date, i.e. the Bid Due Date):", BODY))
    story.append(Spacer(1, 6))
    story.append(_formula_block(fixed, wC, wW, wE))
    story.append(Spacer(1, 6))
    story.append(tbl([
        ["Index component", "Symbol", "Weight", "Source series (Base = Bid Due Date)"],
        ["Consumer Price Index (Industrial Workers)", "CPI-IW", "%.2f %% wC",
         "Labour Bureau, All-India CPI-IW"],
        ["Wholesale Price Index (All Commodities)", "WPI", "%.2f %% wW",
         "Office of the Economic Adviser, WPI"],
        ["Charging Electricity Tariff", "Elec", "%.2f %% wE",
         "State DISCOM LT-VII / EV tariff"],
        ["Fixed (non-escalating) portion", "-", "%.2f %% fixed", "Not indexed"],
    ], [70*mm, 22*mm, 20*mm, 53*mm]))
    if note:
        story.append(Spacer(1, 4))
        story.append(Paragraph(note, SMALL))
        story.append(Spacer(1, 8))

def cost_basis(story, rows):
    story.append(Paragraph("4. SUPPORTING COST BASIS (for information)", H2))
    story.append(Paragraph(
        "The Quoted Per-Kilometre Rate has been derived from the following lifecycle cost "
        "assumptions (grounded in prevailing Indian e-bus economics):", BODY))
    story.append(Spacer(1, 4))
    story.append(tbl([["Cost component", "Value", "Basis"]] + rows,
                     [60*mm, 40*mm, 65*mm]))
    story.append(Spacer(1, 8))

def footer(story):
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "We confirm that the rates quoted are firm except for the price-adjustment mechanism "
        "stated in Clause 3 above, and remain valid for 180 days from the Bid Due Date. "
        "All figures are inclusive of charging electricity cost borne by the Operator, subject "
        "to the tariff pass-through and permissible kWh/km as per the RFP.", BODY))
    story.append(Spacer(1, 6))
    story.append(Paragraph("For and on behalf of the Bidder &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; "
                           "Authorised Signatory", BODY))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "SYNTHETIC DEMONSTRATION DOCUMENT - generated for the AwardShield project. Not a real "
        "bid. Figures are grounded in public data (CRUT RFP formula; CAG DTC Delhi audit rates; "
        "LBNL/WRI India e-bus TCO; CESL electricity tariffs).", SMALL))

# --- BID 1 - GreenMetro Mobility (lifetime WINNER as extracted; carries the PLANTED ERROR)
def bid_greenmetro():
    story = []
    common_header(story, "GreenMetro Mobility Pvt. Ltd.", "U60100OR2019PTC031884")
    story.append(Paragraph("2. QUOTED PRICE", H2))
    story.append(Paragraph(
        "GreenMetro Mobility offers a next-generation 320 kWh LFP electric MIDI fleet with "
        "depot charging, quoting the following firm per-kilometre rate:", BODY))
    story.append(Spacer(1, 4))
    story.append(tbl([
        ["Item", "Quoted Rate (INR / assured km)"],
        ["Per-kilometre Gross Cost Rate (AC MIDI, 9 m)", "Rs 63.00 / km"],
        ["(rate in words)", "Rupees Sixty Six only per kilometre"],
    ], [110*mm, 55*mm]))
    story.append(Spacer(1, 6))
    escalation_clause(story, wC=0.12, wW=0.14, wE=0.10,
                      note="Note: GreenMetro's low indexed weights (fixed portion 0.64) reflect a "
                           "deliberate commercial strategy for long-term rate stability.")
    cost_basis(story, [
        ["Electric bus capex (320 kWh)", "Rs 1.00 crore / bus", "LBNL/WRI India e-bus TCO"],
        ["Charging electricity tariff", "Rs 5.50 / kWh", "CESL Delhi benchmark"],
        ["Energy consumption", "0.80 kWh / km", "ICCT BMTC median"],
        ["Battery replacement", "once, end of year 7", "LBNL assumption"],
        ["Maintenance", "Rs 4.00 / km", "LBNL BEB maintenance"],
    ])
    footer(story)
    return story

# --- BID 2 - MetroLink Fleet
def bid_metrolink():
    story = []
    common_header(story, "MetroLink Fleet Services Ltd.", "U60221OR2017PLC028776")
    story.append(Paragraph("2. QUOTED PRICE", H2))
    story.append(Paragraph(
        "MetroLink Fleet offers the most competitive headline per-kilometre rate in this "
        "tender, based on a cost-optimised 250 kWh fleet:", BODY))
    story.append(Spacer(1, 4))
    story.append(tbl([
        ["Item", "Quoted Rate (INR / assured km)"],
        ["Per-kilometre Gross Cost Rate (AC MIDI, 9 m)", "Rs 61.00 / km"],
        ["(rate in words)", "Rupees Sixty One only per kilometre"],
    ], [110*mm, 55*mm]))
    story.append(Spacer(1, 6))
    escalation_clause(story, wC=0.40, wW=0.20, wE=0.10,
                      note="Note: MetroLink's headline rate is the lowest, but 70% of the fee is "
                           "indexed (CPI-IW 0.40, WPI 0.20, Electricity 0.10) and escalates with "
                           "inflation over the 12-year term.")
    cost_basis(story, [
        ["Electric bus capex (250 kWh)", "Rs 0.92 crore / bus", "LBNL/WRI (smaller battery)"],
        ["Charging electricity tariff", "Rs 6.00 / kWh", "CESL multi-city benchmark"],
        ["Energy consumption", "0.85 kWh / km", "ICCT BMTC range"],
        ["Battery replacement", "once, end of year 6", "shorter-cycle assumption"],
        ["Maintenance", "Rs 4.20 / km", "LBNL BEB maintenance"],
    ])
    footer(story)
    return story

# --- BID 3 - UrbanDrive Transit
def bid_urbandrive():
    story = []
    common_header(story, "UrbanDrive Transit Solutions Pvt. Ltd.", "U60232OR2018PTC029551")
    story.append(Paragraph("2. QUOTED PRICE", H2))
    story.append(Paragraph(
        "UrbanDrive Transit offers a balanced 300 kWh fleet with opportunity charging:", BODY))
    story.append(Spacer(1, 4))
    story.append(tbl([
        ["Item", "Quoted Rate (INR / assured km)"],
        ["Per-kilometre Gross Cost Rate (AC MIDI, 9 m)", "Rs 65.50 / km"],
        ["(rate in words)", "Rupees Sixty Five and Fifty paise per kilometre"],
    ], [110*mm, 55*mm]))
    story.append(Spacer(1, 6))
    escalation_clause(story, wC=0.15, wW=0.18, wE=0.12,
                      note="Note: UrbanDrive quotes moderate index weights (indexed portion 0.45).")
    cost_basis(story, [
        ["Electric bus capex (300 kWh)", "Rs 0.98 crore / bus", "LBNL/WRI India e-bus TCO"],
        ["Charging electricity tariff", "Rs 6.50 / kWh", "CESL Lot-3 benchmark"],
        ["Energy consumption", "0.82 kWh / km", "ICCT BMTC median"],
        ["Battery replacement", "once, end of year 7", "LBNL assumption"],
        ["Maintenance", "Rs 4.10 / km", "LBNL BEB maintenance"],
    ])
    footer(story)
    return story

def build(name, story):
    path = os.path.join(OUT, name)
    doc = SimpleDocTemplate(path, pagesize=A4,
                            topMargin=18*mm, bottomMargin=16*mm,
                            leftMargin=18*mm, rightMargin=18*mm)
    doc.build(story)
    print("wrote", path)

if __name__ == "__main__":
    build("BID_1_GreenMetro.pdf", bid_greenmetro())
    build("BID_2_MetroLink.pdf", bid_metrolink())
    build("BID_3_UrbanDrive.pdf", bid_urbandrive())
    print("done")


3. agent/truecost/prompts.py – COST_MODEL rule K1 (small edit)

This rule went into the K1 section of the COST_MODEL prompt (right before K2. CONTRACT-WIDE PARAMETERS).

Why it was needed: without it, Gemini sometimes applied "words prevail" by itself. That produced 66.00 and made the demo baseline inconsistent. The decision belongs to RedSeal.

[text]
FIGURE vs WORDS: a price parameter takes the term's printed figure ('amount'), source_kind SOURCE_FACT - even when amount_in_words says something else. Never apply a 'words prevail' rule
yourself; a separate auditor checks that conflict against the tender and re-runs the engine.
Mention the disagreement in the parameter's quote.


4. Run recorder (new) + runner hooks

Each runner gets a Recorder and feeds it every ADK event. At the end it writes data/output/<rfq>/runs/<name>.json (name = 'truecost', 'truecost_answers' or 'redseal'). That record has the start time, the duration, and time-coded events (agent, kind = call/result/text, tool, short payload). GET /api/cases/{id}/runs serves these records, and the UI's Agent run page replays them.

agent/recorder.py (full file)

[python]
"""recorder.py - a time-coded record of one agent run, for the UI's run replay.

rec = Recorder("truecost", rfq_id)
rec.event(adk_event) # inside the runner's async for e in runner.run_async(...)`
rec.save(extra={...}) # -> data/output/<rfq_id>/runs/truecost.json

Each entry: t (seconds since start), agent, kind (call / result / reply / done), name, detail (short).
Only what the replay needs - no document bytes, no full prompts.
"""

import json
import time
from datetime import datetime, timezone
from .truecost.settings import OUTPUT_DIR

def _short(x, n: int = 220) -> str:
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + "..."

class Recorder:
    def __init__(self, name: str, rfq_id: str):
        self.name, self.rfq_id, self.t0 = name, rfq_id, time.time()
        self.started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.events: list[dict] = []

    def _add(self, agent: str, kind: str, name: str = "", detail: str = "", tokens: int | None = None) -> None:
        self.events.append({"t": round(time.time() - self.t0, 1), "agent": agent, "kind": kind, "name": name,
                            "detail": detail, **({"tokens": tokens} if tokens else {})})

    def event(self, e) -> None:
        tokens = getattr(getattr(e, "usage_metadata", None), "prompt_token_count", None)
        for p in (e.content.parts if e.content else []) or []:
            if p.function_call:
                self._add(e.author, "call", p.function_call.name, _short(dict(p.function_call.args or {})), tokens)
            elif p.function_response:
                r = p.function_response.response or {}
                self._add(e.author, "result", p.function_response.name,
                          _short({k: r.get(k) for k in ("status", "series_key", "url", "summary", "note", "proxy") if r.get(k) or r}))
        if e.is_final_response():
            text = "".join(p.text or "" for p in (e.content.parts if e.content else []) or [] if not p.thought)
            self._add(e.author, "done", detail=_short(text.strip(), 260), tokens=tokens)

    def save(self, extra: dict | None = None) -> None:
        out = OUTPUT_DIR / self.rfq_id / "runs"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{self.name}.json").write_text(json.dumps({
            "run": self.name, "rfq_id": self.rfq_id, "started_at": self.started,
            "duration_s": round(time.time() - self.t0, 1), "events": self.events, **(extra or {})
        }, indent=1, ensure_ascii=False))


agent/truecost/runner.py (full file)

[python]
"""runner.py - run TrueCost for one tender from the command line.

python -m agent.truecost.runner IN-CRUT-EBUS # full run, then ask the buyer
python -m agent.truecost.runner IN-CRUT-EBUS --answers-only # re-apply stored answers (no document reading)
python -m agent.truecost.runner IN-CRUT-EBUS --set rfq.contract.start=2026-04 --set rfq.index.base_year=2025

Round 1 runs the whole agent tree (agent.build_root): tender volume, every bidder in parallel, merged
report. The buyer then answers the report's questions in the terminal (Enter = accept the suggestion,
'skip' = leave open); answers are stored in data/state/<rfq_id>/answers.json and reused on every
run. Rounds 2+ run only build_answers_root: each bidder's cost_model + finalizer, then the orchestrator -
the extraction records are reused, so no document is read again.
"""

import argparse
import asyncio
import json
import logging
import sys
import time

from google.adk.agents import ParallelAgent, SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from .agent import bidder_key, build_root, make_orchestrator
from .doc_reader import Case, pack
from .finalizer import _slug, make_finalizer
from .settings import MAX_QUESTION_ROUNDS, OUTPUT_DIR, STATE_DIR
from .subagents.cost_model import make_cost_model
from ..recorder import Recorder

APP, USER = "truecost", "buyer"

def answers_path(case: Case):
    return STATE_DIR / case.rfq_id / "answers.json"

def load_answers(case: Case) -> dict:
    p = answers_path(case)
    return json.loads(p.read_text()) if p.exists() else {}

def save_answers(case: Case, answers: dict) -> None:
    p = answers_path(case)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(answers, indent=1, ensure_ascii=False))

def ask(questions: list[dict], known: dict) -> dict:
    """Ask every open question once in the terminal. Enter = the suggestion, a number = that option,
    'skip' = leave it open, anything else = your answer. No terminal -> nothing is asked."""
    todo = [q for q in questions if q["key"] not in known]
    if not todo or not sys.stdin.isatty():
        return {}
    print(f"\n{'=' * 78}\n{len(todo)} question(s) for you - Enter accepts the suggestion, 'skip' leaves it open\n"
          f"{'=' * 78}")
    answers = {}
    for i, q in enumerate(todo, 1):
        print(f"\n{i}. [{q['key']}] {q['question']}")
        if q.get("why"):
            print(f"   why: {q['why'][:300]}")
        opts = q.get("options") or []
        for n, o in enumerate(opts, 1):
            print(f"      {n}. {o}")
        if q.get("suggestion"):
            print(f"   suggested: {q['suggestion']}")
        raw = input("   answer > ").strip()
        if raw.lower() == "skip" or (not raw and not q.get("suggestion")):
            continue
        answers[q["key"]] = (q["suggestion"] if not raw else
                             opts[int(raw) - 1] if raw.isdigit() and 1 <= int(raw) <= len(opts) else raw)
    return answers

def build_answers_root(case: Case) -> SequentialAgent:
    """Rounds 2+: re-link each bidder's cost model with the buyer's answers, re-check, re-report."""
    relinks = [SequentialAgent(name=f"relink_{bidder_key(s)}", description=f"{s}: cost model with answers.",
                               sub_agents=[make_cost_model(s, bidder_key(s)),
                                           make_finalizer(s, bidder_key(s))])
               for s in case.supplier_names]
    return SequentialAgent(name="truecost_answers", description="Apply the buyer's answers to every cost model.",
                           sub_agents=[ParallelAgent(name="relink", description="Every bidder at once.",
                                                     sub_agents=relinks),
                                       make_orchestrator(case)])

def records_from_disk(case: Case) -> dict:
    """The extraction records a previous full run saved, as session state (for --answers-only)."""
    out = OUTPUT_DIR / case.rfq_id
    state = {"volume": json.loads((out / "volume.json").read_text())}
    for s in case.supplier_names:
        folder, k = out / "suppliers" / _slug(s), bidder_key(s)
        for name in ("commercial", "escalation", "index_resolutions"):
            state[f"{name}_{k}"] = json.loads((folder / f"{name}.json").read_text())
    return state

async def run_tree(agent, state: dict, parts: list[types.Part], t0: float, rec: "Recorder | None" = None) -> dict:
    """Run one agent tree in a fresh session; print each sub-agent as it finishes; return the final state.
    rec: a Recorder that keeps a time-coded copy of every event for the UI's run replay."""
    runner = InMemoryRunner(agent=agent, app_name=APP)
    session = await runner.session_service.create_session(app_name=APP, user_id=USER, state=state)
    async for e in runner.run_async(user_id=USER, session_id=session.id,
                                      new_message=types.Content(role="user", parts=parts)):
        if rec is not None:
            rec.event(e)
        if e.is_final_response() and e.content and e.content.parts:
            text = (e.content.parts[0].text or "").strip()
            print(f"[{time.time() - t0:5.0f}s] {e.author}: {text if e.author.startswith('finalizer') else 'done'}",
                  flush=True)
    return (await runner.session_service.get_session(app_name=APP, user_id=USER, session_id=session.id)).state

def print_report(report: dict) -> None:
    print(f"\n{'=' * 78}\nTRUECOST REPORT {report['rfq_id']}\n{'=' * 78}")
    for b in report["bidders"]:
        print(f"  {b['supplier']:<14} {b['status']:<14} {b['quoted_price']:<26} {b['escalation']}")
        for p in b.get("problems", []):
            print(f"     unresolved: {p}")
    print(f"\n ready for evaluation: {report['ready_for_evaluation'] or 'none yet'}")
    print(f" {report['summary']}")

async def main(case_id: str, sets: list[str], answers_only: bool) -> None:
    case = Case.load(case_id)
    answers = load_answers(case)
    for item in sets:
        k, _, v = item.partition("=")
        answers[k.strip()] = v.strip()
    save_answers(case, answers)

    t0 = time.time()
    base = {"rfq_id": case.rfq_id, "country": case.country, "answers": answers}
    print(f"{case.rfq_id}: {len(case.documents)} documents, bidders {case.supplier_names}"
          f"{' - answers only, no document reading' if answers_only else ''}", flush=True)
    rec = Recorder("truecost_answers" if answers_only else "truecost", case.rfq_id)
    if answers_only:
        st = await run_tree(build_answers_root(case), {**base, **records_from_disk(case)},
                            [types.Part(text="Apply the buyer's answers.")], t0, rec)
    else:
        intro = types.Part(text=f"Tender {case.rfq_id}: {case.title}. Documents follow.")
        st = await run_tree(build_root(case), base, [intro, *pack(case.documents)], t0, rec)
    rec.save({"bidders": case.supplier_names})

    for _ in range(MAX_QUESTION_ROUNDS):
        print_report(st["report"])
        questions = st["report"]["questions_for_buyer"]
        q_path = STATE_DIR / case.rfq_id / "questions.json"
        q_path.write_text(json.dumps(questions, indent=1, ensure_ascii=False))
        print(f"\n {len(questions)} question(s) saved: {q_path}")
        new = ask(questions, answers)
        if not new:
            break
        answers.update(new)
        save_answers(case, answers)
        print(f"\nanswers stored in {answers_path(case)} - re-linking the cost models ...", flush=True)
        st = await run_tree(build_answers_root(case), {**st, "answers": answers},
                            [types.Part(text="Apply the buyer's answers.")], t0)

    out = OUTPUT_DIR / case.rfq_id
    (out / "report.json").write_text(json.dumps(st["report"], indent=1, ensure_ascii=False))
    print(f"\ncost model: {out / 'cost_model.json'}\nreport:     {out / 'report.json'} ({time.time() - t0:.0f}s)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run TrueCost for one tender.")
    ap.add_argument("case", help="RFQ id or path of the manifest (config/projects/<country>/<id>.manifest.json)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="store a buyer answer")
    ap.add_argument("--answers-only", action="store_true", help="skip document reading; re-link the cost models with the stored answers")
    args = ap.parse_args()
    asyncio.run(main(args.case, args.set, args.answers_only))
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)


agent/redseal/runner.py (full file)

[python]
"""runner.py - run RedSeal on a tender TrueCost has already built, and write the Proof Pack.

python -m agent.redseal.runner IN-CRUT-EBUS
python -m agent.redseal.runner IN-CRUT-EBUS --output IN-CRUT-EBUS-ROBUST   # audit a variant cost model

Needs data/output/<rfq_id>/cost_model.json (+ frozen_indices, suppliers/*) from TrueCost. Writes
data/output/<rfq_id>/proof_pack.json and prints the verdict.
"""

import argparse
import asyncio
import json
import logging
import time

from google.adk.runners import InMemoryRunner
from google.genai import types

from ..truecost.doc_reader import Case, pack
from ..truecost.settings import OUTPUT_DIR
from ..recorder import Recorder
from .agent import build_root

APP, USER = "redseal", "buyer"

async def run(case_id: str, output: str = "") -> dict:
    case = Case.load(case_id)
    runner = InMemoryRunner(agent=build_root(case_id, output), app_name=APP)
    session = await runner.session_service.create_session(app_name=APP, user_id=USER, state={})
    intro = types.Part(text=f"Tender {case.rfq_id}: {case.title}. Documents follow.")
    t0 = time.time()
    rec = Recorder("redseal", output or case.rfq_id)
    async for e in runner.run_async(user_id=USER, session_id=session.id,
                                      new_message=types.Content(role="user", parts=[intro, *pack(case.documents)])):
        rec.event(e)
        if e.is_final_response():
            print(f"[{time.time() - t0:5.0f}s] {e.author}: done", flush=True)
    st = (await runner.session_service.get_session(app_name=APP, user_id=USER, session_id=session.id)).state
    pack_ = {**st["verdict"], "narrative": st.get("narrative"), "narrative_check": st.get("narrative_check"),
             "challenger_raw": {"extraction": st.get("extraction"), "assumptions": st.get("assumptions")}}
    path = OUTPUT_DIR / (output or case.rfq_id) / "proof_pack.json"
    path.write_text(json.dumps(pack_, indent=1, ensure_ascii=False))
    rec.save({"verdict": pack_["status"]})
    print_verdict(pack_)
    print(f"\nproof pack: {path} ({time.time() - t0:.0f}s)")
    return pack_

def print_verdict(p: dict) -> None:
    print(f"\n{'=' * 78}\nREDSEAL VERDICT {p['rfq_id']}: {p['status']}{' (contested)' if p['contested'] else ''}"
          f" {p['original_winner']} -> {p['final_winner']}\n{'=' * 78}")
    b = p["baseline"]
    print("baseline: " + ", ".join(f"{n}: {v:.2f} Cr" for n, v in b["ranking"]) +
          f" (margin {b['margin_cr']:.2f} Cr)")
    for c in p["challenges"]:
        print(f"\n [{c['status']:<9}] {c['challenge_id']} ({c['target']}): {c['original_value']} -> {c['corrected_value']}")
        if c["effect"]:
            print(f"          {c['effect']}")
        print(f"       check: {c['checks'][-1]}")
    print("\n flip thresholds:")
    for t in p["flip_thresholds"]:
        print(f"   {t['supplier']:<11} {t['param']} {t['current']:g} -> {t['threshold']:.2f} ({t['change_pct']:+.1f} %) "
              f"vs {t['against']}{' PLAUSIBLE' if t['plausible'] else ''}")
    print(" sensitivity:")
    for r in p["sensitivity"]:
        print(f"   {r['driver']:<14} {r['low_label']:>11} {r['winner_low']:>10} {r['high_label']:>11} {r['winner_high']:>10}"
              f"{' FLIPS' if r['flips'] else ''}")
    n = p.get("narrative")
    if n:
        print(f"\n {n['headline']}")
        for f in n["findings"]:
            print(f"   - {f}")
        print(f" {n['recommendation']}")
    elif p.get("narrative_check"):
        print(f"\n (narrative dropped - numbers not in the proof: {p['narrative_check']['numbers not in proof']})")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run RedSeal on a tender TrueCost has already built.")
    ap.add_argument("case", help="RFQ id or manifest path")
    ap.add_argument("--output", default="", help="optional variant output folder")
    args = ap.parse_args()
    asyncio.run(run(args.case, args.output))
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)


5. API for the UI (api/app.py)

Method	Path	Returns
GET	/api/cases	list of cases
GET	/api/cases/{id}	overview for the landing + decision pages: bidders, three acts, verdict
GET	/api/cases/{id}/truecost	volume, per-supplier records, official indices (url, sha256, downloaded_at), report
GET	/api/cases/{id}/engine	parameters, rates{Supplier:{param,value}}, result.suppliers[].yearly, escalators, indices, award
POST	/api/cases/{id}/evaluate	body {"overrides": {...}} -> re-runs the deterministic engine. Keys: <Supplier>.<param>, discount_rate, horizon_months, base_year, index:<series>, driver_scale
GET	/api/cases/{id}/redseal	proof_pack.json
GET	/api/cases/{id}/runs	recorded runs (section 4)
GET	/api/cases/{id}/documents/{name}	bid/RFP PDF
GET	/	built UI from ui/dist/awardshield-ui/browser (only if it has been built)

Run it with uvicorn api.app:app --port 8900.

api/app.py (full file)

[python]
"""app.py - the AwardShield API: serves the case files and live engine what-ifs to the UI.

    uvicorn api.app:app --port 8900     (from awardshield/)

Read-only over data/output/<rfq_id>/ (written by TrueCost and RedSeal). The only computation is
engine.evaluate - deterministic, no model calls. The built UI (ui/dist/awardshield-ui/browser) is served at /.
"""

import json
import sys
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]       # .../awardshield
sys.path.insert(0, str(ROOT))

from engine import award, evaluate, load_case              # noqa: E402
from engine.indices import rate_for                      # noqa: E402

OUTPUT, CONFIG = ROOT / "data" / "output", ROOT / "config"
UI = ROOT / "ui" / "dist" / "awardshield-ui" / "browser"

app = FastAPI(title="AwardShield API")

def _json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None

def _out(case_id: str) -> Path:
    out = OUTPUT / case_id
    if not (out / "cost_model.json").exists():
        raise HTTPException(404, f"no cost model for {case_id} - run TrueCost first")
    return out

@lru_cache(maxsize=8)
def _model(case_id: str, mtime: float):
    return load_case(_out(case_id), _json(CONFIG / "buyer_policy.json") or {})

def model(case_id: str):
    return _model(case_id, (_out(case_id) / "cost_model.json").stat().st_mtime)

def _manifest(case_id: str) -> dict:
    hit = next((CONFIG / "projects").rglob(f"{case_id}.manifest.json"), None)
    return _json(hit) if hit else {}

def _rate(m, supplier: str) -> tuple[str, float]:
    sup = m.suppliers[supplier]
    for ln in sup.lines:
        for f in ln.factors:
            if f.startswith("p:") and f[2:] in sup.parameters:
                return f[2:], float(sup.parameters[f[2:]].value)
    return "", 0.0

def _year_one(result: dict) -> dict:
    out = {}
    m0 = int(result["start"][5:7])
    for n, v in result["suppliers"].items():
        ys = sorted(v["yearly"])
        first = v["yearly"][ys[0]]["tco_esc"]
        rest = 12 - (13 - m0)
        out[n] = first + (v["yearly"][ys[1]]["tco_esc"] * rest / 12 if rest > 0 and len(ys) > 1 else 0.0)
    return out

@app.get("/api/cases")
def cases():
    return [{"id": p.name, "title": _manifest(p.name).get("title", p.name),
             "has_verdict": (p / "proof_pack.json").exists()}
            for p in sorted(OUTPUT.iterdir()) if (p / "cost_model.json").exists()]

@app.get("/api/cases/{case_id}")
def case(case_id: str):
    m, h = model(case_id)
    out = _out(case_id)
    r = evaluate(m, h)
    life, sticker = award(r), award(r, "tco")
    y1 = _year_one(r)
    bidders = []
    for n in m.suppliers:
        param, rate = _rate(m, n)
        esc = r["suppliers"][n]["escalators"]
        last = list(next(iter(esc.values()))["by_year"].values())[-1] if esc else 1.0
        com = _json(out / "suppliers" / n / "commercial.json") or {}
        unit = next((t for t in com.get("terms", []) if t.get("kind") == "unit_rate"), {})
        fx = next((f for f in (_json(out / "suppliers" / n / "escalation.json") or {}).get("formulae", [])), {})
        bidders.append({"name": n, "rate": rate, "rate_param": param,
                        "amount_in_words": unit.get("amount_in_words", ""),
                        "sticker_cr": dict(sticker.ranking)[n], "lifetime_cr": dict(life.ranking)[n],
                        "year_one_cr": y1[n] / 1e7, "factor_end": last,
                        "fixed": fx.get("fixed_weight"), "terms": [(t["symbol"], t["weight"]) for t in fx.get("terms", [])]})
    proof = _json(out / "proof_pack.json")
    after = None
    if proof:
        flip = next((c for c in proof["challenges"] if c.get("rerun") and c.get("rerun")["winner"] != proof["original_winner"]), None)
        if flip:
            after = {"ranking": flip["rerun"]["ranking"], "winner": flip["rerun"]["winner"], "challenge": flip["challenge_id"],
                     "change": f"{flip['target']}: {flip['original_value']} -> {flip['corrected_value']}"}
    man = _manifest(case_id)
    vol = _json(out / "volume.json") or {}
    return {"id": case_id, "title": man.get("title", ""), "buyer": man.get("buyer", ""), "country": man.get("country", ""),
            "currency": man.get("currency", "INR"), "start": r["start"], "months": r["months"],
            "discount": r["discount"], "base_year": r["base_year"],
            "volume": [{"id": d["driver_id"], "label": d["label"], "build": d["build"],
                        "components": [(c["name"], c["value"], c["unit"]) for c in d["components"]]}
                       for d in vol.get("drivers", []) if d.get("primary", True)],
            "bidders": bidders,
            "acts": {"sticker": {"ranking": sticker.ranking, "winner": sticker.winner},
                     "lifetime": {"ranking": life.ranking, "winner": life.winner,
                                  "margin_cr": life.margin_cr},
                     "after": after,
                     "year_one_winner": min(y1, key=y1.get)},
            "verdict": {k: proof[k] for k in ("status", "contested", "original_winner", "final_winner", "summary", "fragile")}
            | {"narrative": proof.get("narrative")} if proof else None}

@app.get("/api/cases/{case_id}/truecost")
def truecost(case_id: str):
    out = _out(case_id)
    m, h = model(case_id)
    sups = {}
    for n in m.suppliers:
        d = out / "suppliers" / n
        sups[n] = {k: _json(d / f"{k}.json") for k in ("commercial", "escalation", "index_resolutions", "open_questions")}
    idx = {}
    for f in sorted((out / "frozen_indices").glob("*.json")):
        j = _json(f)
        idx[f.stem] = {k: j.get(k) for k in ("symbol", "label", "annual_values", "url", "official", "downloaded_at",
                                             "sha256", "step", "proxy", "partial_years", "frequency")}
    return {"volume": _json(out / "volume.json"), "suppliers": sups, "indices": idx,
            "report": _json(out / "report.json"), "answers": _json(ROOT / "data" / "state" / case_id / "answers.json")}

@app.get("/api/cases/{case_id}/engine")
def engine(case_id: str):
    m, h = model(case_id)
    r = evaluate(m, h)
    return {"result": r, "award": award(r).model_dump(), "sticker": award(r, "tco").model_dump(),
            "indices": {s: {"method": spec.method, "years": spec.years, "history": dict(h[s]),
                            "rate": rate_for(h[s], spec.method, spec.rate, spec.years)}
                        for s, spec in m.indices.items()},
            "parameters": {k: p.model_dump() for k, p in m.parameters.items()},
            "rates": {n: dict(zip(("param", "value"), _rate(m, n))) for n in m.suppliers},
            "policy": _json(CONFIG / "buyer_policy.json"), "rfp_basis": _json(CONFIG / "rfp_basis.json")}

class WhatIf(BaseModel):
    overrides: dict = {}

@app.post("/api/cases/{case_id}/evaluate")
def what_if(case_id: str, body: WhatIf):
    m, h = model(case_id)
    try:
        r = evaluate(m, h, body.overrides)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, f"bad override: {e}")
    return {"award": award(r).model_dump(), "sticker": award(r, "tco").model_dump(),
            "yearly": {n: {y: v["tco_esc"] for y, v in s["yearly"].items()} for n, s in r["suppliers"].items()},
            "factors": {n: next(iter(s["escalators"].values()))["by_year"] if s["escalators"] else {}
                        for n, s in r["suppliers"].items()},
            "discount": r["discount"], "months": r["months"], "start": r["start"]}

@app.get("/api/cases/{case_id}/redseal")
def redseal(case_id: str):
    p = _json(_out(case_id) / "proof_pack.json")
    if p is None:
        raise HTTPException(404, "RedSeal has not run for this case")
    return p

@app.get("/api/cases/{case_id}/runs")
def runs(case_id: str):
    d = _out(case_id) / "runs"
    return {f.stem: _json(f) for f in sorted(d.glob("*.json"))} if d.exists() else {}

@app.get("/api/cases/{case_id}/documents/{name}")
def document(case_id: str, name: str):
    for p in (ROOT / "assets").rglob(name):
        if p.is_file() and p.suffix.lower() == ".pdf":
            return FileResponse(p, media_type="application/pdf")
    raise HTTPException(404, name)

if UI.exists():
    app.mount("/", StaticFiles(directory=UI, html=True), name="ui")


6. Verification done on this machine

⚬ TrueCost re-run took 434 s; GreenMetro came out at unit_rate_base = 63.0 (SOURCE_FACT); the run asked 5 buyer questions.

⚬ RedSeal took 101 s: OVERTURNED, GreenMetro -> MetroLink, narrative check ok.

⚬ engine.cli output matches section 1.

⚬ POST /evaluate {"GreenMetro.unit_rate_base":66} -> MetroLink 562.64, GreenMetro 575.17.

⚬ pytest -> 36 passed.

⚬ The UI was built and checked in a browser.

7. Buyer answers used (data/state/IN-CRUT-EBUS/answers.json)

These are free-text answers to TrueCost's buyer questions. Copy this file before step 3 so your run uses the same choices. Without it, the runner asks the questions interactively.

[json]
{
 "rfq.contract.start": "2026-04",
 "rfq.index.base_year": "2025",
 "rfq.contract.adjustment_trigger": "Apply revision every 6 months regardless of the variation percentage.",
 "index.proxy.Elec": "accept",
 "greenmetro.volume.assured_km": "Use the RFP's figure of 64,800 km/bus/year, as this is specified in the RFP's payment calculation examples and minimum guarantee clause, and the bidder's price is a per-km rate that can be applied to this volume.",
 "greenmetro.escalation.formula_deviation": "Apply the bidder's proposed formula: Payable Fee = Quoted Rate x [ 0.64 + 0.12 x CPI-IW + 0.14 x WPI + 0.10 x Elec ]",
 "greenmetro.escalation.trigger_basis": "Apply the RFP's trigger: compare current index to the index at the time of the last 6-monthly revision.",
 "metrolink.commitment.km": "Use the RFP's value of 64,800 km/bus/year.",
 "metrolink.escalation.formula": "Use the bidder's simplified formula.",
 "metrolink.capex.scope": "Assume the all-inclusive Rs 61.00/km rate covers buses, depot equipment and charging infrastructure; confirm with the bidder.",
 "urbandrive.escalation.formula": "Apply the mechanism from UrbanDrive's bid (BID_3_UrbanDrive.pdf, p. 1): Formula with weights (Fixed 55%, CPI 15%, WPI 18%, Elec 12%)",
 "urbandrive.volume.assured_km": "Accept the rate of Rs 64.00/km as quoted."
}


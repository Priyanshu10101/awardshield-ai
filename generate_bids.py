"""
Generate 3 synthetic supplier bid PDFs for the AwardShield demo.

    python generate_bids.py      -> assets/Bids/BID_1_GreenMetro.pdf, BID_2_MetroLink.pdf, BID_3_UrbanDrive.pdf

Domain: CRUT tender 1376/CRUT (real), 200 midi electric buses in 2 packages, GCC, 10 +2 years.
These bids RESPOND to the real CRUT tender. They are SYNTHETIC but grounded in public data:
- per-km rates: CAG Delhi DTC audit real bid range (Rs 68-80/km) + CESL award (Rs 43-63/km)
- cost inputs: LBNL/WRI India e-bus TCO (capex, electricity, battery, maintenance)
- escalation: CPI-IW + WPI + electricity weighted formula (as in the CRUT tender)

CALIBRATED with the TrueCost engine on the real tender volume (2 x 100 buses x 64,800 km/yr),
144 months, live official index series (CPI-IW, WPI, WPI Electricity, mean_yoy 3), 12 % discount.
Verified in 18/18 scenarios (base year 2024/2025, start 2026-01/04/07, discount 10/12/14 %):

ACT 1 (escalation flip): MetroLink has the LOWEST per-km rate (Rs 61.00) but HIGH escalation
    (fixed 0.30, CPI-IW 0.40) and loses the 12-year lifetime NPV to GreenMetro.
ACT 2 (RedSeal extraction flip): GreenMetro's price cell reads "Rs 63.00 / km"; the rate IN WORDS
    (which the tender says prevails, ITB 20.vii) is "Sixty Six Rupees". TrueCost takes the figure
    63.00 -> GreenMetro wins. RedSeal reads the words -> true 66.00 -> the award flips to MetroLink.
ACT 3 (RedSeal understated): the buyer's evaluation basis (10 %, 5-year index window) raises every
    bidder's lifetime cost by ~100 Cr - the policy basis understates it.
"""

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "Bids")
os.makedirs(OUT, exist_ok=True)

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=15, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontSize=9, leading=12)
SMALL = ParagraphStyle("SMALL", parent=styles["BodyText"], fontSize=8, textColor=colors.grey)


def _formula_block(fixed, wC, wW, wE):
    """Clean single-line escalation equation (index names only, no fractions):
       Payable Fee = Quoted Rate x [ fixed + wC x CPI-IW + wW x WPI + wE x Elec ]
    """
    expr = ("Payable Fee&nbsp;&nbsp;=&nbsp;&nbsp;Quoted Rate&nbsp;&nbsp;&times;&nbsp;&nbsp;"
            "[&nbsp;%.2f&nbsp;&nbsp;+&nbsp;&nbsp;%.2f&nbsp;&times;&nbsp;CPI-IW"
            "&nbsp;&nbsp;+&nbsp;&nbsp;%.2f&nbsp;&times;&nbsp;WPI"
            "&nbsp;&nbsp;+&nbsp;&nbsp;%.2f&nbsp;&times;&nbsp;Elec&nbsp;]" % (fixed, wC, wW, wE))
    eq = Paragraph(expr, ParagraphStyle("EQLINE", parent=styles["BodyText"], fontName="Helvetica-Bold",
                                        fontSize=11, leading=15, alignment=1))
    panel = Table([[eq]], colWidths=[176 * mm])
    panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff4e0")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e0b060")),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return panel


def tbl(data, colw):
    t = Table(data, colWidths=colw)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3864")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef2f8")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
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
    ], [55 * mm, 110 * mm]))
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
        ["Consumer Price Index (Industrial Workers)", "CPI-IW", "%.2f" % wC, "Labour Bureau, All-India CPI-IW"],
        ["Wholesale Price Index (All Commodities)", "WPI", "%.2f" % wW, "Office of the Economic Adviser, WPI"],
        ["Charging Electricity Tariff", "Elec", "%.2f" % wE, "State DISCOM LT-VII / EV tariff"],
        ["Fixed (non-escalating) portion", "-", "%.2f" % fixed, "Not indexed"],
    ], [70 * mm, 22 * mm, 20 * mm, 53 * mm]))
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
    story.append(tbl([["Cost component", "Value", "Basis"]] + rows, [60 * mm, 40 * mm, 65 * mm]))
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
    ], [110 * mm, 55 * mm]))
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
    ], [110 * mm, 55 * mm]))
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
    story.append(Paragraph("UrbanDrive Transit offers a balanced 300 kWh fleet with opportunity charging:", BODY))
    story.append(Spacer(1, 4))
    story.append(tbl([
        ["Item", "Quoted Rate (INR / assured km)"],
        ["Per-kilometre Gross Cost Rate (AC MIDI, 9 m)", "Rs 65.50 / km"],
        ["(rate in words)", "Rupees Sixty Five and Fifty paise per kilometre"],
    ], [110 * mm, 55 * mm]))
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
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=18 * mm, bottomMargin=16 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm)
    doc.build(story)
    print("wrote", path)


if __name__ == "__main__":
    build("BID_1_GreenMetro.pdf", bid_greenmetro())
    build("BID_2_MetroLink.pdf", bid_metrolink())
    build("BID_3_UrbanDrive.pdf", bid_urbandrive())
    print("done")

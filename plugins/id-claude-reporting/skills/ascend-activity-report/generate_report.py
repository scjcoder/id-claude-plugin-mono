#!/usr/bin/env python3
"""
Ascend API Monthly Activity Report — PDF generator.

Usage:
  python3 generate_report.py \
    --month  "May 2026" \
    --slug   "2026-05" \
    --outdir "/path/to/output/dir" \
    --data   '<JSON string>'

JSON schema for --data:
{
  "month_label":     "May 2026",
  "total_locations": 116,
  "active_count":    112,
  "onboarded_count": 2,
  "offboarded_count": 2,
  "inactive_count":  0,
  "active_locations": [
    { "facility_id": "123", "client": "...", "location": "...",
      "snapshot_count": 28, "last_snapshot": "May 31, 2026" }
  ],
  "onboarded_locations": [
    { "facility_id": "456", "client": "...", "location": "...",
      "snapshot_count": 8, "last_snapshot": "May 31, 2026" }
  ],
  "offboarded_locations": [
    { "facility_id": "789", "client": "...", "location": "...",
      "snapshot_count": 3, "last_snapshot": "May 06, 2026" }
  ],
  "inactive_locations": [
    { "facility_id": "000", "client": "...", "location": "..." }
  ]
}

Output:  {outdir}/ascend_activity_{slug}.pdf
"""

import argparse, json, os, sys
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
except ImportError:
    print("ERROR: reportlab not installed. Run: pip install reportlab --break-system-packages")
    sys.exit(1)

# ── Palette ────────────────────────────────────────────────────────────────────
NAVY        = colors.HexColor("#1B2B4B")
TEAL        = colors.HexColor("#2E7D9B")
TEAL_LIGHT  = colors.HexColor("#E8F4F8")
GREEN       = colors.HexColor("#2E7D52")
GREEN_LIGHT = colors.HexColor("#E8F5EE")
RED         = colors.HexColor("#C0392B")
RED_LIGHT   = colors.HexColor("#FDECEA")
AMBER       = colors.HexColor("#D68910")
AMBER_LIGHT = colors.HexColor("#FEF9E7")
GRAY_LIGHT  = colors.HexColor("#F7F8FA")
GRAY_MID    = colors.HexColor("#D5D8DC")
WHITE       = colors.white
BLACK       = colors.black


def build_styles():
    base = getSampleStyleSheet()
    styles = {}
    styles["title"] = ParagraphStyle(
        "title", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=20, textColor=WHITE,
        leading=24, spaceAfter=2
    )
    styles["subtitle"] = ParagraphStyle(
        "subtitle", parent=base["Normal"],
        fontName="Helvetica", fontSize=11, textColor=colors.HexColor("#BDC3C7"),
        leading=14
    )
    styles["section_header"] = ParagraphStyle(
        "section_header", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=11, textColor=WHITE,
        leading=14
    )
    styles["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontName="Helvetica", fontSize=9, textColor=BLACK, leading=13
    )
    styles["caption"] = ParagraphStyle(
        "caption", parent=base["Normal"],
        fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#7F8C8D"),
        leading=11
    )
    styles["stat_number"] = ParagraphStyle(
        "stat_number", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=26, textColor=NAVY,
        leading=30, alignment=TA_CENTER
    )
    styles["stat_label"] = ParagraphStyle(
        "stat_label", parent=base["Normal"],
        fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#7F8C8D"),
        leading=10, alignment=TA_CENTER
    )
    return styles


def make_header(month_label, generated_on, styles):
    header_data = [[
        Paragraph("Ascend API Activity Report", styles["title"]),
        Paragraph(f"{month_label}  ·  Generated {generated_on}", styles["subtitle"])
    ]]
    tbl = Table(header_data, colWidths=[4.5*inch, 3*inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("LEFTPADDING",   (0, 0), (0, -1), 20),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 20),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def make_stat_cards(total, active, onboarded, offboarded, inactive, styles):
    def card(number, label, num_color=NAVY):
        return [
            Paragraph(str(number), ParagraphStyle(
                "n", parent=styles["stat_number"], textColor=num_color)),
            Paragraph(label, styles["stat_label"])
        ]

    data = [[
        card(total,      "Total Billed This Month"),
        card(active,     "Active — Full Month",    GREEN),
        card(onboarded,  "Newly Onboarded",        TEAL),
        card(offboarded, "Offboarded — Still Billed", AMBER if offboarded > 0 else GREEN),
        card(inactive,   "No Snapshots",           RED   if inactive   > 0 else GREEN),
    ]]

    col_w = 7.5 * inch / 5
    tbl = Table(data, colWidths=[col_w] * 5)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GRAY_LIGHT),
        ("BOX",           (0, 0), (-1, -1), 0.5, GRAY_MID),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, GRAY_MID),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def make_section_header(label, bg_color, styles):
    tbl = Table([[Paragraph(label, styles["section_header"])]],
                colWidths=[7.5 * inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg_color),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
    ]))
    return tbl


def make_active_table(locations, row_bg, styles):
    """Table with snapshot count and last date — used for active, onboarded, offboarded."""
    col_widths = [2.3*inch, 2.6*inch, 1.2*inch, 1.4*inch]
    header = ["Client", "Location", "Snapshots", "Last Snapshot"]
    rows = [header]
    for loc in locations:
        rows.append([
            loc.get("client", ""),
            loc.get("location", ""),
            str(loc.get("snapshot_count", 0)),
            loc.get("last_snapshot", "—"),
        ])
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING",    (0, 0), (-1, 0), 7),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, row_bg]),
        ("GRID",          (0, 0), (-1, -1), 0.4, GRAY_MID),
        ("ALIGN",         (2, 0), (2, -1), "CENTER"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 8),
    ]))
    return tbl


def make_inactive_table(inactive_locations, styles):
    col_widths = [2.8*inch, 4.7*inch]
    header = ["Client", "Location"]
    rows = [header] + [[loc.get("client",""), loc.get("location","")] for loc in inactive_locations]
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), RED),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING",    (0, 0), (-1, 0), 7),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [RED_LIGHT, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, GRAY_MID),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 8),
    ]))
    return tbl


def make_explainer_section(styles):
    """FAQ / explainer section appended at the end of the report."""
    DARK_NAVY   = colors.HexColor("#1B2B4B")
    RULE_COLOR  = colors.HexColor("#D5D8DC")
    Q_COLOR     = colors.HexColor("#1B2B4B")
    A_COLOR     = colors.HexColor("#2C3E50")
    BOX_BG      = colors.HexColor("#F7F8FA")

    header_style = ParagraphStyle(
        "faq_header", fontName="Helvetica-Bold", fontSize=11,
        textColor=WHITE, leading=14
    )
    q_style = ParagraphStyle(
        "faq_q", fontName="Helvetica-Bold", fontSize=9,
        textColor=Q_COLOR, leading=13, spaceBefore=8
    )
    a_style = ParagraphStyle(
        "faq_a", fontName="Helvetica", fontSize=8.5,
        textColor=A_COLOR, leading=13
    )

    faqs = [
        (
            "How is this report built?",
            "GoldenEye is the single source of truth. At the start of each run, all Ascend API "
            "facilities are read from the GoldenEye Facilities page — both active and inactive. "
            "Snapshot activity for the report month and the prior month is then pulled from the "
            "GoldenEye API. Locations are placed into one of four categories based on their "
            "GoldenEye status and whether they had snapshot activity in each month."
        ),
        (
            "What counts as 'billed'?",
            "Any location with at least one snapshot received during the report month is counted "
            "as billed under the HS1 rule — this applies regardless of cancellation status. "
            "The Total Billed figure includes Active, Newly Onboarded, and Offboarded "
            "Still Billed locations. Locations with no snapshot activity are excluded from "
            "the billed count and flagged in the No Snapshots section instead."
        ),
        (
            "Why does a cancelled location still appear as 'Offboarded — Still Billed'?",
            "When a client cancels, the location is marked inactive in GoldenEye, but the PMS "
            "connection may continue sending data for days or weeks until fully disabled. If any "
            "snapshot arrives during the billing month — even one — the location is billed. "
            "Offboarded locations in this section should be reviewed to confirm when the "
            "connection was cut and whether a billing adjustment is warranted."
        ),
        (
            "What does 'Newly Onboarded' mean?",
            "A location is flagged as Newly Onboarded if it had snapshots this month but had "
            "no snapshot activity in the prior month. This is a proxy for 'first billing month' "
            "— it may occasionally catch a location that went briefly offline last month rather "
            "than a true new install. Cross-reference with the install pipeline if needed."
        ),
    ]

    elements = []

    # Section header bar
    hdr_tbl = Table([[Paragraph("About This Report", header_style)]], colWidths=[7.5*inch])
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK_NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
    ]))
    elements.append(hdr_tbl)
    elements.append(Spacer(1, 6))

    # FAQ entries inside a light box
    faq_content = []
    for i, (question, answer) in enumerate(faqs):
        faq_content.append(Paragraph(f"Q: {question}", q_style))
        faq_content.append(Paragraph(answer, a_style))
        if i < len(faqs) - 1:
            faq_content.append(Spacer(1, 4))

    box_tbl = Table([[faq_content]], colWidths=[7.5*inch])
    box_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), BOX_BG),
        ("BOX",           (0,0),(-1,-1), 0.5, RULE_COLOR),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ]))
    elements.append(box_tbl)

    return KeepTogether(elements)


def generate(month_label, slug, outdir, data):
    out_path = os.path.join(outdir, f"ascend_activity_{slug}.pdf")
    generated_on = datetime.now().strftime("%B %d, %Y")

    total      = data.get("total_locations", 0)
    active     = data.get("active_count", 0)
    onboarded  = data.get("onboarded_count", 0)
    offboarded = data.get("offboarded_count", 0)
    inactive   = data.get("inactive_count", 0)

    active_locs     = data.get("active_locations", [])
    onboarded_locs  = data.get("onboarded_locations", [])
    offboarded_locs = data.get("offboarded_locations", [])
    inactive_locs   = data.get("inactive_locations", [])

    styles = build_styles()

    doc = SimpleDocTemplate(
        out_path, pagesize=letter,
        leftMargin=0.5*inch, rightMargin=0.5*inch,
        topMargin=0.4*inch,  bottomMargin=0.5*inch,
    )
    story = []

    story.append(make_header(month_label, generated_on, styles))
    story.append(Spacer(1, 12))
    story.append(make_stat_cards(total, active, onboarded, offboarded, inactive, styles))
    story.append(Spacer(1, 16))

    # Inactive alert
    if inactive > 0:
        alert_text = (
            f"⚠  {inactive} location{'s' if inactive != 1 else ''} had zero snapshot activity "
            f"this month and may have a sync or connectivity issue."
        )
        alert_style = ParagraphStyle("alert", fontName="Helvetica-Bold", fontSize=9,
                                     textColor=RED, leading=13)
        alert_tbl = Table([[Paragraph(alert_text, alert_style)]], colWidths=[7.5*inch])
        alert_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), RED_LIGHT),
            ("BOX",           (0,0),(-1,-1), 1, RED),
            ("TOPPADDING",    (0,0),(-1,-1), 10),
            ("BOTTOMPADDING", (0,0),(-1,-1), 10),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ]))
        story.append(alert_tbl)
        story.append(Spacer(1, 14))

    # ── Newly Onboarded ──────────────────────────────────────────────────────
    if onboarded_locs:
        story.append(make_section_header(
            f"Newly Onboarded This Month  ({onboarded})", TEAL, styles))
        story.append(Spacer(1, 4))
        story.append(make_active_table(onboarded_locs, TEAL_LIGHT, styles))
        story.append(Spacer(1, 16))

    # ── Offboarded — Still Billed ────────────────────────────────────────────
    if offboarded_locs:
        story.append(make_section_header(
            f"Offboarded — Still Billed This Month  ({offboarded})", AMBER, styles))
        story.append(Spacer(1, 4))
        story.append(make_active_table(offboarded_locs, AMBER_LIGHT, styles))
        story.append(Spacer(1, 16))

    # ── Active — Full Month ──────────────────────────────────────────────────
    if active_locs:
        story.append(make_section_header(
            f"Active — Full Month  ({active})", GREEN, styles))
        story.append(Spacer(1, 4))
        story.append(make_active_table(active_locs, GREEN_LIGHT, styles))
        story.append(Spacer(1, 16))

    # ── Inactive / No Snapshots ──────────────────────────────────────────────
    if inactive_locs:
        story.append(make_section_header(
            f"No Snapshots This Month  ({inactive})", RED, styles))
        story.append(Spacer(1, 4))
        story.append(make_inactive_table(inactive_locs, styles))
        story.append(Spacer(1, 16))

    # ── About This Report (FAQ) ──────────────────────────────────────────────
    story.append(make_explainer_section(styles))
    story.append(Spacer(1, 14))

    # Footer
    footer_style = ParagraphStyle("footer", fontName="Helvetica", fontSize=7.5,
                                  textColor=colors.HexColor("#95A5A6"), leading=11)
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_MID))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Report period: {month_label}.  "
        f"Active = had snapshots in both prior and current month.  "
        f"Newly Onboarded = first appeared this month.  "
        f"Offboarded = cancelled but had snapshot activity this month.  "
        f"Source: InsideDesk GoldenEye.",
        footer_style
    ))

    doc.build(story)
    size_kb = os.path.getsize(out_path) / 1024
    print(f"PDF written: {out_path}  ({size_kb:.1f} KB)")
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month",  required=True)
    parser.add_argument("--slug",   required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--data",   required=True)
    args = parser.parse_args()

    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in --data: {e}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.outdir, exist_ok=True)
    generate(args.month, args.slug, args.outdir, data)


if __name__ == "__main__":
    main()

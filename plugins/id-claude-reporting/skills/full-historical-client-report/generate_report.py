#!/usr/bin/env python3
"""
generate_report.py — Full Historical Client Report PDF generator
Usage:
    python3 generate_report.py --client "Client Name" --slug "slug" --outdir "/path" --data '<json>'
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
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
    print("reportlab not installed. Run: pip install reportlab --break-system-packages -q")
    sys.exit(1)


# ── Colour palette ────────────────────────────────────────────────────────────
C_ACTIVE   = colors.HexColor("#27AE60")
C_AT_RISK  = colors.HexColor("#E67E22")
C_CHURNED  = colors.HexColor("#E74C3C")
C_TEAL     = colors.HexColor("#1ABC9C")
C_HEADER   = colors.HexColor("#2C3E50")
C_SUBHEAD  = colors.HexColor("#34495E")
C_ROW_ALT  = colors.HexColor("#F8F9FA")
C_WHITE    = colors.white
C_LIGHT    = colors.HexColor("#ECF0F1")
C_WINBACK  = colors.HexColor("#8E44AD")
C_CARD_BG  = colors.HexColor("#F0F3F4")
C_CANCEL   = colors.HexColor("#E74C3C")
C_SUPPORT  = colors.HexColor("#2980B9")
C_INSTALL  = colors.HexColor("#27AE60")
C_ONBOARD  = colors.HexColor("#8E44AD")
C_AR       = colors.HexColor("#E67E22")
C_MISC     = colors.HexColor("#7F8C8D")

STATUS_COLOR = {
    "Active":  C_ACTIVE,
    "At Risk": C_AT_RISK,
    "Churned": C_CHURNED,
}

# Pipeline label detection from stage string
PIPELINE_ORDER = ["Onboarding", "Support", "Install", "AR", "Claim Feedback", "Other"]
PIPELINE_COLOR = {
    "Onboarding":      C_ONBOARD,
    "Support":         C_SUPPORT,
    "Install":         C_INSTALL,
    "AR":              C_AR,
    "Claim Feedback":  C_TEAL,
    "Other":           C_MISC,
}

def detect_pipeline(stage_str):
    s = (stage_str or "").lower()
    if "onboarding" in s:   return "Onboarding"
    if "install" in s:      return "Install"
    if "claim feedback" in s or "claim" in s: return "Claim Feedback"
    if "ar" in s or "accounts receivable" in s: return "AR"
    if "support" in s:      return "Support"
    return "Other"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--client",  required=True)
    p.add_argument("--slug",    required=True)
    p.add_argument("--outdir",  required=True)
    p.add_argument("--data",    required=True, help="JSON string")
    return p.parse_args()


def make_styles():
    return {
        "title":     ParagraphStyle("title",    fontSize=20, textColor=C_WHITE,   leading=24, fontName="Helvetica-Bold"),
        "subtitle":  ParagraphStyle("subtitle", fontSize=11, textColor=C_LIGHT,   leading=14, fontName="Helvetica"),
        "h2":        ParagraphStyle("h2",       fontSize=13, textColor=C_HEADER,  leading=18, fontName="Helvetica-Bold", spaceAfter=4),
        "h3":        ParagraphStyle("h3",       fontSize=10, textColor=C_SUBHEAD, leading=13, fontName="Helvetica-Bold", spaceAfter=2),
        "body":      ParagraphStyle("body",     fontSize=9,  textColor=C_HEADER,  leading=13, fontName="Helvetica"),
        "small":     ParagraphStyle("small",    fontSize=8,  textColor=C_SUBHEAD, leading=11, fontName="Helvetica"),
        "small_w":   ParagraphStyle("small_w",  fontSize=8,  textColor=C_WHITE,   leading=11, fontName="Helvetica"),
        "bullet":    ParagraphStyle("bullet",   fontSize=9,  textColor=C_HEADER,  leading=13, fontName="Helvetica", leftIndent=12),
        "card_num":  ParagraphStyle("card_num", fontSize=22, textColor=C_HEADER,  leading=26, fontName="Helvetica-Bold", alignment=TA_CENTER),
        "card_lbl":  ParagraphStyle("card_lbl", fontSize=8,  textColor=C_SUBHEAD, leading=10, fontName="Helvetica",      alignment=TA_CENTER),
        "rec_title": ParagraphStyle("rec_title",fontSize=9,  textColor=C_WHITE,   leading=12, fontName="Helvetica-Bold"),
        "rec_body":  ParagraphStyle("rec_body", fontSize=8,  textColor=C_HEADER,  leading=11, fontName="Helvetica"),
        "rec_key":   ParagraphStyle("rec_key",  fontSize=8,  textColor=C_SUBHEAD, leading=11, fontName="Helvetica-Bold"),
        "pip_hdr":   ParagraphStyle("pip_hdr",  fontSize=9,  textColor=C_WHITE,   leading=12, fontName="Helvetica-Bold"),
    }


def section_header(title, styles):
    return [
        Spacer(1, 0.15 * inch),
        Paragraph(title.upper(), styles["h2"]),
        HRFlowable(width="100%", thickness=1, color=C_LIGHT, spaceAfter=6),
    ]


def kv_table(pairs, styles, key_width=1.6, val_width=5.0):
    data = [[Paragraph(f"<b>{k}</b>", styles["rec_key"]),
             Paragraph(str(v), styles["rec_body"])] for k, v in pairs]
    t = Table(data, colWidths=[key_width * inch, val_width * inch])
    t.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
    ]))
    return t


def summary_cards(data, styles):
    """Row of metric cards: Locations · Contacts · Cancellations · Tickets · Emails."""
    summary      = data.get("summary", {})
    n_locs_ever  = summary.get("total_locations_ever", 0)
    n_active     = summary.get("current_active", 0)
    n_cancel     = len(data.get("cancellations", []))
    n_tickets    = len(data.get("tickets", []))
    n_contacts   = len(data.get("contacts", []))
    n_emails     = len(data.get("email_summary", []))

    metrics = [
        (str(n_locs_ever),  "Locations\n(All-time)"),
        (str(n_active),     "Currently\nActive"),
        (str(n_cancel),     "Cancellation\nRecords"),
        (str(n_tickets),    "HubSpot\nTickets"),
        (str(n_contacts),   "Contacts"),
        (str(n_emails),     "Email\nThreads"),
    ]

    card_w = 7.1 / len(metrics) * inch
    cells  = []
    for num, label in metrics:
        cell = Table(
            [[Paragraph(num, styles["card_num"])],
             [Paragraph(label, styles["card_lbl"])]],
            colWidths=[card_w - 0.1 * inch]
        )
        cell.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), C_CARD_BG),
            ("TOPPADDING",   (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("BOX",          (0, 0), (-1, -1), 0.5, C_LIGHT),
        ]))
        cells.append(cell)

    row = Table([cells], colWidths=[card_w] * len(metrics))
    row.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING",(0, 0), (-1, -1), 2),
    ]))
    return row


def cancellation_record_block(c, index, total, styles):
    """Render a single cancellation record as a clearly bordered card."""
    stage      = c.get("stage", "—")
    stage_colour = C_CANCEL if "churn" in stage.lower() else C_AT_RISK

    # Header bar
    header_text = f"Record {index} of {total}  ·  {c.get('name', '—')}"
    header_row  = Table(
        [[Paragraph(header_text, styles["rec_title"])]],
        colWidths=[6.7 * inch]
    )
    header_row.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), stage_colour),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
    ]))

    # Detail rows
    pairs = [
        ("Stage",     stage),
        ("Reason(s)", c.get("reason", "—")),
        ("Requested", c.get("date_requested", "—")),
        ("HubSpot",   c.get("hs_url", "—")),
    ]
    detail = kv_table(pairs, styles, key_width=1.1, val_width=5.6)

    body = Table(
        [[detail]],
        colWidths=[6.7 * inch]
    )
    body.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), colors.HexColor("#FEF9F9")),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
    ]))

    outer = Table(
        [[header_row], [body]],
        colWidths=[6.7 * inch]
    )
    outer.setStyle(TableStyle([
        ("BOX",         (0, 0), (-1, -1), 1, stage_colour),
        ("TOPPADDING",  (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0,0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",(0, 0), (-1, -1), 0),
    ]))
    return outer


def ticket_pipeline_section(pipeline, tickets, pip_color, styles):
    """Render one pipeline group with a coloured sub-header and ticket rows."""
    count = len(tickets)
    hdr = Table(
        [[Paragraph(f"{pipeline.upper()}  ({count})", styles["pip_hdr"])]],
        colWidths=[6.7 * inch]
    )
    hdr.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), pip_color),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
    ]))

    rows = [["Subject", "Stage", "Created", "Link"]]
    for t in tickets:
        # Strip pipeline suffix from stage for display
        stage_clean = re.sub(r'\s*\(.*?\)', '', t.get("stage", "—")).strip()
        rows.append([
            Paragraph(t.get("subject", "—"), styles["small"]),
            Paragraph(stage_clean, styles["small"]),
            t.get("created", "—"),
            Paragraph(t.get("hs_url", "—"), styles["small"]),
        ])

    tbl = Table(rows, colWidths=[2.5*inch, 0.9*inch, 0.75*inch, 2.55*inch], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  C_HEADER),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_ROW_ALT]),
        ("GRID",          (0, 0), (-1, -1), 0.25, C_LIGHT),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
    ]))

    return [hdr, tbl, Spacer(1, 0.08 * inch)]


def build_pdf(data, client, slug, outdir):
    out_path = os.path.join(outdir, f"client_history_{slug}.pdf")
    doc = SimpleDocTemplate(
        out_path, pagesize=letter,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch
    )
    styles       = make_styles()
    story        = []
    client_status = data.get("client_status", "Unknown")
    status_colour = STATUS_COLOR.get(client_status, C_HEADER)
    summary       = data.get("summary", {})
    report_date   = data.get("report_date", datetime.today().strftime("%Y-%m-%d"))

    # ── Cover header ──────────────────────────────────────────────────────────
    ht = Table([[p] for p in [
        Paragraph("Client History Report", styles["title"]),
        Paragraph(client, ParagraphStyle("cn", fontSize=16, textColor=C_WHITE, fontName="Helvetica-Bold", leading=20)),
        Paragraph(f"Generated {report_date}  ·  Status: {client_status}", styles["subtitle"]),
    ]], colWidths=[7.1 * inch])
    ht.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), status_colour),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 12),
    ]))
    story.append(ht)
    story.append(Spacer(1, 0.12 * inch))

    # ── Summary cards ─────────────────────────────────────────────────────────
    story.append(summary_cards(data, styles))
    story.append(Spacer(1, 0.12 * inch))

    # ── Section 1: Client Overview ────────────────────────────────────────────
    story += section_header("1. Client Overview", styles)
    pms_str = ", ".join(f"{k} ({v})" for k, v in summary.get("pms_breakdown", {}).items())
    pairs = [
        ("HubSpot",          data.get("hubspot_company_url", "—")),
        ("Status",           client_status),
        ("First Snapshot",   summary.get("first_snapshot", "—")),
        ("Last Snapshot",    summary.get("last_snapshot", "—")),
        ("Tenure",           f"{summary.get('tenure_months', '—')} months"),
        ("Locations (ever)", summary.get("total_locations_ever", "—")),
        ("Peak Active",      summary.get("peak_active", "—")),
        ("Currently Active", summary.get("current_active", "—")),
        ("PMS Mix",          pms_str or "—"),
    ]
    story.append(kv_table(pairs, styles))

    # ── Section 2: Location Summary ───────────────────────────────────────────
    story += section_header("2. Location Summary", styles)
    locs = data.get("locations", [])
    if locs:
        headers = ["GE ID", "Location", "PMS", "Status", "First Snap", "Last Snap"]
        rows    = [headers]
        for loc in locs:
            rows.append([
                loc.get("facility_id", "—"),
                loc.get("name", "—"),
                loc.get("pms", "—"),
                loc.get("status", "—"),
                loc.get("first_snap", "—"),
                loc.get("last_snap", "—"),
            ])
        col_w = [0.55*inch, 2.4*inch, 1.1*inch, 0.75*inch, 0.9*inch, 0.9*inch]
        t = Table(rows, colWidths=col_w, repeatRows=1)
        style = [
            ("BACKGROUND",    (0, 0), (-1, 0),  C_HEADER),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_ROW_ALT]),
            ("GRID",          (0, 0), (-1, -1), 0.25, C_LIGHT),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        for i, loc in enumerate(locs, start=1):
            style.append(("TEXTCOLOR", (3, i), (3, i),
                          C_CHURNED if loc.get("status") == "inactive" else C_ACTIVE))
        t.setStyle(TableStyle(style))
        story.append(t)
    else:
        story.append(Paragraph("No location records found in HubSpot.", styles["body"]))

    # ── Section 3: Snapshot Activity Timeline ─────────────────────────────────
    timeline = data.get("snapshot_timeline", {})
    if timeline:
        story += section_header("3. Snapshot Activity Timeline", styles)
        sorted_months = sorted(timeline.keys())
        max_val = max(timeline.values()) or 1
        bar_max_w = 5.5 * inch
        rows = []
        for month in sorted_months:
            val   = timeline[month]
            bar_w = max(0.05 * inch, (val / max_val) * bar_max_w)
            bar   = Table([[""]], colWidths=[bar_w], rowHeights=[10])
            bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), C_TEAL)]))
            rows.append([Paragraph(month, styles["small"]), bar, Paragraph(str(val), styles["small"])])
        t = Table(rows, colWidths=[0.75*inch, bar_max_w + 0.1*inch, 0.5*inch])
        t.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(t)

    # ── Section 4: Cancellation History ───────────────────────────────────────
    cancellations = data.get("cancellations", [])
    if cancellations:
        n = len(cancellations)
        story += section_header(f"4. Cancellation History ({n})", styles)
        for i, c in enumerate(cancellations, start=1):
            story.append(cancellation_record_block(c, i, n, styles))
            if i < n:
                story.append(Spacer(1, 0.1 * inch))

    # ── Section 5: HubSpot Tickets ────────────────────────────────────────────
    tickets = data.get("tickets", [])
    if tickets:
        n = len(tickets)
        story += section_header(f"5. HubSpot Tickets ({n})", styles)

        # Group by pipeline
        grouped = defaultdict(list)
        for t in tickets:
            grouped[detect_pipeline(t.get("stage", ""))].append(t)

        for pipeline in PIPELINE_ORDER:
            if pipeline not in grouped:
                continue
            pip_color = PIPELINE_COLOR[pipeline]
            story += ticket_pipeline_section(pipeline, grouped[pipeline], pip_color, styles)

    # ── Section 6: Key Contacts ───────────────────────────────────────────────
    contacts = data.get("contacts", [])
    if contacts:
        n = len(contacts)
        story += section_header(f"6. Key Contacts ({n})", styles)
        headers = ["Name", "Email", "Title", "Type"]
        rows    = [headers] + [
            [c.get("name", "—"), c.get("email", "—"),
             c.get("title", "—"), c.get("type", "—")]
            for c in contacts
        ]
        t = Table(rows, colWidths=[1.5*inch, 2.2*inch, 1.9*inch, 1.1*inch], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  C_HEADER),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_ROW_ALT]),
            ("GRID",          (0, 0), (-1, -1), 0.25, C_LIGHT),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    # ── Section 7: Email Trail ────────────────────────────────────────────────
    emails = data.get("email_summary", [])
    if emails:
        n = len(emails)
        story += section_header(f"7. Email Trail ({n})", styles)
        headers = ["Date", "Subject", "Direction", "Tag", "Snippet"]
        rows    = [headers] + [
            [e.get("date", "—"),
             Paragraph(e.get("subject", "—"), styles["small"]),
             e.get("direction", "—"),
             e.get("tag", "—"),
             Paragraph(e.get("snippet", "—"), styles["small"])]
            for e in emails
        ]
        t = Table(rows, colWidths=[0.75*inch, 1.8*inch, 0.75*inch, 0.85*inch, 2.55*inch], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  C_HEADER),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_ROW_ALT]),
            ("GRID",          (0, 0), (-1, -1), 0.25, C_LIGHT),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    # ── Section 8: Winback Intelligence (churned only) ────────────────────────
    winback = data.get("winback_intel", {})
    if winback.get("show"):
        story += section_header("8. Winback Intelligence", styles)
        wb_pairs = [
            ("Tenure",          winback.get("tenure_summary", "—")),
            ("Peak Footprint",  winback.get("peak_footprint", "—")),
            ("Churn Reasons",   ", ".join(winback.get("churn_reasons", []))),
            ("Primary Contact", winback.get("primary_contact", "—")),
            ("Last Email",      winback.get("last_email_date", "—")),
        ]
        wb_kv  = kv_table(wb_pairs, styles)
        points = winback.get("talking_points", [])
        bullets = [Paragraph(f"• {pt}", styles["bullet"]) for pt in points]

        inner = [[wb_kv]] + [[b] for b in bullets]
        inner_t = Table(inner, colWidths=[6.9 * inch])
        inner_t.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), colors.HexColor("#F5EEF8")),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
            ("BOX",          (0, 0), (-1, -1), 1, C_WINBACK),
        ]))
        story.append(inner_t)

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story)
    print(f"PDF written: {out_path}")
    return out_path


def main():
    args = parse_args()
    data = json.loads(args.data)
    out  = build_pdf(data, args.client, args.slug, args.outdir)
    print(f"OK: {out}")


if __name__ == "__main__":
    main()

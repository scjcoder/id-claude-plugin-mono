#!/usr/bin/env python3
"""
Generate PDF Snapshot Error Report for InsideDesk.

This script is the CANONICAL template for snapshot error reports.
Claude must always call this script — never generate report code inline.

Usage:
    python3 generate_report.py \
        --dates  "2026-05-10_11" \
        --outdir "/Users/sean/CODE/insidedesk-claude-plugin/Insidedesk Claude Plugin" \
        --data   '<JSON string>'

JSON data schema:
{
  "date_range_display": "May 10-11, 2026",
  "total_records": 1720,

  "errors_422": [
    {
      "client": "Southeast-Dental-Partners",
      "facility": "Monroe Dental Care",
      "count": 1,
      "received": "May 10 6:00 PM",
      "notes": "OpenDental 25.2.52.0 - 2 chunks / 122 claims. Tax ID not in system config - action required"
    }
  ],

  "errors_400_today_label":     "May 11, 2026 (7:42 AM - 9:12 AM)",
  "errors_400_today_summary":   "A broad burst of 400 errors affected multiple large clients...",
  "errors_400_today": [
    {
      "client":     "ProSmile-Dental-Group",
      "facilities": ["Little Falls", "Hazlet", "Old Bridge"],
      "count":      "~380+",
      "first":      "7:42 AM",
      "last":       "8:06 AM",
      "notes":      "All active facilities hit. ~24-min window."
    }
  ],

  "errors_400_yesterday_label":     "May 10, 2026 (2:10 AM - 2:17 AM)",
  "errors_400_yesterday_summary":   "A separate overnight burst...",
  "errors_400_yesterday": [ ... same shape as errors_400_today ... ],

  "errors_201": [
    {
      "client":     "IDSO",
      "facility":   "Lakewood Family Dental of Fortwayne",
      "chunks":     "6 / 155 claims",
      "digested":   "4",
      "errors":     "8",
      "received":   "May 10 5:24 AM",
      "assessment": "Elevated - monitor next run"
    }
  ]
}

Omit (or pass empty list []) any section that has no entries.
"""

import argparse
import json
import os
import re
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(text):
    """Normalize Unicode characters that Helvetica can't render."""
    if not isinstance(text, str):
        text = str(text)
    return (text
            .replace("–", "-")   # en-dash
            .replace("—", "-")   # em-dash
            .replace("‑", "-")   # non-breaking hyphen
            .replace("·", " · ") # middle dot
            .replace("’", "'")   # right single quote
            .replace("‘", "'")   # left single quote
            .replace("“", '"')   # left double quote
            .replace("”", '"')   # right double quote
            .replace("&nbsp;", " ")
            .replace("&middot;", " · "))


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

def build_pdf(data, output_path):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    )

    # ---- Color palette ----
    NAVY      = colors.HexColor("#1a2e4a")
    RED_HDR   = colors.HexColor("#b71c1c")
    AMBER_HDR = colors.HexColor("#bf6000")
    GREEN_HDR = colors.HexColor("#1b5e20")
    LIGHT     = colors.HexColor("#f8f8f8")
    BORDER    = colors.HexColor("#e0e0e0")
    TEXT      = colors.HexColor("#1a1a1a")
    SUBTEXT   = colors.HexColor("#555555")
    GREEN_BG  = colors.HexColor("#e8f5e9")

    # ---- Styles ----
    s_title  = ParagraphStyle("title",  fontName="Helvetica-Bold",    fontSize=15,
                               textColor=colors.white, spaceAfter=4)
    s_meta   = ParagraphStyle("meta",   fontName="Helvetica",         fontSize=9,
                               textColor=colors.HexColor("#aaccdd"), spaceAfter=0)
    s_sec    = ParagraphStyle("sec",    fontName="Helvetica-Bold",    fontSize=11,
                               textColor=colors.white)
    s_note   = ParagraphStyle("note",   fontName="Helvetica-Oblique", fontSize=8,
                               textColor=SUBTEXT, leading=11, spaceAfter=6)
    s_th     = ParagraphStyle("th",     fontName="Helvetica-Bold",    fontSize=8,
                               textColor=SUBTEXT, leading=10)
    s_td     = ParagraphStyle("td",     fontName="Helvetica",         fontSize=8.5,
                               textColor=TEXT, leading=12)
    s_td_b   = ParagraphStyle("td_b",   fontName="Helvetica-Bold",    fontSize=8.5,
                               textColor=TEXT, leading=12)
    s_td_sm  = ParagraphStyle("td_sm",  fontName="Helvetica",         fontSize=7.5,
                               textColor=SUBTEXT, leading=11)
    s_ok     = ParagraphStyle("ok",     fontName="Helvetica-Bold",    fontSize=11,
                               textColor=colors.HexColor("#1b5e20"), alignment=1)

    W = 7.2 * inch  # usable width

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.65*inch, rightMargin=0.65*inch,
        topMargin=0.65*inch, bottomMargin=0.65*inch
    )
    story = []

    date_range    = _safe(data.get("date_range_display", ""))
    total_records = data.get("total_records", 0)
    generated     = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    errors_422         = data.get("errors_422", [])
    errors_400_today   = data.get("errors_400_today", [])
    errors_400_yest    = data.get("errors_400_yesterday", [])
    errors_201         = data.get("errors_201", [])
    has_422  = bool(errors_422)
    has_400  = bool(errors_400_today or errors_400_yest)
    has_201  = bool(errors_201)
    no_errors = not (has_422 or has_400 or has_201)

    # ---- Title block ----
    title_tbl = Table(
        [[Paragraph("Snapshot Error Report", s_title)],
         [Paragraph(
             f"Period: {date_range}  ·  Errors Only Filter  ·  "
             f"{total_records:,} error records  ·  Generated {generated}", s_meta
         )]],
        colWidths=[W]
    )
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 14))

    # ---- Overview table ----
    ov_rows = [[
        Paragraph("<b>Status</b>",        s_th),
        Paragraph("<b>Description</b>",   s_th),
        Paragraph("<b>Total Records</b>", s_th),
        Paragraph("<b>Priority</b>",      s_th),
    ]]
    if has_422:
        ov_rows.append([
            Paragraph('<font color="#c0392b"><b>422</b></font>',  s_td_b),
            Paragraph("Tax ID Not in Config",                      s_td),
            Paragraph(f"<b>{len(errors_422)}</b>",                 s_td_b),
            Paragraph('<font color="#c0392b"><b>HIGH</b></font>',  s_td_b),
        ])
    if has_400:
        total_400 = len(errors_400_today) + len(errors_400_yest)
        ov_rows.append([
            Paragraph('<font color="#d4820a"><b>400</b></font>',  s_td_b),
            Paragraph("Malformed JSON",                            s_td),
            Paragraph(f"<b>~{total_400:,}+</b>",                  s_td_b),
            Paragraph('<font color="#d4820a"><b>HIGH</b></font>',  s_td_b),
        ])
    if has_201:
        ov_rows.append([
            Paragraph('<font color="#2e7d32"><b>201*</b></font>', s_td_b),
            Paragraph("Digestion Warnings (info only)",            s_td),
            Paragraph(f"<b>{len(errors_201)} snaps</b>",           s_td_b),
            Paragraph('<font color="#2e7d32"><b>INFO</b></font>',  s_td_b),
        ])
    if no_errors:
        ov_rows.append([
            Paragraph("—", s_td), Paragraph("No errors found", s_td),
            Paragraph("0", s_td), Paragraph("—", s_td),
        ])

    ov_tbl = Table(ov_rows,
                   colWidths=[0.8*inch, 3.0*inch, 1.5*inch, 1.9*inch],
                   repeatRows=1)
    ov_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  LIGHT),
        ("LINEBELOW",     (0, 0), (-1, 0),  1.5, BORDER),
        ("LINEBELOW",     (0, 1), (-1, -1), 0.5, BORDER),
        ("BOX",           (0, 0), (-1, -1), 1, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(ov_tbl)
    if has_201:
        story.append(Paragraph(
            "* 201 digestion warnings noted but none meet the flagging threshold "
            "(majority of chunks erroring).", s_note
        ))
    story.append(Spacer(1, 16))

    # ---- Helper: section header bar ----
    def sec_hdr(title, bg):
        t = Table([[Paragraph(title, s_sec)]], colWidths=[W])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ]))
        return t

    # ---- Helper: table style (shared) ----
    def base_table_style():
        return TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0),  LIGHT),
            ("LINEBELOW",      (0, 0), (-1, 0),  1.5, BORDER),
            ("LINEBELOW",      (0, 1), (-1, -1), 0.5, BORDER),
            ("BOX",            (0, 0), (-1, -1), 1, BORDER),
            ("TOPPADDING",     (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
            ("LEFTPADDING",    (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
            ("VALIGN",         (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#fafafa")]),
        ])

    # ---- 422 section ----
    if has_422:
        story.append(sec_hdr("422 — Tax ID Not in Config (HIGH IMPORTANCE)", RED_HDR))
        story.append(Spacer(1, 4))
        rows = [[
            Paragraph("<b>Client</b>",    s_th),
            Paragraph("<b>Facility</b>",  s_th),
            Paragraph("<b>Count</b>",     s_th),
            Paragraph("<b>Received</b>",  s_th),
            Paragraph("<b>PMS / Notes</b>", s_th),
        ]]
        for e in errors_422:
            rows.append([
                Paragraph(_safe(e.get("client",   "")), s_td_b),
                Paragraph(_safe(e.get("facility", "")), s_td),
                Paragraph(_safe(str(e.get("count", ""))), s_td),
                Paragraph(_safe(e.get("received", "")), s_td_sm),
                Paragraph(_safe(e.get("notes",    "")), s_td_sm),
            ])
        t = Table(rows,
                  colWidths=[1.8*inch, 2.0*inch, 0.55*inch, 1.0*inch, 1.85*inch],
                  repeatRows=1)
        t.setStyle(base_table_style())
        story.append(t)
        story.append(Spacer(1, 16))

    # ---- 400 section helper ----
    def render_400(errors, label, summary_key):
        story.append(sec_hdr(f"400 — Malformed JSON  ·  {label}", AMBER_HDR))
        story.append(Spacer(1, 4))
        summary = data.get(summary_key, "")
        if summary:
            story.append(Paragraph(_safe(summary), s_note))
        rows = [[
            Paragraph("<b>Client</b>",             s_th),
            Paragraph("<b>Facilities Affected</b>", s_th),
            Paragraph("<b>Count</b>",              s_th),
            Paragraph("<b>First</b>",              s_th),
            Paragraph("<b>Last</b>",               s_th),
            Paragraph("<b>Notes</b>",              s_th),
        ]]
        for e in errors:
            facs = e.get("facilities", [])
            fac_text = " · ".join(_safe(f) for f in facs) if isinstance(facs, list) else _safe(str(facs))
            rows.append([
                Paragraph(_safe(e.get("client", "")),          s_td_b),
                Paragraph(fac_text,                             s_td_sm),
                Paragraph(_safe(str(e.get("count", ""))),       s_td),
                Paragraph(_safe(e.get("first", "")),            s_td_sm),
                Paragraph(_safe(e.get("last",  "")),            s_td_sm),
                Paragraph(_safe(e.get("notes", "")),            s_td_sm),
            ])
        t = Table(rows,
                  colWidths=[1.45*inch, 2.2*inch, 0.6*inch, 0.7*inch, 0.7*inch, 1.55*inch],
                  repeatRows=1)
        t.setStyle(base_table_style())
        story.append(t)
        story.append(Spacer(1, 16))

    if errors_400_today:
        render_400(errors_400_today,
                   _safe(data.get("errors_400_today_label", "TODAY")),
                   "errors_400_today_summary")
    if errors_400_yest:
        render_400(errors_400_yest,
                   _safe(data.get("errors_400_yesterday_label", "YESTERDAY")),
                   "errors_400_yesterday_summary")

    # ---- 201 section ----
    if has_201:
        story.append(sec_hdr("201 — Digestion Notes (Informational — No Action Required)", GREEN_HDR))
        story.append(Spacer(1, 4))
        intro = data.get(
            "errors_201_intro",
            "The following 201 snapshots appeared in the error view due to at least one "
            "digestion error, but none meet the flagging threshold (majority of chunks "
            "erroring). Included for visibility only."
        )
        story.append(Paragraph(_safe(intro), s_note))
        rows = [[
            Paragraph("<b>Client</b>",     s_th),
            Paragraph("<b>Facility</b>",   s_th),
            Paragraph("<b>Chunks</b>",     s_th),
            Paragraph("<b>Digested</b>",   s_th),
            Paragraph("<b>Errors</b>",     s_th),
            Paragraph("<b>Received</b>",   s_th),
            Paragraph("<b>Assessment</b>", s_th),
        ]]
        for e in errors_201:
            rows.append([
                Paragraph(_safe(e.get("client",     "")), s_td_b),
                Paragraph(_safe(e.get("facility",   "")), s_td),
                Paragraph(_safe(e.get("chunks",     "")), s_td_sm),
                Paragraph(_safe(str(e.get("digested",""))), s_td_sm),
                Paragraph(_safe(str(e.get("errors",  ""))), s_td_sm),
                Paragraph(_safe(e.get("received",   "")), s_td_sm),
                Paragraph(_safe(e.get("assessment", "")), s_td_sm),
            ])
        t = Table(rows,
                  colWidths=[1.35*inch, 1.65*inch, 0.85*inch,
                              0.65*inch, 0.55*inch, 1.1*inch, 1.05*inch],
                  repeatRows=1)
        t.setStyle(base_table_style())
        story.append(t)

    # ---- No-errors block ----
    if no_errors:
        ok_tbl = Table(
            [[Paragraph("No snapshot errors found  ·  All snapshots completed successfully", s_ok)]],
            colWidths=[W]
        )
        ok_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), GREEN_BG),
            ("BOX",           (0, 0), (-1, -1), 1, colors.HexColor("#a5d6a7")),
            ("TOPPADDING",    (0, 0), (-1, -1), 18),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
            ("LEFTPADDING",   (0, 0), (-1, -1), 16),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(ok_tbl)

    doc.build(story)
    return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate InsideDesk Snapshot Error Report PDF"
    )
    parser.add_argument("--data",   required=True, help="JSON data string (see module docstring)")
    parser.add_argument("--dates",  required=True, help="Date slug e.g. 2026-05-10_11")
    parser.add_argument("--outdir", required=True, help="Output directory path")
    args = parser.parse_args()

    data     = json.loads(args.data)
    pdf_path = os.path.join(args.outdir, f"snapshot_error_report_{args.dates}.pdf")

    build_pdf(data, pdf_path)
    print(f"PDF  -> {pdf_path}")


if __name__ == "__main__":
    main()

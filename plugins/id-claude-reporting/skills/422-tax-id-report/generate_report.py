#!/usr/bin/env python3
"""
Generate HTML and PDF 422 Tax ID error reports for a single client.

Usage:
    python3 generate_report.py \
        --data   '{"Acme Dental of Howell": {"pms": "Denticon", "taxIds": {...}}}' \
        --client "Eastern-Dental-Management" \
        --dates  "2026-05-14_15" \
        --outdir "/Users/sean/CODE/insidedesk-claude-plugin/Insidedesk Claude Plugin"
"""

import argparse
import json
import os
import re
from datetime import datetime

PREVIEW_LIMIT = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(name):
    return re.sub(r'[^a-z0-9_-]', '_', name.lower()).strip('_')


def client_display_name(client_slug):
    return client_slug.replace("-", " ").replace("_", " ").title()


def sorted_claims(claims):
    ids = claims["ids"] if isinstance(claims, dict) else claims
    try:
        return sorted(ids, key=int)
    except ValueError:
        return sorted(ids)


def claim_count(claims):
    """Return the true total claim count, handling both plain list and compact {count, ids} format."""
    if isinstance(claims, dict):
        return claims.get("count", len(claims.get("ids", [])))
    return len(claims)


def claims_overflow(claims):
    """Return number of claims beyond the preview limit (not shown as IDs)."""
    if isinstance(claims, dict):
        shown = len(claims.get("ids", []))
        total = claims.get("count", shown)
        return max(0, total - shown)
    return max(0, len(claims) - PREVIEW_LIMIT)


def is_invalid_ein(taxid):
    """
    Flag tax IDs that are obviously not valid EINs.
    EINs are exactly 9 digits (GoldenEye stores them without dashes).
    We can't cryptographically verify an EIN, but we flag:
      - Wrong digit count (not 9 digits after stripping non-digits)
      - All-same-digit sequences (000000000, 111111111, etc.)
      - Obvious sequential values (123456789, 987654321)
    """
    digits = re.sub(r'\D', '', taxid)
    if len(digits) != 9:
        return True
    if len(set(digits)) == 1:          # 000000000, 111111111, etc.
        return True
    if digits in ('123456789', '987654321'):
        return True
    return False


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Tax ID Error Report - {client_display}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
      background:#f5f5f5;color:#1a1a1a;font-size:14px}}
.page{{max-width:980px;margin:0 auto;padding:36px 28px}}
.header{{background:#1a2e4a;color:white;padding:28px;border-radius:10px;margin-bottom:24px}}
.header h1{{font-size:20px;font-weight:700}}
.header .meta{{font-size:12px;opacity:.65;margin-top:6px}}
.badge{{display:inline-block;background:rgba(255,255,255,.15);color:white;
        font-size:11px;font-weight:600;padding:2px 10px;border-radius:100px;margin-left:10px;
        vertical-align:middle}}
.summary{{display:flex;gap:14px;margin-bottom:24px;flex-wrap:wrap}}
.card{{background:white;border-radius:8px;padding:14px 18px;flex:1;min-width:150px;
       box-shadow:0 1px 3px rgba(0,0,0,.07);border-left:4px solid #c94a25}}
.card .num{{font-size:26px;font-weight:700;color:#c94a25}}
.card .lbl{{font-size:11px;color:#666;margin-top:2px}}
.facility{{background:white;border-radius:10px;margin-bottom:18px;
           box-shadow:0 1px 3px rgba(0,0,0,.07);overflow:hidden}}
.fac-hdr{{display:flex;align-items:center;justify-content:space-between;
          padding:12px 18px;background:#f8f8f8;border-bottom:1px solid #ebebeb}}
.fac-name{{font-size:14px;font-weight:700;color:#1a2e4a}}
.fac-meta{{display:flex;align-items:center;gap:10px}}
.fac-pms{{font-size:11px;color:#666;background:#ebebeb;padding:2px 8px;border-radius:4px}}
.fac-count{{font-size:11px;color:#c94a25;font-weight:600}}
.fac-id{{font-size:11px;color:#888;font-family:monospace}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;padding:7px 14px;font-size:11px;font-weight:600;color:#555;
    background:#fafafa;border-bottom:2px solid #ebebeb;
    text-transform:uppercase;letter-spacing:.4px}}
th.center{{text-align:center}}
td{{padding:9px 14px;border-bottom:1px solid #f2f2f2;vertical-align:top}}
tr:last-child td{{border-bottom:none}}
.taxid{{font-family:monospace;font-size:12px;font-weight:600;color:#1a2e4a;white-space:nowrap}}
.count{{text-align:center;font-weight:700;color:#c94a25}}
.claims{{font-family:monospace;font-size:11px;color:#555;line-height:1.75;word-break:break-all}}
.more{{font-family:sans-serif;font-style:italic;color:#aaa;font-size:11px}}
.flag{{display:inline-flex;align-items:center;gap:3px;color:#7a4800;font-size:10px;
       font-weight:700;background:#FFF3CD;border:1px solid #FFCC6F;
       padding:2px 7px;border-radius:3px;margin-left:6px;vertical-align:middle}}
.footer{{text-align:center;font-size:11px;color:#bbb;margin-top:32px;
         padding-top:16px;border-top:1px solid #e8e8e8}}
.faq{{background:white;border-radius:10px;margin-top:28px;margin-bottom:18px;
      box-shadow:0 1px 3px rgba(0,0,0,.07);overflow:hidden;border-top:4px solid #1a2e4a}}
.faq-title{{font-size:14px;font-weight:700;color:#1a2e4a;padding:14px 18px 0 18px}}
.faq-section{{padding:12px 18px;border-bottom:1px solid #f2f2f2}}
.faq-section:last-child{{border-bottom:none}}
.faq-q{{font-size:12px;font-weight:700;color:#1a2e4a;margin-bottom:5px}}
.faq-a{{font-size:12px;color:#444;line-height:1.65}}
.faq-a ul{{margin:6px 0 0 18px}}
.faq-a li{{margin-bottom:4px}}
.faq-a .action{{color:#1a2e4a;font-weight:600}}
.faq-link{{color:#c94a25;text-decoration:none}}
</style>
</head>
<body>
<div class="page">

<div class="header">
  <h1>{client_display} <span class="badge">422 Tax ID errors</span></h1>
  <div class="meta">Claim Batches Received &nbsp;&middot;&nbsp; {date_range_display} &nbsp;&middot;&nbsp; Generated {generated}</div>
</div>

<div class="summary">
  <div class="card"><div class="num">{n_facilities}</div><div class="lbl">Facilities affected</div></div>
  <div class="card"><div class="num">{n_taxids}</div><div class="lbl">Unique tax IDs</div></div>
  <div class="card"><div class="num">{n_claims}</div><div class="lbl">Total claims affected</div></div>
</div>

{facility_sections}

<div class="faq">
  <div class="faq-title">Understanding Your Tax ID Exception Report</div>
  <div class="faq-section">
    <div class="faq-q">What is this report?</div>
    <div class="faq-a">This report identifies tax ID numbers (TINs) attached to incoming claims that are not currently associated with the offices listed. Each office block in the report shows the unrecognized TIN and the specific claim numbers tied to it.</div>
  </div>
  <div class="faq-section">
    <div class="faq-q">Why does this matter?</div>
    <div class="faq-a">If a TIN isn&rsquo;t in our configuration for a given office, the claims attached to it will not process correctly on our end. This report gives you the information needed to resolve that.</div>
  </div>
  <div class="faq-section">
    <div class="faq-q">What do I need to do?</div>
    <div class="faq-a">Review each office listed and answer the following for each unrecognized TIN:
      <ul>
        <li><span class="action">Is this TIN valid and should it be associated with this office?</span><br>Let us know and we&rsquo;ll add it to our configuration. Those claims will then process normally.</li>
        <li><span class="action">Is this TIN incorrect or a data entry error?</span><br>The claims tied to it will need to be corrected directly in your practice management system. Once updated, they&rsquo;ll process correctly on our end.</li>
      </ul>
    </div>
  </div>
  <div class="faq-section">
    <div class="faq-a">Questions? Visit <a class="faq-link" href="https://insidedesk.pro">insidedesk.pro</a> to connect with us or schedule a time to review the report together.</div>
  </div>
</div>

<div class="footer">InsideDesk &nbsp;&middot;&nbsp; {client_display} &nbsp;&middot;&nbsp; {date_range_display}</div>
</div>
</body>
</html>"""


FACILITY_SECTION = """\
<div class="facility">
  <div class="fac-hdr">
    <span class="fac-name">{facility}</span>
    <span class="fac-meta">
      {fac_id_badge}
      <span class="fac-pms">{pms}</span>
      <span class="fac-count">{fac_total:,} claims</span>
    </span>
  </div>
  <table>
    <thead><tr><th>Tax ID</th><th class="center"># Claims</th><th>Claim IDs</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
</div>"""

TABLE_ROW = '      <tr><td class="taxid">{taxid}{flag}</td><td class="count">{count}</td><td class="claims">{claims_html}</td></tr>'


def _claims_html(claims):
    sc = sorted_claims(claims)
    overflow = claims_overflow(claims)
    if overflow <= 0:
        return ", ".join(sc[:PREVIEW_LIMIT])
    shown = ", ".join(sc[:PREVIEW_LIMIT])
    return f'{shown} <span class="more">... and {overflow:,} more</span>'


def build_html(client_display, date_range_display, facilities_data):
    all_taxids   = set()
    total_claims = 0
    for fac_info in facilities_data.values():
        for tid, claims in fac_info["taxIds"].items():
            all_taxids.add(tid)
            total_claims += claim_count(claims)

    sections = []
    for facility, fac_info in sorted(facilities_data.items()):
        pms       = fac_info.get("pms", "-")
        tax_ids   = fac_info["taxIds"]
        fac_total = sum(claim_count(c) for c in tax_ids.values())
        rows = []
        for taxid, claims in sorted(tax_ids.items(), key=lambda x: -claim_count(x[1])):
            flag = ' <span class="flag">&#9888; Invalid EIN</span>' if is_invalid_ein(taxid) else ""
            rows.append(TABLE_ROW.format(
                taxid=taxid, flag=flag,
                count=f"{claim_count(claims):,}",
                claims_html=_claims_html(claims)
            ))
        facility_id = fac_info.get("facilityId")
        fac_id_badge = f'<span class="fac-id">Fac {facility_id}</span>' if facility_id else ""
        sections.append(FACILITY_SECTION.format(
            facility=facility, pms=pms, fac_total=fac_total,
            fac_id_badge=fac_id_badge,
            rows="\n".join(rows)
        ))

    return HTML_TEMPLATE.format(
        client_display=client_display,
        date_range_display=date_range_display,
        generated=datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        n_facilities=len(facilities_data),
        n_taxids=len(all_taxids),
        n_claims=f"{total_claims:,}",
        facility_sections="\n".join(sections)
    )


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

def _pdf_safe(text):
    """Strip characters outside Latin-1 that Helvetica cannot render."""
    return (text
            .replace("–", "-")   # en-dash
            .replace("—", "-")   # em-dash
            .replace("‑", "-")   # non-breaking hyphen
            .replace("·", " | ") # middle dot -> pipe separator
            .replace("&nbsp;", " ")
            .replace("&middot;", " | "))


def build_pdf(client_display, date_range_display, facilities_data, output_path):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    )

    NAVY   = colors.HexColor("#1a2e4a")
    RED    = colors.HexColor("#c94a25")
    LIGHT  = colors.HexColor("#f8f8f8")
    BORDER = colors.HexColor("#ebebeb")

    styles = getSampleStyleSheet()

    s_white  = ParagraphStyle("white",  fontName="Helvetica-Bold",   fontSize=16,
                               textColor=colors.white, spaceAfter=4)
    s_meta   = ParagraphStyle("meta",   fontName="Helvetica",        fontSize=9,
                               textColor=colors.HexColor("#aaccdd"), spaceAfter=0)
    s_fac    = ParagraphStyle("fac",    fontName="Helvetica-Bold",   fontSize=12,
                               textColor=NAVY, spaceBefore=18, spaceAfter=4)
    s_pms    = ParagraphStyle("pms",    fontName="Helvetica",        fontSize=9,
                               textColor=colors.HexColor("#888888"), spaceAfter=8)
    s_th     = ParagraphStyle("th",     fontName="Helvetica-Bold",   fontSize=8,
                               textColor=colors.HexColor("#555555"))
    s_cnt    = ParagraphStyle("cnt",    fontName="Helvetica-Bold",   fontSize=10,
                               alignment=1)
    s_claims = ParagraphStyle("claims", fontName="Courier",          fontSize=7,
                               leading=11)

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.7*inch, rightMargin=0.7*inch,
        topMargin=0.7*inch,  bottomMargin=0.7*inch
    )
    story = []

    all_taxids   = set()
    total_claims = 0
    for fac_info in facilities_data.values():
        for tid, claims in fac_info["taxIds"].items():
            all_taxids.add(tid)
            total_claims += claim_count(claims)

    # Safe ASCII versions for PDF
    dates_pdf  = _pdf_safe(date_range_display)
    client_pdf = _pdf_safe(client_display)
    generated  = datetime.now().strftime("%B %d, %Y")

    # Title block
    title_tbl = Table(
        [[Paragraph(client_pdf, s_white)],
         [Paragraph(f"422 Tax ID Errors  |  {dates_pdf}  |  Generated {generated}", s_meta)]],
        colWidths=[7.1*inch]
    )
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 10))

    # Summary row
    summary_data = [[
        Paragraph(f"<b>{len(facilities_data)}</b><br/><font size='8' color='#666666'>Facilities affected</font>", styles["Normal"]),
        Paragraph(f"<b>{len(all_taxids)}</b><br/><font size='8' color='#666666'>Unique tax IDs</font>", styles["Normal"]),
        Paragraph(f"<b>{total_claims:,}</b><br/><font size='8' color='#666666'>Total claims affected</font>", styles["Normal"]),
    ]]
    summary_t = Table(summary_data, colWidths=[2.37*inch]*3, hAlign="LEFT")
    summary_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT),
        ("TEXTCOLOR",     (0, 0), (-1, -1), NAVY),
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 16),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("LINEAFTER",     (0, 0), (1, 0),  1, BORDER),
        ("BOX",           (0, 0), (-1, -1), 1, BORDER),
    ]))
    story.append(summary_t)
    story.append(Spacer(1, 16))

    # Per-facility sections
    for facility, fac_info in sorted(facilities_data.items()):
        pms       = _pdf_safe(fac_info.get("pms", "-"))
        tax_ids   = fac_info["taxIds"]
        fac_total = sum(claim_count(c) for c in tax_ids.values())

        fac_id_str = fac_info.get("facilityId")
        fac_id_prefix = f"Fac {fac_id_str}  |  " if fac_id_str else ""
        section = [
            Paragraph(_pdf_safe(facility), s_fac),
            Paragraph(f"{fac_id_prefix}{pms}  |  {fac_total:,} claims affected", s_pms),
        ]

        header_row = [
            Paragraph("<b>Tax ID</b>",    s_th),
            Paragraph("<b># Claims</b>",  s_th),
            Paragraph("<b>Claim IDs</b>", s_th),
        ]
        table_data = [header_row]

        for taxid, claims in sorted(tax_ids.items(), key=lambda x: -claim_count(x[1])):
            sc = sorted_claims(claims)
            overflow = claims_overflow(claims)
            if overflow <= 0:
                claims_str = ", ".join(sc[:PREVIEW_LIMIT])
            else:
                claims_str = ", ".join(sc[:PREVIEW_LIMIT]) + f" ... and {overflow:,} more"

            flag = "  [!] Invalid EIN" if is_invalid_ein(taxid) else ""
            taxid_style = ParagraphStyle("taxid_warn", fontName="Courier-Bold", fontSize=9, textColor=colors.HexColor("#8b1a00")) if is_invalid_ein(taxid) else styles["Normal"]
            table_data.append([
                Paragraph(f'<font name="Courier">{taxid}{flag}</font>', taxid_style),
                Paragraph(f'<font color="#c94a25"><b>{claim_count(claims):,}</b></font>', s_cnt),
                Paragraph(f'<font name="Courier" size="7">{claims_str}</font>', s_claims),
            ])

        t = Table(table_data, colWidths=[1.2*inch, 0.75*inch, 5.15*inch], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0),  LIGHT),
            ("LINEBELOW",      (0, 0), (-1, 0),  1.5, BORDER),
            ("LINEBELOW",      (0, 1), (-1, -1), 0.5, BORDER),
            ("BOX",            (0, 0), (-1, -1), 1,   BORDER),
            ("VALIGN",         (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",     (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
            ("LEFTPADDING",    (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
            ("ALIGN",          (1, 0), (1, -1),  "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
        ]))
        section.append(t)
        story.append(KeepTogether(section))

    # FAQ / explainer section
    story.append(Spacer(1, 20))

    DARK_BORDER = colors.HexColor("#1a2e4a")
    FAQ_BG      = colors.HexColor("#f8f8f8")

    s_faq_title = ParagraphStyle("faq_title", fontName="Helvetica-Bold", fontSize=12,
                                  textColor=NAVY, spaceAfter=10)
    s_faq_q     = ParagraphStyle("faq_q",     fontName="Helvetica-Bold", fontSize=10,
                                  textColor=NAVY, spaceAfter=3)
    s_faq_a     = ParagraphStyle("faq_a",     fontName="Helvetica",      fontSize=9,
                                  textColor=colors.HexColor("#444444"),  leading=14, spaceAfter=6)
    s_faq_link  = ParagraphStyle("faq_link",  fontName="Helvetica",      fontSize=9,
                                  textColor=colors.HexColor("#c94a25"),  leading=14)

    faq_items = [
        Paragraph("Understanding Your Tax ID Exception Report", s_faq_title),
        Paragraph("What is this report?", s_faq_q),
        Paragraph(
            "This report identifies tax ID numbers (TINs) attached to incoming claims that are not "
            "currently associated with the offices listed. Each office block shows the unrecognized "
            "TIN and the specific claim numbers tied to it.",
            s_faq_a
        ),
        Paragraph("Why does this matter?", s_faq_q),
        Paragraph(
            "If a TIN isn't in our configuration for a given office, the claims attached to it will "
            "not process correctly on our end. This report gives you the information needed to resolve that.",
            s_faq_a
        ),
        Paragraph("What do I need to do?", s_faq_q),
        Paragraph(
            "Review each office listed and answer the following for each unrecognized TIN:",
            s_faq_a
        ),
        Paragraph(
            u"•  <b>Is this TIN valid and should it be associated with this office?</b><br/>"
            u"Let us know and we'll add it to our configuration. Those claims will then process normally.",
            s_faq_a
        ),
        Paragraph(
            u"•  <b>Is this TIN incorrect or a data entry error?</b><br/>"
            u"The claims tied to it will need to be corrected directly in your practice management system. "
            u"Once updated, they'll process correctly on our end.",
            s_faq_a
        ),
        Paragraph(
            'Questions? Visit <a href="https://insidedesk.pro"><u>insidedesk.pro</u></a> to connect with us '
            'or schedule a time to review the report together.',
            s_faq_link
        ),
    ]

    faq_table = Table([[faq_items]], colWidths=[7.1*inch])
    faq_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.white),
        ("BOX",           (0, 0), (-1, -1), 1,   BORDER),
        ("LINEABOVE",     (0, 0), (-1,  0), 3,   DARK_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(faq_table)

    doc.build(story)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",   required=True, help="JSON: facility -> {pms, taxIds}")
    parser.add_argument("--client", required=True, help="Client name/slug")
    parser.add_argument("--dates",  required=True, help="Date range e.g. 2026-05-14_15")
    parser.add_argument("--outdir", required=True, help="Output directory")
    args = parser.parse_args()

    facilities_data    = json.loads(args.data)
    client_slug        = slugify(args.client)
    client_display     = client_display_name(args.client)
    date_range_display = args.dates.replace("_", " to ")

    base      = os.path.join(args.outdir, f"tax_id_report_{client_slug}_{args.dates}")
    html_path = base + ".html"
    pdf_path  = base + ".pdf"

    html = build_html(client_display, date_range_display, facilities_data)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML -> {html_path}")

    build_pdf(client_display, date_range_display, facilities_data, pdf_path)
    print(f"PDF  -> {pdf_path}")


if __name__ == "__main__":
    main()

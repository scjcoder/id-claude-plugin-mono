---
name: dos-report
description: >
  Generate the InsideDesk Date of Service (DOS) Inactivity Report from an exported Power BI
  Excel file. Use this skill whenever Sean asks about DOS report, date of service inactivity,
  offices not submitting claims, "which locations haven't had a DOS", "days since last DOS",
  "days since last claim", or "offices that are syncing but not billing". A location is
  flagged when it has a healthy PMS sync (Days Since Last PMS Snap ≤ 2) but has not had a
  new claim submitted in more than 14 days (Days Since Latest DoS > 14). The output is a
  clean PDF report grouped by client, delivered as a DM to Sean in Slack, archived to the
  long-term reports folder. Always trigger this skill when the user mentions DOS, date of
  service, or claim submission inactivity — even if they don't use the word "report".
---

# DOS Inactivity Report Skill

This skill produces the InsideDesk Date of Service (DOS) Inactivity Report. It uses the
same Power BI Excel export as the PMS OOS report (CS Datafeed table). The focus here is
different: we're looking for locations that **are syncing fine** (connection is healthy)
but **haven't submitted any new claims** in more than 14 days. These offices need a
check-in — they may be having a billing workflow issue, be temporarily closed, or simply
need a reminder.

The final deliverable is a **PDF**, sent as a Slack **DM to Sean** (`sean.johnson@insidedesk.com`).

---

## Platform note — Python path

All `$PYTHON3` references below resolve at runtime. Set the variable in bash before any
Python command:

```bash
PYTHON3=$(which python3 2>/dev/null | grep -v WindowsApps | head -1)
[ -z "$PYTHON3" ] && PYTHON3=/Users/sean/scoop/shims/python3
```

---

## Step 0 — Retrieve credentials (prerequisite)

Run the `get-secret` skill with name `slack-bot-token` to retrieve the Slack bot token
before reaching the Slack delivery step.

---

## Step 1 — Get the Power BI export

If Sean has already attached an Excel file in this conversation, use that file and skip
to Step 2.

Otherwise, **run the `powerbi-export` skill automatically** to download the latest CS
Datafeed export from Power BI. Do not ask Sean to export manually. Once complete, use
the file saved at:

```
/Users/sean/CODE/id-claude-reporting/PMS_Sync_Status_Report_YYYY-MM-DD.xlsx
```

(where `YYYY-MM-DD` is today's date). Proceed to Step 2 with that file.

---

## Step 2 — Analyze the Excel data

Use pandas to load the `Export` sheet. Key columns:

- `Client`
- `Office`
- `facility_id`
- `PMS`
- `Days Since Last PMS Snap`
- `Days Since Latest DoS`
- `Days Since Last claim Created`
- `Adjusted Active Status`
- `Notes`

### Cleaning (same as pms-oos-report)

1. Drop rows where `Client` is null or starts with `"Applied filters"` — Power BI metadata.
2. Drop the `monitoring` client (Fac 2002) — internal placeholder.
3. Drop `Inactive` rows entirely — deactivated locations have meaningless day counts.
4. Set aside `Active/Expired` and `Active/Paused` rows as pending cancellation — not
   actionable, shown separately if present.
5. Treat `NaN` status as `Active`.

After filtering, the working dataset contains only `Active` (and NaN-as-Active) rows.

### Flagging logic

A location is **flagged** when both conditions are true:

| Condition | Column | Threshold |
|---|---|---|
| Healthy PMS sync | `Days Since Last PMS Snap` | ≤ 2 (or null with known PMS) |
| No recent claims | `Days Since Latest DoS` | > 14 |

The intent: we want offices where the connection is working fine but claims have gone
quiet. If the PMS sync is also broken, that's a PMS OOS issue — route it to the OOS
report instead, don't double-flag here.

**Do not flag:**
- Locations with `Days Since Last PMS Snap` > 2 (connection issue — separate report)
- Locations with `PMS == 'Unk'` (never connected — onboarding, not a DOS issue)
- Locations where `Days Since Latest DoS` is null (no claim history — likely brand new;
  treat same as onboarding, exclude from flagged rows)

### Severity tiers

| Tier | Days Since Latest DoS |
|---|---|
| HIGH | 30+ days |
| MEDIUM | 15–29 days |

Both tiers get flagged; HIGH gets priority placement in the report.

### Compute footer stats

- Count of flagged locations (active, syncing, DOS > 14)
- Count of HIGH vs MEDIUM tier locations
- Total active clients in the dataset (for context)
- Count of pending cancellation locations (if any — shown separately, not in flagged count)

---

## Step 3 — Enrich with HubSpot tickets and Gmail threads

For each flagged location, check whether there's already an open ticket or recent email
thread explaining the inactivity. This keeps the report actionable rather than generating
noise for known situations.

### 3a — HubSpot ticket lookup

Use the HubSpot MCP connector (`mcp__eba53d3c-d280-4218-ba07-d9e0e4624ed7`) to search
the Install Pipeline for tickets related to each flagged client:

```
search_crm_objects(
  objectType: "tickets",
  query: "<client name>",
  properties: ["subject", "hs_pipeline_stage", "hubspot_owner_id",
               "hs_lastmodifieddate", "closedate", "content"]
)
```

After finding a ticket, fetch associated notes:
```
get_crm_objects(objectType: "notes", associatedWith: ticket_id)
```

Notes contain the real context — resolution updates, contact info, reasons for
inactivity — that won't be in the ticket subject alone.

**Lookback:** 30 days for HIGH tier, 14 days for MEDIUM tier.

**Interpretation:**
- Open ticket → note stage, owner, and any context from notes.
- Recently closed ticket → likely resolved; note "Verify claim activity resumed."
- No ticket → fall through to Gmail.

### 3b — Gmail thread lookup

Use the Gmail MCP connector (`mcp__bdbc2263-f755-4531-b2b3-91da919069f8`):

```
search_threads(query: "<client name> OR <office name> claims", maxResults: 5)
```

Lookback: 14 days only. Look for signals like "temporary closure", "on vacation",
"transitioning billing staff", "resolved", "claims submitted", etc.

### 3c — Merge signals and build enriched context

Priority order (highest wins):

1. Recently closed HubSpot ticket (≤7 days) — likely resolved
2. Open HubSpot ticket — use stage + owner + notes
3. Recent Gmail thread with clear signal
4. Context Sean provides in this conversation
5. Nothing found → "— needs follow-up", flag for Sean

For each flagged location, produce:
- **Reason** — what's known about why claims are quiet (if anything)
- **Status** — most current signal
- **Waiting On** — owner or team, if known
- **ETA** — if mentioned in ticket or email

---

## Step 4 — Handle any context Sean provides

If Sean mentions anything in the conversation about a specific location ("they're closed
this week", "billing staff changed"), use it in the report. After delivery, offer to add
it as a note to the relevant HubSpot ticket so it's not lost between sessions.

---

## Step 5 — Produce the HTML report

Save to the outputs folder as an intermediate file:

```
{outputs}/DOS_Inactivity_Report.html
```

> ⛔ **NEVER write your own HTML template. Copy the template below VERBATIM.**
> Do not change CSS, class names, font stack, or structure. Every DOS Report must look
> identical to prior runs. The style is intentionally minimal: white background,
> horizontal rules only, no heavy fills. Color is reserved for small dot indicators
> and subtle tag badges only.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>DOS Inactivity Report</title>
<style>
  @page { size: Letter landscape; margin: 0.4in; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 12px; color: #1a1a1a; background: #fff;
    padding: 0; max-width: 1100px;
  }
  .report-title { font-size: 16px; font-weight: 600; margin-bottom: 3px; }
  .report-meta  { font-size: 12px; color: #888; margin-bottom: 28px; }
  table { width: 100%; border-collapse: collapse; }
  thead th {
    text-align: left; font-weight: 600; font-size: 12px; color: #555;
    padding: 0 12px 10px 0; border-bottom: 1.5px solid #1a1a1a;
  }
  tbody tr { border-bottom: 1px solid #e8e8e8; page-break-inside: avoid; }
  tbody tr:last-child { border-bottom: 1.5px solid #1a1a1a; }
  tbody td { padding: 11px 12px 11px 0; vertical-align: top; line-height: 1.45; }
  .client { font-weight: 600; }
  .sub { font-weight: 400; color: #666; font-size: 12px; margin-top: 1px; }
  .tag {
    display: inline-block; font-size: 11px; font-weight: 600;
    padding: 2px 7px; border-radius: 3px; white-space: nowrap; letter-spacing: 0.02em;
  }
  .tag-high     { background: #fde8e8; color: #c0392b; }
  .tag-medium   { background: #fef3e2; color: #d4820a; }
  .tag-progress { background: #e8f4fd; color: #1a6fa8; }
  .tag-waiting  { background: #fef3e2; color: #d4820a; }
  .tag-internal { background: #f0ecfd; color: #6b3fa0; }
  .tag-expired  { background: #f2f2f2; color: #888; }
  .dot-red    { color: #e53935; margin-right: 4px; }
  .dot-orange { color: #f57c00; margin-right: 4px; }
  .days { font-weight: 600; white-space: nowrap; }
  .days-high   { color: #c0392b; }
  .days-medium { color: #d4820a; }
  .days-sync-ok   { color: #27ae60; font-weight: 600; }
  .days-sync-warn { color: #d4820a; font-weight: 600; }
  .owner { font-size: 11px; color: #444; }
  .eta   { font-size: 11px; color: #666; white-space: nowrap; }
  tbody tr.section-divider td {
    padding-top: 22px; padding-bottom: 4px; font-size: 11px;
    font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase;
    color: #aaa; border-bottom: none;
  }
  tbody tr.client-header td {
    padding-top: 16px; padding-bottom: 5px; font-size: 11px;
    font-weight: 700; color: #1a1a1a; border-bottom: 1px solid #d0d0d0;
    background: #fafafa;
  }
  .footer { margin-top: 20px; font-size: 11px; color: #888; }
  .footer strong { color: #333; }
</style>
</head>
<body>
  <div class="report-title">Date of Service Inactivity Report</div>
  <div class="report-meta"><!-- DATE --> · Grouped by client · Locations syncing but with no claims in 14+ days · Green sync = 0 days, orange = 1–2 days (all within healthy threshold)</div>
  <table>
    <thead>
      <tr>
        <th style="width:14%">Client</th>
        <th style="width:30%">Office / Context</th>
        <th style="width:9%">PMS</th>
        <th style="width:8%">Days Since DOS</th>
        <th style="width:7%">Days Since Sync</th>
        <th style="width:13%">Status</th>
        <th style="width:11%">Waiting On</th>
        <th style="width:8%">ETA</th>
      </tr>
    </thead>
    <tbody>
      <!-- Rows are grouped by client (alphabetical). Within each client, sorted by Days Since DOS descending. -->
      <!-- Each client group starts with a client-header row: -->
      <!-- <tr class="client-header"><td colspan="8">ClientName — N locations</td></tr> -->
      <!-- Then one data row per office. The Client column is left blank on data rows (client shown in header). -->

      <!-- SECTION: Pending Cancellation (Active/Expired + Active/Paused, if any) -->
      <!-- Omit this entire section if there are no pending_cancel rows -->
      <tr class="section-divider"><td colspan="8">Pending Cancellation — No Action Needed</td></tr>
      <!-- Grouped by client, tag-expired -->
    </tbody>
  </table>
  <div class="footer">
    <strong><!-- N_HIGH --></strong> high priority (30+ days) &nbsp;·&nbsp;
    <strong><!-- N_MEDIUM --></strong> medium (15–29 days) &nbsp;·&nbsp;
    <!-- IF pending_cancel > 0: <strong>N_CANCEL</strong> pending cancellation (excluded) &nbsp;·&nbsp; -->
    <!-- POLICY NOTE: All flagged locations have healthy PMS sync (≤ 2 days). -->
  </div>
</body>
</html>
```

### Row construction rules

**Grouping:** Rows are grouped by client (alphabetical). Each client group opens with a
`client-header` row showing the client name and location count, then one data row per
office. The Client column cell is left empty on data rows — the client is shown in the
header row above.

**Within each client group**, rows are sorted by Days Since DOS descending (highest first).

**Flagged rows** — one row per office. Use dot + reason text in the Office/Context column:
- `<span class="dot-red">●</span>` for HIGH (30+ days)
- `<span class="dot-orange">●</span>` for MEDIUM (15–29 days)

**Days Since Sync column** — display the value from `Days Since Last PMS Snap`:
- 0 days → `<span class="days-sync-ok">0</span>` (green)
- 1–2 days → `<span class="days-sync-warn">N</span>` (orange)

This lets Sean distinguish a true billing/claims issue (sync = 0, green) from a
borderline connection case (sync = 1–2, orange) at a glance.

**Tag selection** — pick the class that best matches actual status:
- `tag-high` — HIGH tier with no known explanation
- `tag-medium` — MEDIUM tier with no known explanation
- `tag-waiting` — waiting on client response
- `tag-progress` — active follow-up in progress (appointment, ticket open)
- `tag-internal` — waiting on internal InsideDesk action (e.g. Legacy location)

**Pending Cancellation rows** — always `tag-expired`, no dot needed. Days Since DOS and
Days Since Sync columns: show actual values for context but not actionable. Waiting On / ETA: "—".

**Omit the Pending Cancellation section entirely** if there are no pending_cancel rows.

---

## Step 6 — Convert HTML to PDF

Save the PDF to:

```
/Users/sean/CODE/id-claude-reporting/DOS_Inactivity_Report.pdf
```

Use the first available method:

1. **WeasyPrint** (preferred):
   ```bash
   pip install weasyprint --break-system-packages --quiet
   $PYTHON3 -c "from weasyprint import HTML; HTML('{outputs}/DOS_Inactivity_Report.html').write_pdf('/Users/sean/CODE/id-claude-reporting/DOS_Inactivity_Report.pdf')"
   ```
2. **Chromium headless** (fallback): `chromium --headless --no-sandbox --print-to-pdf=...`
3. **wkhtmltopdf** (fallback if installed)

Verify the PDF is non-empty (> 5 KB) before continuing. If conversion fails, surface the
error to Sean rather than falling back to HTML.

---

## Step 7 — Send the PDF to Sean via Slack DM

Use the shared Slack upload script via Desktop Commander. Substitute today's date for
`{Month D, YYYY}`:

```bash
$PYTHON3 "/Users/sean/CODE/id-claude-reporting/skills/_shared/slack-upload.py" \
  --token   "<slack-bot-token from get-secret>" \
  --file    "/Users/sean/CODE/id-claude-reporting/DOS_Inactivity_Report.pdf" \
  --filename "DOS_Inactivity_Report.pdf" \
  --title   "DOS Inactivity Report — {Month D, YYYY}" \
  --comment "DOS Inactivity Report — {Month D, YYYY}"
```

Verify success: script prints `ok=True  permalink=https://...`. Do not archive until
Slack delivery has succeeded.

---

## Step 8 — Archive the PDF

After successful Slack delivery, move the PDF into long-term archive:

```
/Users/sean/CODE/id-claude-reporting/reports/dos-inactivity/
  YYYY/
    MM/
      DOS_Inactivity_Report_YYYY-MM-DD.pdf
```

```bash
TODAY=$(date +%Y-%m-%d)
YEAR=$(date +%Y)
MONTH=$(date +%m)
PROJ="/Users/sean/CODE/id-claude-reporting"
DEST_DIR="$PROJ/reports/dos-inactivity/$YEAR/$MONTH"
mkdir -p "$DEST_DIR"
mv "$PROJ/DOS_Inactivity_Report.pdf" "$DEST_DIR/DOS_Inactivity_Report_${TODAY}.pdf"
```

If the same date already exists, overwrite it — latest run is canonical. Archives are
kept indefinitely.

---

## Step 9 — Respond to Sean in chat

After Slack delivery and archive:

1. "Sent the PDF to your Slack DMs."
2. A `computer://` link to the archived PDF.
3. 2–3 sentence summary: how many flagged, breakdown by tier, anything needing attention.
4. Any locations with no signal from HubSpot/Gmail — flag these explicitly for Sean to
   reach out to.

Keep it brief — the PDF has the details.

---

## Policy reminders

- **Only flag syncing locations.** If `Days Since Last PMS Snap` > 2, that's an OOS issue,
  not a DOS issue. Don't double-flag in this report.
- **`Inactive` = drop entirely.** Never include.
- **`Active/Expired` and `Active/Paused` = pending cancellation, not actionable.** Show in
  the separate Pending Cancellation section only; never include in the flagged count.
- **`Unk` PMS = onboarding, not a DOS issue.** Exclude from flagged rows.
- **14-day threshold is fixed.** Do not adjust without Sean's explicit instruction.
- **Context Sean provides in chat must end up in HubSpot.** After delivery, offer to add
  any conversational context to the relevant open ticket.
- **Final deliverable is a PDF** posted to Sean's Slack DMs.
- **Archive every PDF** after successful Slack delivery.

---

## Step 10 — Log the run

After Step 9, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `dos-report` |
| `status` | `success` if the PDF was delivered to Slack · `partial` if enrichment or archiving failed · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: date of report, count of flagged locations by tier (HIGH/MEDIUM), and whether any locations had no HubSpot/Gmail signal. |
| `inputs` | `{ "excel_file": "<file path or 'auto-exported'>", "report_date": "<YYYY-MM-DD>" }` |
| `outputs` | `{ "pdf_path": "<archived PDF path>", "slack_ts": "<ts or null>", "flagged_count": N, "high_count": N, "medium_count": N, "clients_count": N }` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{ "pending_cancel_count": N }` |

Call skill-logger even on failure — the log should capture what went wrong.

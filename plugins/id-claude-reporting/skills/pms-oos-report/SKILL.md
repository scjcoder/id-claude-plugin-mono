---
name: pms-oos-report
description: >
  Generate the InsideDesk PMS Out-of-Sync (OOS) report from an exported Power BI Excel file.
  Use this skill whenever Sean asks for the PMS sync report, OOS report, out-of-sync locations,
  which locations are behind on their PMS snap, PMS connection status, sync status update,
  or anything about Days Since Last PMS Snap. Also trigger when Sean pastes or attaches an
  Excel file from the BI report and wants analysis or a summary. The output is a clean
  minimalist PDF report grouped by issue type, delivered as a DM to Sean in Slack, archived
  to the long-term reports folder, with an updated notes file saved to the project folder.
---

# PMS OOS Report Skill

This skill produces the InsideDesk PMS Out-of-Sync report. Power BI connects to Snowflake
directly, so the workflow is: Sean exports the report to Excel and hands it off here.

The final deliverable is a **PDF**, sent as a Slack **DM to Sean** (`sean.johnson@insidedesk.com`),
with a short post body containing only the title and date.

---

## Platform note — Python path

All `$PYTHON3` references below resolve at runtime. Before running any Python command,
set the variable in bash:

```bash
PYTHON3=$(which python3 2>/dev/null | grep -v WindowsApps | head -1)
[ -z "$PYTHON3" ] && PYTHON3=/Users/sean/scoop/shims/python3
```

This picks up the system `python3` on Mac and falls back to the Scoop install on Windows.

---

## Step 0 — Retrieve credentials (prerequisite)

Run the `get-secret` skill with name `slack-bot-token` to retrieve the Slack bot token
before reaching the Slack delivery step. See `id-claude-shared` plugin:
`skills/_shared/slack-setup.md` — Section A (token retrieval) is handled by the `get-secret` skill.

---

## Step 0.5 — DataCo health check (prerequisite)

Run the **`id-claude-ops:dataco-health-check`** skill. It checks https://status.dataco.vet/#
for any active or unresolved incidents and returns a `DATACO_HEALTH_STATUS` block plus a
ready-to-insert `DATACO_ALERT_BANNER` HTML snippet.

**Record the outputs:**
- `overall_status` — `OPERATIONAL`, `DEGRADED`, or `OUTAGE`
- `alert_banner_html` — the `<div>` snippet (or the empty `<!-- DATACO_ALERT_BANNER: none -->` comment)

This step always runs. Do not skip it even if Sean has already mentioned a DataCo outage
in chat — the skill captures the exact status text needed for the report.

If the dataco-health-check skill is unavailable (e.g. browser is busy), note the failure
and continue with `alert_banner_html = <!-- DATACO_ALERT_BANNER: skipped -->`.

---

## Step 1 — Get the Power BI export

If Sean has already attached an Excel file in this conversation, use that file and
skip to Step 2.

Otherwise, **run the `powerbi-export` skill automatically** (`skills/powerbi-export/SKILL.md`)
to download the latest CS Datafeed export from Power BI. Do not ask Sean to export
the file manually. The powerbi-export skill will:

1. Navigate to the PMS Snapshot Monitoring report in the browser
2. Export the CS Datafeed table as `.xlsx`
3. Save it to the project folder as `PMS_Sync_Status_Report_YYYY-MM-DD.xlsx`

Once the powerbi-export skill completes, use the file it saved at:
```
/Users/sean/CODE/id-claude-reporting/PMS_Sync_Status_Report_YYYY-MM-DD.xlsx
```
(where `YYYY-MM-DD` is today's date). Proceed to Step 2 with that file.

---

## Step 2 — Analyze the Excel data

Use pandas to analyze the uploaded file. The expected sheet is named `Export` with these
key columns:
- `Client`
- `Office`
- `facility_id`
- `PMS`
- `Days Since Last PMS Snap`
- `Latest PMS Snap`
- `Days Since Latest DoS`
- `Adjusted Active Status`
- `Notes`

### Cleaning (in order)

1. Drop rows where `Client` is null or starts with `"Applied filters"` — Power BI metadata.
2. Drop the `monitoring` client (Fac 2002, "Monitoring Only") — internal placeholder.
3. **Drop `Inactive` rows entirely.** Locations with `Adjusted Active Status == 'Inactive'`
   are fully deactivated and will show artificially high OOS day counts. Never include them
   in any section of the report.
4. **Set aside `Active/Expired` and `Active/Paused` rows as a "pending_cancel" bucket.**
   These are locations where the client has notified cancellation (or the account is on hold)
   but the system hasn't removed them yet. Install has been told not to take further action.
   They are NOT counted in the active OOS list. See Step 4 for how they appear in the report.
5. Treat `NaN` status as `Active` — likely a data gap, process normally.

After filtering, the working dataset contains only `Active` (and NaN-treated-as-Active) rows.

### Categorize each **Active** location

| Category | Condition |
|---|---|
| Out of Sync | `Days Since Last PMS Snap` > 2 |
| In Sync | `Days Since Last PMS Snap` ≤ 2 |
| Onboarding | `PMS == 'Unk'` (no snap data, never connected) |
| No Snap — Known PMS | `Days Since Last PMS Snap` is null, PMS is not Unk |

**Severity tiers for OOS locations:**
- CRITICAL: 30+ days
- HIGH: 7–29 days
- MEDIUM: 3–6 days

**Group OOS by client** — if a client has multiple OOS locations with the same root cause
(same PMS, similar days count), note it as a cluster (e.g., "3 locations").

### Compute footer stats

- Count of OOS locations — Active rows with Days Since Last PMS Snap > 2 only.
- Count of Pending Cancellation — `Active/Expired` + `Active/Paused` rows (any day count).
- Count of Onboarding locations — Active rows with Unk PMS.
- Total active clients — unique Client values from the Active-only working dataset
  (excludes Inactive, monitoring, metadata rows).

---

## Step 3 — Enrich each OOS location

Enrichment has two parts. **Step 3a (HubSpot ticket cross-reference) is MANDATORY and must
run for every OOS location.** Step 3b (full-sync-status deep dive) is optional and may be
skipped under time pressure — but skipping 3b never permits skipping 3a.

### Step 3a — MANDATORY HubSpot ticket cross-reference (fast, API-only)

Before writing any OOS row, you MUST look up whether an open HubSpot ticket already exists
for that location. This is a direct HubSpot MCP query — it does NOT require the browser or
`full-sync-status`, so it must never be skipped for performance reasons.

Do this **once for the whole batch**, then match locally:

1. Pull all open tickets in the Installation Team pipeline (`hs_pipeline = 66471460`,
   exclude Closed stage `129440439`), requesting `subject`, `hs_pipeline_stage`,
   `hs_object_id`, `hs_lastmodifieddate`. Page through all results (there are typically
   30–60 open tickets — well within one or two calls).
2. For each OOS location, match against the open-ticket subjects by **office/location name**
   (the office name almost always appears verbatim in the subject, e.g.
   `SGA Dental Partners - OOS - Southern Oak Conway [SGA]`). Match on the distinctive part
   of the office name, not just the client, so cluster members are matched individually.
3. For any OOS location with **no match** in the Installation Team pipeline, run one
   targeted `search_crm_objects` by the distinctive office name across all pipelines
   (open tickets only) to catch sync tickets filed elsewhere before declaring "no ticket".
   Treat tickets in the Support pipeline (`hs_pipeline = 0`) stage `4` as CLOSED — they do
   not count as an open ticket.

Record, per location: `ticket_id`, `stage_label` (use the stage map below), and whether the
ticket is open. **A row may only be labelled "needs investigation" / "no ticket" after this
search has run and returned nothing open.** Never infer "no ticket" from the notes file,
prior runs, or memory alone.

**Installation Team stage map** (for labelling the Status column):
`133962530`→New · `129495447`→Sync Issues · `133774246`→Add Loc / Reactivate ·
`159888918`→Escalated · `133988666`→Support / Investigation · `244905906`→Remit ·
`133962531`→Account Updates

When a ticket is found, put its number and stage in the Status column
(e.g. `Open #45736938574 · Sync Issues`).

### Step 3b — OPTIONAL full-sync-status deep dive

For richer root-cause detail you MAY additionally run the **`full-sync-status` skill**
(`id-claude-ops/skills/full-sync-status/SKILL.md`) per OOS location. It covers GoldenEye
snapshots, Dataco pipeline stages (Bitwerx PMS), and HubSpot/Gmail ticket history,
synthesized into a `FULL_SYNC_STATUS_REPORT` block. This is browser-driven and slow, so on
unattended/scheduled runs or large OOS lists it is acceptable to skip 3b and rely on the
mandatory 3a ticket lookup plus the data and notes file. **If you skip 3b, you MUST still
complete 3a.**

**When you do run `full-sync-status`, run it once per OOS location** (not per client — if a
client has a cluster of locations, run it for each individual location). Collect the
`FULL_SYNC_STATUS_REPORT` output for each.

### Mapping full-sync-status output → report columns

Use the `FULL_SYNC_STATUS_REPORT` fields to populate the OOS row in the PDF report:

| Report column | Source field |
|---|---|
| **Issue** | `verdict` + `Recommended action` — distill to a concise root-cause phrase |
| **Status** | `Ticket History.context` — most recent open/closed ticket signal |
| **Waiting On** | Owner from open ticket, or "office IT" / "Bitwerx" per recommended action |
| **ETA** | From ticket context if mentioned; otherwise "—" |

**Tag selection** — map from `verdict`:
- `✅ Fully in sync` — office has recovered; use `tag-progress` and note "Verify — now in sync"
- `⚠️ Intermediate stale` — use `tag-waiting` ("Waiting on Bitwerx")
- `❌ Stage failed / Connectivity red` — use `tag-critical` or `tag-blocked`
- `❌ Non-Bitwerx, no snapshots` — use `tag-waiting` ("Waiting on office IT")
- `Open ticket exists` (from Ticket History) — use `tag-progress` or `tag-waiting` per ticket stage
- `No signal` → "— needs investigation", use `tag-internal`, flag for Sean

**Priority order when signals conflict** (highest wins):
1. Open HubSpot ticket found in Step 3a — its number + stage are authoritative for the
   Status column; never report "no ticket" when 3a found one.
2. `FULL_SYNC_STATUS_REPORT.Recommended action` — synthesized verdict (only if 3b was run)
3. `Ticket History.context` — most recent ticket/Gmail signal
4. Context Sean provided in this conversation (see Step 4)
5. Step 3a returned no open ticket AND nothing else found → "— needs investigation"

**MB2 exception:** MB2 locations frequently have no HubSpot ticket — this is normal.
MB2 uses Monday Board for OOS communication. For MB2 locations where ticket history is
empty, note "No ticket — MB2 help desk process" rather than "needs investigation."

---

## Step 4 — Capture any context Sean provides in chat

During the report run, Sean may mention context that isn't in HubSpot or Gmail yet —
e.g. "we're waiting on their new server" or "I spoke to their IT contact this morning."

**For each piece of context Sean provides:**
1. Use it in the report (it takes priority over "needs investigation").
2. After the report is delivered, ask Sean: *"You mentioned [X] for [Client] — want me to add a note to their HubSpot ticket?"*
3. If Sean says yes, find the relevant open ticket and add the context as a note via the HubSpot MCP connector.
4. If there's no open ticket, offer to create one or note that there isn't one.

Do not silently discard conversational context — it should end up in HubSpot, not lost between sessions.

---

## Step 5 — Handle pending cancellations

### Active OOS locations

For any OOS location with no signal from HubSpot, Gmail, or the current conversation,
leave Status/Waiting On/ETA as "— needs investigation" and flag it so Sean notices.

### Pending Cancellation locations (Active/Expired and Active/Paused)

These locations appear in a **separate sub-section** at the bottom of the OOS section,
after all actionable OOS rows. They are clearly labelled "Not actionable" and are never
assigned owners or investigation steps.

**Grouping:** Collapse all `Active/Expired` and `Active/Paused` rows for the same client
into one report row with a location count. If a client has only one such location, name it
directly. If they have many, summarize (e.g., "23 locations — pending contract termination").

**Tag to use:** `tag-expired` (muted gray — see HTML template). Do NOT use any other tag.

**Do not** include these locations in:
- The actionable OOS count in the footer
- "Needs Sean's attention" callouts in the chat response
- Any investigation or follow-up notes

**Check the notes file** for context — a location may already be noted as "cancellation
in progress" or similar. If so, reflect that briefly. If not, "Pending cancellation — no
further action needed" is sufficient.

---

## Step 6 — Produce the HTML report (intermediate, then convert to PDF)

Save the HTML to a temporary working path (the outputs folder, not the project folder):

```
{outputs}/PMS_OOS_Report.html
```

This is intermediate — the final deliverable is the PDF. Do not save the HTML to the
project folder.

> ⛔ **MANDATORY — NEVER write your own HTML template.**
>
> Copy the template below **VERBATIM** — do not change the CSS, the class names, the font
> stack, or the structure. Do NOT use Arial. Do NOT add stat-box grids or section cards.
> Do NOT use background fills on rows. Do NOT use a different color scheme or layout.
> The style is intentionally minimal: white background, horizontal rules only, no heavy
> cell fills. Color is used only in the small dot indicators and subtle tag badges.
> Every PMS OOS Report must look identical to prior runs.
> **If you modify the template or write your own HTML, you are producing the wrong output.**

**DataCo alert banner:** If `alert_banner_html` from Step 0.5 is a `<div>` (not a comment),
insert it immediately after `<body>`, before the `.report-title` div. If it is a comment
(`<!-- DATACO_ALERT_BANNER: none -->` or `skipped`), insert the comment as-is and do not
render a visible banner. This means every report either has a visible warning or a silent
placeholder — never a missing check.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PMS Out-of-Sync Report</title>
<style>
  @page { size: Letter; margin: 0.5in; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 13px; color: #1a1a1a; background: #fff;
    padding: 0; max-width: 900px;
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
  .tag-critical { background: #fde8e8; color: #c0392b; }
  .tag-waiting  { background: #fef3e2; color: #d4820a; }
  .tag-progress { background: #e8f4fd; color: #1a6fa8; }
  .tag-internal { background: #f0ecfd; color: #6b3fa0; }
  .tag-onboard  { background: #edf7ed; color: #2e7d32; }
  .tag-blocked  { background: #fde8e8; color: #c0392b; }
  .tag-expired  { background: #f2f2f2; color: #888; }
  .dot-red    { color: #e53935; margin-right: 4px; }
  .dot-orange { color: #f57c00; margin-right: 4px; }
  .dot-blue   { color: #1976d2; margin-right: 4px; }
  .days { font-weight: 600; white-space: nowrap; }
  .days-critical { color: #c0392b; }
  .days-high     { color: #d4820a; }
  .days-medium   { color: #1a6fa8; }
  .owner { font-size: 12px; color: #444; }
  .eta   { font-size: 12px; color: #666; white-space: nowrap; }
  tbody tr.section-divider td {
    padding-top: 22px; padding-bottom: 4px; font-size: 11px;
    font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase;
    color: #aaa; border-bottom: none;
  }
  .footer { margin-top: 20px; font-size: 12px; color: #888; }
  .footer strong { color: #333; }
</style>
</head>
<body>
  <!-- DATACO_ALERT_BANNER — insert output from Step 0.5 here (div or comment) -->
  <div class="report-title">PMS Out-of-Sync Report</div>
  <div class="report-meta"><!-- DATE --> · Locations where Days Since Last PMS Snap &gt; 2</div>
  <table>
    <thead>
      <tr>
        <th style="width:18%">Client</th>
        <th style="width:36%">Issue</th>
        <th style="width:10%">PMS</th>
        <th style="width:8%">Days OOS</th>
        <th style="width:10%">Status</th>
        <th style="width:10%">Waiting On</th>
        <th style="width:8%">ETA</th>
      </tr>
    </thead>
    <tbody>
      <!-- SECTION: Connection / Sync Issues (Active only, sorted by days desc) -->
      <tr class="section-divider"><td colspan="7">Connection / Sync Issues</td></tr>
      <!-- OOS rows go here — one <tr> per client or cluster -->

      <!-- SECTION: Pending Cancellation (Active/Expired + Active/Paused, if any) -->
      <!-- Omit this entire section if there are no pending_cancel rows -->
      <tr class="section-divider"><td colspan="7">Pending Cancellation — No Action Needed</td></tr>
      <!-- Grouped by client, tag-expired, Days OOS column shows highest day count or "—" if not OOS -->

      <!-- SECTION: New / Onboarding -->
      <tr class="section-divider"><td colspan="7">New / Onboarding (Not Yet Installed)</td></tr>
      <!-- Onboarding rows go here — group by client, show location count -->
    </tbody>
  </table>
  <div class="footer">
    <strong><!-- N_OOS --></strong> connection/sync issues &nbsp;·&nbsp;
    <strong><!-- N_ONBOARD --></strong> locations in onboarding &nbsp;·&nbsp;
    <!-- IF pending_cancel > 0: <strong>N_CANCEL</strong> pending cancellation (excluded) &nbsp;·&nbsp; -->
    <!-- POLICY NOTE -->
  </div>
</body>
</html>
```

### Row construction rules

**Active OOS rows** — one row per client (or per cluster). Use the dot + issue text pattern
for the Issue column:
- `<span class="dot-red">●</span>` for CRITICAL/HIGH
- `<span class="dot-orange">●</span>` for MEDIUM
- `<span class="dot-blue">●</span>` for internal action items (no active connection issue)

**Tag selection for OOS rows** — pick the class that best matches the actual status:
- `tag-critical` / `tag-blocked` — hardware failure, no path forward yet
- `tag-waiting` — waiting on client (no response, pending info)
- `tag-progress` — active appointment or scheduled next step
- `tag-internal` — waiting on internal InsideDesk action (ticket, assignment)

**Pending Cancellation rows** — always use `tag-expired`. No dot color needed in the Issue
column (these are not actionable). Days OOS column: show the actual highest day count for
context, using `days-critical` / `days-high` / `days-medium` class as appropriate, but
the reader understands these are not real work items. Waiting On and ETA cells: use "—".
Issue column text: brief factual note, e.g. "Pending contract termination — no further
action needed." or "Client cancelled — awaiting system removal."

**Onboarding rows** — group all Unk locations by Client. Show count of locations.
Keep the Issue column brief: "N new locations not yet installed."

**Sort order:**
1. Active OOS rows — by Days OOS descending (most critical first).
2. Pending Cancellation section — by client name alphabetically.
3. Onboarding section — by client name alphabetically.

**Omit the Pending Cancellation section entirely** if there are zero `Active/Expired` or
`Active/Paused` rows in the dataset. Don't render an empty section.

---

## Step 7 — Convert HTML to PDF

Render the intermediate HTML to PDF. Save the PDF to a **working location** in the
project folder root:

```
/Users/sean/CODE/id-claude-reporting/PMS_OOS_Report.pdf
```

This is a transient working file — it gets moved into long-term archive in Step 8.

Use the first available method, in this order:

1. **WeasyPrint** (preferred — pure Python, respects the `@page` CSS rule):
   ```bash
   pip install weasyprint --break-system-packages --quiet
   $PYTHON3 -c "from weasyprint import HTML; HTML('{outputs}/PMS_OOS_Report.html').write_pdf('/Users/sean/CODE/id-claude-reporting/PMS_OOS_Report.pdf')"
   ```
2. **Chromium headless** (fallback): `chromium --headless --no-sandbox --print-to-pdf=...`
3. **wkhtmltopdf** (fallback if installed).

Verify the PDF is non-empty (>5 KB) before continuing. If conversion fails, surface the
error to Sean rather than falling back to HTML — PDF is the required deliverable.

The intermediate HTML file in the outputs folder can be left in place (gets cleared
between sessions). Do **not** save the HTML to the project folder.

---

## Step 8 — Send the PDF to Sean via Slack DM

Run the shared Slack upload script via **Desktop Commander** (`mcp__Desktop_Commander__start_process`).
Substitute today's date for `{Month D, YYYY}` (e.g. `May 12, 2026`):

```bash
$PYTHON3 "/Users/sean/CODE/id-claude-reporting/skills/_shared/slack-upload.py" \
  --token   "<slack-bot-token from get-secret>" \
  --file    "/Users/sean/CODE/id-claude-reporting/PMS_OOS_Report.pdf" \
  --filename "PMS_OOS_Report.pdf" \
  --title   "PMS Out-of-Sync Report — {Month D, YYYY}" \
  --comment "PMS Out-of-Sync Report — {Month D, YYYY}"
```

No summary or bullet list in the comment — Sean reviews the details inside the PDF.

Verify success: the script prints `ok=True  permalink=https://...`. Anything else is a failed delivery —
surface the raw error to Sean and provide the local PDF path so he can share it manually.

**Do not move the PDF to the archive (Step 9) until Slack delivery has succeeded.**



---

## Step 9 — Archive the PDF to long-term storage

After Slack delivery succeeds, move the PDF from the project root into the long-term
archive folder. Structure:

```
/Users/sean/CODE/id-claude-reporting/reports/pms-oos/
  YYYY/
    MM/
      PMS_OOS_Report_YYYY-MM-DD.pdf
```

Use the **run date** (today's date) for both folder path and filename. Create the
year/month folders if they don't exist:

```bash
TODAY=$(date +%Y-%m-%d)
YEAR=$(date +%Y)
MONTH=$(date +%m)
PROJ="/Users/sean/CODE/id-claude-reporting"
DEST_DIR="$PROJ/reports/pms-oos/$YEAR/$MONTH"
mkdir -p "$DEST_DIR"
mv "$PROJ/PMS_OOS_Report.pdf" "$DEST_DIR/PMS_OOS_Report_${TODAY}.pdf"
```

If the same date already exists in the archive (skill run twice in one day), overwrite
it — the latest run is the canonical version for that day.

After the move, the project root must not contain a stray `PMS_OOS_Report.pdf`. The
archive is the single source of truth.

These archives are kept indefinitely for historical reference. Never delete entries.

---

## Step 10 — Respond to Sean in chat

After Slack delivery + archive + notes update, respond in chat with:

1. Confirmation that the PDF was sent ("Sent the PDF to your Slack DMs.")
2. A computer:// link to the **archived** PDF (in `reports/pms-oos/YYYY/MM/`), not
   the working file at the project root.
3. A 2–3 sentence plain-English summary: how many OOS, any new since last run, any
   resolved since last run.
4. If `overall_status` from Step 0.5 is `DEGRADED` or `OUTAGE`, include a one-sentence
   callout, e.g.: "⚠ DataCo has an active outage (Batch API + PIMS Data degraded) —
   OOS counts may be artificially elevated." Link to https://status.dataco.vet/#.
5. Anything needing Sean's attention (new unknown locations not in notes, anyone
   overdue for follow-up). Never include `Active/Expired` or `Active/Paused` locations
   in the attention callouts — they are not actionable.

Keep it brief — the PDF has the details.

---

## Step 11 — Log the run

After Step 10 (chat response), call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `pms-oos-report` |
| `status` | `success` if PDF delivered and archived · `partial` if any step failed silently · `error` if delivery failed |
| `summary` | 1–3 sentences: how many OOS, how many clients, whether DataCo had an outage |
| `inputs` | `file={excel_filename}` · `source=powerbi` · `dataco_status={overall_status from Step 0.5}` |
| `outputs` | `pdf={archived_pdf_path}` · `slack_ts={permalink or ts}` · `oos_count={N}` · `onboarding_count={N}` · `pending_cancel_count={N}` |
| `errors` | Any steps that failed or were skipped (empty dict if none) |
| `metadata` | `total_active_locations={N}` · `total_clients={N}` · `dataco_alert_shown={true/false}` |

This step is always the last — logging happens after all primary deliverables are complete.

---

## Policy reminders (baked into every run)

- **`Inactive` = drop entirely.** Never include in any section of the report. These
  locations are deactivated and their OOS day counts are meaningless artifacts.
- **`Active/Expired` and `Active/Paused` = pending cancellation, not actionable.**
  The client has notified InsideDesk of cancellation (or the account is on hold) but
  the system hasn't removed them yet. Install has been told not to take further action.
  Show them in the "Pending Cancellation" section with the `tag-expired` tag, grouped by
  client. Never assign owners, never triage, never include in the actionable OOS count
  or in Sean's attention callouts. These statuses are controlled by the
  `Disabled_Locations_List` tab of the Master Support File (SharePoint).
- **`Active/Paused` is treated identically to `Active/Expired`** — both mean "hold,
  don't act." The distinction matters only for the Master Support File, not for this report.
- **Unk PMS = onboarding, not a problem.** Never flag these as sync failures. They are
  new locations in the install pipeline that have never been connected.
- **`monitoring` Fac 2002 is excluded.** Internal placeholder, never include in any
  section of the report.
- **Cluster logic:** When multiple Active locations at the same client share the same PMS
  and similar OOS day count, treat as one row with a location count. One fix usually
  resolves all.
- **Don't manufacture context.** If a location has no signal from HubSpot, Gmail, or
  the current conversation, say "needs investigation" clearly rather than guessing. Flag it for Sean.
- **Never report "no ticket" without a confirmed HubSpot search.** The mandatory Step 3a
  ticket cross-reference must run for every OOS location on every run, scheduled or
  interactive. "No ticket" / "needs investigation" is only valid after 3a (Installation Team
  pipeline match + targeted all-pipeline fallback) returns nothing open. Notes-file context
  and prior runs are NOT a substitute for the live lookup. Step 3a is API-only and fast — it
  is never acceptable to skip it for performance, even when skipping the browser-based 3b.
- **Context Sean provides in chat must end up in HubSpot.** After the report is delivered,
  offer to add any conversational context to the relevant open ticket. Don't let it disappear.
- **Final deliverable is a PDF posted to Sean's Slack DMs**, not an HTML file.
- **Archive every PDF.** After successful Slack delivery, move the working PDF into
  `reports/pms-oos/YYYY/MM/PMS_OOS_Report_YYYY-MM-DD.pdf`. These are kept indefinitely.

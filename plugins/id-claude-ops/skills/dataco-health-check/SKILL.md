---
name: dataco-health-check
description: >
  Check the Bitwerx DataCo public status page (https://status.dataco.vet/#) for active
  or unresolved incidents affecting the Batch API, PIMS Data, CSV Export, Daylight, or
  other DataCo services. Returns a structured DATACO_HEALTH_STATUS block for use by
  downstream skills. Use this skill whenever you need to know if DataCo is experiencing
  an outage before running an OOS report or sync diagnosis, or when the user asks "is
  DataCo down?", "any DataCo outages today?", "check the DataCo status page", or similar.
  Also triggered automatically at the start of the pms-oos-report skill.
---

# DataCo Health Check

Check https://status.dataco.vet/# for active or unresolved incidents affecting InsideDesk
sync quality. Returns a structured status block that downstream skills (e.g. pms-oos-report)
can use to add a context banner to their output.

---

## Step 1 — Navigate to the status page

Open the DataCo status page using the Claude-controlled browser:

```
https://status.dataco.vet/#
```

Read the full page text with `get_page_text`.

---

## Step 2 — Extract incident data

From the page text, identify:

### Active / Unresolved incidents
Any incident block that does **not** contain "Resolved" as its final status update.
Look for incidents listed under today's date (use `currentDate` from context) or
any entry labelled "Unresolved incident".

For each active incident, capture:
- **Title** (e.g. "Batch API Data Delay")
- **Affected components** — any services shown as "Degraded Performance" or "Partial
  Outage" in the uptime bar section (e.g. Batch API, CSV Export, PIMS Data, Daylight)
- **Latest status message** — the most recent investigator note (date + text)
- **Started** — earliest timestamp in the incident block

### Component health summary
From the uptime bars section, note the current status of each component:
- Batch API
- CSV Export
- PIMS Data (Daylight)
- On-Demand API
- Prism
- Instance Support API
- SupportCo

Mark each as `Operational` or `Degraded Performance` (or `Partial Outage` / `Major Outage`
if present).

---

## Step 3 — Assess impact on InsideDesk sync

Map active incidents to expected InsideDesk impact:

| Affected component | InsideDesk impact |
|---|---|
| Batch API | Scheduled nightly sync jobs may not complete — locations will appear OOS in the morning report |
| PIMS Data | PMS snapshot data may be stale — Days Since Last PMS Snap counts will be artificially elevated |
| CSV Export | Batch data export unavailable — affects any workflow that pulls DataCo exports |
| Daylight | Daylight code mappings may be unavailable — affects code-level sync accuracy |
| On-Demand API | Real-time data requests may fail — affects direct API integrations |
| SupportCo | SupportCo portal may be unavailable — affects fingerprint lookups |

If **Batch API** or **PIMS Data** is degraded, add a note:
> "OOS counts in today's report may be artificially elevated — verify before escalating."

---

## Step 4 — Output a DATACO_HEALTH_STATUS block

Always produce this structured block, regardless of whether incidents were found:

```
DATACO_HEALTH_STATUS
====================
Checked: {today's date and time, e.g. Jun 9, 2026 at 10:14 AM}
Overall: {OPERATIONAL | DEGRADED | OUTAGE}

Active Incidents: {count, or "None"}
{For each active incident:}
  ⚠ {Title}
    Affected: {comma-separated component list}
    Started: {timestamp}
    Latest update: {most recent status message, truncated to ~120 chars}

Component Status:
  Batch API         {Operational | Degraded Performance | ...}
  CSV Export        {Operational | Degraded Performance | ...}
  PIMS Data         {Operational | Degraded Performance | ...}
  On-Demand API     {Operational | Degraded Performance | ...}
  Prism             {Operational | ...}
  Instance Support  {Operational | ...}
  SupportCo         {Operational | ...}

InsideDesk Impact:
  {One or two plain-English sentences describing what the active incidents mean
   for InsideDesk data quality today. If no incidents: "No known DataCo issues —
   OOS counts reflect actual connectivity status."}
====================
```

---

## Step 5 — Produce an HTML alert banner (if incidents found)

If `Active Incidents > 0`, also produce a ready-to-insert HTML snippet for use in PDF
reports. This banner should be inserted **above the report table** (just after `<body>`),
before the `.report-title` div:

```html
<!-- DATACO_ALERT_BANNER — insert only when DataCo incidents are active -->
<div style="
  background: #fef3e2;
  border-left: 4px solid #f57c00;
  padding: 10px 14px;
  margin-bottom: 20px;
  font-size: 12px;
  line-height: 1.5;
  border-radius: 0 3px 3px 0;
">
  <span style="font-weight:700; color:#d4820a;">⚠ DataCo Status Alert</span>
  &nbsp;—&nbsp;
  <span style="color:#333;">{one-line plain-English summary of active incident(s), e.g.
  "Batch API Data Delay (since Jun 9 08:22 EDT) — PIMS Data and CSV Export degraded.
  OOS counts in this report may be artificially elevated."}</span>
  &nbsp;
  <a href="https://status.dataco.vet/#" style="color:#1a6fa8; text-decoration:none;">
    View status →
  </a>
</div>
```

If no incidents: output an empty comment `<!-- DATACO_ALERT_BANNER: none -->` as a
placeholder so downstream skills know the check ran.

---

## Step 6 — Report to the user (when called standalone)

When triggered directly (not as a sub-step of another skill), respond with:

1. The `DATACO_HEALTH_STATUS` block.
2. A one-sentence plain-English verdict, e.g.:
   - "DataCo is fully operational — no active incidents." 
   - "⚠ DataCo has an active outage affecting Batch API and PIMS Data (since Jun 9,
     08:22 EDT). OOS data in any reports run today may be artificially elevated."
3. Link to the status page: https://status.dataco.vet/#

When called as a sub-step, skip this step and let the calling skill handle user output.

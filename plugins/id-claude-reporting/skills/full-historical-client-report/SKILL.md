---
name: full-historical-client-report
description: >
  Generate a full historical report for any InsideDesk client — active, churned,
  or potential winback. Pulls data from GoldenEye (snapshot history, facility status),
  HubSpot (locations, cancellation records, install tickets, contacts), and Gmail
  (email threads). Produces a PDF summary delivered to Sean's Slack DM.
  Use whenever Sean says "full history for [client]", "what happened with [client]",
  "refresh my memory on [client]", "winback report for [client]", "client history
  report for [client]", or needs a complete picture of a client relationship
  before a call, re-engagement, or internal review.
---

# Full Historical Client Report

Produces a single-PDF report covering a client's entire relationship with InsideDesk —
from onboarding through current status. Works for active clients, churned clients,
and potential winbacks.

**Sources:** GoldenEye · HubSpot · Gmail
**Not used:** Monday Board (MB2-only channel — not applicable to other clients)

---

## Step 0 — Prerequisites

Run the **`get-secret`** skill with name `hubspot-token`.
Run the **`get-secret`** skill with name `slack-bot-token`.

---

## Step 0b — Resolve the client name

Ask Sean to confirm the client name if ambiguous. The name must match (or be close
to) the HubSpot company name — that is the anchor for all downstream lookups.

Store as `client_name_query` (the search string) and `client_label` (display name
for the report).

---

## Step 1 — HubSpot: Find the company record

```python
import requests

TOKEN = "<hubspot_token>"
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

resp = requests.post(
    "https://api.hubapi.com/crm/v3/objects/companies/search",
    headers=headers,
    json={
        "filterGroups": [{"filters": [{
            "propertyName": "name",
            "operator": "CONTAINS_TOKEN",
            "value": client_name_query
        }]}],
        "properties": ["name", "hs_object_id", "customer_success_manager",
                       "hubspot_owner_id", "createdate", "hs_lastmodifieddate",
                       "domain", "phone"],
        "limit": 5
    }
)
companies = resp.json().get("results", [])
```

Pick the closest name match. Store `company_id` and `company_name`.
If multiple results, surface them and ask Sean to confirm.

---

## Step 2 — HubSpot: Get all location records (active + inactive)

Search the Locations custom object for this company. We want ALL locations,
regardless of active status, to build the complete picture.

```python
resp = requests.post(
    "https://api.hubapi.com/crm/v3/objects/2-14718097/search",
    headers=headers,
    json={
        "filterGroups": [{"filters": [{
            "propertyName": "company_name",
            "operator": "CONTAINS_TOKEN",
            "value": company_name
        }]}],
        "properties": ["name", "facility_id", "pms", "activity_status",
                       "activation_date", "deactivation_date",
                       "deactivation_reason", "hs_object_id", "client_id"],
        "limit": 200
    }
)
locations = resp.json().get("results", [])
```

If zero results, try searching by `client_id` using the company's domain or a
known client ID. Note any missing associations in the report.

Build a lookup: `location_map = {loc["properties"]["facility_id"]: loc for loc in locations}`

---

## Step 3 — HubSpot: Get cancellation records

```python
resp = requests.post(
    "https://api.hubapi.com/crm/v3/objects/2-33013991/search",
    headers=headers,
    json={
        "filterGroups": [{"filters": [{
            "propertyName": "cancellation_name",
            "operator": "CONTAINS_TOKEN",
            "value": company_name
        }]}],
        "properties": ["cancellation_name", "cancellation_reason",
                       "date_requested", "hs_pipeline_stage", "hs_createdate",
                       "hs_lastmodifieddate", "hubspot_owner_id"],
        "limit": 20
    }
)
cancellations = resp.json().get("results", [])
```

Pipeline stage reference (id → label):
- `222298644` → CS Investigation
- `222305660` → Holding
- `222305661` → Cancel Immediately
- `1028096063` → CS Saved
- `232959327` → Churned

---

## Step 4 — HubSpot: Get install/support tickets

```python
# Get tickets associated with the company
resp = requests.get(
    f"https://api.hubapi.com/crm/v4/objects/companies/{company_id}/associations/tickets",
    headers=headers
)
ticket_ids = [r["toObjectId"] for r in resp.json().get("results", [])]

# Fetch ticket details in batches of 10
tickets = []
for i in range(0, len(ticket_ids), 10):
    batch = ticket_ids[i:i+10]
    r = requests.post(
        "https://api.hubapi.com/crm/v3/objects/tickets/batch/read",
        headers=headers,
        json={
            "inputs": [{"id": str(tid)} for tid in batch],
            "properties": ["subject", "hs_pipeline_stage", "hs_createdate",
                           "hs_lastmodifieddate", "hs_ticket_priority",
                           "content", "hubspot_owner_id"]
        }
    )
    tickets.extend(r.json().get("results", []))
```

---

## Step 5 — HubSpot: Get key contacts

```python
resp = requests.get(
    f"https://api.hubapi.com/crm/v4/objects/companies/{company_id}/associations/contacts",
    headers=headers
)
contact_ids = [r["toObjectId"] for r in resp.json().get("results", [])]

contacts = []
for i in range(0, len(contact_ids), 10):
    batch = contact_ids[i:i+10]
    r = requests.post(
        "https://api.hubapi.com/crm/v3/objects/contacts/batch/read",
        headers=headers,
        json={
            "inputs": [{"id": str(cid)} for cid in batch],
            "properties": ["firstname", "lastname", "email", "phone",
                           "jobtitle", "hs_lead_status", "contact_type"]
        }
    )
    contacts.extend(r.json().get("results", []))
```

---

## Step 6 — GoldenEye: Snapshot history per facility

Navigate to `https://<GOLDENEYE_HOST>/production/admin/snapshots` for
authenticated API access.

**Use the `facility=<id>` query parameter** to fetch snapshots for one facility at a time.
This keeps each query to a manageable number of pages (typically 10–30 per facility for
an 18-month window) instead of scanning all snapshots globally.

> **Key discovery:** The snapshot API supports `facility=<id>` as a filter parameter.
> Do NOT omit it and filter client-side — without it the global dataset has millions
> of rows and the query will time out. Always query per-facility.

Run this in browser JS, iterating over each facility ID from `location_map`:

```javascript
(async function() {
  const facilities = FACILITY_MAP;  // { "1234": "Location Name", ... } from location_map
  const monthStart = 'YYYY-MM-DD';  // 18 months ago (or 24 if last snap is older)
  const monthEnd   = 'YYYY-MM-DD';  // today
  const snaps = {};

  for (const [fid, fname] of Object.entries(facilities)) {
    snaps[fid] = { name: fname, months: {}, firstSnap: null, lastSnap: null };
    const base = `https://<ADMIN_API_HOST>/pms-snapshot/?page_size=100&date_from=${monthStart}&date_to=${monthEnd}&facility=${fid}&page=`;

    const r1 = await fetch(base + '1', { credentials: 'include' });
    const pag = JSON.parse(r1.headers.get('x-pagination'));

    const processRows = rows => {
      if (!Array.isArray(rows)) return;
      rows.forEach(row => {
        const month = (row.received_date || '').substring(0, 7);
        if (month) snaps[fid].months[month] = (snaps[fid].months[month] || 0) + 1;
        const d = (row.received_date || '').substring(0, 10);
        if (d && (!snaps[fid].firstSnap || d < snaps[fid].firstSnap)) snaps[fid].firstSnap = d;
        if (d && (!snaps[fid].lastSnap  || d > snaps[fid].lastSnap))  snaps[fid].lastSnap  = d;
      });
    };

    processRows(await r1.json());
    for (let p = 2; p <= pag.total_pages; p++) {
      processRows(await fetch(base + p, { credentials: 'include' }).then(r => r.json()));
    }

    console.log(`${fid} ${fname}: ${pag.total} snaps, first=${snaps[fid].firstSnap}, last=${snaps[fid].lastSnap}`);
  }

  sessionStorage.setItem('_clientHistory', JSON.stringify(snaps));
  return snaps;
})()
```

> **Async syntax note:** All browser JS in this skill must wrap code in
> `(async function() { ... })()` — bare `await` at the top level is not supported
> in the GoldenEye browser context.

Export via Blob download → copy to project folder as `client_history_{slug}.json`.

> **Note:** Facilities with zero snapshots in the window won't appear in results.
> Cross-reference with `location_map` — any facility ID absent from snapshot results
> had no activity in the query window.

**Also useful — facility detail API** (for name/status without scraping the UI):
```
GET https://<ADMIN_API_HOST>/facility/{id}/
```
Returns `facility.name`, `facility.active`, `facility.created`, `facility.pms_type`.
Use this to fill in names when HubSpot location records lack a `name` property.

---

## Step 7 — Gmail: Find relevant email threads

Use the Gmail MCP connector to search for email threads related to this client.
Run two searches and deduplicate:

1. Company name: `"{company_name}" newer_than:2y`
2. Any contact email domains found in Step 5: `"@{contact_domain}" newer_than:2y`

For each thread returned, fetch full content and extract:
- Date, subject, snippet
- Direction (inbound from client vs. outbound from InsideDesk)
- Tag as: Onboarding / Support / Cancellation / General

Limit to 20 most recent threads. Summarize — do not include full body text in report.

---

## Step 8 — Determine client status

Based on collected data, classify the client into one of three states:

| Status | Criteria |
|---|---|
| **Active** | Has locations with `activity_status = active` AND recent snapshots (within 7 days) |
| **At Risk** | Has active locations but no recent snapshots, OR has open cancellation record in CS Investigation / Holding / Cancel Immediately |
| **Churned** | All locations inactive AND cancellation record in Churned stage (or no cancellation record but zero snapshots for 60+ days) |

Store as `client_status` for the report header and winback section logic.

---

## Step 9 — Build report data

Compute these summary figures from all collected data:

```python
# Tenure
first_ever_snap = min(snaps[fid]["firstSnap"] for fid in snaps if snaps[fid].get("firstSnap"))
last_ever_snap  = max(snaps[fid]["lastSnap"]  for fid in snaps if snaps[fid].get("lastSnap"))
tenure_months   = month_diff(first_ever_snap, last_ever_snap)  # integer

# Location counts
total_locations_ever = len(location_map)
peak_active          = max(monthly_active_counts.values())  # from snapshot timeline
current_active       = sum(1 for l in locations if l["properties"].get("activity_status") == "active")

# PMS breakdown
from collections import Counter
pms_counts = Counter(l["properties"].get("pms", "Unknown") for l in locations)
```

---

## Step 10 — Generate the PDF

> ⛔ **MANDATORY — call `generate_report.py` — never write reportlab code inline.**

```bash
python3 "/Users/sean/CODE/id-claude-reporting/skills/full-historical-client-report/generate_report.py" \
  --client  "Client Name" \
  --slug    "client-name-YYYY-MM-DD" \
  --outdir  "/Users/sean/CODE/id-claude-reporting" \
  --data    '<JSON>'
```

### JSON schema for `--data`:

```json
{
  "client_name":        "Acme Dental Partners",
  "client_status":      "Churned",
  "report_date":        "2026-06-09",
  "hubspot_company_url":"https://app.hubspot.com/contacts/<HUBSPOT_PORTAL_ID>/company/12345",

  "summary": {
    "first_snapshot":       "2024-01-15",
    "last_snapshot":        "2026-04-20",
    "tenure_months":        27,
    "total_locations_ever": 14,
    "peak_active":          14,
    "current_active":       0,
    "pms_breakdown":        {"Dentrix": 8, "Eaglesoft": 4, "Ascend API": 2}
  },

  "locations": [
    {
      "facility_id": "1234",
      "name":        "Acme - Main Street",
      "pms":         "Dentrix",
      "status":      "inactive",
      "first_snap":  "2024-01-15",
      "last_snap":   "2026-04-18",
      "hs_url":      "https://app.hubspot.com/contacts/<HUBSPOT_PORTAL_ID>/record/2-14718097/..."
    }
  ],

  "snapshot_timeline": {
    "2024-01": 280,
    "2024-02": 295
  },

  "cancellations": [
    {
      "name":       "Acme Dental - All Locations",
      "reason":     "Buggy Product; ROI Concerns",
      "stage":      "Churned",
      "date_requested": "2026-02-10",
      "hs_url":     "https://app.hubspot.com/contacts/<HUBSPOT_PORTAL_ID>/record/2-33013991/..."
    }
  ],

  "tickets": [
    {
      "subject":   "Acme - Main Street OOS",
      "stage":     "Closed",
      "created":   "2025-11-04",
      "hs_url":    "https://app.hubspot.com/contacts/<HUBSPOT_PORTAL_ID>/ticket/..."
    }
  ],

  "contacts": [
    {
      "name":  "Jane Smith",
      "email": "jane@acmedental.com",
      "title": "Director of Operations",
      "type":  "Account POC"
    }
  ],

  "email_summary": [
    {
      "date":      "2026-02-12",
      "subject":   "Re: InsideDesk renewal discussion",
      "direction": "inbound",
      "tag":       "Cancellation",
      "snippet":   "We've decided to move forward with cancellation..."
    }
  ],

  "winback_intel": {
    "show": true,
    "tenure_summary":   "27-month client (Jan 2024 – Apr 2026)",
    "churn_reasons":    ["Buggy Product", "ROI Concerns"],
    "peak_footprint":   "14 locations across Dentrix, Eaglesoft, and Ascend API",
    "primary_contact":  "Jane Smith — jane@acmedental.com",
    "last_email_date":  "2026-02-12",
    "talking_points": [
      "Address product stability concerns — reference recent improvements",
      "Reconnect with Jane Smith (last contact Feb 2026)",
      "Peak of 14 locations — significant revenue opportunity"
    ]
  }
}
```

**Winback Intel section logic:**
- Show only when `client_status = "Churned"`
- Talking points are auto-generated from churn reasons, contact info, and tenure data
- Keep it actionable — 3–5 bullet points max

---

## Step 11 — Deliver via Slack

```bash
python3 "/Users/sean/CODE/id-claude-reporting/skills/_shared/slack-upload.py" \
  --token    "<slack-bot-token>" \
  --file     "/Users/sean/CODE/id-claude-reporting/client_history_{slug}.pdf" \
  --filename "client_history_{slug}.pdf" \
  --title    "Client History · {client_name}" \
  --comment  "*Client History Report* · {client_name} · {report_date}"
```

---

## Step 12 — Deliver links to Sean

```
[View PDF Report](computer:///Users/sean/CODE/id-claude-reporting/client_history_{slug}.pdf)
```

Plain-English summary covering:
- Client status (Active / At Risk / Churned)
- Tenure and location count
- Churn reason if applicable
- Key contact name
- Any open issues or tickets worth knowing

---

## Report PDF sections (in order)

| # | Section | Always shown? |
|---|---|---|
| 1 | **Client Overview** — status badge, HubSpot link, tenure, CSM, PMS breakdown | Always |
| 2 | **Location Summary** — table of all locations (active first, then inactive), with first/last snap dates | Always |
| 3 | **Snapshot Activity Timeline** — monthly total snapshot count chart across all locations | If any snapshot data exists |
| 4 | **Cancellation History** — all records with reason, stage, dates, HubSpot link | If cancellation records exist |
| 5 | **Tickets** — list of HubSpot install/support tickets | If tickets exist |
| 6 | **Key Contacts** — table of contacts with email, title, type | If contacts exist |
| 7 | **Email Trail** — summarized recent threads, tagged by type | If Gmail threads found |
| 8 | **Winback Intelligence** — tenure summary, churn reasons, talking points | Churned clients only |

---

## Key rules

- **Pure reporting only** — no HubSpot record creation, no email sending, no side effects.
- **Monday Board is MB2-only** — do not check Monday Board for any client in this skill.
- **All API calls via Desktop Commander** — never the sandbox.
- **GoldenEye is the source of truth for snapshot dates** — HubSpot activation/deactivation
  dates are secondary and may be stale.
- **18-month snapshot window** is the default — extend to 24 months if the client's
  last snapshot is older than 18 months.
- **PDF generated via `generate_report.py`** — never write reportlab inline.
- **Winback section appears only for Churned clients.**

---

## Step 13 — Log the run

After Step 12, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `full-historical-client-report` |
| `status` | `success` if the PDF was delivered to Slack · `partial` if any data source (GoldenEye, HubSpot, Gmail) returned no results · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: client name, their status (Active/At Risk/Churned), tenure in months, and total locations covered in the report. |
| `inputs` | `{ "client_name": "<client_name_query>" }` |
| `outputs` | `{ "pdf_path": "<client_history_{slug}.pdf>", "slack_ts": "<ts or null>" }` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{ "client_status": "<Active|At Risk|Churned>", "tenure_months": N, "total_locations_ever": N, "current_active": N }` |

Call skill-logger even on failure — the log should capture what went wrong.

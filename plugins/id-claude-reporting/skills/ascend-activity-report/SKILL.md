---
name: ascend-activity-report
description: >
  Generate the InsideDesk Ascend API Monthly Activity Report.
  Uses GoldenEye as the single source of truth. Snapshot data is the primary
  billing baseline — any facility with a snapshot in the report month was billed.
  The GoldenEye Facilities page is used only as a name/status lookup.
  Produces an Excel data file and a PDF summary report, delivered to Sean's
  Slack DM. Use this skill whenever Sean asks for the Ascend activity report,
  wants to know which Ascend API locations had snapshot activity last month, says
  "run the Ascend report", "which Ascend locations were active", or
  "monthly Ascend activity". Always defaults to the prior calendar month.
---

# Ascend API Monthly Activity Report

> **Read first:** Before running this report, read `references/ascend-activity-report.md`
> (bundled in this skill). It contains the full data model, the snapshot-first billing
> rationale, and the historical-month edge cases that this report depends on. Do not
> skip it — the methodology there overrides any assumptions.

GoldenEye is the **single source of truth** for this report — do not use HubSpot.

Produces two deliverables:
1. **Excel spreadsheet** — all Ascend API locations with activity data (+ client summary tab)
2. **PDF report** — formatted summary with four sections, sent to Sean's Slack DM

## Data Model

**Snapshot data is the primary billing baseline.** Any facility with ≥1 snapshot
in the report month was billed, regardless of current active/inactive status. The
GoldenEye Facilities page is used only to determine which facilities are currently
active — it is NOT the baseline.

This approach is reliable for historical months because:
- Facilities cancelled after the report month still appear in snapshot data
- Facilities onboarded after the report month are absent from snapshot data and
  are automatically excluded (no false "No Snapshots" entries)

## Report Sections

The report has four possible sections (only shown if non-empty):

| Section | Color | Definition |
|---|---|---|
| **Active — Full Month** | Green | In report month snaps + in prior month snaps + currently active |
| **Newly Onboarded This Month** | Teal | In report month snaps + NOT in prior month snaps + currently active |
| **Offboarded — Still Billed This Month** | Amber | In report month snaps + NOT currently active (offboarded sometime after report month) |
| **No Snapshots This Month** | Red | In prior month snaps + currently active + zero snapshots in report month (sync issue) |

HS1 billing rule: any location with ≥1 snapshot in the report month is billed.

---

## Step 0 — Prerequisites

Run the **`get-secret`** skill with name `slack-bot-token` to retrieve the Slack bot token.
Store the returned value — it will be passed to `slack-upload.py` in Step 8.

---

## Step 0b — Calculate the date range

Default to the **prior calendar month** (e.g. if today is June 9 2026, report on May 1–31 2026).

Compute:
- `month_start` / `month_end` — first/last day of report month (`YYYY-MM-DD`)
- `prior_month_start` / `prior_month_end` — first/last day of the month BEFORE that
- `month_label` — e.g. `"May 2026"`
- `date_slug` — e.g. `"2026-05"`

---

## Step 1 — Fetch report month snapshots (primary billing baseline)

The GoldenEye Snapshots page uses an underlying API at:
```
https://<ADMIN_API_HOST>/pms-snapshot/
```

**Key parameters** (note: different from URL params on the page):
- `page_size=100` (not `pageSize`)
- `date_from=YYYY-MM-DD` (not `dateFrom`)
- `date_to=YYYY-MM-DD` (not `dateTo`)
- `pms_type=ascend_api` (not `pms`)

Pagination info is in the `x-pagination` response header: `{"total": N, "total_pages": N, ...}`

Navigate to `https://<GOLDENEYE_HOST>/production/admin/snapshots` (must be on the
GoldenEye domain for `credentials: 'include'` to work), then call the API from browser JS:

```javascript
(async () => {
  const base = 'https://<ADMIN_API_HOST>/pms-snapshot/?page_size=100&date_from=MONTH_START&date_to=MONTH_END&pms_type=ascend_api&page=';
  const snaps = {};

  const r1 = await fetch(base + '1', { credentials: 'include' });
  const pag = JSON.parse(r1.headers.get('x-pagination'));
  (await r1.json()).forEach(row => {
    const fid = String(row.facility?.id);
    if (!snaps[fid]) snaps[fid] = { facilityId: fid, facilityName: row.facility?.name, clientName: row.client?.name, count: 0, lastReceived: '' };
    snaps[fid].count++;
    const d = row.received_date?.substring(0, 10);
    if (!snaps[fid].lastReceived || d > snaps[fid].lastReceived) snaps[fid].lastReceived = d;
  });

  for (let p = 2; p <= pag.total_pages; p++) {
    (await fetch(base + p, { credentials: 'include' }).then(r => r.json())).forEach(row => {
      const fid = String(row.facility?.id);
      if (!snaps[fid]) snaps[fid] = { facilityId: fid, facilityName: row.facility?.name, clientName: row.client?.name, count: 0, lastReceived: '' };
      snaps[fid].count++;
      const d = row.received_date?.substring(0, 10);
      if (!snaps[fid].lastReceived || d > snaps[fid].lastReceived) snaps[fid].lastReceived = d;
    });
  }
  sessionStorage.setItem('_snapsReport', JSON.stringify(snaps));
  return Object.keys(snaps).length + ' unique facilities in report month (' + pag.total + ' total snapshots)';
})();
```

Run in batches of 30 pages if needed to avoid timeouts.

**Export to file:** trigger a browser download using a Blob URL:
```javascript
const blob = new Blob([sessionStorage.getItem('_snapsReport')], {type: 'application/json'});
const a = document.createElement('a');
a.href = URL.createObjectURL(blob);
a.download = 'ascend_snaps_report_{date_slug}.json';
document.body.appendChild(a); a.click();
```

Then copy from `~/Downloads/` to the project folder via Desktop Commander.

---

## Step 2 — Fetch prior month snapshots

Call the same API for the prior month. We only need the set of facility IDs (not full snap data):

```javascript
(async () => {
  const base = 'https://<ADMIN_API_HOST>/pms-snapshot/?page_size=100&date_from=PRIOR_START&date_to=PRIOR_END&pms_type=ascend_api&page=';
  const r1 = await fetch(base + '1', { credentials: 'include' });
  const pag = JSON.parse(r1.headers.get('x-pagination'));
  const priorIds = new Set();
  (await r1.json()).forEach(r => priorIds.add(String(r.facility?.id)));
  for (let p = 2; p <= pag.total_pages; p++) {
    (await fetch(base + p, { credentials: 'include' }).then(r => r.json()))
      .forEach(r => priorIds.add(String(r.facility?.id)));
  }
  sessionStorage.setItem('_priorIds', JSON.stringify([...priorIds]));
  return priorIds.size + ' unique facilities in prior month';
})();
```

Export `_priorIds` array to `ascend_snaps_prior_{date_slug}.json` via Blob download, then copy to project folder.

---

## Step 3 — Build facility name/status lookup from GoldenEye Facilities page

The facilities page is used **only as a lookup** — it tells us which facilities are currently
active and provides names for facilities not in the snapshot data (i.e. the "No Snapshots" group).

Navigate to:
```
https://<GOLDENEYE_HOST>/production/admin/facility?pms=ascend_api&page=1&pageSize=100
```

Wait 3 seconds, then paginate all pages:

```javascript
const rows = document.querySelectorAll('table tbody tr');
const lookup = {};
rows.forEach(row => {
  const link = row.querySelector('a[href*="/facility/"]');
  const fid = link?.href.match(/\/facility\/(\d+)/)?.[1];
  const cells = Array.from(row.querySelectorAll('td')).map(c => c.textContent.trim());
  if (fid) lookup[fid] = { facilityId: fid, clientName: cells[1], facilityName: cells[2], isActive: true };
});
sessionStorage.setItem('_facilityLookup', JSON.stringify(lookup));
Object.keys(lookup).length + ' active facilities';
```

Click "next page" to collect all pages (save to same `sessionStorage._facilityLookup` key by merging).

> **Do not check the inactive facilities page** — any facility in snapshot data that is absent
> from the active list is inferred as offboarded. No separate inactive scrape needed.

Export `_facilityLookup` to `ascend_facility_lookup_{date_slug}.json` via Blob download and copy to project folder.

---

## Step 4 — Categorise locations and build report data

Load the three JSON files in a Python script via Desktop Commander:

```python
import json

with open('ascend_snaps_report_{date_slug}.json') as f:
    report_snaps = json.load(f)   # {facilityId: {facilityId, clientName, facilityName, count, lastReceived}}

with open('ascend_snaps_prior_{date_slug}.json') as f:
    prior_ids = set(json.load(f)) # set of facilityId strings

with open('ascend_facility_lookup_{date_slug}.json') as f:
    facility_lookup = json.load(f) # {facilityId: {clientName, facilityName, isActive}}

active_ids = set(facility_lookup.keys())

# --- Billed facilities (primary billing baseline) ---
active_locations    = []  # Active Full Month
onboarded_locations = []  # Newly Onboarded
offboarded_locations = [] # Offboarded Still Billed

for fid, snap in report_snaps.items():
    name   = snap['facilityName'] or facility_lookup.get(fid, {}).get('facilityName', f'Facility {fid}')
    client = snap['clientName']   or facility_lookup.get(fid, {}).get('clientName', 'Unknown')
    entry  = {"facility_id": fid, "client": client, "location": name,
               "snapshot_count": snap['count'], "last_snapshot": snap['lastReceived']}
    if fid not in active_ids:
        offboarded_locations.append(entry)     # not in active list → offboarded
    elif fid in prior_ids:
        active_locations.append(entry)          # active + had prior month snaps
    else:
        onboarded_locations.append(entry)       # active + no prior month snaps → newly onboarded

# --- No Snapshots: were in prior month, still active, but missed report month ---
inactive_locations = []
for fid in prior_ids:
    if fid in active_ids and fid not in report_snaps:
        fac = facility_lookup[fid]
        inactive_locations.append({"facility_id": fid,
                                    "client": fac['clientName'],
                                    "location": fac['facilityName']})

# Sort each section by client then location name
for lst in [active_locations, onboarded_locations, offboarded_locations, inactive_locations]:
    lst.sort(key=lambda x: (x['client'], x['location']))
```

---

## Step 5 — Build the Excel spreadsheet

Install if needed: `pip install openpyxl --break-system-packages -q`

**Sheet 1 — "All Locations"**
Columns: GoldenEye ID | Client | Location | Snapshot Count | Last Snapshot Date | Status

Section divider rows (colored bars) before each group:
- Active Full Month → green divider + green row fill
- Newly Onboarded → teal divider + teal row fill
- Offboarded Still Billed → amber divider + amber row fill
- No Snapshots → red divider + red row fill

**Sheet 2 — "Client Summary"**
Columns: Client | Total Billed | Active Full Month | Newly Onboarded | Offboarded Billed | No Snapshots

Save to: `{OUTDIR}/ascend_activity_{date_slug}.xlsx`

---

## Step 6 — Build the PDF report

> ⛔ **MANDATORY — call `generate_report.py` — never write reportlab code inline.**

Install: `pip install reportlab --break-system-packages -q`

JSON schema:
```json
{
  "month_label":       "May 2026",
  "total_locations":   116,
  "active_count":      112,
  "onboarded_count":   2,
  "offboarded_count":  2,
  "inactive_count":    0,
  "active_locations":     [{"facility_id","client","location","snapshot_count","last_snapshot"}],
  "onboarded_locations":  [{"facility_id","client","location","snapshot_count","last_snapshot"}],
  "offboarded_locations": [{"facility_id","client","location","snapshot_count","last_snapshot"}],
  "inactive_locations":   [{"facility_id","client","location"}]
}
```

```bash
python3 "/Users/sean/CODE/id-claude-reporting/skills/ascend-activity-report/generate_report.py" \
  --month  "May 2026" \
  --slug   "2026-05" \
  --outdir "/Users/sean/CODE/id-claude-reporting" \
  --data   '<JSON>'
```

Output: `{outdir}/ascend_activity_{slug}.pdf`

---

## Step 7 — Send the PDF to Sean via Slack DM

```bash
python3 "/Users/sean/CODE/id-claude-reporting/skills/_shared/slack-upload.py" \
  --token    "<slack-bot-token>" \
  --file     "/Users/sean/CODE/id-claude-reporting/ascend_activity_{slug}.pdf" \
  --filename "ascend_activity_{slug}.pdf" \
  --title    "Ascend API Activity Report · {month_label}" \
  --comment  "*Ascend API Activity Report* · {month_label}"
```

Verify: `ok=True  permalink=https://...`

---

## Step 8 — Deliver links to Sean

```
[View Spreadsheet](computer:///Users/sean/CODE/id-claude-reporting/ascend_activity_{slug}.xlsx)
[View PDF Report](computer:///Users/sean/CODE/id-claude-reporting/ascend_activity_{slug}.pdf)
```

Plain-English summary: total billed, breakdown by section, call out any newly onboarded or offboarded locations by name.

---

## Key rules and constraints

- **Snapshot data is the primary billing baseline** — the facilities page is a lookup only.
- **Facilities onboarded after the report month are automatically excluded** — they have no
  snapshots in the report period so they never enter the classification logic.
- **GoldenEye is the single source of truth** — no HubSpot for location data.
- **Default to prior calendar month.**
- **All snapshots, not errors only** — do NOT pass `errorsOnly=true`.
- **API params use underscores**: `page_size`, `date_from`, `date_to`, `pms_type` — NOT camelCase.
- **page_size=100 exactly** — higher values silently return 0 results.
- **Prior month comparison is required** to correctly identify newly onboarded facilities and
  flag facilities that stopped syncing this month.
- **Do NOT check the inactive facilities page** — offboarded status is inferred from absence
  in the current active list. Snapshot data provides names for offboarded facilities directly.
- **PDF must be generated via `generate_report.py`** — never write reportlab inline.
- **HS1 billing rule**: any location with ≥1 snapshot in the month is billed.
- Install deps: `pip install openpyxl reportlab --break-system-packages -q`

---

## Step 9 — Close browser tabs

Before logging, close any GoldenEye browser tabs using the **`chrome-cleanup`** helper skill.
Pass the `tabId` from your browser navigation responses.

---

## Step 10 — Log the run

After Step 9, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `ascend-activity-report` |
| `status` | `success` if the PDF was delivered to Slack · `partial` if any data step failed silently · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: report month covered, total billed locations, breakdown by section (active, onboarded, offboarded, no-snapshots). |
| `inputs` | `{ "report_month": "<month_label>" }` |
| `outputs` | `{ "excel_path": "<ascend_activity_{slug}.xlsx>", "pdf_path": "<ascend_activity_{slug}.pdf>", "slack_ts": "<ts or null>", "active_count": N, "onboarded_count": N, "offboarded_count": N, "inactive_count": N }` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{ "date_slug": "<slug>", "total_billed": N }` |

Call skill-logger even on failure — the log should capture what went wrong.

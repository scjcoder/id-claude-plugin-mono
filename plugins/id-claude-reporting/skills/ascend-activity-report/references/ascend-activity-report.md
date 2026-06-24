# Ascend API Monthly Activity Report — Documentation

## Purpose

HS1 (our Ascend API data vendor) bills InsideDesk for each office that had **any snapshot activity during the month**, regardless of whether that office is currently active or has been cancelled. This report is used to verify our monthly royalty payment to HS1 and to track which offices are joining or leaving the Ascend API integration.

---

## Data Model

**Snapshot data is the primary billing baseline.** The GoldenEye Facilities page is used only as a name/status lookup — it is not the baseline.

This matters for historical months. If you run the May report in June, some facilities may have been cancelled or onboarded between May and now. A facilities-page-first approach would:
- **Miss** facilities cancelled after May (they'd be inactive and excluded from the baseline)
- **Falsely flag** facilities onboarded after May as "No Snapshots" (they're on the active list but had no May activity)

The snapshot-first approach avoids both problems:
- Any facility with a snapshot in the report month is billed — full stop
- Facilities onboarded after the report month have no snapshots and are naturally excluded

---

## How the Report Is Built

### Step 1 — Report month snapshots (primary billing baseline)
- Call the GoldenEye Snapshots API for the full report month (e.g. April 1–30)
- Collect every unique facility ID + snapshot count + last received date
- **This is the billing list.** Every facility here was billed for the month.

### Step 2 — Prior month snapshots
- Call the same API for the prior month (e.g. March 1–31)
- Result: set of facility IDs that were active the month before
- Used to distinguish newly onboarded (first month) from full-month active

### Step 3 — Active facilities lookup
- Read the GoldenEye Facilities page (all pages, Ascend API filter)
- Build a lookup dict: `{facilityId → {clientName, facilityName}}`
- This tells us which facilities are **currently active** — used for two things:
  1. Classifying billed facilities as active vs. offboarded
  2. Getting names for "No Snapshots" facilities (not in snapshot data)
- **Do not check the inactive page** — offboarded status is inferred from absence in the active list

### Step 4 — Categorize

```
For each facility in report month snapshots (billed):
  ├─ NOT in current active list?       → "Offboarded — Still Billed"
  ├─ In prior month snapshots?         → "Active — Full Month"
  └─ NOT in prior month snapshots?     → "Newly Onboarded"

For each facility in prior month snapshots:
  ├─ In current active list?
  │   └─ NOT in report month snapshots? → "No Snapshots" (sync issue)
  └─ Not in active list → skip (was cancelled, and had no report-month snaps either)
```

### Step 5 — HS1 Billing Rule
Any facility with ≥1 snapshot in the month = billed, no exceptions.
This includes offboarded offices (Offboarded section).

### Step 6 — Output
PDF sections (in this order):
1. **Newly Onboarded This Month** — first month on the bill
2. **Offboarded — Still Billed** — last month on the bill (or partial)
3. **Active — Full Month** — ongoing, no change
4. **No Snapshots** — not billed, needs investigation

Excel: same data in spreadsheet form + client summary tab

---

## Report Sections Explained

| Section | Color | What it means |
|---|---|---|
| Newly Onboarded | Teal | Facility appeared in the report month's snapshots but NOT the prior month's. First month of billing. |
| Offboarded — Still Billed | Amber | Facility had report-month snapshots but is no longer in the active facilities list (cancelled since then). HS1 bills for it. Typically the final partial month. |
| Active — Full Month | Green | Facility was present in both prior and current month snapshots and is still active. Normal ongoing billing. |
| No Snapshots | Red | Facility was active in the prior month and is still currently active, but sent zero snapshots in the report month. NOT billed — may indicate a sync or connectivity problem. |

---

## Key Business Rules

- **HS1 bills per office, per month, if they had ANY snapshot activity** — even one snapshot counts. Reason for cancellation, timing within the month, or current active/inactive status in GoldenEye does not affect billing.
- **Facilities onboarded after the report month are automatically excluded** — they have no snapshots in the report period and never enter the classification logic.
- **Gladstein Dental Center example (May 2026):** Licence transferred to The Scarsdale Dentist in early May. Gladstein had 1 snapshot on 05/03 and Scarsdale was already active — both appear on the May report as separate billable entries.
- **Gherardi & Moore example (April 2026):** Cancellation effective before April, but 123 snapshots still came through in April. Appears in Offboarded section — still billed for April.
- **Finesse Dental Partners (April 2026):** 12 locations with April snapshot activity despite being offboarded. All appear in the Offboarded Still Billed section.

---

## Data Sources

| Source | What it provides | How accessed |
|---|---|---|
| GoldenEye Snapshots API | Primary billing baseline — all facilities with snapshot activity in the report month | Browser JS `fetch()` from the GoldenEye domain |
| GoldenEye Snapshots API (prior month) | Set of facility IDs active the month before — used for onboarding detection and No Snapshots detection | Same API, prior month date range |
| GoldenEye Facilities page | Name/status lookup — which facilities are currently active | Claude-controlled browser only |

**GoldenEye is the single source of truth** — HubSpot is not used for this report.

### GoldenEye Snapshots API — Important Notes
The underlying API uses different parameter names than the page URL:

| Page URL param | API param |
|---|---|
| `pageSize` | `page_size` |
| `dateFrom` | `date_from` |
| `dateTo` | `date_to` |
| `pms` | `pms_type` |

- Use `page_size=100` exactly — higher values silently return 0 results
- Pagination info is in the `x-pagination` response header
- Auth is handled automatically via browser session cookies (`credentials: 'include'`)
- Must call the API from a GoldenEye page (e.g. `/admin/snapshots`) — same-domain only
- Data is exported to a local file by triggering a browser Blob download, then copying from `~/Downloads/`

---

## Implementation Notes

### Why snapshot-first instead of facilities-first
The old approach used the GoldenEye Facilities page as the baseline. This worked well for same-month runs but had two failure modes when running reports for historical months:

1. **False "No Snapshots" entries** — facilities onboarded after the report month appeared in the active list but had no historical snapshots, incorrectly landing in the No Snapshots section.
2. **Missed offboarded locations** — facilities cancelled after the report month but before the report was run were invisible to the active-page query, requiring a separate inactive-page scrape that was brittle to paginate.

The snapshot-first model eliminates both: snapshot data is immutable and historical, so it always reflects exactly who was billing in that month regardless of when the report is run.

### Detecting offboarded facilities
Any facility in the report-month snapshots that is absent from the current active facilities list is classified as offboarded. Client and facility names come from the snapshot API response itself (the `facility.name` and `client.name` fields), so no separate inactive-page scrape is needed.

### Detecting newly onboarded facilities
A facility is "newly onboarded" if its ID appears in the report-month snapshots but NOT in the prior-month snapshots. Both datasets come from the same API; the prior-month call returns IDs only (no need for full snap data).

### Detecting No Snapshots facilities
A facility is flagged as "No Snapshots" if it appears in the prior-month snapshots AND is currently in the active facilities list AND has zero report-month snapshots. The active-list check excludes facilities that were cancelled between the prior month and the report month (they wouldn't have been expected to sync either).

---

## Files

| File | Purpose |
|---|---|
| `skills/ascend-activity-report/SKILL.md` | Full step-by-step skill instructions for Claude |
| `skills/ascend-activity-report/generate_report.py` | ReportLab PDF generator — must be called via subprocess, never inlined |
| `ascend_snaps_report_{slug}.json` | Report-month snapshot data (primary billing baseline) |
| `ascend_snaps_prior_{slug}.json` | Prior-month facility IDs (for onboarding/no-snaps detection) |
| `ascend_facility_lookup_{slug}.json` | Active facilities name/status lookup |
| `ascend_report_data_{slug}.json` | Categorized report data passed to generate_report.py |
| `ascend_activity_{slug}.xlsx` | Final Excel output |
| `ascend_activity_{slug}.pdf` | Final PDF output (sent to Slack) |

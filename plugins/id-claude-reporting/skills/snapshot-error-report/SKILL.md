---
name: snapshot-error-report
description: >
  Generate the InsideDesk GoldenEye Snapshot Error Report by reading the Snapshots page
  in the browser, producing an Excel data table and a PDF summary report, and delivering
  the PDF to Sean's Slack DM.
  Use this skill whenever Sean asks for a snapshot error report, wants to audit what's
  failing in GoldenEye snapshots, asks about 400 or 422 errors in snapshots, says
  "run the snapshot report", or "what snapshots are erroring". Always scopes to today only.
  Always use the Claude-controlled browser — never attempt API calls to gather the same data.
---

# GoldenEye Snapshot Error Report Skill

This skill reads the GoldenEye Snapshots page in the browser, collects all error records,
and produces two deliverables saved to the project folder:
1. **Excel spreadsheet** — raw error log + client summary tab
2. **PDF report** — formatted summary organized by status code

---

## Step 0 — Prerequisites

Run the **`get-secret`** skill with name `slack-bot-token` to retrieve the Slack bot token.
Store the returned value — it will be passed to `slack-upload.py` in Step 7.

---

## Step 0b — Date range

The date range is always **today only**. Do not ask Sean for a date range. Do not use yesterday's date.

Determine today's date (e.g. via `date +%Y-%m-%d` in bash) and use it for both `dateFrom` and `dateTo`.

---

## Step 1 — Open GoldenEye Snapshots page

**Determine today's date** from Step 0b. You will need it in two formats:
- URL / filename format: `YYYY-MM-DD` (e.g. `2026-06-19`)
- Input field format: `MM/DD/YYYY` (e.g. `06/19/2026`)

Navigate to:

```
https://goldeneye.insidedesk.net/production/admin/snapshots?page=1&errorsOnly=true&dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD&pageSize=100
```

Substitute today's date (YYYY-MM-DD) for both parameters. Wait 3 seconds for the page to fully load.

**Set the date fields by clicking — required every run:**

The URL params are not reliable on their own; React's internal state can override them with a previously cached date range. You must actively set the fields:

1. Triple-click the **Date From** input to select all existing content.
2. Type today's date in `MM/DD/YYYY` format (replaces whatever was there).
3. Press Tab to advance to the **Date To** field.
4. Triple-click the **Date To** input to select all existing content.
5. Type today's date in `MM/DD/YYYY` format.
6. Press Tab or Enter to confirm, then wait 1 second.
7. If an **Apply**, **Search**, or **Filter** button is visible, click it and wait 2 seconds.

After clicking, run this JavaScript to reinforce the React state update:

```javascript
const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
const dateFromInput = document.querySelector('input[name="dateFrom"]');
const dateToInput   = document.querySelector('input[name="dateTo"]');
// Substitute actual MM/DD/YYYY date for both
setter.call(dateFromInput, 'MM/DD/YYYY');
dateFromInput.dispatchEvent(new Event('input',  { bubbles: true }));
dateFromInput.dispatchEvent(new Event('change', { bubbles: true }));
setter.call(dateToInput, 'MM/DD/YYYY');
dateToInput.dispatchEvent(new Event('input',  { bubbles: true }));
dateToInput.dispatchEvent(new Event('change', { bubbles: true }));
```

Wait 2 seconds for the data to reload.

**MANDATORY date verification — do not skip, do not proceed without passing this gate:**

Take a screenshot. Read the actual values shown in the **Date From** and **Date To** fields.

- ✅ Both fields show today's date → proceed to Step 2.
- ❌ Either field shows any other date (yesterday, a range, blank) → **stop and retry**: triple-click each field, delete all content, retype today's date in `MM/DD/YYYY`, press Tab/Enter, wait 2 seconds, take another screenshot. Repeat until both fields confirm today's date. Do not read any snapshot data until this check passes.

Also confirm the **"Errors only"** toggle is active (blue). If it is off, click it before proceeding.

Note the total row count shown at the bottom of the page (e.g. "1–100 of 1,720"). This
tells you how many pages to read: `ceil(total / 100)`.

---

## Step 2 — Read all pages

Read each page by iterating the `page` parameter from 1 to the final page, keeping
`pageSize=100`. Use `get_page_text` on each page — do not screenshot every page, just
navigate and extract text.

For each page, capture every row in the table:
- **Snapshot ID** (Id column)
- **Client**
- **Facility**
- **Status** code
- **# Claims** (including chunk count if shown)
- **Received** timestamp
- **Latest Digestion** (Digested count and Errors count if shown)

**Do NOT use API calls, curl, Python requests, or any non-browser method to gather this
data.** Only the Claude browser extension is permitted.

---

## Step 3 — Classify each row

Apply these rules as you collect data:

### Status 422 — HIGH IMPORTANCE
Flag every 422. These indicate "Tax ID not in config" and require immediate action.
Note the client, facility, received timestamp, PMS, and claims count.

### Status 400 — HIGH IMPORTANCE
Flag every 400 ("Malformed JSON"). Group by client. Note the first and last Received
timestamp for each client group to define the error window.

### Status 201 — Check digestion only
A 201 snapshot only appears in Errors Only view when it has at least one digestion error.
- If only **a few chunks** have errors (e.g. 1–2 errors out of many chunks) → **skip**.
  These are minor and within normal range.
- If **almost all chunks** are erroring (digested count near zero, error count covering
  most or all chunks) → **flag** with a note. Include in the 201 section of the report.
- Rule of thumb: flag when errors represent the majority of the chunk payload.

### Status N/A — DISCARD
N/A status (Unhandled BaseException) entries are minor and should be completely ignored.
Do not include them in either deliverable.

---

## Step 4 — Compile the data

After reading all pages, organize the collected data into two structures:

**Error Log** (one row per client-error-cluster):
- Status Code, Priority, Client, Facility / Location, Error Count, First Seen, Last Seen, Notes

**Client Summary** (one row per client):
- Client, Status 422 count, Status 400 count

Group 400 errors by date cluster if multiple distinct time windows are present
(e.g. a morning burst today vs. an overnight burst yesterday).

---

## Step 5 — Build the Excel spreadsheet

Use `openpyxl` to create an `.xlsx` file with two sheets:

**Sheet 1 — "Error Log"**
Columns: Status Code | Priority | Client | Facility / Location | Error Count | First Seen | Last Seen | Notes

- Color-code the Status Code column: red for 422, orange for 400, green for 201 info.
- Use section header rows (navy background, white bold text) to separate:
  - 422 section
  - 400 — Today section (if applicable)
  - 400 — Yesterday section (if applicable)
  - 201 Digestion Notes section
- Set row height to ~45pt and enable text wrapping on all cells.
- Freeze the header row.

**Sheet 2 — "Client Summary"**
One row per client with counts per status code. Color-code 422 cells red, 400 cells orange.

Save to:
```
/Users/sean/CODE/id-claude-reporting/snapshot_errors_YYYY-MM-DD_DD.xlsx
```

---

## Step 6 — Build the PDF report

> ⛔ **MANDATORY — NEVER write reportlab code inline or generate HTML for this step.**
>
> The PDF format is defined in `generate_report.py` in this skill directory.
> You MUST call that script. Every run must produce output that is visually identical
> to prior runs. If you write your own HTML or reportlab code instead of calling
> `generate_report.py`, you are producing the wrong output.

Install dependencies first:
```bash
pip install reportlab --break-system-packages -q
```

Build the JSON data structure from your compiled data (Step 4), then call the script:

```bash
python3 "/Users/sean/CODE/id-claude-reporting/skills/snapshot-error-report/generate_report.py" \
  --dates  "YYYY-MM-DD_DD" \
  --outdir "/Users/sean/CODE/id-claude-reporting" \
  --data   '<JSON>'
```

**JSON schema** — omit (or pass `[]`) any section with no entries:

```json
{
  "date_range_display":         "May 10-11, 2026",
  "total_records":              1720,

  "errors_422": [
    {
      "client":   "Southeast-Dental-Partners",
      "facility": "Monroe Dental Care",
      "count":    1,
      "received": "May 10 6:00 PM",
      "notes":    "OpenDental 25.2.52.0 - Tax ID not in system config"
    }
  ],

  "errors_400_today_label":   "May 11, 2026 (7:42 AM - 9:12 AM)",
  "errors_400_today_summary": "A broad burst affected multiple clients...",
  "errors_400_today": [
    {
      "client":     "ProSmile-Dental-Group",
      "facilities": ["Little Falls", "Hazlet", "Old Bridge"],
      "count":      "~380+",
      "first":      "7:42 AM",
      "last":       "8:06 AM",
      "notes":      "All active facilities. ~24-min window."
    }
  ],

  "errors_400_yesterday_label":   "May 10, 2026 (2:10 AM - 2:17 AM)",
  "errors_400_yesterday_summary": "Overnight burst...",
  "errors_400_yesterday": [ ],

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
```

The script outputs:
```
/Users/sean/CODE/id-claude-reporting/snapshot_error_report_YYYY-MM-DD_DD.pdf
```

Verify the PDF is non-empty (> 5 KB) before continuing. If the script fails, surface
the raw error to Sean — do not fall back to HTML or any other format.

---

## Step 7 — Send the PDF to Sean via Slack DM

Run the shared Slack upload script via **Desktop Commander** (`mcp__Desktop_Commander__start_process`).
Substitute the actual date range string for `{date_range}` (e.g. `May 11, 2026`) and the exact PDF filename:

```bash
python3 "/Users/sean/CODE/id-claude-reporting/skills/_shared/slack-upload.py" \
  --token   "<slack-bot-token from get-secret>" \
  --file    "/Users/sean/CODE/id-claude-reporting/snapshot_error_report_YYYY-MM-DD_DD.pdf" \
  --filename "snapshot_error_report_YYYY-MM-DD_DD.pdf" \
  --title   "Snapshot Error Report · {date_range}" \
  --comment "*Snapshot Error Report* · {date_range}"
```

Verify success: the script prints `ok=True  permalink=https://...`. If it fails, surface the raw error — do not proceed silently.

---

## Step 8 — Deliver links to Sean

After the PDF has been sent to Slack, provide direct links in chat:

```
[View Spreadsheet](computer:///Users/sean/CODE/id-claude-reporting/snapshot_errors_YYYY-MM-DD_DD.xlsx)
[View PDF Report](computer:///Users/sean/CODE/id-claude-reporting/snapshot_error_report_YYYY-MM-DD_DD.pdf)
```

Follow with a concise plain-English summary covering:
- Any 422s found (flag as requiring immediate action)
- The 400 error clusters — clients affected, approximate counts, time windows
- Any 201 digestion items worth watching
- Total row count processed

---

## Key rules and constraints

- **PDF must be generated via `generate_report.py`** — never write reportlab code inline,
  never output an HTML file as the report. The script is the canonical template.
- **Never use API calls** to fetch snapshot data. Browser only.
- **Discard N/A (Unhandled BaseException)** rows entirely — do not surface them.
- **201 rows**: only flag if almost all chunks are erroring. A few isolated digestion
  errors are normal and should be noted in the informational section only.
- Use `pageSize=100` in the URL — this is the maximum the backend supports. Values above 100
  (e.g. 500) are silently accepted by the URL but return 0 results, so always use 100.
- Date format in filenames: use the actual calendar dates, e.g. `2026-05-10_11` for
  a May 10–11 report.
- Install deps in bash with `--break-system-packages` flag if needed:
  `pip install openpyxl reportlab --break-system-packages -q`

---

## Step 9 — Log the run

After Step 8, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `snapshot-error-report` |
| `status` | `success` if the PDF was delivered to Slack · `partial` if any data pages were unreadable · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: date scanned, total snapshot rows processed, count of 422 and 400 errors found, and whether any 201 digestion items were flagged. |
| `inputs` | `{ "date_scanned": "<YYYY-MM-DD>" }` |
| `outputs` | `{ "excel_path": "<snapshot_errors_YYYY-MM-DD_DD.xlsx>", "pdf_path": "<snapshot_error_report_YYYY-MM-DD_DD.pdf>", "slack_ts": "<ts or null>", "error_count": N }` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{ "count_422": N, "count_400": N, "count_201_flagged": N, "total_rows": N }` |

Call skill-logger even on failure — the log should capture what went wrong.

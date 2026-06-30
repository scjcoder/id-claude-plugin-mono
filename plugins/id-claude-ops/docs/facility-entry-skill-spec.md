# Skill Spec: `insidedesk-facility-entry` v2

**Status:** Draft — pending implementation
**Author:** Review by Sean Johnson, original skill by David
**Date:** 2026-05-27
**Target plugin:** `id-claude-ops`

---

## Overview

This document captures the full enhancement spec for the `insidedesk-facility-entry` skill. It includes the original skill file for reference, a prioritized list of improvements, and implementation notes for each. The goal is a v2 that is faster for bulk runs, safer against data entry errors, and leaves a clear audit trail.

The skill automates entering facility/office records into the InsideDesk Operations Dashboard from a spreadsheet, one row at a time, using Claude in Chrome (browser automation only — no API calls).

---

## Enhancement Summary

### 🔴 High Priority

| # | Enhancement | Problem It Solves |
|---|---|---|
| 1 | URL/domain validation | Prevents submitting to wrong environment on typo |
| 2 | Tax ID and phone format validation at parse time | Catches bad data before touching the browser |
| 3 | PMS "Dentrix Ascend" ambiguity resolved at Step 0 | Eliminates mid-loop surprises with ascend_api extra fields |

### 🟠 Medium Priority

| # | Enhancement | Problem It Solves |
|---|---|---|
| 4 | Full upfront row validation pass | User sees all problems before the session starts |
| 5 | Audit log written per submission | Leaves a record of what was actually submitted |
| 6 | Screenshot saved as receipt after each submit | Evidence if a record is later disputed |
| 7 | Duplicate detection before each form open | Prevents silently creating duplicate facilities |

### 🟡 Nice-to-Have

| # | Enhancement | Problem It Solves |
|---|---|---|
| 8 | Batch confirm mode | Cuts down per-row confirmation overhead for large trusted batches |
| 9 | Dry-run mode (no browser) | Lets user verify spreadsheet is clean before committing |
| 10 | Progress counter in every prompt | User always knows where they are in the batch |
| 11 | Don't re-navigate between records | Saves time on large batches |
| 12 | City/State/Zip parser validation | Catches malformed combined-field cells |

---

## Detailed Specs

### 1 — URL/Domain Validation

**Where:** Before Step 2 (Navigate), immediately after getting the URL from the user.

**Behavior:**
- Extract the hostname from the provided URL.
- Assert it matches `*.insidedesk.com` (or a hardcoded allowlist of known valid hostnames, e.g. `operations.insidedesk.com`).
- If the URL does not match, halt and show:

```
⛔ URL validation failed.
The URL you provided does not appear to be an InsideDesk Operations Dashboard URL.

Provided: https://example.com/facilities
Expected: a URL under *.insidedesk.com

Please double-check the URL and try again.
```

**Implementation note:** This can be done with a simple Python `urllib.parse.urlparse` check in Step 0, before any browser connection is attempted.

---

### 2 — Tax ID and Phone Format Validation

**Where:** Step 0 — Spreadsheet Read, after stripping dashes.

**Rules:**
- Tax ID after stripping non-digits: must be exactly 9 digits (`\d{9}`).
- Phone after stripping non-digits: must be exactly 10 digits (`\d{10}`).

**Behavior:**
- Flag any row that fails either check with a `⚠️ INVALID` marker.
- Include flagged rows in the upfront validation summary (see Enhancement #4).
- Do not enter any flagged row until the user resolves it or explicitly overrides.

**Implementation note:** Add to the pandas parse loop:

```python
import re

def validate_tax_id(raw):
    stripped = re.sub(r'\D', '', str(raw))
    return stripped if len(stripped) == 9 else None

def validate_phone(raw):
    stripped = re.sub(r'\D', '', str(raw))
    return stripped if len(stripped) == 10 else None
```

---

### 3 — PMS "Dentrix Ascend" Ambiguity Resolved at Step 0

**Where:** Step 0 — Spreadsheet Read.

**Behavior:**
- After parsing all rows, identify any row where the PMS value is "Dentrix Ascend".
- Before proceeding, ask the user for each such row:

```
⚠️ PMS Clarification Needed

Row 4 — "Miami Dental Group" has PMS value: "Dentrix Ascend"

This could map to:
  - dentrix (standard Dentrix, cloud-hosted UI) — most common
  - ascend_api (Ascend API integration — requires Organization ID and Ascend Location)

Which should I use?
  A) dentrix
  B) ascend_api (I will provide Organization ID and Ascend Location)
```

- If the user selects B, collect Organization ID and Ascend Location for that row before the browser loop starts.
- Store the resolved PMS value back into the row dict so no ambiguity remains during form-fill.

---

### 4 — Full Upfront Row Validation Pass

**Where:** End of Step 0, before Step 1 (Connect to Browser).

**Behavior:**
- After parsing all rows and resolving PMS ambiguities, display a full preview table of every row, with a status column:

```
📋 Spreadsheet Preview — 8 rows found

| # | Name                  | City       | State | Zip   | Phone      | Tax ID    | PMS     | Status  |
|---|-----------------------|------------|-------|-------|------------|-----------|---------|---------|
| 1 | Miami Dental Group    | Miami      | FL    | 33101 | 3051234567 | 123456789 | dentrix | ✅ OK   |
| 2 | Scarsdale Dentist     | Scarsdale  | NY    | 10583 | 9147250707 | 392822453 | dentrix | ✅ OK   |
| 3 | Broken Phone Office   | Austin     | TX    | 78701 | 512-???    | 987654321 | eaglesoft | ⚠️ Invalid phone |
| 4 | No Tax ID Office      | Denver     | CO    | 80201 | 7205551234 |           | opendental | ⚠️ Missing Tax ID |

Issues found: 2 rows need attention before proceeding.
Please fix rows 3 and 4 in your spreadsheet and re-run, or reply "skip" to exclude them and proceed with the clean rows.
```

- If all rows are clean, confirm and proceed to Step 1.
- If there are issues, halt until the user resolves them or explicitly skips the flagged rows.

---

### 5 — Audit Log

**Where:** After each successful submission (Step 6).

**Behavior:**
- Append a row to a local CSV file: `facility-entry-log-YYYY-MM-DD.csv` in the current working directory (or a `logs/` subfolder if it exists).
- Columns: `timestamp`, `facility_name`, `city`, `state`, `zip`, `phone`, `tax_id`, `pms`, `status`, `notes`
- `status` is `SUCCESS` on a confirmed submission, `SKIPPED` if the user skipped the row, `FAILED` if an error occurred.
- At the end of the run, inform the user of the log file path.

---

### 6 — Screenshot as Receipt

**Where:** After each successful submission (Step 6), immediately after the success confirmation message appears.

**Behavior:**
- Take a screenshot and save it to `facility-entry-receipts/YYYY-MM-DD/` with filename `{row_number}_{facility_name_slug}.png`.
- Confirm the screenshot was saved in the post-submit message to the user.

**Implementation note:** Use the `screenshot` browser action and save the file via bash. Sanitize the facility name for use in a filename (replace spaces with underscores, strip special characters).

---

### 7 — Duplicate Detection

**Where:** Step 3 — Before clicking NEW for each row.

**Behavior:**
- Before clicking NEW, use `get_page_text` or `find` to search the current facilities list for the facility name about to be entered.
- If a match is found, show:

```
⚠️ Possible Duplicate Detected

A facility named "Miami Dental Group" may already exist in the system.
Please check the list before proceeding.

Reply "skip" to skip this row, or "proceed" to enter it anyway.
```

- Do not click NEW until the user responds.

**Implementation note:** A fuzzy match is not needed — an exact case-insensitive string search on the page text is sufficient as a first guard.

---

### 8 — Batch Confirm Mode

**Where:** Asked at the very start (before Step 0), or as a flag the user can include in their initial message.

**Behavior:**
- At the start of the skill, ask:

```
How would you like to confirm submissions?

  A) Per-row (default) — I'll confirm each record individually before it's submitted.
  B) Batch — Show me all rows upfront, I'll confirm once, then run the full loop unattended.
```

- In **per-row mode** (A): behavior is unchanged from v1 — confirm before each submit.
- In **batch mode** (B): show the full preview table (Enhancement #4), get one "confirm all" from the user, then run the loop without pausing. Still halt on any error or duplicate warning.

---

### 9 — Dry-Run Mode

**Where:** Invokable via user message, e.g. "dry run" or "just preview".

**Behavior:**
- Run Step 0 only (spreadsheet parse + validation).
- Display the full preview table (Enhancement #4).
- Do not connect to the browser at all.
- End with:

```
✅ Dry run complete. No records were submitted.
Reply with the URL to begin actual entry, or fix any flagged rows first.
```

---

### 10 — Progress Counter

**Where:** Every user-facing prompt during the browser loop.

**Behavior:**
- Prepend every confirmation prompt and status message with a progress line:

```
📍 Record 3 of 9 — Scarsdale Dentist
```

---

### 11 — Avoid Re-Navigation Between Records

**Where:** Step 7 — After submission, before next record.

**Current behavior:** Implied full page reload between records.

**New behavior:**
- After a successful submit and the modal closes, attempt to click the NEW button directly from the current page state.
- Only reload the full page (`navigate` back to the URL) if the NEW button cannot be found within 2 attempts.
- This eliminates one full page load per record on most runs.

---

### 12 — City/State/Zip Parser Validation

**Where:** Step 0 — Spreadsheet Read, in the parse function for Column G.

**Rules:**
- After splitting "City, State  Zip" → city must be non-empty string, state must be a 2-letter uppercase US abbreviation, zip must be 5 digits.
- If parsing fails for any row, flag it in the validation summary (Enhancement #4).

**Implementation note:**

```python
import re

VALID_STATES = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
    'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
    'VA','WA','WV','WI','WY','DC'
}

def parse_city_state_zip(combined):
    """Parse 'City, ST  ZZZZZ' format."""
    match = re.match(r'^(.+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$', str(combined).strip())
    if not match:
        return None, None, None, 'Could not parse city/state/zip'
    city, state, zip_code = match.groups()
    if state not in VALID_STATES:
        return city, state, zip_code, f'Unrecognized state: {state}'
    return city.strip(), state, zip_code[:5], None  # error=None means OK
```

---

## Skill Location

Once implemented, this skill belongs at:

```
skills/insidedesk-facility-entry/SKILL.md
```

It should reference `_shared/` only if HubSpot or Slack are needed (they are not required for v1 of this skill). The bash tool (pandas) and Claude in Chrome are the only dependencies.

---

## Reference: Original Skill File (David's v1)

The following is the complete original `SKILL.md` as submitted, preserved here for reference during implementation.

---

```markdown
---
name: insidedesk-facility-entry
description: >
  Use this skill to bulk-enter facility/office records into the InsideDesk Operations Dashboard
  from a spreadsheet. Triggers when the user provides an InsideDesk URL and a spreadsheet
  (Excel/CSV) containing office/facility data to be entered into the system, or when they ask to
  "add facilities", "enter offices", "fill out the facility form", or "submit facilities to InsideDesk".
  Always use this skill when the user mentions an InsideDesk URL along with a spreadsheet of office data.
compatibility:
  tools:
    - Claude in Chrome (browser automation)
    - bash_tool (spreadsheet reading)
---

# InsideDesk Facility Entry Skill

Automates entering facility/office records into the InsideDesk admin panel from a spreadsheet,
one row at a time, with user confirmation before each submit.

---

## Step 0 — Read the Spreadsheet

Before connecting to the browser, read the spreadsheet data using pandas:

```python
import pandas as pd

df = pd.read_excel('file.xlsx', sheet_name='Sheet1', header=None)

# Print rows around row 22 to identify header and data start
for i in range(18, min(40, len(df))):
    print(f'Row {i+1}: {list(df.iloc[i])}')
```

- Data starts at **row 22** (index 21) by default unless the user specifies otherwise.
- The header row is typically row 19. Columns of interest:
  - Column B (index 1): **Office Name**
  - Column C (index 2): Claims Follow-up (Centralized/Decentralized)
  - Column D (index 3): Posting (Centralized/Decentralized)
  - Column E (index 4): **Tax ID**
  - Column F (index 5): **Address Line 1**
  - Column G (index 6): **City, State, Zipcode** (combined — parse apart)
  - Column H (index 7): **Phone**
  - Column I (index 8): **Practice Management Software (PMS)**
- Collect all rows starting at row 22 that have a non-null Office Name. Stop at the first row where Office Name is blank/null.
- Parse City/State/Zip from the combined field (e.g. "Scarsdale, NY  10583") → City: "Scarsdale", State: "NY", Zip: "10583"
- **Strip all dashes** from Phone and Tax ID values before entry.

---

## Step 1 — Connect to the Browser

Use `list_connected_browsers` to check if a browser is already connected. If not, call
`switch_browser` and ask the user to click Connect in their Chrome extension.

Once connected, call `tabs_context_mcp` (with `createIfEmpty: true`) to get a tab ID.

---

## Step 2 — Navigate to the URL

Navigate to the URL provided by the user. Wait for the page to fully load (use a `wait` + `screenshot`).

---

## Step 3 — Click the NEW Button

Look for the **NEW** button near the "Facilities" count in the top header area (not the `+ NEW`
button in the workflow states panel). It typically appears as a small button labeled **NEW** next
to a number like "8 Facilities".

Click it and wait for the **Facility / New** modal to open.

---

## Step 4 — Fill Out the Form

Fill in each field in order. Use `triple_click` then `type` to replace existing content in text fields.

### Info Section
| Field | Value | Notes |
|---|---|---|
| Name | Office Name | Text field |
| City | Parsed city | Text field |
| State | Parsed state abbreviation | **Dropdown** — click, scroll to find state, click it |
| Zipcode | Parsed zip | Text field |
| Phone | Phone number | **No dashes** |
| Address Line 1 | Street address | Text field |

### Configuration Section
| Field | Value | Notes |
|---|---|---|
| Expected Tax Ids | Tax ID | **No dashes** |
| Products | settings, iq, assist | **Multi-select** — click dropdown, check all three |

#### Products Multi-Select
- Click the Products dropdown to open it
- The dropdown shows checkboxes: `settings`, `iq`, `assist`, `inside_dial`, etc.
- `settings` is usually pre-checked — verify it
- Check `iq` and `assist` if not already checked
- Press Escape or click outside to close

### PMS Section
| Field | Value | Notes |
|---|---|---|
| PMS Type | Map from spreadsheet value | **Dropdown** — see mapping below |

#### PMS Type Mapping
| Spreadsheet Value | Select in Dropdown |
|---|---|
| Dentrix Ascend | `dentrix` (NOT ascend_api, unless user confirms otherwise) |
| Dentrix | `dentrix` |
| Eaglesoft | `eaglesoft` |
| Denticon | `denticon` |
| Open Dental | `opendental` |
| Dentrix Enterprise | `dentrix_enterprise` |
| Other | `other` |

> ⚠️ If `ascend_api` is selected, additional required fields (Organization ID, Ascend Location)
> will appear. Only select `ascend_api` if the user explicitly confirms and provides those values.

---

## Step 5 — Confirm with User Before Submitting

After filling all fields, take a screenshot to verify, then **stop and present a confirmation table**:

```
📋 Please confirm the following data before I click SUBMIT:

| Field              | Value                  |
|--------------------|------------------------|
| Name               | The Scarsdale Dentist  |
| City               | Scarsdale              |
| State              | NY                     |
| Zipcode            | 10583                  |
| Phone              | 9147250707             |
| Address Line 1     | 842 Post Rd            |
| Expected Tax IDs   | 392822453              |
| Products           | settings, iq, assist   |
| PMS Type           | dentrix                |

Please reply "confirm" to submit, or let me know any corrections.
```

**Do not click SUBMIT until the user explicitly confirms** (e.g., replies "confirm", "yes", "submit it").

If the user requests changes, make them in the browser, then re-present the updated summary and
wait for confirmation again.

---

## Step 6 — Submit

Once confirmed, click the **SUBMIT** button and wait for the success confirmation message
(e.g., "Facility successfully created!"). Take a screenshot to verify.

---

## Step 7 — Repeat or End

After successful submission:
- Move to the next row in the spreadsheet.
- If that row has a non-null Office Name → go back to **Step 3** (click NEW again) and repeat the process.
- If that row is blank/null → inform the user the process is complete.

```
✅ All rows processed. The facility entry workflow is complete.
```

---

## Error Handling

- **Dropdown not found**: Try scrolling the modal, or use the `find` tool to locate the element.
- **Required field validation error on submit**: Read the error, fix the field, re-confirm with user.
- **Page not loaded**: Wait longer and retry the screenshot.
- **ascend_api selected accidentally**: Go back to PMS Type dropdown and change to correct value.
- **Extra fields appear after PMS selection** (e.g., Organization ID for ascend_api): Ask the user if they have values for those fields. If not, consider switching to a different PMS type.

---

## Notes

- Always strip dashes from Phone and Tax ID before entering.
- The State field is a scrollable dropdown — scroll down within it to reach states like NY.
- The Products field is a multi-select with checkboxes — do not use the `type` action on it.
- Each new facility requires clicking the **NEW** button again from the main page — the modal
  does not reset automatically for a new entry.
```

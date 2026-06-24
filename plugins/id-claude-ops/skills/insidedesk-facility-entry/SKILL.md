---
name: insidedesk-facility-entry
description: >
  Use this skill to bulk-enter facility/office records into the InsideDesk Operations Dashboard
  from a spreadsheet. Triggers when the user provides an InsideDesk GoldenEye URL and a spreadsheet
  (Excel/CSV) containing office/facility data to be entered into the system, or when they ask to
  "add facilities", "enter offices", "fill out the facility form", or "submit facilities to InsideDesk".
  Always use this skill when the user mentions an InsideDesk GoldenEye URL along with a spreadsheet
  of office data.
compatibility:
  tools:
    - Claude in Chrome (browser automation)
    - bash_tool (spreadsheet reading)
---

# InsideDesk Facility Entry Skill v2

Automates bulk entry of facility/office records into the InsideDesk GoldenEye admin panel from
a spreadsheet. Parses and validates all rows upfront, collects a single batch confirmation from
the user, then runs the full entry loop unattended — pausing only on errors or duplicate warnings.

---

## Allowed Domains

Only the following GoldenEye environments are permitted. Reject any URL that does not match one
of these three base paths:

| Environment | Base URL |
|---|---|
| Production | `https://<GOLDENEYE_HOST>/production/` |
| Testing | `https://<GOLDENEYE_HOST>/testing/` |
| UAT / Staging | `https://<GOLDENEYE_HOST>/uat-staging/` |

---

## PMS Mapping

### Spreadsheet label → GoldenEye dropdown value

Match the spreadsheet PMS value case-insensitively against the label column.

| Spreadsheet label (case-insensitive) | GoldenEye dropdown value | Requires credentials? |
|---|---|---|
| open dental, opendental | `opendental` | No |
| dentrix, dentrix core | `dentrix` | No |
| eaglesoft, eagle soft | `eaglesoft` | No |
| softdent | `other` | No |
| denticon | `denticon` | **Yes** |
| dentrix enterprise | `dentrix_enterprise` | No |
| dentrix ascend, ascend, ascend_api | `ascend_api` | **Yes** |
| skysync denticon, skysync_denticon | `skysync_denticon` | **Yes** |
| skysync kolla, skysync_kolla | `skysync_kolla` | **Yes** |
| other | `other` | No |

If no label matches, set GoldenEye value to `other` and flag the row with `⚠️ PMS unrecognized`.

**Dynamic PMS types** (denticon, ascend_api, skysync_denticon, skysync_kolla) display
additional credential fields (username + password) in the GoldenEye form when selected.
Collect those credentials before the browser loop starts (see Step 0e).

### GoldenEye value → duplicate-name abbreviation

Used during duplicate detection to match shortened facility names:

| GoldenEye value | Abbreviation |
|---|---|
| opendental | OD |
| dentrix | DX |
| eaglesoft | ES |
| other | Legacy |
| dentrix_enterprise | DXE |
| ascend_api | ASC |
| denticon | DTC |
| skysync_denticon | SD |
| skysync_kolla | SK |

---

## Step 0 — Pre-flight: Parse & Validate Spreadsheet

Run all sub-steps before connecting to the browser.

### 0a — Read all rows

```python
import pandas as pd
import re

df = pd.read_excel('file.xlsx', sheet_name='Sheet1', header=None)

# Columns of interest (0-indexed):
# B=1  Office Name
# C=2  Claims Follow-up
# D=3  Posting
# E=4  Tax ID
# F=5  Address Line 1
# G=6  City, State, Zipcode (combined)
# H=7  Phone
# I=8  PMS

# Data starts at row 22 (index 21). Stop at first blank Office Name.
rows = []
for i in range(21, len(df)):
    name = df.iloc[i, 1]
    if pd.isna(name) or str(name).strip() == '':
        break
    rows.append({
        'row_num':   i + 1,
        'name':      str(name).strip(),
        'tax_id_raw': df.iloc[i, 4],
        'address':   df.iloc[i, 5],
        'csz_raw':   df.iloc[i, 6],
        'phone_raw': df.iloc[i, 7],
        'pms_raw':   df.iloc[i, 8],
    })
```

### 0b — URL domain validation

Before anything else, validate the URL the user provided:

```python
from urllib.parse import urlparse

ALLOWED_BASES = [
    'https://<GOLDENEYE_HOST>/production/',
    'https://<GOLDENEYE_HOST>/testing/',
    'https://<GOLDENEYE_HOST>/uat-staging/',
]

def validate_url(url):
    return any(url.startswith(base) for base in ALLOWED_BASES)
```

If validation fails, halt immediately and show:

```
⛔ URL validation failed.

The URL you provided is not a recognized GoldenEye environment:
  Provided: <url>

Allowed environments:
  Production  → https://<GOLDENEYE_HOST>/production/
  Testing     → https://<GOLDENEYE_HOST>/testing/
  UAT/Staging → https://<GOLDENEYE_HOST>/uat-staging/

Please check the URL and try again.
```

### 0c — Validate each row

For each row, parse and validate all fields. Collect a `flags` list per row.

```python
VALID_STATES = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
    'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
    'VA','WA','WV','WI','WY','DC'
}

def parse_csz(combined):
    """Parse 'City, ST  ZZZZZ' → (city, state, zip, error)"""
    match = re.match(r'^(.+),\s*([A-Za-z]{2})\s+(\d{5})(?:-\d{4})?$', str(combined).strip())
    if not match:
        return None, None, None, 'Cannot parse city/state/zip'
    city, state, zip5 = match.groups()
    state = state.upper()
    if state not in VALID_STATES:
        return city.strip(), state, zip5, f'Unrecognized state: {state}'
    return city.strip(), state, zip5, None

def clean_digits(raw):
    return re.sub(r'\D', '', str(raw)) if not pd.isna(raw) else ''

def validate_tin(raw):
    """Return (cleaned, flag_message_or_None)"""
    cleaned = clean_digits(raw)
    if not cleaned:
        return cleaned, 'Missing Tax ID'
    if len(cleaned) != 9:
        return cleaned, f'Unusual TIN length ({len(cleaned)} digits — expected 9)'
    if cleaned == '000000000':
        return cleaned, 'TIN is all zeros'
    return cleaned, None

def validate_phone(raw):
    """Return (cleaned, flag_message_or_None)"""
    cleaned = clean_digits(raw)
    if not cleaned:
        return cleaned, 'Missing phone'
    if len(cleaned) != 10:
        return cleaned, f'Unusual phone length ({len(cleaned)} digits — expected 10)'
    return cleaned, None
```

For each row, build the parsed dict:

```python
for row in rows:
    row['flags'] = []

    city, state, zip5, csz_err = parse_csz(row['csz_raw'])
    row.update({'city': city, 'state': state, 'zip': zip5})
    if csz_err:
        row['flags'].append(f'⚠️ {csz_err}')

    tax_id, tin_flag = validate_tin(row['tax_id_raw'])
    row['tax_id'] = tax_id
    if tin_flag:
        row['flags'].append(f'⚠️ TIN: {tin_flag}')  # warn only — do not block

    phone, phone_flag = validate_phone(row['phone_raw'])
    row['phone'] = phone
    if phone_flag:
        row['flags'].append(f'⚠️ Phone: {phone_flag}')

    row['address'] = str(row['address']).strip() if not pd.isna(row['address']) else ''
    if not row['address']:
        row['flags'].append('⚠️ Missing address')
```

### 0d — Resolve PMS for each row

```python
PMS_MAP = {
    'open dental':        'opendental',
    'opendental':         'opendental',
    'dentrix':            'dentrix',
    'dentrix core':       'dentrix',
    'eaglesoft':          'eaglesoft',
    'eagle soft':         'eaglesoft',
    'softdent':           'other',
    'denticon':           'denticon',
    'dentrix enterprise': 'dentrix_enterprise',
    'dentrix ascend':     'ascend_api',
    'ascend':             'ascend_api',
    'ascend_api':         'ascend_api',
    'skysync denticon':   'skysync_denticon',
    'skysync_denticon':   'skysync_denticon',
    'skysync kolla':      'skysync_kolla',
    'skysync_kolla':      'skysync_kolla',
    'other':              'other',
}

DYNAMIC_PMS = {'denticon', 'ascend_api', 'skysync_denticon', 'skysync_kolla'}

for row in rows:
    raw_pms = str(row['pms_raw']).strip().lower() if not pd.isna(row['pms_raw']) else ''
    resolved = PMS_MAP.get(raw_pms)
    if resolved:
        row['pms'] = resolved
    else:
        row['pms'] = 'other'
        row['flags'].append(f'⚠️ PMS unrecognized: "{row["pms_raw"]}" → defaulted to other')
    row['pms_needs_creds'] = row['pms'] in DYNAMIC_PMS
```

### 0e — Collect credentials for dynamic PMS types

After resolving all rows, identify which dynamic PMS types appear in the batch:

```python
dynamic_needed = {row['pms'] for row in rows if row['pms_needs_creds']}
```

For each type in `dynamic_needed`, ask the user before proceeding:

```
🔐 Credentials required for [pms_type] entries in this batch.
Please provide the username and password that GoldenEye uses for [pms_type].
These will be used during form entry and will not be logged.

Username: ___
Password: ___
```

Store credentials in memory keyed by PMS type for use during the form loop. Do not write them to the audit log or any file.

### 0f — Dry-run check

If the user said "dry run" or "just preview", skip all browser steps. Show the preview table
(Step 1) and end with:

```
✅ Dry run complete — no records were submitted. Fix any flagged rows and re-run with the URL to begin entry.
```

---

## Step 1 — Preview Table & Batch Confirm

Display all rows in a single table. Show flags in the Status column. Include the environment
inferred from the URL.

```
📋 Facility Entry Preview — [N] records — Environment: [Production / Testing / UAT-Staging]

| #  | Name                 | City      | ST | Zip   | Phone      | Tax ID    | PMS              | Status            |
|----|--------------------- |-----------|----|-------|------------|-----------|------------------|-------------------|
|  1 | Miami Dental Group   | Miami     | FL | 33101 | 3051234567 | 123456789 | dentrix          | ✅ OK             |
|  2 | Scarsdale Dentist    | Scarsdale | NY | 10583 | 9147250707 | 392822453 | dentrix          | ✅ OK             |
|  3 | Apex Smiles          | Austin    | TX | 78701 | 5125551234 | 00471234  | eaglesoft        | ⚠️ TIN: 8 digits  |
|  4 | Kolla Test Clinic    | Denver    | CO | 80201 | 7205559876 | 981234567 | skysync_kolla    | ✅ OK (creds set) |

Flagged rows will still be submitted — warnings are logged only.
Reply "confirm" to begin entry, or "cancel" to abort.
```

**Do not touch the browser until the user replies "confirm".** On "cancel", end the skill.

---

## Step 2 — Connect to Browser

Use `list_connected_browsers` to check if a browser is connected. If not, call `switch_browser`
and prompt the user to click Connect in their Chrome extension. Once connected, call
`tabs_context_mcp` (with `createIfEmpty: true`) to get a tab ID.

---

## Step 3 — Navigate to URL

Navigate to the validated URL. Wait for the page to fully load (`wait` + `screenshot`).

Set up the local log folder:

```
~/insidedesk-logs/facility-entry/YYYY-MM-DD/
  facility-entry-YYYY-MM-DD.csv       ← audit log
  receipts/                           ← screenshot receipts
    01_facility-name-slug.png
    02_facility-name-slug.png
    ...
```

Create these directories if they don't exist. Initialize the CSV with headers:
`timestamp, row_num, facility_name, city, state, zip, phone, tax_id, pms, status, flags, notes`

---

## Step 4 — Facility Entry Loop

Run for each row in order. Pause only on error or duplicate warning.

### 4a — Progress counter

Begin every action and every status message with:

```
📍 Record [N] of [TOTAL] — [Facility Name]
```

### 4b — Duplicate detection

Before clicking NEW, use `get_page_text` or `find` to search the current facilities list for the
facility name (case-insensitive exact match). Also check for the name + PMS abbreviation pattern
(e.g. "Scarsdale Dentist - DX") which GoldenEye uses for renamed duplicates.

If a match is found, pause and show:

```
📍 Record [N] of [TOTAL] — [Facility Name]
⚠️ Possible duplicate detected — a facility matching "[name]" already appears in the list.

Reply "skip" to skip this record, or "proceed" to enter it anyway.
```

Wait for user response before continuing.

### 4c — Click NEW

Look for the **NEW** button near the "Facilities" count in the top header (not the `+ NEW`
button in the workflow states panel). It typically appears as a small button labeled **NEW**
next to a count like "8 Facilities".

**Avoid re-navigating between records.** After each successful submission, attempt to click NEW
from the current page state. Only reload the full URL if the NEW button cannot be located within
2 screenshot attempts.

Click NEW and wait for the **Facility / New** modal to open.

### 4d — Fill the form

Fill each field in order. Use `triple_click` then `type` to replace text fields.

#### Info Section
| Field | Value | Input type |
|---|---|---|
| Name | Office Name | Text |
| City | Parsed city | Text |
| State | Parsed state abbreviation | Dropdown — scroll to state, click |
| Zipcode | Parsed zip (5 digits) | Text |
| Phone | Cleaned phone (10 digits, no dashes) | Text |
| Address Line 1 | Street address | Text |

#### Configuration Section
| Field | Value | Input type |
|---|---|---|
| Expected Tax Ids | Cleaned tax ID (no dashes) | Text |
| Products | settings, iq, assist | Multi-select — click dropdown, check each |

**Products multi-select:**
- Click the Products dropdown
- `settings` is usually pre-checked — verify it
- Check `iq` and `assist` if not already checked
- Press Escape or click outside to close

#### PMS Section
| Field | Value | Input type |
|---|---|---|
| PMS Type | Resolved GoldenEye value from PMS map | Dropdown |

After selecting PMS type, check if additional fields appear:

- **ascend_api**: additional fields for Organization ID and Ascend Location will appear
- **denticon**: username + password fields will appear
- **skysync_denticon / skysync_kolla**: username + password fields will appear

For dynamic PMS rows, fill the credential fields with the values collected in Step 0e.
Do not log credentials.

### 4e — Submit

Click the **SUBMIT** button. Wait for the success confirmation message
(e.g. "Facility successfully created!"). Take a screenshot.

If a field validation error appears instead, read the error message, correct the field, and
retry the submit once. If it fails again, log the row as `FAILED`, take a screenshot, and move
to the next record.

### 4f — Screenshot receipt

Save the post-submit screenshot to:
```
~/insidedesk-logs/facility-entry/YYYY-MM-DD/receipts/[NN]_[name-slug].png
```

Where `NN` is the zero-padded row number and `name-slug` is the facility name lowercased with
spaces replaced by hyphens and special characters removed.

### 4g — Write audit log row

Append one row to the CSV:

| Field | Value |
|---|---|
| timestamp | ISO 8601 UTC |
| row_num | Spreadsheet row number |
| facility_name | Office Name |
| city / state / zip / phone | Parsed values |
| tax_id | Cleaned value (no dashes) |
| pms | GoldenEye dropdown value used |
| status | `SUCCESS`, `SKIPPED`, or `FAILED` |
| flags | Pipe-separated list of ⚠️ flags from validation (if any) |
| notes | Any error message or skip reason |

TIN flags from Step 0c are written to the `flags` column for every affected row, regardless of
outcome. They are informational only and do not affect submission.

---

## Step 5 — Complete

After all rows are processed, print the final summary:

```
✅ Facility entry complete — [N] of [TOTAL] submitted successfully.

  ✅ Submitted: N
  ⏭️  Skipped:   N
  ❌ Failed:    N

Audit log: ~/insidedesk-logs/facility-entry/YYYY-MM-DD/facility-entry-YYYY-MM-DD.csv
Receipts:  ~/insidedesk-logs/facility-entry/YYYY-MM-DD/receipts/
```

---

## Error Handling

| Error | Action |
|---|---|
| URL not in allowed list | Halt before any browser connection; show domain list |
| Dropdown not found | Scroll modal; use `find` to locate element; retry once |
| State dropdown won't scroll to target | Take screenshot, report state value, ask user to select manually |
| PMS extra fields appear unexpectedly | Halt, show screenshot, ask user for field values |
| Submit validation error | Read error, fix field, retry once; log FAILED if still fails |
| Modal fails to open | Close any open modal, take screenshot, retry NEW click once; skip if still fails |
| Duplicate confirmed by user as "proceed" | Enter the record and note "user confirmed duplicate" in audit log |
| Browser disconnects mid-loop | Halt, report last successful row number, ask user to reconnect |

---

## Notes

- Always use `triple_click` + `type` for text fields to clear existing content first.
- The State field is a scrollable dropdown — scroll within it to reach the target state.
- The Products field is a multi-select with checkboxes — do not use `type` on it.
- Credentials for dynamic PMS types are held in memory only; never written to log files.
- TIN warnings are informational — InsideDesk intentionally stores non-standard TINs as a
  workaround for 422 claim ingestion errors. Always submit the value from the spreadsheet.
- The spreadsheet layout (row 22 data start, columns B–I) is fixed for the current template.
  If a different layout is needed, the user will say so at the start.

---

## Step 6 — Log the run

After Step 5, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `insidedesk-facility-entry` |
| `status` | `success` if all rows were processed without failures · `partial` if any rows failed or were skipped · `error` if the skill failed entirely (e.g. URL validation failed, browser disconnected) |
| `summary` | 1–3 sentences: total rows attempted, number successfully submitted, number skipped (duplicates), and number failed. |
| `inputs` | `spreadsheet_file={filename}` · `goldeneye_url={url}` · `total_rows={N}` |
| `outputs` | `submitted={N}` · `skipped={N}` · `failed={N}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `environment={Production/Testing/UAT-Staging}` · `dynamic_pms_types={list or "none"}` |

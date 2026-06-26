---
name: mb2-monday-to-ge
description: >
  Read the MB2 Monday Board "To Be Installed" group via Chrome and create GoldenEye facility
  records for any office not yet in GoldenEye. Called automatically as the second step in the
  MB2 install ticket scheduled scan, or manually by Sean. In unattended mode, auto-skips
  facilities already in GoldenEye without pausing. Always uses the Production GoldenEye
  environment. Trigger when Sean says "enter MB2 Monday offices into GoldenEye", "run the
  MB2 facility entry", or when the scheduled install ticket scan invokes it.
compatibility:
  tools:
    - Claude in Chrome (browser automation)
    - Desktop Commander (Python, Slack)
---

# Skill: MB2 Monday Board → GoldenEye Facility Entry

Reads the MB2 "To Be Installed" group from their Monday Board via Chrome, parses each row
into validated facility data, and creates GoldenEye records for any office not already
present. In unattended (scheduled) mode, duplicates are auto-skipped and a Slack summary
is sent on completion.

---

## Key Constants

| Item | Value |
|---|---|
| Monday Board URL | `https://mb2dental-team.monday.com/boards/1911559021` |
| GoldenEye environment | Production — `https://<GOLDENEYE_HOST>/production/` |
| Monday group to read | `To Be Installed` |
| Permanent exclusion | Any row whose name contains `Smile Lodge Pediatric` (case-insensitive) |
| Slack summary channel | `<SLACK_DM_SEAN>` |

---

## Step 0 — Determine Mode

The skill runs in one of two modes based on how it was invoked:

| Mode | Trigger | Behavior |
|---|---|---|
| **Unattended** | Scheduled scan, or caller says "unattended run" | Auto-skip duplicates; no preview confirmation; Slack summary on completion |
| **Manual** | Sean invokes directly in chat | Show preview table; require "confirm" before entry; pause on duplicates |

If invoked from the scheduled `mb2-install-ticket` scan, treat as **unattended**.
If invoked by Sean in chat with no explicit mode, treat as **manual**.

---

## Step 1 — Retrieve Slack Token

Run the `id-claude-shared:get-secret` skill with name `slack-bot-token`.
Store the token in memory for the Slack summary in Step 8.

---

## Step 2 — Connect to Chrome and Navigate to Monday Board

Use `list_connected_browsers` to check for a connected browser. If none, call `switch_browser`
and prompt Sean to click Connect in the Chrome extension. Once connected, call
`tabs_context_mcp` with `createIfEmpty: true` to get a tab ID.

Navigate to:
```
https://mb2dental-team.monday.com/boards/1911559021
```

Wait for the board to fully load (`wait` 3s + `screenshot`). If the page redirects to a login
screen, halt and report: "Monday Board requires login — please ensure you are logged in to
mb2dental-team.monday.com in Chrome."

---

## Step 3 — Extract "To Be Installed" Rows

### 3a — Locate the group

Use `get_page_text` to read the full board text. Search for the heading **"To Be Installed"**.
If not visible, scroll down until it appears.

Monday renders groups as collapsible sections. If the group is collapsed (no rows visible below
the heading), click the group header to expand it, then wait 1s and re-read.

### 3b — Identify column positions

Monday Board renders column headers in a sticky header row at the top of the board. Before
reading any rows, confirm the position (left-to-right order) of these columns by reading the
header row:

| Column name in Monday | Field to extract |
|---|---|
| Name | `name` |
| Full/Reporting | `access_type` (`Full Access` or `Reporting Only`) |
| PMS | `pms_raw` |
| Address | `address` |
| City | `city` |
| State/Zip | `state_zip_raw` |
| Tax ID | `tax_id_raw` |
| Phone Number | `phone_raw` |

**Never read or record:** Facility ID, Credential, Subitems, Date of Install, Termination Date,
Clearing House, Entity, Office NPI, Office Email, Server with Data, ID REP, MB2 Rep,
Initial Claim Count, Synching Time, Setup Complete, MB2 Priority Order, Installer Link,
Last OK Data Feed Date. These are internal MB2 fields.

### 3c — Read each row

For each row in the "To Be Installed" group, extract the values for the eight fields above.
If Monday uses virtual scrolling and not all rows are loaded, scroll down within the group
until no new rows appear.

**After extracting all rows visible, also try using `javascript_tool` to ensure completeness:**

```javascript
// Extract all item rows from the "To Be Installed" group
// Monday renders group headers with aria-label or text matching the group name
// Return array of {name, access_type, pms, address, city, state_zip, tax_id, phone}
const rows = [];
const allCells = document.querySelectorAll('[data-testid="table-body-row"]');
// Iterate and read cell text by column index — adapt if testid differs
allCells.forEach(row => {
  const cells = row.querySelectorAll('[data-testid="table-body-cell"]');
  if (cells.length > 0) {
    rows.push(Array.from(cells).map(c => c.innerText.trim()));
  }
});
JSON.stringify(rows);
```

Use whichever extraction method (page text parse or JS) produces the more complete and
structured result. If both return rows, prefer the JS result.

### 3d — Apply permanent exclusion

Remove any row where `name` (case-insensitive) contains `smile lodge pediatric`.
These are permanently excluded and should never be submitted to GoldenEye.
Log: `Excluded (permanent): [name]`

---

## Step 4 — Parse and Validate Rows

Run this parsing in Desktop Commander (Python) after extracting raw row data. Write the
rows to a temp JSON file and read it back for processing, or build the validated list
in-memory via a Python script.

### 4a — PMS mapping

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

PMS_ABBREV = {
    'opendental': 'OD', 'dentrix': 'DX', 'eaglesoft': 'ES',
    'other': 'Legacy', 'dentrix_enterprise': 'DXE',
    'ascend_api': 'ASC', 'denticon': 'DTC',
    'skysync_denticon': 'SD', 'skysync_kolla': 'SK',
}
```

### 4b — Products from access type

```python
def resolve_products(access_type):
    """Full Access → settings+iq+assist. Reporting Only → settings+iq."""
    normalized = str(access_type).strip().lower()
    if 'reporting' in normalized:
        return ['settings', 'iq']       # NO assist for Reporting Only
    return ['settings', 'iq', 'assist'] # Full Access default
```

### 4c — State/Zip parser (Monday format: "IL, 60073")

```python
import re

VALID_STATES = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
    'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
    'VA','WA','WV','WI','WY','DC'
}

def parse_state_zip(raw):
    """Parse 'IL, 60073' or 'IL 60073' → (state, zip, error_or_None)"""
    match = re.match(r'^([A-Za-z]{2})[,\s]+(\d{5})(?:-\d{4})?$', str(raw).strip())
    if not match:
        return None, None, f'Cannot parse state/zip: "{raw}"'
    state, zip5 = match.groups()
    state = state.upper()
    if state not in VALID_STATES:
        return state, zip5, f'Unrecognized state: {state}'
    return state, zip5, None
```

### 4d — Phone parser (Monday format: "Phone: 847-740-0217")

```python
def parse_phone(raw):
    """Strip 'Phone: ' prefix and non-digits → 10-digit string."""
    if not raw or str(raw).strip() in ('', 'nan'):
        return '', 'Missing phone'
    cleaned = re.sub(r'\D', '', str(raw))
    if not cleaned:
        return '', 'Missing phone'
    if len(cleaned) != 10:
        return cleaned, f'Unusual phone length ({len(cleaned)} digits — expected 10)'
    return cleaned, None
```

### 4e — Tax ID parser

```python
def parse_tax_id(raw):
    """Strip dashes and non-digits. Warn if not 9 digits or all zeros."""
    if not raw or str(raw).strip() in ('', 'nan'):
        return '', 'Missing Tax ID'
    cleaned = re.sub(r'\D', '', str(raw))
    if not cleaned:
        return '', 'Missing Tax ID'
    if len(cleaned) != 9:
        return cleaned, f'Unusual TIN length ({len(cleaned)} digits — expected 9)'
    if cleaned == '000000000':
        return cleaned, 'TIN is all zeros'
    return cleaned, None
```

### 4f — Build validated row list

For each extracted row, apply all parsers and collect flags:

```python
for row in raw_rows:
    flags = []

    state, zip5, sz_err = parse_state_zip(row['state_zip_raw'])
    if sz_err: flags.append(f'⚠️ {sz_err}')

    phone, ph_err = parse_phone(row['phone_raw'])
    if ph_err: flags.append(f'⚠️ Phone: {ph_err}')

    tax_id, tin_err = parse_tax_id(row['tax_id_raw'])
    if tin_err: flags.append(f'⚠️ TIN: {tin_err}')

    address = str(row['address']).strip() if row['address'] else ''
    if not address: flags.append('⚠️ Missing address')

    pms_key = str(row['pms_raw']).strip().lower() if row['pms_raw'] else ''
    pms = PMS_MAP.get(pms_key, 'other')
    if pms_key and pms_key not in PMS_MAP:
        flags.append(f'⚠️ PMS unrecognized: "{row["pms_raw"]}" → defaulted to other')

    products = resolve_products(row['access_type'])

    validated_rows.append({
        'name':     row['name'].strip(),
        'city':     row['city'].strip() if row['city'] else '',
        'state':    state,
        'zip':      zip5,
        'phone':    phone,
        'address':  address,
        'tax_id':   tax_id,
        'pms':      pms,
        'pms_abbrev': PMS_ABBREV.get(pms, '?'),
        'pms_needs_creds': pms in DYNAMIC_PMS,
        'products': products,
        'access_type': row['access_type'],
        'flags':    flags,
    })
```

---

## Step 5 — Handle Dynamic PMS Credentials

After parsing all rows, check if any require credentials:

```python
dynamic_needed = {r['pms'] for r in validated_rows if r['pms_needs_creds']}
```

**Manual mode:** For each PMS type in `dynamic_needed`, ask Sean before proceeding:
```
🔐 Credentials required for [pms_type] entries in this batch.
Please provide the GoldenEye username and password for [pms_type].

Username: ___
Password: ___
```

**Unattended mode:** If any dynamic PMS rows are present, do NOT proceed with those rows.
Log them as `SKIPPED (dynamic PMS — credentials required for unattended run)` and post
to Slack:
```
⚠️ mb2-monday-to-ge: [N] row(s) skipped — dynamic PMS ([pms_types]) requires credentials
and cannot be entered in unattended mode. Review in chat.
```
Continue the run for the remaining non-dynamic rows.

Credentials are held in memory only. Never write them to the audit log or any file.

---

## Step 6 — Preview and Confirm (Manual Mode Only)

**Skip this step in unattended mode — proceed directly to Step 7.**

Display the validated rows:

```
📋 MB2 Monday → GoldenEye Preview — [N] records — Production

| #  | Name                       | City        | ST | Zip   | Phone      | Tax ID    | PMS       | Products           | Status          |
|----|----------------------------|-------------|----|-------|------------|-----------|-----------|--------------------|-----------------|
|  1 | Round Lake Family Dentistry| Round Lake  | IL | 60073 | 8477400217 | 273160146 | eaglesoft | settings, iq, assist | ✅ OK          |
|  2 | Parkway Dental Center      | Dallas      | TX | 75201 | 2145559999 | 123456789 | dentrix   | settings, iq       | ✅ OK (Reporting)|

Flagged rows will still be submitted — warnings are logged only.
Reply "confirm" to begin entry, or "cancel" to abort.
```

Do not touch GoldenEye until Sean replies "confirm". On "cancel", end the skill.

---

## Step 7 — Navigate to GoldenEye

Navigate to:
```
https://<GOLDENEYE_HOST>/production/
```

Wait for the page to fully load (`wait` + `screenshot`). Set up the audit log:

```
~/insidedesk-logs/mb2-monday-to-ge/YYYY-MM-DD/
  mb2-monday-to-ge-YYYY-MM-DD.csv     ← audit log
  receipts/                           ← screenshot receipts
    01_office-name-slug.png
    ...
```

Initialize the CSV with headers:
`timestamp, row_num, facility_name, city, state, zip, phone, tax_id, pms, products, access_type, status, flags, notes`

---

## Step 8 — Facility Entry Loop

Run for each validated row in order.

### 8a — Progress counter

Begin every status message with:
```
📍 Record [N] of [TOTAL] — [Facility Name]
```

### 8b — Duplicate detection

Before clicking NEW, use `get_page_text` or `find` to search the GoldenEye facilities list
for the facility name (case-insensitive). Also check for the `[name] - [PMS_ABBREV]` pattern
that GoldenEye uses for renamed duplicates.

**Manual mode:** If a match is found, pause:
```
📍 Record [N] of [TOTAL] — [Facility Name]
⚠️ Possible duplicate — "[name]" already appears in GoldenEye.
Reply "skip" to skip, or "proceed" to enter anyway.
```

**Unattended mode:** If a match is found, auto-skip:
Log `SKIPPED (already in GoldenEye)` and move to next row. No pause.

### 8c — Click NEW

Look for the **NEW** button near the "Facilities" count in the top header (not the `+ NEW`
workflow states button). Click it and wait for the **Facility / New** modal to open.

Avoid re-navigating between records. After each successful submission, click NEW from the
current page state. Only reload the full GoldenEye URL if NEW cannot be located within
2 screenshot attempts.

### 8d — Fill the form

Use `triple_click` then `type` for all text fields.

#### Info Section
| Field | Value |
|---|---|
| Name | `row['name']` |
| City | `row['city']` |
| State | `row['state']` — scrollable dropdown |
| Zipcode | `row['zip']` — 5 digits |
| Phone | `row['phone']` — 10 digits, no formatting |
| Address Line 1 | `row['address']` |

#### Configuration Section
| Field | Value |
|---|---|
| Expected Tax Ids | `row['tax_id']` — no dashes |
| Products | `row['products']` — multi-select checkboxes |

**Products multi-select:**
- Click the Products dropdown
- `settings` is usually pre-checked — verify
- Check each product in `row['products']`; uncheck any that should NOT be present
- For Reporting Only rows: `assist` must **not** be checked
- For Full Access rows: `settings`, `iq`, and `assist` must all be checked
- Press Escape or click outside to close

#### PMS Section
| Field | Value |
|---|---|
| PMS Type | `row['pms']` — GoldenEye dropdown value |

For dynamic PMS rows (credentials collected in Step 5), fill the credential fields that
appear after PMS type selection. Do not log credentials.

### 8e — Submit

Click **SUBMIT**. Wait for success confirmation (e.g. "Facility successfully created!").
Take a screenshot.

If a validation error appears: read the error, correct the field, retry once. If it fails
again, log `FAILED`, take a screenshot, and move to the next record.

### 8f — Screenshot receipt

```
~/insidedesk-logs/mb2-monday-to-ge/YYYY-MM-DD/receipts/[NN]_[name-slug].png
```

`name-slug` = name lowercased, spaces → hyphens, special characters removed.

### 8g — Write audit log row

| Field | Value |
|---|---|
| timestamp | ISO 8601 UTC |
| row_num | Sequential row number from Monday Board |
| facility_name | Name |
| city / state / zip / phone | Parsed values |
| tax_id | Cleaned (no dashes) |
| pms | GoldenEye dropdown value used |
| products | Comma-separated list |
| access_type | `Full Access` or `Reporting Only` |
| status | `SUCCESS`, `SKIPPED`, or `FAILED` |
| flags | Pipe-separated ⚠️ flags |
| notes | Error message, skip reason, or blank |

---

## Step 9 — Summary and Slack Notification

After all rows are processed, print the summary:

```
✅ MB2 Monday → GoldenEye complete — [N] of [TOTAL] submitted.

  ✅ Submitted:  N
  ⏭️  Skipped:   N  (already in GoldenEye or dynamic PMS)
  ❌ Failed:     N

Audit log: ~/insidedesk-logs/mb2-monday-to-ge/YYYY-MM-DD/mb2-monday-to-ge-YYYY-MM-DD.csv
```

Post to Slack channel `<SLACK_DM_SEAN>` via Desktop Commander:

```python
import requests

token = "<slack-bot-token>"
channel = "<SLACK_DM_SEAN>"

if submitted == 0 and failed == 0:
    # Silent — nothing new to report in unattended mode
    pass
else:
    lines = [f":office: *MB2 Monday → GoldenEye*"]
    if submitted:
        lines.append(f"✅ *{submitted} new facilit{'y' if submitted == 1 else 'ies'} created:*")
        for r in submitted_rows:
            lines.append(f"  • {r['name']} ({r['pms']}, {r['access_type']})")
    if skipped_already_ge:
        lines.append(f"⏭️ {skipped_already_ge} already in GoldenEye — skipped")
    if skipped_creds:
        lines.append(f"⚠️ {skipped_creds} skipped — dynamic PMS requires credentials (review manually)")
    if failed:
        lines.append(f"❌ {failed} failed — check audit log")

    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"channel": channel, "text": "\n".join(lines), "mrkdwn": True}
    )
    if not resp.json().get("ok"):
        print(f"Slack notification failed: {resp.json().get('error')}")
```

If nothing was submitted and nothing failed (all skipped as already in GoldenEye), stay
silent — do not send a Slack message. This is the expected steady-state after the first
bulk entry.

---

## Scheduled Task Integration

This skill runs as the **second step** in the MB2 install ticket scheduled scan. The
scheduled task prompt should read:

```
1. Run the `id-claude-ops:mb2-install-ticket` skill and follow all its instructions exactly.
   This is a scheduled/unattended run — do not ask for confirmation before processing.

2. After mb2-install-ticket completes (whether or not new tickets were created), run the
   `id-claude-ops:mb2-monday-to-ge` skill in unattended mode. Do not ask for confirmation
   before entering facilities — auto-skip any already in GoldenEye.
```

The two skills are independent — mb2-monday-to-ge always runs regardless of whether
mb2-install-ticket created any tickets. This ensures the GoldenEye facility list stays
in sync even if tickets were created in a prior run.

---

## Error Handling

| Error | Action |
|---|---|
| Monday Board requires login | Halt; report "Login required — please ensure Chrome is logged in to mb2dental-team.monday.com" |
| "To Be Installed" group not found | Scroll down, try again; if still missing, halt and report |
| Group collapsed / no rows visible | Click group header to expand; wait 1s; retry |
| Row missing required field (name, city, address) | Flag row as `⚠️ Missing [field]`; still attempt entry unless name is blank |
| Name is blank | Skip row entirely; log `SKIPPED (blank name)` |
| State/Zip cannot be parsed | Flag; in manual mode pause for correction; in unattended mode skip and report in Slack |
| Dynamic PMS in unattended mode | Skip those rows; report in Slack summary (see Step 5) |
| GoldenEye dropdown not found | Scroll modal; use `find`; retry once |
| State dropdown won't scroll | Screenshot; report state value; ask user to select manually (both modes) |
| Submit validation error | Read error, fix field, retry once; log FAILED if still fails |
| Modal fails to open | Close any open modal; screenshot; retry NEW click once; skip if still fails |
| Browser disconnects mid-loop | Halt; report last successful row number; ask user to reconnect |

---

## Notes

- Always use `triple_click` + `type` for text fields to clear existing content first.
- The State field is a scrollable dropdown — scroll within it to reach the target state.
- The Products field is a multi-select with checkboxes — **verify the final checked state
  matches `row['products']` before submitting**. Getting Products wrong (assist present
  on Reporting Only, or absent on Full Access) is a silent data error.
- TIN warnings are informational only — InsideDesk intentionally stores non-standard TINs.
  Always submit the value from the Monday Board.
- Never read, record, or use the Facility ID column (MB2 internal ID) or Credential column.
- Monday Board columns may scroll horizontally. If a needed column is off-screen, scroll
  right within the board header to locate it.

---

## Step 10 — Close browser tabs

Before logging, close any Monday Board and GoldenEye tabs that were opened during Steps 3-9 using the **`chrome-cleanup`** helper skill.
Pass the `tabId` from your browser navigation responses.

---

## Step 11 — Log the run

After Step 10, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `mb2-monday-to-ge` |
| `status` | `success` if all rows were processed · `partial` if any rows failed or were skipped due to dynamic PMS in unattended mode · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: total rows read from Monday Board, number of GoldenEye facilities created, number skipped (already in GoldenEye), and number failed. |
| `inputs` | `monday_board=To Be Installed` · `mode={manual/unattended}` · `total_rows={N}` |
| `outputs` | `submitted={N}` · `skipped={N}` · `failed={N}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `dynamic_pms_skipped={N}` |

---
name: cancellation-ticket
description: Create HubSpot CANCELLATIONS custom object records from Monday Board cancellation-mention emails. Reads Gmail for the last 7 days, identifies cancellation requests (mentions that contain "cancel" and lack a Vendor: line), looks up the location and company in HubSpot, and creates a Cancellation record with full associations. Use whenever Sean says "process cancellations", "create cancellation tickets", "check cancellation emails", or similar.
---

# Skill: Cancellation Ticket Creator

Automates creating HubSpot CANCELLATIONS records for locations requesting to cancel InsideDesk services.
The source of truth is Gmail — Monday Board sends a notification when a team member @mentions Sean
on a cancellation-related update.

---

## Prerequisites

Run the `get-secret` skill with name `hubspot-token` to retrieve the HubSpot API token.
See `id-claude-shared` plugin: `skills/_shared/hubspot-setup.md` — Steps B (aws-login) and C (token retrieval) are handled by the `get-secret` skill.

Run the `get-secret` skill with name `slack-bot-token` to retrieve the Slack bot token.
See `id-claude-shared` plugin: `skills/_shared/slack-setup.md` — Section A (token retrieval) is handled by the `get-secret` skill.

⚠️ **ALL HubSpot operations in this skill use the HubSpot REST API directly via Desktop Commander
(`mcp__Desktop_Commander__start_process`), NOT the HubSpot MCP connector.** The MCP connector does
not support custom objects. Use the token retrieved via `get-secret` for all API calls.

---

## Key constants

| Item | Value |
|---|---|
| CANCELLATIONS object type | `2-33013991` |
| Cancellations pipeline ID | `127090059` |
| Opening stage (CS Investigation) | `222298644` |
| Locations object type | `2-14718097` |
| Assigned owner (Sean Johnson) | `628638356` |
| Plugin Slack channel | `<SLACK_DM_SEAN>` |
| Bitwerx PMS types | `eaglesoft`, `dentrix`, `dentrix_enterprise` |

### CANCELLATIONS record fields

| Field | Value / Notes |
|---|---|
| `cancellation_name` | Location name |
| `cancellation_reason` | Enum — see Step 3 |
| `date_requested` | Today's date (when we create the record) |
| `termination_date` | Date the office wants service turned off — parsed from email |
| `cancellation_state` | `Immediate` if "immediately" / same-day, else `Pending` |
| `type_of_cancellation` | `Partial Cancellation (Some Locations, Not All)` for single-location; `No Location Cancellation` for PMS swaps |
| `hs_pipeline` | `127090059` |
| `hs_pipeline_stage` | `222298644` (CS Investigation) |
| `hubspot_owner_id` | `628638356` |

### Association type IDs (for direct API calls)

| Association | ID |
|---|---|
| Cancellation → Company (0-2) | `174` |
| Cancellation → Location (2-14718097) | `170` |
| Note → Cancellation (2-33013991) | `167` (USER_DEFINED — batch endpoint only) |

---

## Step 1 — Find cancellation emails in Gmail

Search Gmail for Monday Board mention emails from the last 7 days:

```
from:notifications@monday.com subject:"[New mention]" -subject:"Re:" newer_than:7d
```

Use `search_threads` with that query. For each result, fetch the full thread
(`get_thread` with `messageFormat: FULL_CONTENT`) and apply **both** filters:

1. **Must contain** the word `cancel` (case-insensitive) anywhere in the `plaintextBody`
2. **Must NOT contain** a line starting with `Vendor:` — emails with `Vendor:` are
   install approvals, not cancellations, and must be skipped silently.

If no qualifying emails are found, report: "No new cancellation requests found in Gmail
for the last 7 days."

---

## Step 2 — Parse each email

The `plaintextBody` follows this general structure:

```
[Sender] mentioned you in an update on [Location Name]:

@[Person1] @[Person2] [Free-text cancellation reason/message]

View update on the pulse [Monday URL]
```

Extract these fields using Python string parsing (split on newlines, strip whitespace
and zero-width chars, ​, &nbsp;):

| Field | How to extract |
|---|---|
| `location_name` | First line of body: `"...update on [Location Name]:"` — strip the trailing colon |
| `reason_text` | All lines between the @mentions block and the "View update" line, joined |
| `requested_by` | Sender name before "mentioned you" on the first line |
| `monday_url` | Line containing `https://` and `monday.com/` |

### Step 2b — Extract termination date

Parse `reason_text` (and the full body) for a termination date. Check patterns in order:

1. **"immediately"** or **"right away"** or **"ASAP"** or **"today"** → `termination_date = today`, `cancellation_state = "Immediate"`
2. **"effective [date]"**, **"as of [date]"**, **"starting [date]"** → extract the date
3. **"on [date]"**, **"by [date]"**, **"turn off on [date]"**, **"cancel on [date]"** → extract the date
4. Any standalone date string (e.g. `06/01/2026`, `June 1`, `1st of June`) near cancel language → extract
5. **No date found** → `termination_date = None`, `cancellation_state = "Pending"`, flag in report

Use Python `dateutil.parser.parse()` for flexible date extraction. Format the result as `YYYY-MM-DD` for HubSpot.

```python
from dateutil import parser as dateparser
import re, datetime

today = datetime.date.today()

def extract_termination_date(text):
    text_lower = text.lower()
    # Immediate patterns
    if any(kw in text_lower for kw in ["immediately", "right away", "asap", "turn off now", "cancel now"]):
        return today.isoformat(), "Immediate"
    if re.search(r'\btoday\b', text_lower):
        return today.isoformat(), "Immediate"

    # Date patterns
    date_patterns = [
        r'effective\s+([\w\s,/]+\d{4})',
        r'as of\s+([\w\s,/]+\d{4})',
        r'starting\s+([\w\s,/]+\d{4})',
        r'on\s+([\w\s,/]+\d{4})',
        r'by\s+([\w\s,/]+\d{4})',
        r'turn off (?:on\s+)?([\w\s,/]+\d{4})',
        r'cancel (?:on\s+)?([\w\s,/]+\d{4})',
        r'(\d{1,2}/\d{1,2}/\d{2,4})',
        r'(\w+ \d{1,2},?\s+\d{4})',
    ]
    for pattern in date_patterns:
        m = re.search(pattern, text_lower)
        if m:
            try:
                dt = dateparser.parse(m.group(1), fuzzy=True)
                if dt:
                    state = "Immediate" if dt.date() <= today else "Pending"
                    return dt.strftime("%Y-%m-%d"), state
            except Exception:
                continue
    return None, "Pending"

termination_date, cancellation_state = extract_termination_date(reason_text)
```

---

## Step 3 — Check for PMS swap

Before mapping to cancellation reason, scan `reason_text` for PMS swap indicators:

```python
PMS_SWAP_KEYWORDS = [
    "switching to", "switch to", "pms change", "pms swap",
    "replacing", "going away", "moving to", "transition to",
    "transitioning to", "eaglesoft going", "dentrix going",
    "open dental", "new pms", "old pms", "legacy pms",
    "removing legacy", "removing eaglesoft", "removing dentrix",
]

is_pms_swap = any(kw in reason_text.lower() for kw in PMS_SWAP_KEYWORDS)
```

If `is_pms_swap`:
- Set `type_of_cancellation = "No Location Cancellation"`
- Map reason to `PMS Change` or `Removing Legacy PMS Connection` (whichever fits)
- Flag in report: `⚠️ PMS Swap detected — confirm before treating as full cancellation`
- Continue with record creation — do **not** skip

If not a PMS swap: `type_of_cancellation = "Partial Cancellation (Some Locations, Not All)"`

---

## Step 4 — Map reason to cancellation_reason enum

Map `reason_text` to one of the following enum values using semantic matching.
If `is_pms_swap` is already set, skip to `PMS Change` or `Removing Legacy PMS Connection`.
If no clear match exists, use `Unknown`.

| Enum value | When to use |
|---|---|
| `Buggy Product` | Product bugs, errors, technical malfunctions |
| `Failure to Launch` | Office never fully deployed or went live |
| `Implementation Issues` | Setup or onboarding problems |
| `Lack of End User Interaction` | Staff not using the product |
| `Lack of Features in Product` | Missing features, doesn't support a workflow |
| `Restructuring` | Organizational changes, merger, acquisition |
| `New Management` | New ownership or leadership |
| `PMS Not supported` | PMS not integrated |
| `Not Realizing Value Proposition` | General ROI dissatisfaction |
| `Office Sold` | Practice sold |
| `Password Management` | Password issues |
| `Payor Portal Passwords` | Payor portal credential issues |
| `ROI Concerns` | Cost vs. value concerns |
| `Not The Right Fit` | Generic poor fit |
| `Cancel 3rd Party Service` | Removing a connected third-party service |
| `POC Poor Utilization / Adoption` | POC or staff not adopting the tool |
| `Unknown` | Cannot determine reason |
| `Office Closed` | Practice closed |
| `Non-Payment` | Billing/payment issue |
| `PMS Change` | Switching PMS (use when `is_pms_swap` and new PMS is known) |
| `Removing Legacy PMS Connection` | Removing old PMS integration (use when `is_pms_swap` and removing old PMS) |

---

## Step 5 — Check for duplicate cancellation records

Search for an existing CANCELLATIONS record using the `query` field (not `filterGroups` —
`CONTAINS_TOKEN` returns 400 on custom objects):

```python
payload = {
    "query": location_name,
    "properties": ["cancellation_name", "hs_pipeline_stage", "hs_createdate"],
    "limit": 10
}

resp = requests.post(
    "https://api.hubapi.com/crm/v3/objects/2-33013991/search",
    headers=headers, json=payload
)
results = resp.json().get("results", [])
```

If any result's `cancellation_name` closely matches the location name → **skip** this email,
note in the final report as "Already has cancellation record: [link]".

---

## Step 6 — Look up location and company in HubSpot

### Step 6a — Find the Location record

Use `query` field (not `CONTAINS_TOKEN` — returns 400 on custom objects):

```python
payload = {
    "query": location_name,
    "properties": ["name", "client_id", "pms", "hs_object_id"],
    "limit": 5
}

resp = requests.post(
    "https://api.hubapi.com/crm/v3/objects/2-14718097/search",
    headers=headers, json=payload
)
location_records = resp.json().get("results", [])
```

- If multiple results: prefer the closest name match.
- If no results: proceed without a location association and note it in the report.
- Store `location_pms = location_record["properties"].get("pms", "")` for Step 7.

### Step 6b — Find the associated Company

```python
resp = requests.get(
    f"https://api.hubapi.com/crm/v4/objects/2-14718097/{location_id}/associations/companies",
    headers=headers
)
associations = resp.json().get("results", [])
company_id = associations[0]["toObjectId"] if associations else None
```

---

## Step 7 — DataCo name check (Bitwerx PMS only)

If `location_pms` is one of `eaglesoft`, `dentrix`, `dentrix_enterprise` **and** `location_id` was found:

**7a.** Navigate to `support.dataco.dental` in the Claude-controlled browser and extract the Azure B2C token from `sessionStorage` (see `dataco-supportco-api` skill for the exact token key).

**7b.** Search DataCo by InsideDesk Partner ID (the GoldenEye/HubSpot facility ID):

```javascript
const resp = await fetch(
  `https://supportcodentalapi.azurewebsites.net/api/v2/practices?pageSize=5&filter=${facilityId}&searchCustomIds=true`,
  { headers: { 'Authorization': 'Bearer ' + token } }
);
const list = await resp.json();
```

**7c.** Compare:
- `list[0].name` (DataCo name) vs `location_name` (HubSpot/email name)
- If names differ → set `dataco_name_mismatch = True`, record both names
- If no DataCo record found → note "Not found in DataCo" and continue
- **Do not block record creation** — log discrepancy and flag in report

```python
# Example mismatch flag output:
# ⚠️ DataCo name mismatch: HubSpot="Rocky Mountain Kids Dentistry" / DataCo="Kids Tooth Doc - Englewood"
# (May be a DBA rename — DataCo not updated)
```

If the token is missing or `support.dataco.dental` is not reachable, skip this step and note it.

---

## Step 8 — Create the CANCELLATIONS record

```python
import datetime

today = datetime.date.today().isoformat()

properties = {
    "cancellation_name": location_name,
    "cancellation_reason": mapped_reason,
    "date_requested": today,
    "hs_pipeline": "127090059",
    "hs_pipeline_stage": "222298644",   # CS Investigation
    "hubspot_owner_id": "628638356",
    "type_of_cancellation": type_of_cancellation,
    "cancellation_state": cancellation_state,
}

# Only set termination_date if one was parsed
if termination_date:
    properties["termination_date"] = termination_date

resp = requests.post(
    "https://api.hubapi.com/crm/v3/objects/2-33013991",
    headers=headers,
    json={"properties": properties}
)
record = resp.json()
record_id = record["id"]
record_url = f"https://app.hubspot.com/contacts/<HUBSPOT_PORTAL_ID>/record/2-33013991/{record_id}"
```

---

## Step 9 — Create associations

### Associate to Company

```python
if company_id:
    requests.put(
        f"https://api.hubapi.com/crm/v4/objects/2-33013991/{record_id}/associations/companies/{company_id}",
        headers=headers,
        json=[{"associationCategory": "USER_DEFINED", "associationTypeId": 174}]
    )
```

### Associate to Location

```python
if location_id:
    requests.put(
        f"https://api.hubapi.com/crm/v4/objects/2-33013991/{record_id}/associations/2-14718097/{location_id}",
        headers=headers,
        json=[{"associationCategory": "USER_DEFINED", "associationTypeId": 170}]
    )
```

---

## Step 10 — Post Slack notification

```python
term_line = f"Termination date: {termination_date}" if termination_date else "Termination date: not specified"
swap_line = "\n⚠️ *PMS Swap detected* — confirm before treating as full cancellation" if is_pms_swap else ""

message = (
    f":rotating_light: *Cancellation Request Received*\n"
    f"*{location_name}*\n"
    f"Reason: {mapped_reason}\n"
    f"Requested by: {requested_by}\n"
    f"{term_line}"
    f"{swap_line}\n"
    f"<{record_url}|View HubSpot Cancellation record>"
)

resp = requests.post(
    "https://slack.com/api/chat.postMessage",
    headers={"Authorization": f"Bearer {slack_token}", "Content-Type": "application/json"},
    json={"channel": "<SLACK_DM_SEAN>", "text": message, "mrkdwn": True}
)
```

---

## Step 11 — Report results

```
Cancellation Records Created (N)
  - [Location Name] → [HubSpot link]
      Reason: [mapped_reason]
      Termination date: [termination_date or "not specified"]
      Cancellation state: [Immediate / Pending]
      Company: [company name or "not found"]
      Location record: [matched or "not found"]
      ⚠️ PMS Swap detected           ← if applicable
      ⚠️ DataCo name mismatch: ...   ← if applicable

Already Has Record (N)
  - [Location Name] → [existing record link]

Skipped (N)
  - [email subject] — reason skipped
```

---

## Step 12 — Write Claude context note

**Create note body** — use the standard format:

```python
import base64, json, time

payload = {
    "v": 2,
    "updated": today + " " + datetime.datetime.now().strftime("%H:%M"),
    "origin": f"Monday Board cancellation mention · {today} · {requested_by}. Monday URL: {monday_url}",
    "checked": (
        f"Gmail scan (last 7 days). Duplicate check: no existing record. "
        f"Location lookup: {'matched – ' + location_name if location_id else 'not found'}. "
        f"Company: {'associated' if company_id else 'not found'}."
        + (f" DataCo checked: {'name mismatch – see decisions' if dataco_name_mismatch else 'name matches'}." if location_pms in ['eaglesoft','dentrix','dentrix_enterprise'] else "")
    ),
    "decisions": (
        f"Reason mapping: '{reason_text[:150]}' → {mapped_reason}. "
        + (f"PMS swap detected — type_of_cancellation set to 'No Location Cancellation'. " if is_pms_swap else "")
        + (f"DataCo name mismatch: HubSpot='{location_name}' / DataCo='{dataco_name}'. Possible DBA rename. " if dataco_name_mismatch else "")
        + (f"Termination date parsed as {termination_date} ({cancellation_state})." if termination_date else "No termination date found in email — set to Pending.")
    ),
    "next": "CS Investigation stage — follow up re: save opportunity." + (" Confirm PMS swap details before disabling." if is_pms_swap else ""),
}

b64 = base64.b64encode(json.dumps(payload).encode()).decode()
note_body = f"🤖 CLAUDE CONTEXT [v2 · {payload['updated']}]\n{b64}"
```

**Create note** (no inline associations — custom object associations must be separate):

```python
note_resp = requests.post(
    "https://api.hubapi.com/crm/v3/objects/notes",
    headers=headers,
    json={
        "properties": {
            "hs_note_body": note_body,
            "hs_timestamp": str(int(time.time() * 1000))
        }
    }
)
note_id = note_resp.json()["id"]
```

**Associate note to cancellation record** (batch endpoint — only way that works for custom objects):

```python
import time as t
t.sleep(1)  # allow note to commit before associating

requests.post(
    "https://api.hubapi.com/crm/v4/associations/notes/2-33013991/batch/create",
    headers=headers,
    json={"inputs": [{
        "from": {"id": note_id},
        "to": {"id": str(record_id)},
        "types": [{"associationCategory": "USER_DEFINED", "associationTypeId": 167}]
    }]}
)
```

---

## Edge cases

- **No "cancel" keyword in body**: Skip — not a cancellation email.
- **Email contains both "cancel" and "Vendor:"**: Ambiguous — skip and note in report.
- **Location not found in HubSpot**: Create record without location/company associations; note in report.
- **Multiple location matches**: Use closest name match; if truly ambiguous, prefer most recently modified.
- **Reason mapping unclear**: Use `Unknown`; include raw `reason_text` in context note.
- **Record already exists in any stage**: Skip — one cancellation record per location.
- **Multiple emails for same location**: Deduplicate — process only the first, skip the rest as duplicates.
- **Termination date not found**: Set `termination_date = None`, `cancellation_state = "Pending"`, flag in report.
- **PMS swap email**: Create record with `type_of_cancellation = "No Location Cancellation"`, flag as swap in report and Slack — do not skip.
- **DataCo unreachable or token missing**: Skip DataCo check, note in report, continue with record creation.
- **DataCo name mismatch**: Log both names in context note, flag in report — do not block creation. Likely a DBA rename where DataCo was not updated.

---

## Step 13 — Log the run

After Step 12, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `cancellation-ticket` |
| `status` | `success` if all qualifying emails were processed · `partial` if any records failed or were skipped due to errors · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: number of cancellation records created, any duplicates or skips, and any PMS swap or DataCo mismatch flags. |
| `inputs` | `date_range=last 7 days` · `emails_scanned={count}` |
| `outputs` | `records_created={N}` · `already_had_record={N}` · `skipped={N}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `pms_swaps_detected={N}` · `dataco_mismatches={N}` |

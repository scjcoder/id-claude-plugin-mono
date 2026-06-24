---
name: create-422-tickets
description: >
  Create HubSpot Install Pipeline tickets from 422 Tax ID Error Report data.
  One ticket per client. Associates the client company, Account POC contacts,
  and affected location records, attaches the PDF report, writes a summary note,
  and posts a Slack summary. Designed to be called automatically at the end of
  the 422-tax-id-report skill, or invoked manually by Sean. Trigger when Sean
  says "create 422 tickets", "ticket up the 422 report", "create HubSpot tickets
  for the tax ID errors", or similar.
---

# Skill: Create 422 Unapproved TIN Tickets

Creates one HubSpot Install Pipeline ticket per client from 422 Tax ID Error
Report data. Associates the client company, finds and links all Account POC
contacts, associates the affected location records, attaches the PDF report,
writes a summary note, and posts to Slack.

---

## Prerequisites

Run the `get-secret` skill with name `hubspot-token` to retrieve the HubSpot API token.
See `id-claude-shared` plugin: `skills/_shared/hubspot-setup.md` — Steps B and C are handled by the `get-secret` skill.

**⚠️ Use Desktop Commander (`mcp__Desktop_Commander__start_process`) for all shell
commands — NOT `mcp__workspace__bash`. The sandbox has no AWS credentials.**

---

## Key constants (inherited from Install pipeline)

| Item | Value |
|---|---|
| Install Pipeline ID | `66471460` |
| Opening stage (New) | `133962530` |
| Slack DM channel | `D0B0YUWV1UK` |
| Locations custom object | `2-14718097` |
| Ticket → Location association typeId | `153` (USER_DEFINED) |

---

## Inputs (passed from 422-tax-id-report, or provided by Sean)

| Field | Description | Example |
|---|---|---|
| `client_name` | Client display name from GoldenEye | `"Acme Dental Management"` |
| `client_data` | Facilities dict for this client (from Step 3 of 422 report) | see below |
| `pdf_path` | Absolute path to the generated PDF report | `"/Users/sean/CODE/..."` |
| `date_range` | Human-readable date range | `"May 14–15, 2026"` |
| `date_slug` | File-safe date range used in filename | `"2026-05-14_15"` |

**`client_data` shape:**
```json
{
  "Acme Dental of Howell": {
    "pms": "Denticon",
    "taxIds": {
      "111224444": ["2867849", "2867852"],
      "111223333": ["2868207"]
    }
  },
  "Acme Dental of Freehold": {
    "pms": "Dentrix",
    "taxIds": { "111224444": ["2870001"] }
  }
}
```

When called from 422-tax-id-report, iterate over each client and invoke this
skill once per client, passing its slice of the data and its PDF path.

---

## Step 1 — Four-front scored duplicate check

Before creating anything, run all four fronts and collect scores. **No short-circuiting** —
all fronts always run so the highest-confidence signals always fire. Decide after all
four complete.

> The original sequential approach failed when prior tickets were closed (excluded by
> the open-only filter) and Front 3 (location overlap) only ran against fronts 1/2 hits
> rather than independently. This scoring model fixes both: closed tickets within 14 days
> are included, and Front 3 runs independently against all company-associated tickets.

---

### Scoring table

| Front | Signal | Points |
|---|---|---|
| 1 | Normalized subject match (open tickets only) | 20 |
| 2 | Company-associated Unapproved TIN ticket (open only) | 20 |
| 3 | Location **+ TIN** overlap in open ticket | 80 |
| 3b | Location overlap only (TINs not parseable from existing note) | 30 |
| 4 | Gmail sent email matching client name (≤ 3 days) | 15 |

**Decision:**
- Score **≥ 80** → **skip** — duplicate detected; do not create
- Score **40–79** → **warn + create** — flag in Slack + context note, but still create
- Score **< 40** → **proceed** normally

> **Why these weights?** Clients actively onboarding new offices can produce daily 422
> errors for the same locations with entirely different TINs — e.g. Acme Dental adding
> offices week-over-week. Location overlap alone is therefore not a reliable duplicate
> signal. Only a TIN + location overlap in an **open** ticket justifies skipping creation.
> Fronts 1 + 2 + 4 combined max out at 55 pts (warn+create) and can never trigger a skip.

---

### Step 1a — Resolve company and pre-fetch ticket IDs

Run the same company lookup described in Step 2, but only to obtain `company_id`
and `client_id`. If the company is not found in HubSpot, Fronts 2 and 3 are
skipped (Fronts 1 and 4 still run).

When `company_id` is available, **also** paginate through all company→ticket
associations now and store the full list as `all_ticket_ids`. Fronts 2 and 3
both reuse this list — fetch it only once:

```python
import requests

all_ticket_ids = []
after = None
while True:
    params = {"limit": 500}
    if after:
        params["after"] = after
    resp = requests.get(
        f"https://api.hubapi.com/crm/v4/objects/companies/{company_id}/associations/tickets",
        headers={"Authorization": f"Bearer {token}"},
        params=params
    )
    data = resp.json()
    all_ticket_ids.extend([r["toObjectId"] for r in data.get("results", [])])
    after = data.get("paging", {}).get("next", {}).get("after")
    if not after:
        break
```

Define the normalization helper once — used by all fronts:

```python
import re
from datetime import datetime, timedelta, timezone

def normalize(s):
    s = re.sub(r'[-–—]', ' ', s or '')   # ASCII hyphen + en/em-dash → space
    s = re.sub(r'\s+', ' ', s)
    return s.strip().lower()

def is_active(props):
    """True only if the ticket is open (not closed). Closed tickets are never
    treated as active duplicates — always create a new ticket when the prior one
    is closed, regardless of how recently it was closed.
    Closed stage ID: 129440439"""""
    return props.get("hs_pipeline_stage", "") != "129440439"
```

---

### Front 1 — Normalized subject match (open or recently closed)

Search HubSpot for Install Pipeline tickets whose subject matches — including
tickets closed within the last 14 days.

```
search_crm_objects on "tickets"
query: "[client_name] – Unapproved TIN"
filterGroups: [{
  filters: [
    { propertyName: "hs_pipeline", operator: "EQ", value: "66471460" }
  ]
}]
properties: ["subject", "hs_pipeline_stage", "createdate", "hs_lastmodifieddate", "hs_object_id"]
limit: 25
```

Filter results client-side using `is_active()` and normalize subject:

```python
expected = normalize(f"{client_name} – Unapproved TIN")
front1_hit = next(
    (t for t in results
     if is_active(t["properties"])
     and normalize(t["properties"].get("subject", "")) == expected),
    None
)
```

---

### Front 2 — Company-associated ticket check (open or recently closed)

Using `all_ticket_ids` from Step 1a, batch-read in chunks of 100 and filter
client-side for Install Pipeline Unapproved TIN tickets that are active:

```python
front2_hit = None
for i in range(0, len(all_ticket_ids), 100):
    chunk = all_ticket_ids[i:i + 100]
    batch_resp = requests.post(
        "https://api.hubapi.com/crm/v3/objects/tickets/batch/read",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "inputs": [{"id": str(tid)} for tid in chunk],
            "properties": ["subject", "hs_pipeline", "hs_pipeline_stage", "hs_lastmodifieddate"]
        }
    )
    for t in batch_resp.json().get("results", []):
        props = t["properties"]
        if (props.get("hs_pipeline") == "66471460"
                and "unapproved tin" in normalize(props.get("subject", ""))
                and is_active(props)):
            front2_hit = t
            break
    if front2_hit:
        break
```

---

### Front 3 — Location + TIN overlap (independent search)

Front 3 runs **independently** — it does not depend on Fronts 1 or 2 finding
anything. It checks all company-associated open Install Pipeline tickets (via
`all_ticket_ids` from Step 1a) for overlap with the facilities **and TINs** in
`client_data`. Both must overlap for the full 80-point score. If locations overlap
but TINs cannot be parsed from the existing ticket's summary note (old format),
score 30 points instead.

> **Why TIN overlap matters:** A client actively adding offices may get 422 errors
> for the same location on consecutive days with entirely different TINs. Those are
> distinct issues requiring separate tickets, not duplicates.

**3a — Resolve location IDs for client_data facilities:**

```python
our_location_ids = set()
for facility_name in client_data.keys():
    payload = {
        "filterGroups": [{"filters": [
            {"propertyName": "client_id",     "operator": "EQ", "value": client_id},
            {"propertyName": "location_name", "operator": "EQ", "value": facility_name}
        ]}],
        "properties": ["hs_object_id"],
        "limit": 5
    }
    r = requests.post(
        "https://api.hubapi.com/crm/v3/objects/2-14718097/search",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload
    )
    for result in r.json().get("results", []):
        our_location_ids.add(str(result["id"]))
```

**3b — Check all company-associated active tickets for location overlap:**

Reuse the batch reads from Front 2 if already done; otherwise batch-read now.
For each active Install Pipeline Unapproved TIN ticket, fetch its location
associations and check for overlap:

```python
def extract_tins_from_note(note_body):
    """Parse TIN values from a Step 8 summary note. Returns a set of TIN strings,
    or None if the note format is unrecognised (old format without TIN lines)."""
    import re
    tins = set(re.findall(r'TIN[s]?:\s*([\d, ]+)', note_body or ""))
    # Flatten: "123456789, 987654321" → {"123456789", "987654321"}
    result = set()
    for match in tins:
        for t in match.split(","):
            t = t.strip()
            if t:
                result.add(t)
    return result if result else None

# Build set of TINs in the current report (for overlap comparison)
current_tins = {
    tin
    for fac in client_data.values()
    for tin in fac["taxIds"]
}

front3_hit = None
for i in range(0, len(all_ticket_ids), 100):
    chunk = all_ticket_ids[i:i + 100]
    batch_resp = requests.post(
        "https://api.hubapi.com/crm/v3/objects/tickets/batch/read",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "inputs": [{"id": str(tid)} for tid in chunk],
            "properties": ["subject", "hs_pipeline", "hs_pipeline_stage", "hs_lastmodifieddate"]
        }
    )
    for t in batch_resp.json().get("results", []):
        props = t["properties"]
        if not (props.get("hs_pipeline") == "66471460"
                and "unapproved tin" in normalize(props.get("subject", ""))
                and is_active(props)):
            continue

        # Check location overlap first (cheap)
        loc_resp = requests.get(
            f"https://api.hubapi.com/crm/v4/objects/0-5/{t['id']}/associations/2-14718097",
            headers={"Authorization": f"Bearer {token}"}
        )
        existing_loc_ids = {str(r["toObjectId"]) for r in loc_resp.json().get("results", [])}
        loc_overlap = our_location_ids & existing_loc_ids
        if not loc_overlap:
            continue

        # Location overlap found — now check TIN overlap from the ticket's summary note
        notes_resp = requests.get(
            f"https://api.hubapi.com/crm/v4/objects/tickets/{t['id']}/associations/notes",
            headers={"Authorization": f"Bearer {token}"}
        )
        note_ids = [a["toObjectId"] for a in notes_resp.json().get("results", [])]
        existing_tins = None
        for nid in note_ids:
            nr = requests.get(
                f"https://api.hubapi.com/crm/v3/objects/notes/{nid}",
                headers={"Authorization": f"Bearer {token}"},
                params={"properties": "hs_note_body"}
            )
            body = nr.json().get("properties", {}).get("hs_note_body", "") or ""
            if "422 Unapproved TIN Summary" in body:
                existing_tins = extract_tins_from_note(body)
                break

        tin_overlap = (existing_tins & current_tins) if existing_tins is not None else None

        if tin_overlap:
            # Full duplicate: same open ticket, same locations, same TINs
            front3_hit = {
                "ticket_id": t["id"],
                "overlapping_location_ids": loc_overlap,
                "overlapping_tins": tin_overlap,
                "score": 80,
                "ticket": t,
            }
        elif existing_tins is None:
            # Old note format — can't parse TINs; score conservatively
            front3_hit = {
                "ticket_id": t["id"],
                "overlapping_location_ids": loc_overlap,
                "overlapping_tins": None,
                "score": 30,
                "ticket": t,
            }
        # If existing_tins parsed but no TIN overlap → different TINs, not a dup; skip
        if front3_hit:
            break
    if front3_hit:
        break
```

---

### Front 4 — Gmail sent-email check (7-day lookback)

Search Gmail sent mail for any 422 / Unapproved TIN email sent to this client
in the last 7 days. Use the Gmail MCP `search_threads` tool:

```
query: 'in:sent subject:"{client_name}" ("Unapproved TIN" OR "422") newer_than:3d'
```

If the search returns one or more threads → `front4_hit = True`.

---

### Step 1 — Score, decide, and report

Tally all front results and apply the decision rule:

```python
score = 0
hits = {}

if front1_hit:
    score += 60
    hits["subject_match"] = front1_hit

if front2_hit:
    score += 50
    hits["company_ticket"] = front2_hit

if front3_hit:
    score += front3_hit["score"]  # 80 = TIN+location overlap; 30 = location only
    hits["location_overlap"] = front3_hit

if front4_hit:
    score += 40
    hits["gmail_sent"] = True

if score >= 80:
    decision = "skip"
elif score >= 50:
    decision = "warn_create"
else:
    decision = "proceed"
```

**If `decision == "skip"`** → do not create a ticket. Report every signal that fired:

```
⚠️  Skipped [client_name] — duplicate detected (score: N)
    • Subject match    → ticket [ID] ([subject]) created [date]
    • Company ticket   → ticket [ID] ([subject]) modified [date]
    • Location overlap → ticket [ID] shares locations: [loc IDs], TINs: [tin values or "unparseable"]
    • Gmail sent email → found [N] thread(s) in last 7 days
```

**If `decision == "warn_create"`** → proceed to Step 2 but include a warning in
the Slack message (Step 9) and Claude context note (Step 10):

```
⚠️  Possible duplicate for [client_name] (score: N) — ticket created anyway.
    Signals fired: [list fronts that scored]
```

**If `decision == "proceed"`** → continue to Step 2 silently.

Company is already resolved from Step 1a — no need to repeat the lookup.

---

## Step 2 — Find the client company in HubSpot

```
search_crm_objects on "companies"
query: "[client_name]"
properties: ["name", "hs_object_id", "client_id", "of_locations___active"]
```

- **Single clear match**: use its `hs_object_id` as `company_id` and its `client_id`
  for the location lookup in Step 3.
- **Multiple matches**: pick the one whose name most closely matches `client_name`
  (exact or near-exact preferred; title-case and punctuation differences are fine).
- **No match**: note this and **skip ticket creation** for this client.
  Do not create unassociated tickets.

Store `client_id` from the matched company — it is required for Step 3.

---

## Step 3 — Resolve HubSpot location records

For each facility in `client_data`, find its corresponding HubSpot location record
in the locations custom object (`2-14718097`) so it can be associated to the ticket.

Use Desktop Commander to run:

```python
import requests, json

token     = "<hubspot_token>"
client_id = "<client_id_from_step_2>"   # string, e.g. "124"
H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

facility_names = list(client_data.keys())  # from the 422 report client_data
location_ids   = []   # HubSpot hs_object_id for each matched location
unmatched      = []   # facility names with no HubSpot match

for facility_name in facility_names:
    # Try exact match first
    payload = {
        "filterGroups": [{"filters": [
            {"propertyName": "client_id",    "operator": "EQ", "value": client_id},
            {"propertyName": "location_name","operator": "EQ", "value": facility_name}
        ]}],
        "properties": ["location_name", "hs_object_id"],
        "limit": 5
    }
    resp = requests.post(
        "https://api.hubapi.com/crm/v3/objects/2-14718097/search",
        headers=H, json=payload
    )
    results = resp.json().get("results", [])

    if not results:
        # Fall back: CONTAINS_TOKEN on the distinctive part of the name.
        # For names like "Acme Dental of Howell" use the part after " of ";
        # otherwise use the last word.
        if " of " in facility_name:
            fragment = facility_name.split(" of ", 1)[-1]
        else:
            fragment = facility_name.split()[-1]

        payload["filterGroups"][0]["filters"][1] = {
            "propertyName": "location_name",
            "operator": "CONTAINS_TOKEN",
            "value": fragment
        }
        resp = requests.post(
            "https://api.hubapi.com/crm/v3/objects/2-14718097/search",
            headers=H, json=payload
        )
        results = resp.json().get("results", [])

    if results:
        loc_id = results[0]["id"]
        loc_name = results[0]["properties"].get("location_name", "?")
        print(f"  ✅ {facility_name} → {loc_name} (ID {loc_id})")
        location_ids.append(loc_id)
    else:
        print(f"  ⚠️  {facility_name} → no HubSpot location match")
        unmatched.append(facility_name)

print(f"\nMatched {len(location_ids)}/{len(facility_names)} locations")
print(f"location_ids = {location_ids}")
```

Store `location_ids` (list of HubSpot location `hs_object_id` strings) and
`unmatched` (list of facility names with no match). Both are used in later steps.

**If `client_id` is missing on the company record**: fall back to searching
locations by `company_name CONTAINS_TOKEN <client_name>` instead of `client_id EQ`.
Note this in the context note.

---

## Step 4 — Find Account POC contacts

The target label is **"Account POC"** — a custom association label visible on the
company's Snapshot tab under "Company POCs". There may be more than one contact
with this label; associate **all** of them to the ticket.

### Step 4a — Fetch all associated contacts with labels (paginated)

Use Desktop Commander to run:

```python
import requests, json

token      = "<hubspot_token>"
company_id = "<company_id>"
all_results = []
after = None

while True:
    params = {}
    if after:
        params["after"] = after
    resp = requests.get(
        f"https://api.hubapi.com/crm/v4/objects/companies/{company_id}/associations/contacts",
        headers={"Authorization": f"Bearer {token}"},
        params=params
    )
    data = resp.json()
    all_results.extend(data.get("results", []))
    after = data.get("paging", {}).get("next", {}).get("after")
    if not after:
        break

print(json.dumps(all_results, indent=2))
```

Each result looks like:
```json
{
  "toObjectId": 12345,
  "associationTypes": [
    { "category": "USER_DEFINED", "typeId": 999, "label": "Account POC" }
  ]
}
```

### Step 4b — Filter for "Account POC" label

Collect `toObjectId` values for every contact where at least one entry in
`associationTypes` has `"label"` equal to `"Account POC"` (case-insensitive).
Associate **all** matching contacts to the ticket — do not cap or filter further.

**If no "Account POC" contacts are found** — do not fall back to other contacts.
Instead, create the ticket with only the company association and note clearly:
`"No Account POC contact found for [client_name] — ticket created without contact association."`

### Step 4c — Fetch display names for the Slack message

For each matched contact ID, fetch `firstname`, `lastname`, `email` via
`search_crm_objects` on `contacts` (or a batch read). Build `poc_display_names`
as a list of `"Firstname Lastname"` strings (fall back to email if name is blank).

---

## Step 5 — Compute summary stats

```python
facility_count = len(client_data)
unique_tax_ids = len({tid for fac in client_data.values() for tid in fac["taxIds"]})
total_claims   = sum(
    len(claims)
    for fac in client_data.values()
    for claims in fac["taxIds"].values()
)
```

Build a per-facility breakdown (sorted descending by claim count):

```
[Facility Name] ([PMS]) — N tax ID(s), N claims
```

---

## Step 6 — Create the HubSpot ticket and associate locations

### Step 6a — Create the ticket

Use `manage_crm_objects` to create the ticket:

| Property | Value |
|---|---|
| `subject` | `[client_name] – Unapproved TIN` |
| `hs_pipeline` | `66471460` |
| `hs_pipeline_stage` | `133962530` |
| `source_type` | `EMAIL` |

**Do not set `hubspot_owner_id`** — tickets are intentionally left unassigned.

Include associations in the same create call:
- Client company: `{ objectType: "companies", id: <company_id> }`
- Each Account POC contact: `{ objectType: "contacts", id: <contact_id> }`
  (one association entry per contact)

Store the returned `hs_object_id` as `ticket_id` for all subsequent steps.

To get `portal_id` for the ticket URL, run once per session:
```python
resp = requests.get(
    "https://api.hubapi.com/account-info/v3/details",
    headers={"Authorization": f"Bearer {token}"}
)
portal_id = resp.json()["portalId"]
ticket_url = f"https://app.hubspot.com/contacts/{portal_id}/ticket/{ticket_id}"
```

### Step 6b — Batch-associate location records to the ticket

After the ticket is created, associate all matched location records using the
v4 batch endpoint. Association typeId for tickets → locations is **153** (USER_DEFINED).

```python
import requests

if location_ids:
    inputs = [
        {
            "from": {"id": str(ticket_id)},
            "to":   {"id": str(loc_id)},
            "types": [{"associationCategory": "USER_DEFINED", "associationTypeId": 153}]
        }
        for loc_id in location_ids
    ]
    resp = requests.post(
        "https://api.hubapi.com/crm/v4/associations/0-5/2-14718097/batch/create",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"inputs": inputs}
    )
    result = resp.json()
    assoc_status = result.get("status")  # "COMPLETE" on success
    assoc_errors = result.get("errors", [])
    if assoc_status == "COMPLETE":
        print(f"✅ Associated {len(location_ids)} location(s) to ticket {ticket_id}")
    else:
        print(f"⚠️  Location association partial/failed: {assoc_errors}")
else:
    print("ℹ️  No location IDs to associate (all facilities unmatched)")
```

If the batch call fails, continue — do not abort. Note the failure in the context
note (Step 10) and include unmatched facilities in the Slack message.

---

## Step 7 — Attach the PDF report to the ticket

### Step 7a — Upload the PDF to HubSpot Files

```python
import os, requests

pdf_filename = os.path.basename(pdf_path)

with open(pdf_path, "rb") as f:
    resp = requests.post(
        "https://api.hubapi.com/files/v3/files",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (pdf_filename, f, "application/pdf")},
        data={"options": '{"access": "PRIVATE", "overwrite": true}', "folderPath": "/"}
    )

result = resp.json()
file_id = result.get("id")
if not file_id:
    print(f"PDF upload failed: {result}")
    pdf_attached = False
else:
    pdf_attached = True
```

If the upload fails, continue — do not abort ticket creation. Note the failure.

### Step 7b — Create an attachment note on the ticket

```python
import time

payload = {
    "properties": {
        "hs_note_body":      f"📎 Tax ID Error Report — {client_name} — {date_range}",
        "hs_timestamp":      str(int(time.time() * 1000)),
        "hs_attachment_ids": str(file_id)
    },
    "associations": [{
        "to": {"id": ticket_id},
        "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 18}]
    }]
}
resp = requests.post(
    "https://api.hubapi.com/crm/v3/objects/notes",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json=payload
)
```

If `associationTypeId: 18` fails, retry with `associationTypeId: 19`.
Update this skill with the confirmed working value once known.

---

## Step 8 — Write a summary note on the ticket

Create a note with the high-level error summary — this is what the team reads
when they open the ticket.

Read `skills/hubspot-human-note/SKILL.md` and run it. Pass:

- `ticket_id`: the ticket ID for this client
- `sections`: built from the data computed above

```python
# Build per-facility rows (sorted by claim count descending)
facility_rows = [
    [
        name,
        f"{data['pms']} · {sum(len(c) for c in data['taxIds'].values())} claims · "
        f"TINs: {', '.join(sorted(data['taxIds'].keys()))}"
    ]
    for name, data in sorted(
        client_data.items(),
        key=lambda x: sum(len(c) for c in x[1]["taxIds"].values()),
        reverse=True
    )
]

sections = [
    {
        "type": "table",
        "title": f"422 Unapproved TIN Summary — {client_name} — {date_range}",
        "rows": [
            ["Affected facilities",  str(facility_count)],
            ["Unique tax IDs",       str(unique_tax_ids)],
            ["Total claims",         str(total_claims)],
            ["Locations associated", f"{len(location_ids)}/{facility_count}"]
        ]
    },
    {"type": "divider"},
    {
        "type": "table",
        "title": "Breakdown by facility",
        "rows": facility_rows
    }
]

# If any locations were unmatched, append a text note
if unmatched:
    sections += [
        {"type": "divider"},
        {"type": "text", "title": "Unmatched locations",
         "body": f"No HubSpot location record found for: {', '.join(unmatched)}"}
    ]

sections.append({
    "type": "text",
    "body": "Next step: Review each tax ID against the practice's EIN on file and correct in the PMS or update GoldenEye config as appropriate."
})
```

# Note: TIN values are included in each facility row above (e.g. "TINs: 123456789, 987654321").
# The extract_tins_from_note() helper in Step 1 (Front 3) parses these for future dup checks.

The `hubspot-token` is already in scope — no need to retrieve it again.

---

## Step 9 — Post Slack notification

Post to `D0B0YUWV1UK` using the Slack Web API via Desktop Commander.
The Slack MCP returns `restricted_action_read_only_channel` for this channel —
always use the Web API directly.

Retrieve the bot token if not already in scope:

Run the `get-secret` skill with name `slack-bot-token` to retrieve the Slack bot token.
See `id-claude-shared` plugin: `skills/_shared/slack-setup.md` — Section A (token retrieval) is handled by the `get-secret` skill.

Post the message:
```python
poc_display = ", ".join(poc_display_names)  # e.g. "Pati Vasquez, Jane Smith"
fac_word    = "facility" if facility_count == 1 else "facilities"
tid_word    = "tax ID" if unique_tax_ids == 1 else "tax IDs"
loc_note    = (
    f"*{len(location_ids)}* location(s) associated"
    if len(location_ids) == facility_count
    else f"*{len(location_ids)}/{facility_count}* locations associated"
         + (f" — no match: {', '.join(unmatched)}" if unmatched else "")
)

message = (
    f":ticket: *422 Ticket Created — {client_name}*\n"
    f"*{facility_count}* {fac_word} · *{unique_tax_ids}* {tid_word} · "
    f"*{total_claims}* claims\n"
    f"{loc_note}\n"
    f"POC: {poc_display if poc_display else '_none found_'}\n"
    f"<{ticket_url}|View HubSpot ticket>"
)

resp = requests.post(
    "https://slack.com/api/chat.postMessage",
    headers={"Authorization": f"Bearer {bot_token}", "Content-Type": "application/json"},
    json={"channel": "D0B0YUWV1UK", "text": message, "mrkdwn": True}
)
if not resp.json().get("ok"):
    print(f"Slack error: {resp.json().get('error')}")
```

If Slack fails, note it but do not fail the skill — ticket creation is primary.

---

## Step 10 — Write Claude context note (mandatory format)

Read `skills/hubspot-context-note/SKILL.md` and follow it **exactly**. Pass:

| Field | Value |
|---|---|
| `ticket_id` | The ticket ID from Step 6 |
| `origin` | `"422-tax-id-report skill · {date_range} · auto-created from GoldenEye snapshot errors"` |
| `what_was_checked` | Duplicate check result + location match results (N/N matched) + Account POC contacts found + PDF upload outcome |
| `decisions` | Contact names associated; location matches/mismatches (include unmatched facility names if any); fuzzy company match details if applicable |
| `next_steps` | `"Team to move ticket to Support / Investigation stage once assigned."` Append `"Manual location association needed for: [unmatched]"` if any facilities were unmatched. |

The HubSpot token is already in scope — no need to retrieve it again.

⚠️ **Format is mandatory — do not shortcut this step:**
- The note body **must** use the two-line `🤖 CLAUDE CONTEXT [v2 · YYYY-MM-DD HH:MM]` format
  with a base64-encoded JSON payload on line 2.
- Plain-text notes will not be parseable by future skill runs.
- The Desktop Commander base64 encoding command in Step 2b of `hubspot-context-note/SKILL.md`
  is **required** — do not skip it or write a human-readable note instead.

---

## Step 11 — Return result to caller

Return a result dict for the 422 report skill's final summary:

```python
{
    "client":               client_name,
    "status":               "created",      # "created" | "skipped" | "error"
    "ticket_id":            ticket_id,
    "ticket_url":           ticket_url,
    "pdf_path":             pdf_path,             # passed through for draft-422-client-email
    "facilities":           facility_count,
    "tax_ids":              unique_tax_ids,
    "claims":               total_claims,
    "poc":                  poc_display_names,   # list of "Firstname Lastname" strings
    "pdf_attached":         pdf_attached,         # True / False
    "locations_associated": len(location_ids),    # int
    "locations_unmatched":  unmatched,            # list of facility names
    "client_data":          client_data,          # passed through for draft-422-client-email
}
```

---

## Step 12 — Draft client email

For every client where `status == "created"`, immediately call the
`draft-422-client-email` skill. Read `skills/draft-422-client-email/SKILL.md`
and follow its instructions, passing:

| Field | Value |
|---|---|
| `client_name` | `client_name` |
| `ticket_id` | `ticket_id` (from Step 6) |
| `pdf_path` | `pdf_path` (input to this skill) |
| `date_range` | `date_range` (input to this skill) |
| `poc` | `poc_display_names` |
| `ticket_url` | `ticket_url` |
| `client_data` | `client_data` (input to this skill) |

Skip this step for any client whose status is `"skipped"` or `"error"` — only
draft emails for tickets that were actually created this run.

The HubSpot token and Slack bot token are already in scope — no need to retrieve
them again. The Google Drive folder lookup (Step 2 of draft-422-client-email) only
needs to happen once across all clients — reuse `folder_id` if already resolved.

---

## Final summary (when run standalone by Sean)

After processing all clients, print:

```
Tickets Created (N)
  ✅ [Client Name]
      Facilities: N  |  Tax IDs: N  |  Claims: N
      Locations associated: N/N
      POC: [name(s) or "none found"]
      PDF attached: ✓ / ✗
      → https://app.hubspot.com/contacts/[portal]/ticket/[id]

Skipped — Already Ticketed (N)
  ⚠️  [Client Name] → [existing ticket URL]

Errors (N)
  ❌ [Client Name]: [reason — company not found, etc.]
```

---

## Edge cases

- **Company not found in HubSpot**: skip ticket creation, log as error. Never
  create unassociated tickets.
- **`client_id` missing on company record**: fall back to searching locations by
  `company_name CONTAINS_TOKEN <client_name>`. Note in context note.
- **Facility name doesn't match any location**: log as unmatched, continue with
  remaining facilities. Note all unmatched names in the summary note and context note.
- **No locations matched at all**: create the ticket and note that no location
  associations were made — do not abort.
- **No Account POC contacts found**: create the ticket associated to the company
  only. Note clearly in summary and context note — do not substitute other contacts.
- **PDF upload fails**: continue with ticket creation; note failure in summary
  and context note. The PDF is already delivered to Slack by the 422 report skill.
- **Duplicate ticket found**: skip with a warning showing every signal that fired
  (subject match, company ticket, location overlap). Do not update the existing
  ticket — that is a manual team decision.
- **Front 1/2 fires but Front 3 finds no location overlap**: still treat as a
  duplicate — subject/company match is sufficient on its own.
- **Front 3 fires but fronts 1/2 don't**: still a duplicate — overlapping offices
  are the strongest signal regardless of subject wording.
- **Company not found in Step 1a**: fronts 2 and 3 are skipped; front 1 still runs.
- **associationTypeId for notes**: confirmed working values are `18` (ticket→note).
  If rejected, try `19`.
- **Multiple facilities share the same tax ID**: already deduplicated by the
  422-tax-id-report skill (Set-based merge). Use counts as-is.
- **Invalid EIN flagged in report**: counts are used as-is. The HTML/PDF already
  flags them — no special handling needed here.

---

## Step 13 — Log the run

After Step 12, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `create-422-tickets` |
| `status` | `success` if all client tickets were created · `partial` if any were skipped as duplicates or had errors · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: number of tickets created, number skipped as duplicates, and any clients that errored (company not found, etc.). |
| `inputs` | `client_count={N}` · `date_range={range}` |
| `outputs` | `tickets_created={N}` · `tickets_skipped={N}` · `tickets_errored={N}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `total_facilities={N}` · `total_claims={N}` |

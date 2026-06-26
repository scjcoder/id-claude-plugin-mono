---
name: client-offboarding
description: >
  End-to-end client offboarding workflow: reads a HubSpot cancellation ticket URL,
  auto-detects full vs. partial cancellation, associates the correct locations to the
  ticket in HubSpot, and (for Ascend API clients) outputs paste-ready data for the
  Ascend Royalty Reports REMOVE tab — no GoldenEye screenshot required.
  Use whenever a client is cancelling — "offboard [client]", "cancel [client]",
  "I'm cancelling [client]", "set up the cancellation for [client]", or when the user
  pastes a HubSpot cancellation ticket URL. Replaces cancel-client-locations,
  goldeneye-disable-location, and goldeneye-remove-tab skills.
---

# Skill: client-offboarding

Complete cancellation workflow driven from a HubSpot cancellation ticket URL. Handles
full-client and partial-location cancellations. All outputs are generated from HubSpot
data — no GoldenEye screenshot needed.

---

## What to collect before starting

Ask the user for the **HubSpot cancellation ticket URL**. Everything else is derived
from the ticket. Do not ask for the client name or Ascend API status upfront — both
are read from HubSpot.

---

## Setup — Auth & HubSpot token

Run the `get-secret` skill with name `hubspot-token` to retrieve the HubSpot API token.
See `id-claude-shared` plugin: `skills/_shared/hubspot-setup.md` — Steps B (aws-login) and
C (token retrieval) are now handled by the `get-secret` skill.

---

## Step 1 — Parse the ticket URL and fetch the cancellation record

Extract the numeric record ID from the URL (last numeric path segment, e.g.
`https://app.hubspot.com/contacts/<HUBSPOT_PORTAL_ID>/record/2-33013991/53650739370/` → `53650739370`).

```bash
TOKEN="<TOKEN>"
TICKET_ID="<ID_FROM_URL>"

curl -s "https://api.hubapi.com/crm/v3/objects/2-33013991/${TICKET_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -G \
  --data-urlencode "properties=cancellation_name,status,cancellation_state,termination_date" \
  --data-urlencode "associations=companies"
```

Extract from the response:
- `cancellation_name` — used for branch detection and confirmation display
- `termination_date` — use as the offboarding date if present; otherwise use today
- `associations.companies.results[0].id` — company record ID

---

## Step 2 — Fetch the associated company

Using the company ID from Step 1's associations:

```bash
COMPANY_ID="<ID_FROM_ASSOCIATIONS>"

curl -s "https://api.hubapi.com/crm/v3/objects/companies/${COMPANY_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -G \
  --data-urlencode "properties=name,client_id,of_locations___active,pms"
```

Extract:
- `name` — company display name
- `client_id` — used to query locations
- `of_locations___active` — expected active location count for verification
- `pms` — if value equals `ASCEND_API`, the REMOVE tab output (Step 6) is required

Present findings to the user before continuing:

> **Client:** [Company Name]
> **Ticket:** "[cancellation_name]" — [View](https://app.hubspot.com/contacts/<HUBSPOT_PORTAL_ID>/record/2-33013991/[TICKET_ID]/)
> **Ascend API client:** Yes / No

---

## Step 3 — Detect cancellation branch

Normalize `cancellation_name` to lowercase and scan for full-cancellation keywords:

| Keyword (case-insensitive) | Real examples from churned tickets |
|---|---|
| `all locations` | "Peak Dental - ALL LOCATIONS", "Alfa Dental - All Locations" |
| `all offices` | "PepperPointe - All offices", "Higginbotham - Cancel All Offices" |
| `all lost` | "McLean - Trial Lost - All Lost" |

**Keyword match → Branch A (Full cancellation)** — all active locations will be processed.
**No keyword match → Branch B (Partial cancellation)** — user selects the subset.
**Ambiguous** (ticket name is just the client name with no scope qualifier) → default to
Branch B and flag it explicitly.

Always show the detected branch and ask for confirmation before proceeding:

> Ticket: **"[cancellation_name]"**
> Detected: **Full cancellation** — I'll process all [N] active locations. Does that look right?

or:

> Ticket: **"[cancellation_name]"**
> Detected: **Partial cancellation** — I'll pull the full location list so you can confirm
> which ones to include.

Do not continue until the user confirms.

---

## Step 4 — Fetch active locations

Using `client_id` from Step 2. Fetch `facility_id` (the GoldenEye Facility ID stored on
the HubSpot location record) — needed for the REMOVE tab if this is an Ascend API client.
Paginate if total exceeds 50.

```bash
curl -s -X POST "https://api.hubapi.com/crm/v3/objects/2-14718097/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filterGroups":[{"filters":[
      {"propertyName":"client_id","operator":"EQ","value":"<CLIENT_ID>"},
      {"propertyName":"activity_status","operator":"EQ","value":"Active"}
    ]}],
    "properties":["location_name","facility_id","pms"],
    "sorts":[{"propertyName":"location_name","direction":"ASCENDING"}],
    "limit":50
  }'
```

For pagination, repeat with `"after": "<cursor>"` from `paging.next.after` until all
records are collected.

Verify the count against `of_locations___active` from Step 2. If counts differ, flag
it and let the user decide whether to proceed.

**Branch A (Full):** Use all locations returned. Confirm the count with the user.

**Branch B (Partial):** Present the full list as a numbered table. Pre-select any
locations whose names appear in `cancellation_name` (partial name match). Ask the user
to confirm the exact subset before continuing:

> Here are all **[N]** active locations for **[Client Name]**. Confirm which to include
> (pre-selected based on ticket name — adjust as needed):
>
> | # | Location Name | Facility ID | Include? |
> |---|---|---|---|
> | 1 | [name] | [id] | ✅ pre-selected |
> | 2 | [name] | [id] | ⬜ |

Wait for explicit confirmation before continuing.

---

## Step 5 — Confirm and associate locations to the cancellation ticket

Always confirm with the user before writing any data:

> Ready to associate **[N] locations** to ticket **"[cancellation_name]"**. Proceed?

Once confirmed, batch-associate using the v4 endpoint.
Association type: cancellations (`2-33013991`) ↔ locations (`2-14718097`),
`USER_DEFINED typeId 170`. Max 100 per batch — split into multiple calls if needed.

```bash
curl -s -X POST "https://api.hubapi.com/crm/v4/associations/2-33013991/2-14718097/batch/create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "from":{"id":"<TICKET_ID>"},
        "to":{"id":"<LOCATION_HUBSPOT_ID>"},
        "types":[{"associationCategory":"USER_DEFINED","associationTypeId":170}]
      }
    ]
  }'
```

Verify the response status is `COMPLETE` and result count matches locations sent.

> ✅ Associated **[N] locations** to [cancellation ticket](https://app.hubspot.com/contacts/<HUBSPOT_PORTAL_ID>/record/2-33013991/[TICKET_ID]/) for **[Client Name]**.

If any inputs errored, list them by name and offer to retry.

---

## Step 6 — Output: REMOVE tab paste block (Ascend API clients only)

**Skip this step if `pms` on the company record is not `ASCEND_API`.**

Generate tab-separated paste-ready data for the **Removed** tab of the Ascend Royalty
Reports Google Sheet.

### Column mapping

| Col | Header | Source |
|-----|--------|--------|
| A | Client Name | Company name, hyphenated (spaces → hyphens) |
| B | Facility Name | `location_name` from HubSpot |
| C | Date Removed | Offboarding date in `M/D/YY` format (e.g. `5/7/26`) |
| D | Goldeneye Facility ID | `facility_id` from HubSpot |

### Client name format

Derive the hyphenated GoldenEye-style name from the HubSpot company name by replacing
spaces with hyphens (e.g. "Smile Co" → `Smile-Co`). Show the derived name and ask for
confirmation before outputting — the GoldenEye format may differ from the HubSpot name:

> For the REMOVE tab I'll use client name **"[Hyphenated-Name]"** — does that match
> what's shown in GoldenEye?

### Output

Deliver a fenced code block, tab-separated, one row per location, no header row.
Date format is `M/D/YY` (two-digit year):

```
Smile-Co	Smile Co - Union Square	5/7/26	2308
Smile-Co	Smile Co - Fort Lee	5/7/26	2150
```

Then confirm:
> Paste starting at **A[N]** in the REMOVE tab — **[X] rows.**

---

## Step 7 — Write Claude context note

Read `skills/hubspot-context-note/SKILL.md` and run it. Pass the following:

| Field | What to pass |
|---|---|
| `ticket_id` | The cancellation ticket ID parsed in Step 1 |
| `origin` | `"Client offboarding — HubSpot cancellation ticket '[cancellation_name]'"` |
| `what_was_checked` | Location fetch result and count verification (e.g. "Fetched 12 active locations via client_id 4821. Count matched of_locations___active.") |
| `decisions` | Cancellation branch detected (Full / Partial / Ambiguous), any count mismatches flagged, Ascend API status, REMOVE tab generated (yes/no). Write `"None."` if all steps were clean. |
| `next_steps` | Omit unless something was left unresolved (e.g. "2 locations had null facility_id — REMOVE tab rows flagged for manual review.") |

The HubSpot token is already in scope — no need to retrieve it again.

---

## Edge cases

| Situation | Handling |
|---|---|
| No company association on ticket | Warn user; ask them to provide the client name manually to look up the company |
| `client_id` missing on company | Fall back to searching locations by `company_name CONTAINS_TOKEN` |
| Location count mismatch vs. `of_locations___active` | Flag before associating; let user decide whether to proceed |
| Batch > 100 locations | Split into multiple calls of 100; report combined totals |
| `facility_id` null on a location (Ascend API only) | Flag those rows in the REMOVE tab output; leave the ID cell blank |
| Ambiguous ticket name (no scope qualifier) | Default to Partial; surface ticket name prominently; ask user to confirm branch |
| `termination_date` present on ticket | Use it (correctly formatted) instead of today's date |

---

## Step 8 — Close browser tabs

Before logging, close any browser tabs that were opened during the HubSpot interaction using the **`chrome-cleanup`** helper skill.
Pass the `tabId` from your browser navigation response (if any tabs were opened).

---

## Step 9 — Log the run

After Step 8, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `client-offboarding` |
| `status` | `success` if locations were associated and the ticket updated · `partial` if association partially failed or REMOVE tab had null facility IDs · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: client name, cancellation branch (full/partial), number of locations associated to the ticket, and whether a REMOVE tab block was generated for Ascend API. |
| `inputs` | `ticket_url={url}` · `cancellation_type={full/partial}` |
| `outputs` | `locations_offboarded={N}` · `ticket_updated=true` · `remove_tab_generated={true/false}` · `tabs_closed=true` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `client_name={name}` · `ascend_api={true/false}` |

---
name: hubspot-ticket-generator
description: >
  Create a HubSpot Install Pipeline ticket from a GoldenEye facility URL.
  Browses the facility detail page to extract location data (name, PMS,
  address, phone, products), asks the user for ticket purpose, resolves the
  company and IT contact in HubSpot, creates the ticket with all associations,
  writes a Claude context note, and posts a Slack summary.
  Trigger when Sean says "create a ticket from this GoldenEye URL",
  "ticket this facility", or pastes a <GOLDENEYE_HOST> facility URL
  and asks to create a ticket.
---

# Skill: HubSpot Ticket Generator

Creates a HubSpot Install Pipeline ticket from a GoldenEye facility URL.
Browses the facility page, extracts location metadata, asks the user for
the ticket purpose, then builds and submits the ticket with company,
location, and IT contact associations.

---

## Prerequisites

Run the `get-secret` skill with name `hubspot-token` to retrieve the HubSpot API token.
See `id-claude-shared` plugin: `skills/_shared/hubspot-setup.md` — Steps B and C are handled by the `get-secret` skill.

Run the `get-secret` skill with name `slack-bot-token` to retrieve the Slack bot token.
See `id-claude-shared` plugin: `skills/_shared/slack-setup.md` — Section A (token retrieval) is handled by the `get-secret` skill.

---

## Key constants

| Item | Value |
|---|---|
| Install Pipeline ID | `66471460` |
| Opening stage (New) | `133962530` |
| Assigned owner (Sean Johnson) | `628638356` |
| Locations custom object | `2-14718097` |
| Ticket → Location association typeId | `153` (USER_DEFINED) |
| Plugin Slack channel | `<SLACK_DM_SEAN>` |

---

## Step 1 — Browse the GoldenEye facility page

### 1a — Primary method: Chrome DevTools MCP / Puppeteer with default Chrome

The GoldenEye dashboard (`<GOLDENEYE_HOST>`) requires Google SSO.
The user's default Chrome browser is normally already authenticated.

**Use Chrome DevTools MCP** (preferred) or **Puppeteer connected to the user's
running Chrome** to navigate to the facility URL. The Puppeteer MCP bundled
with Windsurf launches its own Chromium and will NOT have the user's session —
do NOT use it directly.

To connect to the user's running Chrome:

1. The user must have Chrome running with remote debugging enabled, OR Chrome
   144+ with `chrome://inspect/#remote-debugging` enabled.
2. Use Chrome DevTools MCP with `--autoConnect` or `--browser-url=http://127.0.0.1:9222`.

If the Chrome DevTools MCP server is not available or connection fails,
fall through to Step 1b.

### 1b — Fallback: Ask the user

If the page cannot be loaded (auth wall, MCP not configured, connection
refused), ask the user to provide the following details manually:

- Location name
- Parent company name
- PMS (practice management system)
- Address
- Phone
- Products (Assist, ERA, IQ, Settings, etc.)
- Status (Active / Inactive)

### 1c — Extract facility data

From the rendered page, extract:

| Field | Where to find it |
|---|---|
| `location_name` | Main heading (e.g. "Criswell Main St") |
| `company_name` | Shown above location name (e.g. "Marquee-Dental-Partners") — replace hyphens with spaces |
| `pms` | Listed below company name (e.g. "eaglesoft") — title-case for display |
| `address` | Full address line |
| `phone` | Phone number |
| `products` | Listed under "Products" (e.g. assist, era, iq, settings) |
| `status` | ACTIVE / INACTIVE badge |
| `facility_id` | From the URL path: `/facility/{id}/details` |

---

## Step 2 — Ask the user for ticket purpose

Present the user with a choice of ticket types:

| Option | Subject format | Category logic |
|---|---|---|
| **OOS (Out of Sync)** | `[company] - OOS - [location]` | See Step 2a |
| **Account Update** | `[company] - Account Update - [location]` | `Account Update` |
| **Escalation** | `[company] - Escalation - [location]` | `CHECK_ON` |
| **Installation Request** | `[company] - Install - [location]` | `Installation Request` |
| **Connection Issues** | `[company] - Connection Issues - [location]` | See Step 2a |

If the user provides a different purpose not listed above, use their text
as-is in the subject: `[company] - [purpose] - [location]`.

### Step 2a — Category for OOS / Connection Issues tickets

The category depends on the PMS detected in Step 1:

| PMS | Category value |
|---|---|
| Dentrix | `Bitwerks Connection issues` |
| Eaglesoft | `Bitwerks Connection issues` |
| Enterprise | `Bitwerks Connection issues` |
| Any other PMS | `Connection Issues` |

For non-OOS/Connection ticket types, use the category from the table above.

---

## Step 3 — Find the company in HubSpot

Search for the company by name:

```
search_crm_objects on "companies"
query: "[company_name]"
properties: ["name", "hs_object_id", "client_id", "of_locations___active", "pms"]
```

- **Single match**: use its `hs_object_id` as `company_id` and `client_id` for
  location lookup.
- **Multiple matches**: pick the closest name match; show ambiguous results to
  the user and confirm.
- **No match**: stop and notify the user — do not create unassociated tickets.

---

## Step 4 — Check for duplicate tickets

Search HubSpot for existing tickets matching this location in the Install
Pipeline:

```
search_crm_objects on "tickets"
query: "[location_name]"
filterGroups: [{ filters: [{ propertyName: "hs_pipeline", operator: "EQ", value: "66471460" }] }]
properties: ["subject", "hs_pipeline_stage", "createdate", "hs_object_id"]
```

If any returned ticket subject contains the location name → **stop** and
report to the user:

```
⚠️ Duplicate ticket found: [subject]
   https://app.hubspot.com/contacts/<HUBSPOT_PORTAL_ID>/ticket/[id]
```

If no match → proceed.

---

## Step 5 — Find the HubSpot location record

⚠️ **The HubSpot MCP `search_crm_objects` tool does NOT support the custom object type
`2-14718097`** — it returns a `VALIDATION_ERROR`. You MUST use Desktop Commander with a
direct `curl` call to the HubSpot API:

```bash
python3 -c "
import json, subprocess
token = '<hubspot_token>'
payload = {
    'filterGroups': [{'filters': [
        {'propertyName': 'client_id', 'operator': 'EQ', 'value': '<client_id>'},
        {'propertyName': 'location_name', 'operator': 'EQ', 'value': '<location_name>'}
    ]}],
    'properties': ['location_name', 'hs_object_id', 'client_id', 'pms'],
    'limit': 10
}
r = subprocess.run(
    ['curl', '-s', '-X', 'POST',
     'https://api.hubapi.com/crm/v3/objects/2-14718097/search',
     '-H', f'Authorization: Bearer {token}',
     '-H', 'Content-Type: application/json',
     '-d', json.dumps(payload)],
    capture_output=True, text=True
)
print(r.stdout)
"
```

If no results on exact match, fall back to `CONTAINS_TOKEN` on the distinctive part of the
name (last word, or part before a bracketed suffix like `[SGA]`):

```python
{ propertyName: "location_name", operator: "CONTAINS_TOKEN", value: "<fragment>" }
```

Store the matched `hs_object_id` as `location_id`. If no match is found,
continue without a location association and note it in the ticket body.

---

## Step 6 — Resolve IT contact

The goal is to find the best support-appropriate contact associated with the
company. Contacts are scored using a priority system.

### Step 6a — Fetch all associated contacts with labels

Use the v4 associations endpoint (paginated):

```python
GET /crm/v4/objects/companies/{company_id}/associations/contacts
```

Collect all results across pages.

### Step 6b — Score contacts for support relevance

Rank contacts using this priority order (highest first):

0. **IT/Install POC label (highest)** — Contact has the "IT/Install POC" association
   label (USER_DEFINED typeId 75) on this company. These are explicitly tagged as the
   IT vendor/contact for this client and should always be used first. The contact is
   often from a third-party managed services provider (e.g. Burke Onsite) whose contacts
   are NOT directly associated with the client company — only the IT/Install POC label
   links them. This label is the authoritative signal; do not skip it.

1. **External ticketing system** — Contact name contains "TICKET" or
   "HELPDESK" AND has a portal URL in either:
   - The `jobtitle` field (e.g. `https://encorehelpdesk.bz/login.php`) — this is
     the most common pattern; the portal URL is stored as the job title
   - The `email` field (less common — some clients store the URL there instead)
   Client requires all issues submitted via the portal — do NOT use email.
   Examples: "P4D HELPDESK TICKET SYSTEM", "IT TICKETING HELPDESK"

   ⚠️ **To detect this correctly**, you must fetch `jobtitle` during the scoring
   pass (not just after). Add `jobtitle` to the properties fetched in the
   associations batch or fetch each priority-1 candidate individually before
   scoring lower tiers.

2. **Shared inbox** — email local-part (before the @) exactly matches any of:
   `support`, `helpdesk`, `help`, `it`, `itsupport`, `tech`, `service`,
   `ticketing`, `desk`

3. **Support role** — job title contains any of: `support`, `technician`,
   `helpdesk`, `tech support`, `IT support`, `field tech`, `IT specialist`

4. **Account POC (lowest)** — contacts with the "Account POC" association label

Use the highest-scoring contact as `it_contact_id`. If multiple contacts tie
at the same score, prefer the one whose email domain matches the company domain.

### Step 6c — Fetch contact details

For the selected IT contact AND all Account POC contacts, fetch:
`email`, `firstname`, `lastname`, `jobtitle`, `phone`

All Account POCs will also be associated to the ticket (Step 7).

### Step 6d — Fallback: check recent ticket contacts

If no contact scores at tier 0–3 (only Account POCs found, or no contacts at all),
search the 3 most recent Install Pipeline tickets associated with this company and
collect all contacts on those tickets:

```python
# Search recent tickets for this company
POST /crm/v3/objects/tickets/search
filterGroups: [{ filters: [{ propertyName: "hs_pipeline", operator: "EQ", value: "66471460" }] }]
# Then check associations for company_id
sorts: [{ propertyName: "createdate", direction: "DESCENDING" }]
limit: 5
```

For each prior ticket, fetch its associated contacts via
`GET /crm/v4/objects/tickets/{ticket_id}/associations/contacts`.
Collect all unique contacts across those tickets.

**External-domain contacts are the key signal:** if any contact's email domain does NOT
match the client company's primary domain, that contact is almost certainly an IT vendor.
Use the external-domain contact as the IT contact and note the source as
"external IT vendor — identified from prior ticket history".

If the fallback also finds nothing useful, fall through to Account POC only.

---

## Step 7 — Build the ticket body

Format the ticket `content` as:

```
[company_name] — [Ticket Purpose Description]

Location: [location_name]
PMS: [pms]
Address: [address]
Phone: [phone]
Products: [products]
Status in GoldenEye: [status]

Issue
------------------------------
[Description based on ticket type. For OOS:]
PMS connection ([pms]) is not syncing correctly.
Troubleshooting needed to restore insurance claims data flow.

IT Contact
------------------------------
[contact_name]
[If external ticketing system:]
⚠️ Client requires all IT issues submitted via their helpdesk portal — do NOT use email.
Portal: [portal_url from jobtitle or email field]
[Otherwise:]
Email:   [it_contact_email]
Phone:   [it_contact_phone]
([resolution source — e.g. "shared inbox from company HubSpot record" or
  "external ticketing system — client requires portal submission"])

Source: GoldenEye facility [facility_id]
[goldeneye_url]
```

Adjust the "Issue" section based on ticket type:
- **OOS**: "PMS connection ([pms]) is not syncing correctly. Troubleshooting needed to restore insurance claims data flow."
- **Account Update**: "Account update required for this location."
- **Escalation**: "Issue escalated for this location — requires attention."
- **Installation Request**: "New installation requested for this location."
- **Connection Issues**: "Connection issues reported — investigation needed."

---

## Step 8 — Create the HubSpot ticket

### Step 8a — Create ticket with associations

Use `manage_crm_objects` or the HubSpot API to create the ticket:

| Property | Value |
|---|---|
| `subject` | `[company_name] - [purpose_code] - [location_name]` |
| `content` | (formatted body from Step 7) |
| `hs_pipeline` | `66471460` |
| `hs_pipeline_stage` | `133962530` |
| `hs_ticket_category` | (from Step 2 / Step 2a) |
| `hubspot_owner_id` | `628638356` |
| `source_type` | `EMAIL` |

Include associations in the create call:
- **Company**: `{ objectType: "companies", id: <company_id> }`
- **IT contact**: `{ objectType: "contacts", id: <it_contact_id> }`
- **Each Account POC**: `{ objectType: "contacts", id: <poc_id> }` (one per POC)

### Step 8b — Associate location record

After ticket creation, associate the location record using the v4 batch
endpoint:

```python
POST /crm/v4/associations/0-5/2-14718097/batch/create
{
    "inputs": [{
        "from": {"id": "<ticket_id>"},
        "to": {"id": "<location_id>"},
        "types": [{"associationCategory": "USER_DEFINED", "associationTypeId": 153}]
    }]
}
```

If the location was not found in Step 5, skip this sub-step and note it in the
context note.

### Step 8c — Get the ticket URL

```python
ticket_url = f"https://app.hubspot.com/contacts/<HUBSPOT_PORTAL_ID>/ticket/{ticket_id}"
```

---

## Step 9 — Post Slack notification

Post to `<SLACK_DM_SEAN>` using the Slack Web API via Desktop Commander.

**Important:** The Slack MCP tool returns `restricted_action_read_only_channel`
for this channel. Use Desktop Commander with the Slack Web API directly instead.

Run the `get-secret` skill with name `slack-bot-token` to retrieve the Slack bot token (if not already retrieved in Prerequisites).

Post the message:
```python
message = (
    f":ticket: *{purpose_code} Ticket Created — {company_name}*\n"
    f"*{location_name}* · {pms}\n"
    f"IT Contact: {it_contact_name} ({it_contact_email})\n"
    f"Location associated: {'✅' if location_id else '⚠️ not found'}\n"
    f"<{ticket_url}|View HubSpot ticket>"
)
```

If Slack returns an error, note it but do not fail the skill — ticket creation
is the primary deliverable.

---

## Step 10 — Write Claude context note

⚠️ **Format requirement:** The context note MUST be exactly 2 lines — the marker header and a
base64-encoded JSON payload — as specified in `hubspot-context-note/SKILL.md`. Do NOT create
plain-text engagement notes via the engagements API. The hubspot-context-note skill handles
the encoding and the correct API endpoint (`POST /crm/v3/objects/notes`).

Read `skills/hubspot-context-note/SKILL.md` and run it. Pass:

| Field | Value |
|---|---|
| `ticket_id` | The ticket ID from Step 8 |
| `origin` | `"GoldenEye facility [facility_id] — [purpose] ticket — [date]"` |
| `what_was_checked` | Duplicate check result + company match + location match + IT contact resolution (source and scoring) |
| `decisions` | Category selection rationale (PMS-based for OOS), IT contact scoring outcome, any fallbacks used |
| `next_steps` | Based on ticket type (e.g. "Troubleshoot [pms] connection" for OOS, "Review account details" for Account Update) |

The HubSpot token is already in scope — no need to retrieve it again.

---

## Step 10b — Optional: Gmail draft (DOS follow-up)

If the user requests a Gmail draft as part of this workflow, use the official DOS email
template. Do NOT freeform the message body.

**Template location:** `templates/install/INSTALL - Claim Dates DOS.md`

Read that file for the exact subject line and body. Key rules:
- **Subject:** `[Company Name] - Request for Status Update on Claims Activity`
- **Body:** List affected offices inline (one per line) as `- [Location Name] — Last DOS: [MM/DD/YYYY]`. Do NOT include a screenshot.
- **Recipients:** Address ONLY the Account POC contacts retrieved in Step 6 (not all contacts). If the user specifies a subset of POCs, use only those.
- **CC:** Always CC `install@insidedesk.com`.
- Create the draft via the Gmail MCP `create_draft` tool.

After creating the draft, log it as an email engagement on the ticket:

```python
POST /crm/v3/objects/emails
{
  "properties": {
    "hs_email_direction": "EMAIL",
    "hs_email_status": "DRAFT",
    "hs_email_subject": "<subject>",
    "hs_email_text": "<body text>",
    "hs_timestamp": "<current unix ms>"
  },
  "associations": [{"objectType": "tickets", "id": "<ticket_id>", "associationTypeId": 218}]
}
```

---

## Step 11 — Report results

Print a clean summary:

```
✅ Ticket Created
   Subject:  [company_name] - [purpose_code] - [location_name]
   Ticket:   [ticket_url]
   Category: [category]

   Associations:
     Company:  [company_name] (ID [company_id])
     Location: [location_name] (ID [location_id]) — or "⚠️ not matched"
     IT:       [it_contact_name] ([it_contact_email]) — [resolution source]
     POCs:     [poc_names] — or "none found"

   Slack: ✅ sent / ⚠️ failed
   Context note: ✅ written
```

---

## Edge cases

- **GoldenEye page requires auth**: Fall back to asking the user for facility
  details (Step 1b). Do not attempt to enter credentials.
- **Company not found in HubSpot**: Stop and notify the user. Do not create
  unassociated tickets.
- **Location record not found**: Create the ticket without a location
  association. Note in the ticket body and context note.
- **No IT contact found**: Look for Account POCs. If none found either, create
  the ticket with only the company association. Note in summary.
- **Ticketing system contact found**: Note the portal URL prominently in the
  ticket body (e.g. "Client requires submissions via [portal URL]").
- **Multiple companies match**: Show matches to the user and ask which one.
- **Duplicate ticket found**: Stop and show the existing ticket URL. Do not
  create a second ticket.
- **PMS not recognized for category**: Default to `Connection Issues` for
  OOS/connection tickets. For other ticket types, use the type-specific
  category.
- **Company name has hyphens in GoldenEye**: Replace hyphens with spaces for
  display and HubSpot search (e.g. "Marquee-Dental-Partners" → "Marquee
  Dental Partners").

---

## Step 12 — Close browser tabs

Before logging, close any GoldenEye tabs that were opened during Steps 1-11 using the **`chrome-cleanup`** helper skill.
Pass the `tabId` from your browser navigation response.

---

## Step 13 — Log the run

After Step 12, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `hubspot-ticket-generator` |
| `status` | `success` if the ticket was created · `error` if company not found or duplicate detected |
| `summary` | 1–3 sentences: location name, ticket purpose, ticket URL created, and whether company/location/IT contact associations succeeded. |
| `inputs` | `goldeneye_url={url}` · `ticket_purpose={purpose}` |
| `outputs` | `ticket_url={url}` · `ticket_id={id}` · `location_associated={true/false}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `company_name={name}` · `location_name={name}` · `it_contact_email={email}` |

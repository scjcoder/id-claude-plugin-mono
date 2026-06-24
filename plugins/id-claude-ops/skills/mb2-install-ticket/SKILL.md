---
name: mb2-install-ticket
description: Create HubSpot Install Pipeline tickets for new MB2 additional locations. Reads Monday Board install-approval emails from Gmail (last 7 days), checks for duplicate tickets, finds or creates the IT contact, and creates the ticket associated to MB2 Dental and the IT contact. Use whenever Sean says "create install ticket", "process MB2 installs", "check Monday installs", or pastes a location name and asks to ticket it.
---

# Skill: MB2 Install Ticket Creator

Automates creating HubSpot Install Pipeline tickets for new MB2 additional locations.
The source of truth is Gmail — Monday Board sends a structured approval email every time
Tye Powell or Karina Mendoza tags @Sean Johnson on a "To Be Installed" update.

---

## Prerequisites

Run the `get-secret` skill with name `hubspot-token` to retrieve the HubSpot API token.
See `id-claude-shared` plugin: `skills/_shared/hubspot-setup.md` — Steps B (aws-login) and C (token retrieval) are handled by the `get-secret` skill.

Run the `get-secret` skill with name `slack-bot-token` to retrieve the Slack bot token.
See `id-claude-shared` plugin: `skills/_shared/slack-setup.md` — Section A (token retrieval) is handled by the `get-secret` skill.

---

## Key constants

| Item | Value |
|---|---|
| MB2 Dental HubSpot company ID | `5859417920` |
| Install Pipeline ID | `66471460` |
| Opening stage (New) | `133962530` |
| Ticket category | `+_OFFICES` |
| Assigned owner (Sean Johnson) | `628638356` |
| Plugin Slack channel | `<SLACK_DM_SEAN>` |

---

## Step 1 — Find approval emails in Gmail

Search Gmail for Monday Board install-approval emails from the last 7 days:

```
from:notifications@monday.com subject:"[New mention]" -subject:"Re:" newer_than:7d
```

Use `search_threads` with that query. For each result, fetch the full thread body
(`get_thread` with `messageFormat: FULL_CONTENT`) and check whether the
`plaintextBody` contains `Approved by`. That phrase is the definitive signal that
this is an install approval — not the presence of a `Vendor:` line, which is absent
for in-house IT installs.

Skip silently if the body does **not** contain `Approved by` (e.g. general questions,
name-change requests, cancellation mentions).

If no qualifying emails are found, report: "No new install approvals found in Gmail
for the last 7 days."

---

## Step 2 — Parse each email

Fetch the full thread body (`get_thread` with `messageFormat: FULL_CONTENT`).

The `plaintextBody` follows this structure:

```
[Sender] mentioned you on an update on [Location Name]:

@Sean Johnson @[Other] [Approval Text]
[IT Type]
Vendor: [Vendor Name]
POC: [POC Name]
POC Email: [email] and [email2]          <- sometimes multiple
Phone: [phone] or [phone2]               <- sometimes multiple
+@[Person] for Visibility

View update on the pulse [Monday URL]
```

Extract these fields using Python string parsing (split on newlines, strip whitespace
and zero-width chars, &nbsp;):

| Field | How to extract |
|---|---|
| `location_name` | First line of body: `"...update on [Location Name]:"` |
| `approval_text` | Line starting after the @mentions block |
| `it_type` | Line containing "party IT" or "MB2 IT" or "In-house IT" or "in house IT" (e.g. "3rd party IT", "In-house IT", "MB2 IT") |
| `vendor` | Line starting with `Vendor:` |
| `poc_name` | Line starting with `POC:` (not `POC Email:`) |
| `poc_email` | Line starting with `POC Email:` — may contain `and` for multiple |
| `poc_phone` | Line starting with `Phone:` — may contain `or` for multiple |
| `monday_url` | Line containing `https://mb2dental-team.monday.com/posts/` |

---

## Step 3 — Check for duplicate tickets

Before creating anything, search HubSpot for an existing ticket for this location.
Note: tickets use slightly inconsistent subject prefixes ("Add Location" vs "Additional
Location") — search broadly by location name:

```
search_crm_objects on "tickets"
query: "[location_name]"
filterGroups: [{ filters: [{ propertyName: "hs_pipeline", operator: "EQ", value: "66471460" }] }]
properties: ["subject", "hs_pipeline", "hs_pipeline_stage", "createdate"]
```

If any returned ticket subject contains the location name → **skip** this location,
note it in the final report as "Already ticketed: [link]".
If no match → proceed to Step 4.

---

## Step 4 — Resolve IT contact (vendor company lookup first)

The goal is to associate a *support-appropriate* contact rather than blindly using
the individual MB2 named — who is often a sales or field rep, not the actual helpdesk.

### Step 4a — Look up vendor company in HubSpot

If `vendor` is not empty and not "In-house IT", search HubSpot companies by name:

```
search_crm_objects on "companies"
query: "[vendor]"
properties: ["name", "domain"]
```

If a company match is found, fetch all associated contacts:

```
search_crm_objects on "contacts"
filterGroups: [{ associatedWith: [{ objectType: "companies", operator: "EQUAL", objectIdValues: [company_id] }] }]
properties: ["email", "firstname", "lastname", "jobtitle", "phone"]
```

### Step 4b — Score contacts for support relevance

Rank the retrieved contacts using this priority order:

1. **Shared inbox (highest)** — email local-part (before the @) exactly matches any of:
   `support`, `helpdesk`, `help`, `it`, `tech`, `service`, `ticketing`, `desk`
   (e.g. `support@example.com`, `helpdesk@example.com`)

2. **Support role** — job title contains any of: `support`, `technician`, `helpdesk`,
   `tech support`, `IT support`, `field tech`

3. **Named POC from MB2 email** — fallback if no higher-priority contact found

Use the highest-scoring contact as `it_contact_id`. Note which source was used
(vendor HubSpot record vs. MB2-provided) for inclusion in the ticket body (Step 5).

If multiple contacts tie at the same score, prefer the one whose email domain matches
the vendor company's domain.

### Step 4c — Named POC fallback

If no vendor company match in HubSpot, or the company has no associated contacts,
fall back to the MB2-named contact:

```
search_crm_objects on "contacts"
filterGroups: [{ filters: [{ propertyName: "email", operator: "EQ", value: poc_email }] }]
properties: ["email", "firstname", "lastname", "phone"]
```

- **Found**: use the existing contact ID.
- **Not found**: create with `manage_crm_objects`:
  - `firstname`: first word of POC name
  - `lastname`: remaining words (or "IT" if only one name given)
  - `email`: poc_email
  - `phone`: poc_phone
  - `company`: vendor name
  - `jobtitle`: "IT Support"

---

## Step 5 — Build the ticket body

Format the ticket `content` (description) as:

```
MB2 Additional Location -- Install Approval

Location: [location_name]
Approval: [approval_text]

IT Contact
------------------------------
Type:    [it_type]
Vendor:  [vendor]
POC:     [poc_name]  (per MB2)
Email:   [it_contact_email]
Phone:   [poc_phone]

Monday Board: [monday_url]
```

If the IT contact email was resolved from the vendor company record (Step 4a/4b)
rather than the MB2-provided address, add a parenthetical note on the Email line:
`(resolved from vendor HubSpot record; MB2 provided: [original_poc_email])`

---

## Step 6 — Create the HubSpot ticket

Use `manage_crm_objects` to create the ticket with these properties:

| Property | Value |
|---|---|
| `subject` | `MB2 - Add Location - [location_name]` |
| `content` | (formatted body from Step 5) |
| `hs_pipeline` | `66471460` |
| `hs_pipeline_stage` | `133962530` |
| `hs_ticket_category` | `+_OFFICES` |
| `hubspot_owner_id` | `628638356` |
| `source_type` | `EMAIL` |

Include associations in the same call:
- Associate to **MB2 Dental** company: `{ objectType: "companies", id: 5859417920 }`
- Associate to **IT contact**: `{ objectType: "contacts", id: <it_contact_id> }`

---

## Step 7 — Post Slack notification

After each ticket is successfully created, post a message to `<SLACK_DM_SEAN>`.

**Important:** The Slack MCP tool returns `restricted_action_read_only_channel` for
this channel. Use Desktop Commander with the Slack Web API directly instead.

Run the `get-secret` skill with name `slack-bot-token` to retrieve the Slack bot token.

Then post via Desktop Commander (Python):
```python
import requests

token = "<bot_token_from_above>"
channel = "<SLACK_DM_SEAN>"

message = (
    f":new: *MB2 Install Ticket Created*\n"
    f"*{location_name}*\n"
    f"Vendor: {vendor} ({it_type})\n"
    f"IT contact: {it_contact_email}\n"
    f"<{ticket_url}|View HubSpot ticket>"
)

resp = requests.post(
    "https://slack.com/api/chat.postMessage",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={"channel": channel, "text": message, "mrkdwn": True}
)
result = resp.json()
if not result.get("ok"):
    print(f"Slack notification failed: {result.get('error')}")
else:
    print("Slack notification sent.")
```

If Slack returns an error, note it in the chat summary but do not fail the skill —
ticket creation is the primary deliverable.

---

## Step 8 — Report results

After processing all emails, print a clean summary:

```
Tickets Created (N)
  - [Location Name] -> [HubSpot link]
      IT: [contact name or shared inbox] ([contact email])

Already Ticketed (N)
  - [Location Name] -> [existing ticket link]
```

---

## Step 9 — Write Claude context note

For each ticket created in Step 6, read `skills/hubspot-context-note/SKILL.md` and
run it. Pass the following, assembled from what you found in this workflow:

| Field | What to pass |
|---|---|
| `ticket_id` | The numeric ID of the ticket just created |
| `origin` | `"MB2 Monday Board install-approval email · [date] · Subject: [email subject]"` |
| `what_was_checked` | Duplicate check result + IT contact outcome (e.g. "No duplicate found. IT contact Dave Kowalski — matched existing contact.") |
| `decisions` | Any fuzzy name matches, partial name normalization, or in-house IT handling. Write `"None."` if everything was straightforward. |
| `next_steps` | Omit unless there's a reason to follow up (e.g. "In-house IT — no external contact created.") |

The HubSpot token is already in scope — no need to retrieve it again.

---

## Step 10 — Run MB2 Monday → GoldenEye facility entry

After Step 9 completes (regardless of whether any new tickets were created this run),
invoke the `id-claude-ops:mb2-monday-to-ge` skill in **unattended mode**.

This step runs unconditionally — even if no new install tickets were found. It checks
the Monday Board "To Be Installed" group and creates GoldenEye facilities for any office
not yet present, auto-skipping any that already exist.

Pass this context to the skill: **"This is an unattended run — do not ask for confirmation
before entering facilities. Auto-skip any facilities already in GoldenEye."**

---

## Step 11 — Log the run

After Step 10, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `mb2-install-ticket` |
| `status` | `success` if all qualifying emails were processed · `partial` if any tickets failed or Slack notification failed · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: number of install tickets created, number of locations already ticketed (skipped), and any IT contact resolution notes. |
| `inputs` | `date_range=last 7 days` · `emails_scanned={count}` |
| `outputs` | `tickets_created={N}` · `duplicates_skipped={N}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{}` |

---

## Edge cases

- **Multiple POC emails**: use the first for contact lookup/creation; include all in the ticket body.
- **In-house IT (no Vendor)**: skip Step 4a/4b entirely; fall back to Step 4c using the named contact.
- **Email has no Vendor: line**: this is normal for in-house IT installs. If the body contains `Approved by`, treat it as a valid approval and proceed — the absence of `Vendor:` simply means it's in-house IT with no external vendor to look up.
- **Ticket subject already exists in any pipeline**: still skip — one ticket per location regardless of pipeline.
- **Multiple contacts tie in Step 4b**: prefer the one whose email domain matches the vendor company domain.

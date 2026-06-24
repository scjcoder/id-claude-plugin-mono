---
name: create-kolla-invite
description: >
  Generate a Kolla KollaConnect invite link for a new InsideDesk facility and
  log the result to the HubSpot install ticket. Looks up facility metadata from
  GoldenEye, navigates the Kolla Admin Panel to create the invite link, captures
  the generated URL, and posts both a human-readable HTML note and a base64
  Claude context note to the HubSpot ticket.
  Trigger when Sean says "create a Kolla invite for [facility]", "generate a
  Kolla link for [facility]", "send [facility] a Kolla connect link", or pastes
  a GoldenEye facility URL and asks to set up the Kolla connection.
---

# Skill: Create Kolla Invite Link

Generates a Kolla KollaConnect invite link for a new facility and logs everything
to the HubSpot install ticket. The invite link is what the office's IT contact
opens to authorize their PMS connection to InsideDesk via Kolla.

---

## Prerequisites

Run the `get-secret` skill with name `hubspot-token` to retrieve the HubSpot
API token. See `id-claude-shared` plugin: `skills/_shared/hubspot-setup.md`.

---

## Key constants

| Item | Value |
|---|---|
| Kolla Admin Panel | `https://app.getkolla.com/eiyesv3p6jfpvfhxgsnu45qyla/linked-accounts` |
| Contact email (always) | `install@insidedesk.com` |
| HubSpot Portal ID | `<HUBSPOT_PORTAL_ID>` |

### PMS → Kolla connector mapping

| GoldenEye PMS | Kolla connector name |
|---|---|
| eaglesoft | Eaglesoft |
| dentrix | Dentrix Core |
| dentrix enterprise | Dentrix Enterprise |
| opendental | OpenDental |

If the PMS doesn't appear in this table, ask Sean which connector to use before
proceeding.

---

## Step 1 — Get facility data from GoldenEye

If the user provides a GoldenEye facility URL (e.g.
`https://<GOLDENEYE_HOST>/production/admin/facility/3343/details`),
extract the facility ID from the path and navigate to that URL in the
Claude-controlled browser.

If no URL is provided but a facility name was given, search:
```
https://<GOLDENEYE_HOST>/production/admin/facility?search=<URL-encoded name>
```
and select the matching result.

From the details page, extract:

| Field | Where to find it |
|---|---|
| `facility_id` | URL path: `/facility/{id}/details` |
| `facility_name` | Main heading |
| `client` | Shown above facility name (e.g. "Gen4-Dental-Partners") |
| `pms` | Listed below client name (e.g. "eaglesoft") |
| `status` | ACTIVE / INACTIVE badge |

Map `pms` to the Kolla connector name using the table above.

---

## Step 2 — Navigate to Kolla and open the Create Invite Link modal

Navigate the Claude-controlled browser to the Kolla Admin Panel:

```
https://app.getkolla.com/eiyesv3p6jfpvfhxgsnu45qyla/linked-accounts
```

Click the blue **"Create Invite Link"** button in the top-right corner.

A modal will appear with four fields:
- Select Connector (required dropdown)
- Unique Consumer Identifier (required text)
- Customer Company Name (optional text)
- Contact Email (optional text)

---

## Step 3 — Fill the form

| Field | Value |
|---|---|
| **Select Connector** | Mapped connector name from Step 1 (e.g. "Eaglesoft") |
| **Unique Consumer Identifier** | GoldenEye facility ID (e.g. `3343`) |
| **Customer Company Name** | `{client} - {facility_name}` (e.g. "Gen4-Dental-Partners - JML Lapierre") |
| **Contact Email** | `install@insidedesk.com` (always — this address is never used to send the link) |

Click the **"Generate Link"** button.

---

## Step 4 — Capture the generated URL immediately

⚠️ **Critical:** The generated URL is only shown once in the confirmation modal.
You MUST capture it before clicking Finish or closing the modal.

After clicking Generate Link, a second modal appears with the invite URL.
The URL field is truncated visually — use JavaScript to read the full value:

```javascript
Array.from(document.querySelectorAll('input')).map(i => i.value)
```

The invite URL will be in the array (look for the entry starting with
`https://link.kolla.market/link/`). Store it as `invite_link`.

Note: The link expires in **7 days**. Calculate the expiry date as today + 7 days.

Click **"Finish"** to close the modal.

---

## Step 5 — Post a human-readable HTML note to the HubSpot ticket

Read `skills/hubspot-human-note/SKILL.md` and run it. Pass:

- `ticket_id`: the HubSpot ticket ID
- `sections`: the list below, with placeholders replaced by actual values

```python
[
  {
    "type": "table",
    "title": "🔗 Invite Link (expires {expiry_date})",
    "rows": [
      ["Kolla Invite URL", "<a href=\"{invite_link}\">{invite_link}</a>"],
      ["Expires",          "{expiry_date} (7 days) — send to IT contact promptly"]
    ]
  },
  {"type": "divider"},
  {
    "type": "table",
    "title": "Facility Details",
    "rows": [
      ["Facility",               "{facility_name}"],
      ["Client",                 "{client}"],
      ["PMS / Connector",        "{kolla_connector}"],
      ["GoldenEye Facility ID",  "{facility_id}"],
      ["Consumer ID (Kolla)",    "{facility_id}"],
      ["Company Name (Kolla)",   "{client} - {facility_name}"],
      ["Contact Email",          "install@insidedesk.com"]
    ]
  },
  {"type": "divider"},
  {
    "type": "text",
    "body": "Next step: send this link to the office IT contact to authorize their {kolla_connector} connection to InsideDesk via Kolla. Monitor GoldenEye for first successful snapshot."
  }
]
```

The `hubspot-token` is already in scope — no need to retrieve it again.

---

## Step 6 — Post a Claude context note (base64)

Generate the base64-encoded payload via Desktop Commander:

```bash
python3 -c "
import base64, json, time, datetime

payload = {
  'v': 2,
  'updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
  'origin': 'create-kolla-invite skill — {date}',
  'checked': 'GoldenEye facility {facility_id} details retrieved. PMS: {pms}. Kolla connector mapped to: {kolla_connector}.',
  'decisions': 'Consumer ID set to GoldenEye facility ID ({facility_id}). Company name formatted as \"{client} - {facility_name}\". Contact email always install@insidedesk.com.',
  'next': 'Send invite link to IT contact. Monitor GoldenEye snapshots for first successful sync. Link expires {expiry_date}.'
}
print(base64.b64encode(json.dumps(payload).encode()).decode())
"
```

Compose the note body as exactly two lines:

```
🤖 CLAUDE CONTEXT [v2 · YYYY-MM-DD HH:MM]
<base64 string>
```

⚠️ **Timestamp must be generated dynamically.** Run:

```bash
python3 -c "import time; print(int(time.time() * 1000))"
```

Use `manage_crm_objects` to create the note (same pattern as Step 5, same ticket association).

---

## Step 7 — Report results

Print a clean summary:

```
✅ Kolla Invite Link Created — {facility_name} ({client})

   Connector:    {kolla_connector}
   Consumer ID:  {facility_id}
   Invite Link:  {invite_link}
   Expires:      {expiry_date}

   HubSpot notes: ✅ HTML note posted · ✅ Claude context note posted
```

---

## Edge cases

- **PMS not in connector mapping**: ask Sean which Kolla connector to select before
  opening the modal. Do not guess.
- **GoldenEye requires auth**: the Claude-controlled browser should already be
  authenticated. If not, ask Sean to log in and retry.
- **Kolla page requires auth**: the Claude-controlled browser should already be
  authenticated. If not, ask Sean to log in and retry.
- **Generated URL not found in input fields**: take a screenshot and zoom in to
  try to read the truncated URL visually. If still unreadable, alert Sean
  immediately before clicking Finish.
- **No HubSpot ticket provided**: generate the link and report the URL to Sean
  directly. Skip Steps 5–6 and note that no ticket was updated.
- **Link already exists for this consumer ID**: Kolla may warn about a duplicate
  consumer ID. Ask Sean whether to proceed with a new link anyway.

---

## Step 8 — Log the run

After Step 7, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `create-kolla-invite` |
| `status` | `success` if the invite link was generated and notes posted · `error` if the link could not be captured or Kolla was unavailable |
| `summary` | 1–3 sentences: facility name, connector used, invite link generated, HubSpot ticket updated. |
| `inputs` | `facility_id={id}` · `pms={pms}` · `ticket_id={ticket_id}` |
| `outputs` | `invite_link={url}` · `expires={expiry_date}` · `kolla_connector={connector}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `client={client}` · `facility_name={facility_name}` · `consumer_id={facility_id}` |

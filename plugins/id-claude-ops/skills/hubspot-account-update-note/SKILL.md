---
name: hubspot-account-update-note
description: Post a formatted ACCOUNT UPDATE note to a HubSpot ticket. Use this skill whenever Sean needs to document a change to an account field — TIN, address, facility name, email address, contact info, phone number, or similar. The note includes the field that changed, the old and new values, and a routing guide (Install vs CS) so whoever reads the ticket knows who to assign the work to. AUTOMATICALLY trigger this skill — without waiting to be asked — whenever Sean says "add an account update note", "log this change to the ticket", "document this update in HubSpot", or pastes a before/after value and asks to note it on a ticket.
---

# Skill: HubSpot Account Update Note

Posts a standardized ACCOUNT UPDATE note to a HubSpot ticket's activity feed.
Includes what changed (old → new) and the routing guide so the team knows whether
to assign to Install or CS.

---

## Prerequisites

The `hubspot-token` must already be in scope. If not, run the `get-secret` skill
with name `hubspot-token` first.

⚠️ All commands run via **Desktop Commander** (`mcp__Desktop_Commander__start_process`).
Never use `mcp__workspace__bash` — it has no access to host credentials or keychain.

---

## Collect inputs

You need:

| Field | Description | Example |
|---|---|---|
| `ticket_id` | HubSpot ticket ID (numeric) | `12345678` |
| `what` | The field or thing that changed | `TIN`, `Address`, `Email address` |
| `old_value` | The previous value | `12-3456789` |
| `new_value` | The new value | `98-7654321` |

If Sean doesn't provide all four, ask before proceeding. Don't guess values.

---

## Routing guide

Use this to determine — and tell Sean — who should be assigned the follow-up work:

**Assign to Install:**
- TIN
- Address
- Facility Name Change

**Assign to CS:**
- Email address
- Contact changes
- Phone numbers
- Other (ask team if unsure)

Include the full routing guide in the note body so it's visible to anyone reading
the ticket — they shouldn't need to know this from memory.

---

## Step 1 — Build the note HTML

Run this via Desktop Commander:

```python
import datetime

what = "<what>"
old_value = "<old_value>"
new_value = "<new_value>"

note_body = f"""
<div style="font-family:sans-serif;font-size:14px;line-height:1.6">

  <h3 style="margin:0 0 12px 0;font-size:15px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#333">
    Account Update
  </h3>

  <table style="border-collapse:collapse;width:100%;background:#fafafa;border-radius:6px;margin-bottom:16px">
    <tbody>
      <tr style="border-bottom:1px solid #e8e8e8">
        <td style="padding:8px 12px;color:#888;width:120px;vertical-align:top">What</td>
        <td style="padding:8px 12px;font-weight:500">{what}</td>
      </tr>
      <tr style="border-bottom:1px solid #e8e8e8">
        <td style="padding:8px 12px;color:#888;vertical-align:top">Old Value</td>
        <td style="padding:8px 12px">{old_value}</td>
      </tr>
      <tr>
        <td style="padding:8px 12px;color:#888;vertical-align:top">New Value</td>
        <td style="padding:8px 12px">{new_value}</td>
      </tr>
    </tbody>
  </table>

  <hr style="border:none;border-top:1px solid #e8e8e8;margin:12px 0">

  <p style="margin:0 0 6px 0;font-size:13px;color:#888;font-weight:500">Routing Guide</p>

  <table style="border-collapse:collapse;width:100%;font-size:13px">
    <tbody>
      <tr style="vertical-align:top">
        <td style="padding:6px 12px 6px 0;color:#555;width:50%">
          <strong>Assign to Install</strong><br>
          TIN<br>
          Address<br>
          Facility Name Change
        </td>
        <td style="padding:6px 0;color:#555">
          <strong>Assign to CS</strong><br>
          Email address<br>
          Contact changes<br>
          Phone numbers<br>
          Other – ask team
        </td>
      </tr>
    </tbody>
  </table>

</div>
"""

print(note_body.strip())
```

Substitute actual values before running. Capture the output as `note_body`.

---

## Step 2 — Generate timestamp

```python
import datetime
print(int(datetime.datetime.now().timestamp() * 1000))
```

Store as `hs_timestamp`.

---

## Step 3 — Post the note

```python
import json, subprocess

token = '<hubspot_token>'
note_body = '<note_body>'  # HTML from Step 1
hs_timestamp = '<hs_timestamp>'
ticket_id = '<ticket_id>'

payload = {
    'properties': {
        'hs_note_body': note_body,
        'hs_timestamp': hs_timestamp
    },
    'associations': [{
        'to': {'id': ticket_id},
        'types': [{'associationCategory': 'HUBSPOT_DEFINED', 'associationTypeId': 228}]
    }]
}

r = subprocess.run(
    ['curl', '-s', '-X', 'POST',
     'https://api.hubapi.com/crm/v3/objects/notes',
     '-H', f'Authorization: Bearer {token}',
     '-H', 'Content-Type: application/json',
     '-d', json.dumps(payload)],
    capture_output=True, text=True
)
data = json.loads(r.stdout)
print('Note ID:', data.get('id', 'ERROR'))
if not data.get('id'):
    print(data)
```

---

## Step 4 — Confirm

Tell Sean:

```
✅ Account Update note posted to ticket <ticket_id> (note ID: <note_id>)

What changed: <what>
Old: <old_value> → New: <new_value>

Routing: assign to <Install/CS> based on the routing guide.
```

If the change type is ambiguous (e.g. "Other"), flag it: "This falls under CS / ask the team."

---

## Step 5 — Log the run

Call the **`skill-logger`** skill with:

| Field | Value |
|---|---|
| `skill_name` | `hubspot-account-update-note` |
| `status` | `success` or `error` |
| `summary` | Account update note posted for field `<what>` on ticket `<ticket_id>` |
| `inputs` | `ticket_id`, `what`, `old_value`, `new_value` |
| `outputs` | `note_id` |
| `errors` | Any API failures (empty if none) |

---

## Key constants

| Item | Value |
|---|---|
| Note → Ticket association typeId | `228` (HUBSPOT_DEFINED) |
| HubSpot portal ID | `<HUBSPOT_PORTAL_ID>` |

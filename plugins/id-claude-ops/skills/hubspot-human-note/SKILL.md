---
name: hubspot-human-note
description: Add a nicely formatted HTML note to a HubSpot ticket. Use this skill whenever any workflow needs to post a human-readable structured note — key/value data, section tables, or free-text blocks — to a ticket's activity feed. Trigger when another skill says "write a human note", "add a note to the ticket", or "post the details to HubSpot". Also trigger directly when the user says "add a note to this ticket" and provides structured data (org details, contact info, status updates, etc.). This skill handles formatting — the caller just passes sections and data.
---

# Skill: HubSpot Human Note

Posts a nicely formatted HTML note to a HubSpot ticket's activity feed. Handles
layout and styling — callers pass structured data and this skill renders it cleanly.

Designed to be called by other skills whenever they need to leave a human-readable
record on a ticket. Complements `hubspot-context-note` (which is machine-readable
Claude memory) — this skill is for notes the team will actually read.

---

## Prerequisites

The `hubspot-token` must already be in scope (retrieved via `get-secret`). If not,
run the `get-secret` skill with name `hubspot-token` first.

⚠️ All commands run via **Desktop Commander** (`mcp__Desktop_Commander__start_process`).
Never use `mcp__workspace__bash` — it has no access to host credentials or keychain.

---

## What to collect before writing

The calling skill passes these values:

| Field | Description | Required? |
|---|---|---|
| `ticket_id` | HubSpot ticket ID (numeric string) | Yes |
| `sections` | Ordered list of sections to render (see formats below) | Yes |
| `note_id` | Existing note ID — if provided, update in place instead of creating | No |

### Section formats

Each section is one of three types:

**Key-value table** — the standard format for structured data:
```
{
  "type": "table",
  "title": "Ascend / CDC Details",
  "rows": [
    ["Organization ID", "69fb999444e96d20bbab2e27"],
    ["Practice name (CDC)", "ASPD"],
    ["Status", "active"]
  ]
}
```

**Free text** — a paragraph block:
```
{
  "type": "text",
  "title": "Notes",          ← optional; omit for untitled block
  "body": "Some prose here."
}
```

**Divider** — a horizontal rule between sections:
```
{ "type": "divider" }
```

Multiple sections are stacked vertically with spacing between them.

---

## Step 1 — Build the HTML note body

Use Desktop Commander to render sections into HTML:

```bash
python3 -c "
sections = [...]   # filled in by caller

parts = []
for s in sections:
    if s['type'] == 'table':
        rows_html = ''
        for i, (label, value) in enumerate(s['rows']):
            border = 'border-bottom:1px solid #e8e8e8' if i < len(s['rows']) - 1 else ''
            rows_html += (
                f'<tr style=\"{border}\">'
                f'<td style=\"padding:8px 12px;color:#888;width:220px;vertical-align:top\">{label}</td>'
                f'<td style=\"padding:8px 12px\">{value}</td>'
                f'</tr>'
            )
        title_html = f'<h3 style=\"margin:0 0 8px 0;font-size:14px\">{s[\"title\"]}</h3>' if s.get('title') else ''
        parts.append(
            title_html +
            f'<table style=\"border-collapse:collapse;width:100%;background:#fafafa;border-radius:6px\">'
            f'<tbody>{rows_html}</tbody></table>'
        )
    elif s['type'] == 'text':
        title_html = f'<h3 style=\"margin:0 0 6px 0;font-size:14px\">{s[\"title\"]}</h3>' if s.get('title') else ''
        parts.append(title_html + f'<p style=\"margin:0;color:#333\">{s[\"body\"]}</p>')
    elif s['type'] == 'divider':
        parts.append('<hr style=\"border:none;border-top:1px solid #e8e8e8;margin:4px 0\">')

html = '<br>'.join(parts)
print(html)
"
```

Substitute the actual `sections` list before running. Capture the printed HTML as
`note_body`.

---

## Step 2 — Generate timestamp

Always compute dynamically — never hardcode:

```bash
python3 -c "import datetime; print(int(datetime.datetime.now().timestamp() * 1000))"
```

Store as `hs_timestamp`.

---

## Step 3 — Create or update the note

### Creating a new note

```bash
python3 -c "
import json, subprocess
token = '<hubspot_token>'
payload = {
    'properties': {
        'hs_note_body': '<note_body>',
        'hs_timestamp': '<hs_timestamp>'
    },
    'associations': [{
        'to': {'id': '<ticket_id>'},
        'types': [{'associationCategory': 'HUBSPOT_DEFINED', 'associationTypeId': 228}]
    }]
}
r = subprocess.run(['curl', '-s', '-X', 'POST',
    'https://api.hubapi.com/crm/v3/objects/notes',
    '-H', f'Authorization: Bearer {token}',
    '-H', 'Content-Type: application/json',
    '-d', json.dumps(payload)],
    capture_output=True, text=True)
data = json.loads(r.stdout)
print('Note ID:', data.get('id', 'ERROR'))
if not data.get('id'): print(data)
"
```

### Updating an existing note

```bash
python3 -c "
import json, subprocess
token = '<hubspot_token>'
r = subprocess.run(['curl', '-s', '-X', 'PATCH',
    'https://api.hubapi.com/crm/v3/objects/notes/<note_id>',
    '-H', f'Authorization: Bearer {token}',
    '-H', 'Content-Type: application/json',
    '-d', json.dumps({'properties': {'hs_note_body': '<note_body>'}})],
    capture_output=True, text=True)
data = json.loads(r.stdout)
print('Updated:', data.get('id', 'ERROR'))
"
```

Note: do **not** update `hs_timestamp` on updates — preserves the note's position
in the activity timeline.

---

## Step 4 — Confirm

Return to the calling skill:

```
✅ Human note [created / updated] on ticket <ticket_id> (note ID: <note_id>)
```

---

## Key constants

| Item | Value |
|---|---|
| Note → Ticket association typeId | `228` (HUBSPOT_DEFINED) |
| HubSpot portal ID | `19834291` |

---

## Example rendered output

Given these sections:

```python
[
  {"type": "table", "title": "Ascend / CDC Details", "rows": [
    ["Organization ID", "69fb999444e96d20bbab2e27"],
    ["Practice name (CDC)", "ASPD"],
    ["Ascend Organization ID", "21056"],
    ["Tier", "prod21"],
    ["Status", "active"]
  ]},
  {"type": "divider"},
  {"type": "table", "title": "Support Contact", "rows": [
    ["Name", "Joel White"],
    ["Company", "Henry Schein One"],
    ["Role", "Providing support for API Partners"]
  ]}
]
```

The note renders as two clean labeled tables separated by a rule, with muted label
column, comfortable row padding, and a light background — readable at a glance in
the HubSpot activity feed.

---

## Calling this skill from another skill

```
After completing the main operation, read skills/hubspot-human-note/SKILL.md and
run it. Pass: ticket_id, and sections as a list of table/text/divider objects.
The hubspot-token is already in scope — no need to retrieve it again.
```

---

## Edge cases

- **Empty rows list**: skip that section entirely rather than rendering an empty table.
- **Long values**: HTML will wrap naturally — no truncation needed.
- **Special characters** (`<`, `>`, `&`): escape them in values if they appear in user-provided data (`&amp;`, `&lt;`, `&gt;`).
- **No ticket_id**: stop and ask — cannot proceed without it.

---

## Step 5 — Log the run

Call the **`skill-logger`** skill with:

| Field | Value |
|---|---|
| `skill_name` | `hubspot-human-note` |
| `status` | `success` if note was created/updated · `error` if the API call failed |
| `summary` | 1 sentence: note created or updated on ticket ID, called by which parent skill if known. |
| `inputs` | `ticket_id={id}` · `action={created/updated}` |
| `outputs` | `note_id={id}` |
| `errors` | Any failures (empty if none) |

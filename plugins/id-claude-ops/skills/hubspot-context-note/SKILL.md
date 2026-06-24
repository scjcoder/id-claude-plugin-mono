---
name: hubspot-context-note
description: Write or update a structured "Claude Context" note on a HubSpot ticket. This note captures why the ticket was created, what was checked, any decisions or edge cases, and what Claude should know next time it touches the ticket. Designed to be called by other skills at the end of any workflow that creates or significantly modifies a HubSpot ticket. Also trigger directly if the user asks to "add a Claude note", "update the context note on this ticket", or "document what you did on that ticket". Other InsideDesk skills should call this skill as their final step — pass ticket_id and whatever context was gathered during the workflow.
---

# Skill: HubSpot Context Note

Writes or updates a "Claude Context" note on a HubSpot ticket. The note acts as
per-ticket memory — capturing what Claude did, why, and what it needs to know next
time it touches that ticket. Because this note lives in the ticket's activity history,
it's always in the right place and visible to the whole team.

This skill is designed to be called by other skills, not usually invoked directly by
the user. It handles the upsert logic: if a Claude context note already exists on the
ticket it updates it in place; otherwise it creates a new one.

---

## Prerequisites

Run the `get-secret` skill with name `hubspot-token` to retrieve the HubSpot API token.
See `id-claude-shared` plugin: `skills/_shared/hubspot-setup.md` — Steps B (aws-login) and C (token retrieval) are handled by the `get-secret` skill.

---

## What to collect before writing

The calling skill should pass these values in, assembled from its own findings:

| Field | Description | Required? |
|---|---|---|
| `ticket_id` | HubSpot ticket ID (numeric) | Yes |
| `origin` | What triggered the ticket — email subject, source system, date | Yes |
| `what_was_checked` | Duplicate checks, contact lookups, external sources queried | Yes |
| `decisions` | Judgment calls, fuzzy matches, ambiguous data, anything non-obvious | Yes — write "None." if everything was straightforward |
| `next_steps` | What Claude should do or check next time it touches this ticket | Optional |

If called directly by the user rather than from another skill, ask for these values
before proceeding.

---

## Step 1 — Search for an existing Claude context note

Search for notes already associated with this ticket that carry the Claude context
marker:

```
search_crm_objects on "notes"
filterGroups: [{
  filters: [
    { propertyName: "associations.ticket", operator: "EQ", value: "<ticket_id>" }
  ]
}]
properties: ["hs_note_body", "hs_timestamp"]
limit: 10
```

Scan the results for any note whose `hs_note_body` starts with `🤖 CLAUDE CONTEXT`.

- **Found**: note the ID of that engagement — you will update it in Step 3.
- **Not found**: you will create a new note in Step 3.
- **Search returns an error** (association filter unsupported): skip the search and
  proceed directly to creating a new note. Note this in the confirmation output so
  it's visible for future debugging.

If multiple Claude context notes are found on the same ticket (e.g. from an older
duplicated run), update the most recently timestamped one and leave the others alone.

---

## Step 2 — Build the note body

The note is machine-readable only. Humans skimming the activity timeline will see a
short marker line and an opaque encoded block — that's intentional.

### 2a — Assemble the JSON payload

Build a JSON object with these keys:

```json
{
  "v": 2,
  "updated": "YYYY-MM-DD HH:MM",
  "origin": "...",
  "checked": "...",
  "decisions": "...",
  "next": "..."
}
```

Keep each value to 1–3 sentences. Use `"None."` for `decisions` or `next` if not
applicable.

### 2b — Base64-encode the JSON

Run this via Desktop Commander (macOS):

```bash
python3 -c "
import base64, json
payload = {
  'v': 2,
  'updated': 'YYYY-MM-DD HH:MM',
  'origin': 'ORIGIN_TEXT',
  'checked': 'CHECKED_TEXT',
  'decisions': 'DECISIONS_TEXT',
  'next': 'NEXT_TEXT'
}
print(base64.b64encode(json.dumps(payload).encode()).decode())
"
```

### 2c — Compose the final note body

```
🤖 CLAUDE CONTEXT [v2 · YYYY-MM-DD HH:MM]
<base64 string from 2b>
```

That's the entire note — two lines. The first line is the human-visible marker (just
enough to identify it in the timeline); the second is the encoded payload.

### Reading an existing note

When you encounter a Claude context note and need to read it, decode the second line:

```bash
python3 -c "import base64; print(base64.b64decode('PASTE_BASE64_HERE').decode())"
```

Parse the resulting JSON to recover the fields.

---

## Step 3 — Write the note (create or update)

### Generate the current timestamp

**Always compute `hs_timestamp` dynamically — never hardcode it.** Hardcoded values
will backdate notes to the wrong year (off-by-one year is a common mistake).

Run via Desktop Commander:

```bash
python3 -c "import datetime; print(int(datetime.datetime.now().timestamp() * 1000))"
```

Use the printed value as `hs_timestamp` in the API call below.

### If creating a new note

Use `manage_crm_objects` with `objectType: "notes"`. Use `targetObjectId` /
`targetObjectType` for associations — the `associationTypeId` field causes errors
with the MCP connector:

```json
{
  "objectType": "notes",
  "properties": {
    "hs_note_body": "<note body from Step 2>",
    "hs_timestamp": "<dynamically generated unix timestamp in milliseconds>"
  },
  "associations": [
    {
      "targetObjectType": "tickets",
      "targetObjectId": "<ticket_id>"
    }
  ]
}
```

### If updating an existing note

Use `manage_crm_objects` with the existing note's ID to update only `hs_note_body`.
Do not change `hs_timestamp` — keeping the original timestamp preserves the note's
position in the activity timeline so it doesn't jump to the top on every update.

---

## Step 4 — Confirm

Return a brief single-line confirmation to the calling skill or user:

```
✅ Claude context note [created / updated] on ticket [ticket_id]
```

No other output is needed. This skill is a utility called at the end of other
workflows — the calling skill owns the user-facing summary.

---

## Calling this skill from another skill

Any InsideDesk skill that creates or significantly modifies a HubSpot ticket should
invoke this skill as its final step. The pattern is:

> After completing the main ticket operation, read `skills/hubspot-context-note/SKILL.md`
> and run it. Pass: `ticket_id` (the ticket just created/modified), `origin` (what
> triggered this workflow), `what_was_checked` (duplicate check result, contact lookup
> outcome, external data queried), `decisions` (any fuzzy matches, name normalization,
> or judgment calls made), and optionally `next_steps`.

The HubSpot token is already in scope if the calling skill retrieved it — no need
to fetch it again.

---

## Edge cases

- **No `ticket_id` provided**: stop and ask — this skill cannot proceed without a
  valid ticket ID.
- **Association type ID 18 is wrong for your HubSpot instance**: if the create call
  fails with an association error, try omitting `associationTypeId` entirely and let
  HubSpot infer it, or try `associationTypeId: 19`. Update this note with the working
  value once confirmed.
- **Note body is very long**: trim each value to 2–3 sentences max before encoding.
  The note is a quick-reference summary, not a full audit log.
- **Decoding fails**: if the base64 string is malformed (e.g. truncated by HubSpot),
  treat the note as not found and create a fresh one.

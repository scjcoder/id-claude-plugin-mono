---
name: office-ticket-history
description: >
  Look up recent HubSpot support tickets and Gmail activity for a dental office to provide
  context on known issues, open work, or prior communication. Use this skill when you need
  to understand if there's already an open ticket or active email thread about an office's
  sync problem before creating a new one. Called automatically by the full-sync-status skill.
  Also trigger directly when the user asks "are there any open tickets for [office]",
  "has anyone emailed about [office]", or "what's the history on [office]".
---

# Office Ticket History

Checks HubSpot and Gmail for recent tickets and email activity related to a dental office.
Returns a summary of open work and any relevant context for troubleshooting.

> **Prerequisites:**
> - Run the `get-secret` skill with name `hubspot-token` to retrieve the HubSpot API token.
> - Gmail MCP connector must be available (`mcp__bdbc2263-f755-4531-b2b3-91da919069f8`).

## Inputs

- **facility_name** — the office name to search for (required)
- **client_name** — the InsideDesk client/group name (optional, helps narrow results)
- **days_back** — how far back to look in Gmail (default: 14 days)

## Step 1: Look up the HubSpot location record

Use the HubSpot MCP to find the location record for this facility:

```
mcp__eba53d3c-d280-4218-ba07-d9e0e4624ed7__search_crm_objects
  objectType: "2-14718097"   (InsideDesk locations custom object)
  query: <facility_name>
  properties: ["name", "hs_object_id", "insidedesk_partner_id"]
```

If multiple results, pick the best match (exact name or closest) and note if ambiguous.
If no results, skip to Step 2 — proceed with name-based Gmail search only.

## Step 2: Find open HubSpot tickets for this location

Using the location's `hs_object_id`, search for associated tickets in the Install Pipeline:

```
mcp__eba53d3c-d280-4218-ba07-d9e0e4624ed7__get_crm_objects
  objectType: tickets
  associations: [location hs_object_id]
  properties: ["subject", "hs_pipeline_stage", "hs_ticket_priority", "createdate", "hs_lastmodifieddate", "content"]
  filter: open tickets only
```

Note: focus on tickets in the **Install Pipeline**. Flag any tickets with subjects or notes
mentioning "sync", "snapshot", "out of sync", "Bitwerx", or "Dataco".

## Step 3: Search Gmail for recent email activity

Search Gmail for emails mentioning the facility name in the last `days_back` days:

```
mcp__bdbc2263-f755-4531-b2b3-91da919069f8__search_threads
  query: "<facility_name>" newer_than:<days_back>d
```

Look for:
- Emails from the office's IT contact or staff about sync issues
- Replies from InsideDesk team acknowledging the issue
- Any Jira/Bitwerx correspondence about the office

## Step 4: Output the result

Always emit both a structured result block and a human-readable summary.

### Structured result block

```
TICKET_HISTORY_RESULT:
  facility_name: <name>
  hubspot_location_id: <id or null>
  open_tickets: <count>
  sync_related_tickets: <count>
  most_recent_ticket:
    subject: <subject or null>
    stage: <pipeline stage or null>
    created: <date or null>
    last_modified: <date or null>
  gmail_threads_found: <count>
  gmail_summary: <one-line summary of most relevant thread, or "none">
  context: <brief summary of known issues / open work, or "no prior activity found">
```

### Human-readable summary

Examples:
- 📋 **Monroe Perio** — 1 open sync ticket (created May 20, last updated May 27). No recent Gmail activity.
- 📋 **Monroe Perio** — no open HubSpot tickets. 2 Gmail threads in last 14 days mentioning sync issues.
- 📋 **Monroe Perio** — no prior activity found.

## Notes

- If called as a sub-skill from `full-sync-status`, emit the structured result block so the
  orchestrator can include it in the final report.
- If there is already an open sync ticket, the `full-sync-status` orchestrator should reference
  it rather than prompting to create a new one.

---

## Step 5 — Log the run

After Step 4, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `office-ticket-history` |
| `status` | `success` if HubSpot and Gmail were both checked · `partial` if either source was unavailable · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: office name looked up, number of open HubSpot tickets found (including sync-related), and number of Gmail threads found in the lookback window. |
| `inputs` | `facility_name={name}` · `days_back={N}` |
| `outputs` | `open_tickets={N}` · `sync_related_tickets={N}` · `gmail_threads_found={N}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `hubspot_location_id={id or "not found"}` |

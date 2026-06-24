---
name: list-client-locations
description: >
  List all active locations for an InsideDesk client, including location name and PMS,
  formatted as a table. Use this skill whenever the user asks to "get locations for [client]",
  "list locations for [client]", "show me [client]'s locations", or needs a location/PMS
  summary to share with a client contact. Also trigger when the user asks how many active
  locations a client has or wants to pull a location list for an email or report.
---

# Skill: list-client-locations

Retrieve and display all active locations for an InsideDesk client from HubSpot, with their PMS, grouped for easy sharing.

## What to collect before starting

You need the client name from the user. If it's ambiguous (e.g. a partial name), confirm before proceeding.

## Step-by-step process

### Steps A & B — Find the client and get the API token
Run the `get-secret` skill with name `hubspot-token` to retrieve the HubSpot API token. See `id-claude-shared` plugin: `skills/_shared/hubspot-setup.md` — Steps B (aws-login) and C (token retrieval) are handled by the `get-secret` skill.

### Step 1 — Query active locations

Using the token from Step B and the `client_id` from Step A, call:

```bash
curl -s -X POST "https://api.hubapi.com/crm/v3/objects/2-14718097/search" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "filterGroups":[{"filters":[
      {"propertyName":"client_id","operator":"EQ","value":"<CLIENT_ID>"},
      {"propertyName":"activity_status","operator":"EQ","value":"Active"}
    ]}],
    "properties":["location_name","pms","location_city","state"],
    "sorts":[{"propertyName":"location_name","direction":"ASCENDING"}],
    "limit":50
  }'
```

If `total` exceeds 50, paginate using the `after` cursor until all records are retrieved.

### Step 2 — Cross-check for missing locations

Do a secondary search without the `client_id` filter, using `company_name CONTAINS_TOKEN <client name>` + `activity_status = Active`. If any active locations appear that weren't in Step 1, surface them to the user and offer to update their `client_id`.

### Step 3 — Build and return the table

Apply PMS display rules from the shared setup file. Format as a table:

- **Grouping:** Named PMS types (EagleSoft, Dentrix, etc.) at the top, then Custom FTP — both groups sorted A–Z by location name
- **Columns:** Location Name | PMS | City | State

End with a one-line summary: **X active locations — Y on [PMS], Z on Custom FTP.**

## Edge cases

- **client_id not set on parent company:** Warn the user and fall back to searching locations by `company_name`.
- **Count mismatch:** If results differ from `of_locations___active` on the parent record, flag it and offer to investigate.
- **Blank PMS:** Display as `Unknown` and note at the bottom of the table.

---

## Step 4 — Log the run

After Step 3, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `list-client-locations` |
| `status` | `success` if the location list was returned · `error` if the client was not found or the query failed |
| `summary` | 1–3 sentences: client name, total active locations returned, and any count mismatch vs. the parent company record. |
| `inputs` | `client_name={name}` |
| `outputs` | `location_count={N}` · `table_shown=true` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `count_mismatch={true/false}` |

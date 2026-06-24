---
name: client-pms-summary
description: >
  Show a count of active locations by PMS type for an InsideDesk client.
  Use this skill whenever the user asks "what PMS does [client] use?", "how many
  locations are on Dentrix?", "give me a PMS breakdown for [client]", or needs a
  PMS summary for a report, email, or planning conversation. Also trigger when the
  user wants to know how many locations use each software across a client group.
---

# Skill: client-pms-summary

Return a count of active locations grouped by PMS for a given InsideDesk client.

## What to collect before starting

You need the client name from the user. If it's ambiguous, confirm before proceeding.

## Step-by-step process

### Steps A & B — Find the client and get the API token
Run the `get-secret` skill with name `hubspot-token` to retrieve the HubSpot API token. See `id-claude-shared` plugin: `skills/_shared/hubspot-setup.md` — Steps B (aws-login) and C (token retrieval) are handled by the `get-secret` skill.

### Step 1 — Query active locations (PMS only)

Using the token from Step B and the `client_id` from Step A, call the locations search endpoint requesting only the `pms` property — no need for name, city, or state:

```bash
curl -s -X POST "https://api.hubapi.com/crm/v3/objects/2-14718097/search" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "filterGroups":[{"filters":[
      {"propertyName":"client_id","operator":"EQ","value":"<CLIENT_ID>"},
      {"propertyName":"activity_status","operator":"EQ","value":"Active"}
    ]}],
    "properties":["pms"],
    "limit":100
  }'
```

If `total` exceeds 100, paginate using the `after` cursor until all records are retrieved.

### Step 2 — Aggregate and count

Group results by `pms` value and count each group. Apply PMS display rules from the shared setup file (`Other` → `Custom FTP`, blank → `Unknown`).

Use python to aggregate cleanly:

```python
from collections import Counter
pms_list = [r['properties'].get('pms') or 'Unknown' for r in results]
counts = Counter(pms_list)
```

### Step 3 — Return the summary table

Sort by count descending. Add a total row at the bottom.

| PMS | Locations |
|---|---|
| Dentrix | 18 |
| EagleSoft | 16 |
| Custom FTP | 10 |
| **Total** | **44** |

If the total differs from `of_locations___active` on the parent company record, flag the discrepancy.

## Edge cases

- **All locations show Custom FTP:** Note that the client uses a single FTP-based data warehouse connection — no direct PMS integrations.
- **client_id not set:** Warn the user and fall back to `company_name CONTAINS_TOKEN` search.
- **Count mismatch vs parent record:** Flag and offer to run `list-client-locations` to identify which locations may be missing or miscategorized.

---

## Step 4 — Log the run

After Step 3, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `client-pms-summary` |
| `status` | `success` if the PMS breakdown was returned · `error` if the client was not found or the query failed |
| `summary` | 1–3 sentences: client name, total active locations found, and PMS breakdown (top PMS types and counts). |
| `inputs` | `client_name={name}` |
| `outputs` | `total_locations={N}` · `pms_breakdown={e.g. "Dentrix=18, EagleSoft=16, Custom FTP=10"}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `count_mismatch={true/false}` |

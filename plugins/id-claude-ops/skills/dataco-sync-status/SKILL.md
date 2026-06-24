---
name: dataco-sync-status
description: >
  Check the Bitwerx Dataco sync stage status for a dental facility. Use this skill whenever you
  need to know the detailed pipeline status (Connectivity, Sync, Staging, Intermediate) for an
  office whose PMS is Dentrix, Dentrix Enterprise, or Eaglesoft. Called automatically by the
  full-sync-status skill when the PMS is a Bitwerx type. Also trigger directly when the user
  asks "what's the Dataco status for [office]", "check Bitwerx for [office]", or "why isn't
  [office] syncing" for a Bitwerx PMS office.
---

# Dataco Sync Status Check

Check the Bitwerx Dataco pipeline stages for a facility to determine where in the sync process
the data is, and whether any stage is failing or stale.

> **Prerequisite:** The user must be logged into `support.dataco.dental` in Chrome as PartnerAdmin.
> Read the `dataco-supportco-api` skill (in `id-claude-integrations`) now for authentication
> details and API reference before proceeding.

## Step 1: Retrieve the Azure B2C token

Use browser JavaScript to extract the token from sessionStorage:

```javascript
const KEY = '3559999c-c487-402e-8053-72d73e605635-b2c_1a_signup_signin_dental'
          + '.72742b36-fbc0-48f0-a661-63d6f6aafecb-bitwerxinc.b2clogin.com'
          + '-accesstoken-216adce3-003d-40f9-9e53-d12d83fb7e50'
          + '--https://bitwerxinc.onmicrosoft.com/supportcoapi/read';
const token = JSON.parse(sessionStorage.getItem(KEY)).secret;
```

If the token is missing or expired, ask the user to log in at `support.dataco.dental` first.

## Step 2: Search for the practice by name

```javascript
const resp = await fetch(
  `https://supportcodentalapi.azurewebsites.net/api/v2/practices?pageSize=10&filter=${encodeURIComponent('<FACILITY_NAME>')}`,
  { headers: { 'Authorization': 'Bearer ' + token } }
);
const list = await resp.json();
```

**If no results:** report not found. Ask user to try a different name or check spelling.

**If multiple results:** present them as a numbered list with name, city, state, and PMS so
the user can pick the right one. Wait for selection before continuing.

**If one result:** proceed.

## Step 3: Fetch the practice detail and extract all stage data

All sync stage data lives in `detail.data.practiceStatus` — do **not** call `latestruntimebyjobtype`
(that endpoint returns empty data for InsideDesk practices).

> ⚠️ **async/await:** Top-level `await` does not work in the browser JS tool. Wrap all API calls
> in `(async () => { ... })()` and store results to `window._varName`, then read them in a
> separate JS call.

> ⚠️ **Timestamps:** DataCo returns Unix timestamps in **seconds**. Multiply by 1000 before
> passing to `new Date()` — e.g. `new Date(ps.lastHeartbeatTime * 1000)`.

```javascript
(async () => {
  const UUID = '<PRACTICE_UUID>';
  const detResp = await fetch(
    `https://supportcodentalapi.azurewebsites.net/api/practices/${UUID}`,
    { headers: { 'Authorization': 'Bearer ' + token } }
  );
  const detail = await detResp.json();
  const d = detail.data;
  const ps = d.practiceStatus; // object — contains all stage timestamps and flags

  const today = new Date().toDateString();
  const fmt = t => t ? new Date(t * 1000).toLocaleString() : 'never';
  const isToday = t => t ? new Date(t * 1000).toDateString() === today : false;

  window._dcDetail = {
    name: d.name,
    groupName: d.groupName,          // top-level field — NOT d.group?.name
    isMuted: d.isMuted,
    friendlyId: d.friendlyId,
    fingerprint: d.instanceId,
    pims: d.pims,
    // Connectivity
    hbLast: fmt(ps.lastHeartbeatTime),
    hbSuccess: ps.lastHeartbeatSuccessful,
    hbStale: ps.heartbeatStale,
    // Sync (Extraction)
    syncLast: fmt(ps.lastExtractionRun),
    syncToday: isToday(ps.lastExtractionRun),
    syncIssue: ps.hasExtractionIssue,
    // Staging
    stagingLast: fmt(ps.lastStagingLoadRun),
    stagingToday: isToday(ps.lastStagingLoadRun),
    stagingIssue: ps.hasStagingLoadIssue,
    // Intermediate
    intermediateLast: fmt(ps.lastIntermediateLoadRun),
    intermediateToday: isToday(ps.lastIntermediateLoadRun),
    intermediateIssue: ps.hasIntermediateLoadIssue,
  };
})();
```

Then read the result in a second JS call: `window._dcDetail`

## Step 4: Evaluate stage statuses

Using the `window._dcDetail` fields:

- **Connectivity** — `hbStale: false` + `hbSuccess: true` = OK; `hbStale: true` = STALE; `hbSuccess: false` = FAILED
- **Sync** — `syncIssue: false` + `syncToday: true` = OK
- **Staging** — `stagingIssue: false` + `stagingToday: true` = OK
- **Intermediate** — `intermediateIssue: false` + `intermediateToday: true` = OK

For each stage, check:
- Is the last run timestamp **today**?
- Is the issue flag false (no errors)?

**Bitwerx PMS list** (for reference — caller should have already confirmed this):
- Dentrix (= Dentrix Core)
- Dentrix Enterprise
- Eaglesoft

## Step 6: Output the result

Always emit both a structured result block and a human-readable summary.

### Structured result block

```
DATACO_STATUS_RESULT:
  facility_name: <name>
  group: <practice group name>
  practice_status: Live | Muted
  fingerprint: <uuid or null>
  friendly_id: <e.g. A1H5R97J>
  connectivity: OK | STALE | FAILED | UNKNOWN
  connectivity_last_success: <timestamp or null>
  sync_last_success: <timestamp or null>
  sync_today: true | false
  staging_last_success: <timestamp or null>
  staging_today: true | false
  intermediate_last_success: <timestamp or null>
  intermediate_today: true | false
  overall: ALL_GREEN | STALE | FAILED | PARTIAL
```

Use these `overall` values:
- `ALL_GREEN` — all stages successful today
- `STALE` — no error flags but Intermediate last ran before today
- `FAILED` — any stage has a failure/error status
- `PARTIAL` — some stages green today, others not

### Human-readable summary

Examples:
- ✅ **Monroe Perio** (Dataco) — all stages green, Intermediate last ran today at 7:57 AM
- ⚠️ **Monroe Perio** (Dataco) — stages green but Intermediate last ran May 26 (stale)
- 🔴 **Monroe Perio** (Dataco) — Connectivity red: no heartbeat from server
- 🔴 **Monroe Perio** (Dataco) — Staging failed

---

## Step 6b: Suggested Actions

After outputting the result, apply this decision matrix to determine the recommended next action.
**Always present the recommendation and ask Sean to confirm before executing.**

### Decision Matrix

| Condition | Recommended Action |
|---|---|
| Connectivity FAILED or STALE (`hbStale: true` or `hbSuccess: false`) | Draft IT contact email requesting remote session |
| Connectivity OK, Sync stale or failed (`syncIssue: true` or `syncToday: false`) | File `[Check Sync]` Bitwerx JIRA ticket |
| Connectivity OK, Sync OK, Staging or Intermediate stale/failed | File `[Resend Claims]` Bitwerx JIRA ticket |
| ALL_GREEN | No action needed — report healthy |

Evaluate top-down — stop at the first matching condition. If connectivity is lost, that's the
root cause; don't suggest a JIRA ticket at the same time.

---

### Action A — Draft IT Contact Email (Connectivity lost)

1. Look up the HubSpot location record by searching for `{facility_name}` in the locations
   custom object (`2-14718097`). Use the `hubspot-token` from `_shared/hubspot-setup.md`.

2. From the location record, retrieve the associated IT contact (contact type = IT/Support).
   If no IT contact is found, fall back to the Account POC.

3. Present the proposed email to Sean for confirmation:

   **Subject:** `{facility_name} — DataCo Connectivity Issue`

   **Body:**
   ```
   Hi [IT Contact Name],

   I wanted to reach out because we're seeing a connectivity issue between your
   {facility_name} location and our DataCo data sync. The last successful heartbeat
   was {hbLast}.

   Would you be able to provide us with a remote session so we can investigate the
   connection and get things back up and running?

   Please let us know a good time and we can coordinate from there.

   Thanks,
   Sean
   InsideDesk
   ```

4. After Sean confirms, create the Gmail draft using `mcp__bdbc2263-f755-4531-b2b3-91da919069f8__create_draft`.

---

### Action B — File [Check Sync] JIRA Ticket (Sync stale/failed)

Present to Sean:
> "Connectivity is OK but Sync last ran {syncLast}. Recommend filing a `[Check Sync]` Bitwerx
> ticket. Proceed?"

If confirmed, invoke the `id-claude-ops:bitwerx-jira-ticket` skill with:
- Issue type: `[Check Sync]`
- Facility name: `{facility_name}`
- The fingerprint is already available from `window._dcDetail.fingerprint`

---

### Action C — File [Resend Claims] JIRA Ticket (Staging/Intermediate stale)

Present to Sean:
> "Connectivity and Sync are OK but Staging last ran {stagingLast} and Intermediate last ran
> {intermediateLast}. Recommend filing a `[Resend Claims]` Bitwerx ticket. Proceed?"

If confirmed, invoke the `id-claude-ops:bitwerx-jira-ticket` skill with:
- Issue type: `[Resend Claims]`
- Facility name: `{facility_name}`
- The fingerprint is already available from `window._dcDetail.fingerprint`

---

## Notes

- **Muted status** is set by a Bitwerx technician during maintenance. It is temporary and not
  a cause for concern — continue checking the stage statuses normally and apply the decision
  matrix as usual.
- **Mission Control** is not used by InsideDesk. Ignore it.
- If Intermediate is `ALL_GREEN` but GoldenEye shows no snapshot, there should be no lag —
  flag this as an InsideDesk ingestion issue rather than a Bitwerx issue.
- If called as a sub-skill from `full-sync-status`, emit the structured result block so the
  orchestrator can branch on `overall`.

---

## Step 7 — Log the run

After Step 6, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `dataco-sync-status` |
| `status` | `success` if all pipeline stages were checked · `error` if the facility was not found in DataCo or the token was missing |
| `summary` | 1–3 sentences: facility name checked, overall pipeline status (ALL_GREEN/STALE/FAILED/PARTIAL), and any specific stage failures or staleness. |
| `inputs` | `facility_name={name}` · `fingerprint={fingerprint or "n/a"}` |
| `outputs` | `overall={ALL_GREEN/STALE/FAILED/PARTIAL}` · `connectivity={OK/FAILED/UNKNOWN}` · `intermediate_today={true/false}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `practice_status={Live/Muted}` |

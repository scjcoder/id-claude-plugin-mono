---
name: dataco-supportco-api
description: >
  Reference skill for interacting with the Bitwerx DataCo SupportCo portal (support.dataco.dental)
  on behalf of InsideDesk. Use this skill whenever you need to look up a dental practice in DataCo,
  retrieve a Bitwerx fingerprint (instanceId), search by practice name, HubSpot Facility ID
  (InsideDesk Partner ID), or practice group name, or understand how to authenticate and call
  the DataCo API programmatically via browser JavaScript. Also trigger when the user says things
  like "get the fingerprint for [practice]", "look up [practice] in DataCo", "find the Bitwerx
  fingerprint", or "search DataCo by facility ID / partner ID".
---

# Bitwerx DataCo SupportCo — API Reference

## Prerequisites

**Claude in Chrome must be connected and the user must already be logged into `support.dataco.dental` as PartnerAdmin.** This skill extracts the Azure B2C access token from the browser's `sessionStorage` — there is no offline fallback. If the token is missing or expired, ask the user to log in at `support.dataco.dental` before proceeding.

---

## Overview

DataCo SupportCo (`https://support.dataco.dental`) is Bitwerx's internal support portal for
dental practice management. InsideDesk uses it as a **PartnerAdmin** to look up practice records,
retrieve Bitwerx fingerprints, and verify sync/connectivity status.

The portal is an Angular SPA backed by a REST API at:
```
https://supportcodentalapi.azurewebsites.net/api
```

---

## Authentication

The portal uses **Azure B2C OAuth** (tenant: `bitwerxinc.b2clogin.com`). Access tokens are stored
in `sessionStorage` in the browser after login.

**Retrieving the token in browser JS:**
```javascript
const KEY = '3559999c-c487-402e-8053-72d73e605635-b2c_1a_signup_signin_dental'
          + '.72742b36-fbc0-48f0-a661-63d6f6aafecb-bitwerxinc.b2clogin.com'
          + '-accesstoken-216adce3-003d-40f9-9e53-d12d83fb7e50'
          + '--https://bitwerxinc.onmicrosoft.com/supportcoapi/read';
const token = JSON.parse(sessionStorage.getItem(KEY)).secret;
// Use as: Authorization: Bearer <token>
```

All API calls require `Authorization: Bearer <token>` header.

**Login URL** (InsideDesk service account):
```
https://support.dataco.dental/#state=...&role=PartnerAdmin&partners=60a25ff9-5d21-404d-ac59-a9d91d566049
```
(Use the full SSO redirect URL from the InsideDesk credentials store.)

---

## Key Concepts

| Concept | Description |
|---|---|
| **Bitwerx Fingerprint** | UUID stored as `instanceId` in the practice detail. Uniquely identifies a DataCo practice/server installation. Used by InsideDesk to link HubSpot locations to DataCo records. |
| **InsideDesk Partner ID** | Stored as `partnerCustomId` in `offeringInfo` (list endpoint only). **Equals the HubSpot Facility ID** — this is the cross-reference key. |
| **Practice UUID** | Internal DataCo GUID (`id` field). Used to call the detail endpoint. |
| **Friendly ID** | Short serial code (e.g. `9E1RSC16`). Human-readable identifier for the DataCo agent install. |
| **Dentrix Enterprise** | All locations running Dentrix Enterprise share **one** DataCo record and therefore **one fingerprint**. Individual location configs live in DataCo backend configs, not separate records. |

---

## API Endpoints

### 1. List / Search Practices

```
GET /api/v2/practices
```

**Parameters:**

| Param | Type | Description |
|---|---|---|
| `pageSize` | int | Max results to return (max observed: 100) |
| `filter` | string | Search term — matches practice name OR group name (see toggles) |
| `searchCustomIds` | bool | When `true`, `filter` matches InsideDesk Partner ID (HubSpot Facility ID) |

**Search modes** (maps to UI toggles):

| UI Toggle | API Behaviour |
|---|---|
| *(default — name search)* | `filter=<name>` — exact/fuzzy match on practice name. Returns 1 result for exact match. |
| **Search Practice Groups** | `filter=<group name>` — returns all practices in that practice group |
| **Search Partner Ids** | `filter=<id>&searchCustomIds=true` — finds the practice whose InsideDesk `partnerCustomId` equals the supplied value (= HubSpot Facility ID) |

**Example — find by name:**
```javascript
const resp = await fetch(
  `https://supportcodentalapi.azurewebsites.net/api/v2/practices?pageSize=5&filter=${encodeURIComponent('Coosa')}`,
  { headers: { 'Authorization': 'Bearer ' + token } }
);
const list = await resp.json(); // Array of practice objects
```

**Example — find by HubSpot Facility ID:**
```javascript
const resp = await fetch(
  `https://supportcodentalapi.azurewebsites.net/api/v2/practices?pageSize=5&filter=2876&searchCustomIds=true`,
  { headers: { 'Authorization': 'Bearer ' + token } }
);
const list = await resp.json();
```

**Example — get all practices in a group:**
```javascript
const resp = await fetch(
  `https://supportcodentalapi.azurewebsites.net/api/v2/practices?pageSize=100&filter=${encodeURIComponent('SGA Dental Partners')}`,
  { headers: { 'Authorization': 'Bearer ' + token } }
);
const list = await resp.json();
```

**List response object shape:**
```json
[
  {
    "id": "540e725a-fac2-4af7-9791-67fe3bbee51a",
    "name": "Coosa",
    "city": "Cedartown",
    "stateProvince": "GA",
    "pims": "Dentrix",
    "groupName": "SGA Dental Partners",
    "offeringInfo": [
      {
        "partner": "InsideDesk",
        "partnerOffering": "InsideDesk",
        "partnerCustomId": "2876"
      }
    ],
    "status": { "heartbeatStatus": "Success" },
    "isTestPractice": false,
    "isDormant": false
  }
]
```

> **Note:** `offeringInfo` is only populated on the unfiltered list endpoint (no `filter` param).
> When `filter=` is used, `offeringInfo` returns as `[]`. Use the detail endpoint to get partner info
> for filtered results, or verify via the practice group and name match.

---

### 2. Practice Detail

```
GET /api/practices/<uuid>
```

Returns the full record for a single practice, including the **Bitwerx fingerprint**.

**Example:**
```javascript
const resp = await fetch(
  `https://supportcodentalapi.azurewebsites.net/api/practices/540e725a-fac2-4af7-9791-67fe3bbee51a`,
  { headers: { 'Authorization': 'Bearer ' + token } }
);
const json = await resp.json();
const fingerprint = json.data.instanceId.toUpperCase();
const friendlyId  = json.data.friendlyId;  // e.g. "9E1RSC16"
const displayId   = json.data.displayId;   // e.g. 1119
```

**Detail response shape:**
```json
{
  "success": true,
  "message": null,
  "data": {
    "instanceId":  "4f363442-1ba6-4552-b191-bc37c8cc447a",
    "friendlyId":  "9E1RSC16",
    "displayId":   1119,
    "pimsId":      "5661e598-314a-4fd6-b3c4-c2abb962ccd3",
    "pims":        "Dentrix",
    "name":        "Coosa",
    "groupName":   "SGA Dental Partners",
    "isActive":    true,
    "isDormant":   false,
    "isMuted":     false,
    "practiceStatus": { ... }
  }
}
```

The `instanceId` field **is** the Bitwerx fingerprint.

> ⚠️ **`practiceStatus` is an object, not a string.** Earlier versions of this doc showed
> `"practiceStatus": "Live"` — that is wrong. It is a rich object containing all sync stage
> timestamps and health flags. See below.

#### `practiceStatus` object

This is the primary source of truth for sync pipeline health. **All timestamps are Unix epoch
seconds** — multiply by 1000 before passing to JavaScript's `Date` constructor.

```json
{
  "hasHadHeartbeat":            true,
  "lastHeartbeatTime":          1781309651,
  "lastHeartbeatSuccessful":    true,
  "heartbeatStale":             false,

  "hasHadExtraction":           true,
  "extractionActive":           false,
  "extractionStale":            false,
  "lastExtractionRun":          1781300385,
  "lastExtractionSuccessfulRun": 1781300385,
  "lastExtractionSuccessful":   true,
  "hasExtractionIssue":         false,

  "hasHadStagingLoad":          true,
  "stagingLoadActive":          false,
  "lastStagingLoadRun":         1781301078,
  "lastStagingLoadSuccessful":  true,
  "hasStagingLoadIssue":        false,

  "hasHadIntermediateLoad":     true,
  "intermediateLoadActive":     false,
  "lastIntermediateLoadRun":    1781302235,
  "lastIntermediateLoadSuccessful": true,
  "hasIntermediateLoadIssue":   false,

  "nextSync":                   null,
  "syncRule":                   null,
  "isMissionControlAlive":      false,
  "missionControlLastHeartbeat": null,
  "hasMissionControlIssue":     false
}
```

**Usage pattern — check if a stage ran today:**
```javascript
const ps = detail.data.practiceStatus;
const today = new Date().toDateString();
const isToday = t => t ? new Date(t * 1000).toDateString() === today : false;
const fmt     = t => t ? new Date(t * 1000).toLocaleString() : 'never';

const syncOk         = !ps.hasExtractionIssue && isToday(ps.lastExtractionRun);
const stagingOk      = !ps.hasStagingLoadIssue && isToday(ps.lastStagingLoadRun);
const intermediateOk = !ps.hasIntermediateLoadIssue && isToday(ps.lastIntermediateLoadRun);
const connectivityOk = ps.hasHadHeartbeat && !ps.heartbeatStale;
```

**`isMuted` vs `heartbeatStale`:**
- `isMuted` (`data.isMuted`) — set by a Bitwerx technician during maintenance. Temporary; not a cause for concern.
- `heartbeatStale` — the server hasn't checked in recently. Combined with stale stage timestamps, this signals a real connectivity problem.

---

### 3. Practice Dashboard / Status

```
GET /api/practices/dashboard
```

Returns high-level connectivity and sync status across all practices. No required params.

---

### 4. Last Runtime by Job Type

```
GET /api/practices/<uuid>/latestruntimebyjobtype?jobType=<type>
```

Job types: `StagingLoad`, `IntermediateLoad`, `ConversionPrep`, `LeadsGeneration`, `ExtractionInitiate`

> **Prefer `practiceStatus` over this endpoint.** The `data.practiceStatus` object on the
> detail endpoint (§2 above) contains all the same timestamps and issue flags in a single
> response. Only call `latestruntimebyjobtype` directly if you need a specific job type that
> is not reflected in `practiceStatus` (e.g. `ConversionPrep`, `LeadsGeneration`).

---

## Workflow: Bulk Fingerprint Collection

To collect fingerprints for a list of locations (e.g. for a Gen 4 migration sheet):

```javascript
async function getFingerprints(locations, token) {
  // locations = [{ name: 'Coosa', facilityId: '2876', pms: 'Dentrix' }]
  const ENTERPRISE_FP = '67F206BC-82C5-463C-826C-E5753CAEF222';
  const results = [];

  for (const loc of locations) {
    // Dentrix Enterprise → shared fingerprint, no lookup needed
    if (loc.pms === 'Dentrix Enterprise') {
      results.push({ ...loc, fingerprint: ENTERPRISE_FP });
      continue;
    }

    // All others → search by name, then fetch detail
    const resp = await fetch(
      `https://supportcodentalapi.azurewebsites.net/api/v2/practices?pageSize=5&filter=${encodeURIComponent(loc.name)}`,
      { headers: { 'Authorization': 'Bearer ' + token } }
    );
    const list = await resp.json();
    if (!list.length) { results.push({ ...loc, fingerprint: 'NOT_FOUND' }); continue; }

    const practice = list[0]; // filter returns best match first
    const det = await fetch(
      `https://supportcodentalapi.azurewebsites.net/api/practices/${practice.id}`,
      { headers: { 'Authorization': 'Bearer ' + token } }
    );
    const detJson = await det.json();
    results.push({ ...loc, fingerprint: detJson.data.instanceId.toUpperCase() });
  }
  return results;
}
```

**Verification step:** After collecting, confirm the InsideDesk Partner ID in the DataCo UI detail
panel matches the HubSpot Facility ID for that location (visible as "Partner ID: XXXX" in the
DataCo Configuration section of the practice detail page).

---

## Important Notes

### Dentrix Enterprise — Shared Fingerprint
All locations running **Dentrix Enterprise** on the same server share a single DataCo record and
fingerprint. For SGA Dental Partners, the Enterprise fingerprint is:
```
67F206BC-82C5-463C-826C-E5753CAEF222
```
Individual location configuration is handled in DataCo backend configs, not separate practice records.

### InsideDesk Partner ID = HubSpot Facility ID
The `partnerCustomId` field in DataCo's `offeringInfo` for the InsideDesk partner equals the
HubSpot `Facility ID` property. Use this to cross-reference between the two systems.

### offeringInfo availability
`offeringInfo` is populated in the **unfiltered** `/api/v2/practices?pageSize=N` response but
returns `[]` when a `filter=` parameter is used. To verify partner ID after a name search,
either: (a) use `searchCustomIds=true` with the known facility ID, or (b) check the DataCo UI.

### API caps at 100 results
`pageSize` is capped at 100 records per page. There is no working pagination (page= param cycles
the same records). For large datasets, use `filter=` to narrow results rather than trying to
paginate through the full list.

### Token expiry
Azure B2C tokens expire. If API calls return 401, the user needs to re-authenticate at
`support.dataco.dental`. The token lives in `sessionStorage` only for the current browser session.

---

## UI Reference

| UI Element | What it does |
|---|---|
| Search box + Enter | Searches practices using `filter=<value>` |
| **Search Practice Groups** toggle | Same `filter=` param but matched against group name |
| **Search Partner Ids** toggle | Adds `searchCustomIds=true` — matches InsideDesk Partner ID |
| **Search Partner Offerings** toggle | (Not fully documented — filters by partner offering type) |
| DataCo Configuration panel | Shows: Fingerprint (instanceId), Serial (friendlyId), PMS, last sync date, InsideDesk Partner ID |
| Status panel | Shows: Connectivity, Mission Control, Sync, Staging, Intermediate job last run times |

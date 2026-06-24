# Bitwerx JIRA Service Desk — Reference Guide

Bitwerx operates a Jira Service Management portal ("DataCo technical support") that InsideDesk uses to communicate with Bitwerx techs about sync issues, location changes, and other DataCo-related requests. All tickets apply only to **Bitwerx-synced PMSs**: Dentrix, Dentrix Enterprise, and Eaglesoft.

---

## URLs

| Purpose | URL |
|---|---|
| My open + closed requests | https://bitwerx.atlassian.net/servicedesk/customer/user/requests?reporter=all&statuses=open&statuses=closed |
| Open requests only | https://bitwerx.atlassian.net/servicedesk/customer/user/requests?reporter=all&statuses=open |
| Create new ticket | https://bitwerx.atlassian.net/servicedesk/customer/portal/6/create/246 |

> **Access level:** Guest only — all interactions must be done through the browser. No API access.

---

## Form Fields

The ticket form has three fields:

| Field | Required | Notes |
|---|---|---|
| **Summary** | ✅ | Follow the `[Issue] Client - Facility` format (see below) |
| **Description** | ✅ | Rich text. See templates per issue type below |
| **Attachment** | No | Optional file/screenshot upload |
| **Share with** | ✅ | Pre-set to "Share with InsideDesk" — leave as-is |

---

## Summary Line Format

```
[Issue Type] Client - Facility Name
```

**Examples:**
- `[Check Sync] MB2 - Peppermint Dental - Rowlett`
- `[Server Swap] MB2 - Peppermint Dental - Montgomery (NM)`
- `[Reactivate Location] MB2 - Round Lake Family Dentistry`
- `[Disable Location] MB2 - BLVD Dentistry & Orthodontics - Cypress`
- `[new location] MB2 - North Atlanta Kids Dentistry`
- `[Password Request] Marquee - Criswell Main St`

> **Note on casing:** The bracket tags are case-sensitive in practice but Bitwerx techs understand all variants. Prefer the exact casing shown in the templates below for consistency.

---

## Issue Types & Description Templates

### `[Check Sync]`
Use when a location is not syncing and you need Bitwerx to investigate telemetry on their end.

**Description:**
```
{Bitwerx instanceId / fingerprint}

Please check for any errors
```

**Example:**
```
E9218CA9-47AB-49EA-871B-D9B6B05676A3

Please check for any errors
```

> The fingerprint (instanceId) comes from the DataCo SupportCo portal or the `dataco-sync-status` skill.

---

### `[Server Swap]`
Use when a client's server has been replaced and you need Bitwerx to re-point DataCo to the new server.

**Description:**
```
{Bitwerx instanceId / fingerprint}

Please check for telemetry
```

> "Please check for telemetry" is the correct phrase for Server Swap, new installs, and reactivations — situations where Bitwerx needs to verify the agent is phoning home. Use "Please check for any errors" for Check Sync tickets instead. Any remote session details (from screen share) will be auto-appended below the description.

---

### `[Disable Location]`
Use when a location has cancelled InsideDesk and needs to be disabled in DataCo.

**Description:**
```
{Bitwerx instanceId / fingerprint}

This location has cancelled, please disable in DataCo.
```

---

### `[Deactivate Location]`
Functionally the same as Disable Location. Used interchangeably — prefer `[Disable Location]` for cancellations.

---

### `[Reactivate Location]`
Use when a previously disabled/inactive location needs to be brought back online.

**Description:**
```
Can you reactivate the following location and trigger a new sync if it has a heartbeat

{Location Name}
{Client / Practice Group}
{PMS} (e.g. eaglesoft, dentrix_enterprise, dentrix)
Partner ID: {HubSpot Facility ID / InsideDesk Partner ID}
API: {Kolla API key for this location}
{Full address}
{Phone number or "No phone number"}
Last service: {MM/DD/YYYY}
Last submitted: {MM/DD/YYYY}
```

**Where to find the data:**
- Partner ID → HubSpot location record → "Partner ID" property
- Kolla API key → Kolla account management skill
- Last service / Last submitted → DataCo SupportCo portal or GoldenEye last snapshot date

---

### `[new location]`  (also seen as `[New Facility]`)
Use when onboarding a brand-new location that needs to be **created in DataCo** — i.e. before the installer has run and before any account exists in DataCo. **InsideDesk no longer has permission to create locations in DataCo directly** — this ticket is the only way to get a new location provisioned by Bitwerx.

> **Not the same as [New Install].** Use `[new location]` when the DataCo account doesn't exist yet. Use `[New Install]` after the installer has run and you need Bitwerx to verify telemetry. See `[New Install]` below.

**Description:**
```
{Location Name}
{Client / Practice Group}
{PMS} (e.g. dentrix_enterprise)
{GoldenEye API key for this location}
{Full address}
{Phone number}

{Any additional context — e.g. whether they are part of an existing enterprise data set, IT contact info, installation notes}
```

**Two critical fields for new location tickets:**
- **GoldenEye API key** — permanently shown on the Facility Detail page next to a 🔑 key icon. No label — just the icon and a 40-character hex string (e.g. `952c273ace2cd3e0a48b220000f8048ef63b76e8`). This is the same value as "InsideDesk Api Key" in DataCo's Practice Configuration, but it's masked in DataCo and cannot be unmasked — GoldenEye is the only place to read it.
- **GoldenEye Facility ID** — the numeric ID in the GoldenEye URL (`/facility/{id}/details`). This is what DataCo calls "Partner ID".

---

### `[New Install]`
Use after the InsideDesk installer has been run at a location and you need Bitwerx to verify that the agent is phoning home (telemetry). This is a **post-install** ticket — the DataCo account already exists (or was just created via `[new location]`). The purpose is to confirm the sync pipeline is alive and starting correctly.

> **Not the same as [new location].** `[new location]` is for creating the DataCo account before install. `[New Install]` is for verifying telemetry after the installer has run.

**Description:**
```
{Location Name}
{Client / Practice Group}
{PMS} (e.g. dentrix, dentrix_enterprise, eaglesoft)
Partner ID: {GoldenEye Facility ID}
{GoldenEye API key for this location}
{Full address}
{Phone number}

{Context — e.g. "Office self installed, check for telemetry." or "Installer just ran, please verify telemetry and trigger initial sync."}
```

**Data sources:** Same as `[new location]` — pull facility details from the GoldenEye Facility Detail page (Partner ID from URL, API key from 🔑 icon).

---

### `[Resend Claims]`
Use when connectivity and sync are healthy but staging or intermediate load stages are stale —
meaning data reached Bitwerx but didn't make it through their processing pipeline. Bitwerx will
investigate and re-trigger the downstream stages.

**Description:**
```
{Bitwerx instanceId / fingerprint}

Staging last ran: {date}
Intermediate last ran: {date}

Please resend claims.
```

**Example:**
```
3B7FCB63-C57B-4D85-BCE6-0D323CC25004

Staging last ran: Jun 12, 4:51 PM EST
Intermediate last ran: Jun 12, 5:10 PM EST

Please resend claims.
```

> Use this when `dataco-sync-status` returns `overall: STALE` with connectivity and sync both OK
> but staging/intermediate timestamps are not today.

---

### `[Password Request]`
Use when Bitwerx needs to update credentials for a location's PMS server connection.

**Description:**
```
{Location Name}
{Client}
{Bitwerx instanceId / fingerprint}

New password: {password}
```

---

## The Two Bitwerx Identifiers (Do Not Confuse)

These are completely separate values used for different purposes:

| Identifier | Format | Source | Used In |
|---|---|---|---|
| **Bitwerx Fingerprint** (instanceId) | UUID — `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX` | DataCo SupportCo portal (`support.dataco.dental`) only | [Check Sync], [Server Swap], [Disable Location] tickets |
| **GoldenEye API Key** | 40-char hex — `952c273ace2...` | GoldenEye Facility Detail page (🔑 icon) only — masked in DataCo, unreadable there | [new location], [Reactivate Location] tickets |

The fingerprint is Bitwerx's primary internal identifier — it's how their techs look up an account in their systems. The API key is the InsideDesk integration credential used to connect a location to DataCo.

---

## Key Data Points to Gather Before Ticketing

| Data Point | Where to Get It |
|---|---|
| Bitwerx fingerprint (instanceId) | DataCo SupportCo portal only (`support.dataco.dental`) — not in GoldenEye |
| GoldenEye Facility ID (= Partner ID in DataCo) | GoldenEye URL: `/facility/{id}/details` |
| GoldenEye API key (🔑 icon on Facility Detail page) | GoldenEye Facility Detail page — NOT available in DataCo (masked there) |
| PMS type | GoldenEye facility page or HubSpot |
| Last service / last submitted dates | DataCo SupportCo portal |
| Address / phone | HubSpot location record |

---

## Ticket Statuses

| Status | Meaning |
|---|---|
| **Waiting for Support** | Bitwerx has not yet looked at the ticket |
| **Waiting for Customer** | Bitwerx replied and is waiting on us |
| **Escalated** | Escalated internally at Bitwerx |
| **Resolved** | Bitwerx marked it done (verify before closing) |
| **Closed** | Auto-closed after resolution |

---

## After Submitting a Ticket

After the ticket is created, always share it with David Herrera:

1. On the ticket page, click **+ Share** under "Shared with"
2. Type "David Herrera" and select him from the dropdown
3. Click **Add**

David technically receives notifications via the InsideDesk org already, but sharing directly is standard practice for visibility.

---

## Best Practices

- **Always include the fingerprint** for any sync-related ticket ([Check Sync], [Server Swap], [Disable Location]). Bitwerx uses it to look up the location directly in their system.
- **Use consistent bracket format** in the Summary. Bitwerx techs filter and route by these.
- **For [Reactivate Location]**, include as much detail as possible (Partner ID, Kolla key, last dates) — this lets Bitwerx act without needing to ask follow-up questions.
- **Check DataCo SupportCo first** via the `dataco-sync-status` skill before opening a [Check Sync] ticket. If DataCo already shows the sync is healthy, the issue is upstream of Bitwerx.
- **"Share with InsideDesk"** is always the right share setting — this makes tickets visible to both sean.johnson@insidedesk.com and david.herrera (the InsideDesk org on Bitwerx's side).
- **Don't duplicate open tickets.** Check the open requests list before creating a new one for the same location.

---

## Related Skills

- `dataco-sync-status` — Check Bitwerx DataCo pipeline stages before filing a ticket
- `dataco-supportco-api` — Look up the Bitwerx fingerprint (instanceId) for a facility
- GoldenEye facility page — Source for the API key and Facility ID (Partner ID) needed for new location and reactivate tickets
- `sync-status` — Check GoldenEye snapshots as the first sync diagnostic step

# InsideDesk Sync Status — Full Determination Process

The `sync-status` skill (which checks GoldenEye snapshots) is only **Step 1**. Whether that's
the final answer depends on the office's PMS. This document describes the complete process for
determining whether an office is truly in sync and at what stage it's in.

---

## Step 1: Check GoldenEye Snapshots

Use the `sync-status` skill to check for snapshots in the last 24 hours.

- **Snapshots present** → office is in sync. For non-Bitwerx PMSs, this is the **final answer**.
- **No snapshots** → office is out of sync. Proceed to Step 2.

---

## Step 2: Determine if the PMS uses Bitwerx

**Bitwerx PMSs** (requires Dataco check):
- Dentrix (also called Dentrix Core)
- Dentrix Enterprise
- Eaglesoft

**Non-Bitwerx PMSs** (GoldenEye is the only check):
- OpenDental
- Denticon
- Ascend API
- All others

If the PMS is **not** in the Bitwerx list, GoldenEye snapshots are the only place to check.
If there are no recent snapshots, the office is out of sync and the investigation goes directly
to the office's IT / server side.

---

## Step 3 (Bitwerx offices only): Check Dataco

Navigate to `support.dataco.dental` and search for the practice by name. The **fingerprint**
(UUID shown in the DataCo Configuration panel) is the ultimate unique identifier, but InsideDesk
doesn't maintain a lookup table of fingerprints, so name search is the practical method.

See the `dataco-supportco-api` skill (in `id-claude-integrations`) for how to search and
authenticate on the Dataco site.

### Practice-level Status

At the top of the practice record there is a **Status** badge:

| Status | Meaning |
|--------|---------|
| **Live** | Normal active status |
| **Muted** | A Bitwerx technician has made an adjustment and marked it muted. Temporary. Not a concern — do not treat as out of sync. |

---

### Sync Stages

Below the status there is a **Sync** section with five stages. Four are relevant to InsideDesk:

#### 1. Connectivity
> "Do we have a heartbeat from the office server?"

| Color | Meaning |
|-------|---------|
| Green | Connected — server is reachable |
| Red | Lost heartbeat — no connection to server. This is **automatically an out-of-sync condition**. |

#### 2. Mission Control
> InsideDesk does **not** use this feature. It will always show "Never ran." Ignore it.

#### 3. Sync
> The sync client installed on the office server is communicating with Bitwerx/Dataco and
> syncing claim data. At this stage the data is with Dataco — it has **not** reached InsideDesk yet.

| Color | Meaning |
|-------|---------|
| Blue | Currently running / syncing |
| Green | Last successful run — check the timestamp |
| Red | Problem at this stage |

#### 4. Staging
> Dataco transforms and configures the data received from the Sync stage and loads it into
> their database. Still at Dataco — not yet sent to InsideDesk.

| Color | Meaning |
|-------|---------|
| Blue | Currently running |
| Green | Last successful run — check the timestamp |
| Red | Problem at this stage |

#### 5. Intermediate
> The final Dataco stage. When this completes, Bitwerx sends the claims to the InsideDesk
> Snapshot API. The snapshot should appear in GoldenEye **immediately** upon completion —
> there is no expected lag.

| Color | Meaning |
|-------|---------|
| Blue | Currently running |
| Green | Last successful run — check the timestamp |
| Red | Problem at this stage |

---

### What "Fully In Sync" Looks Like

All four stages (Connectivity, Sync, Staging, Intermediate) are **green** and all timestamps
are from **today**. When you see this, verify by confirming the snapshot also appears in
GoldenEye under the office's Snapshots tab.

Example of a healthy Dataco record:
- Connectivity: Last Successful 5/29/2026 10:17 AM EST
- Mission Control: Never ran *(ignored)*
- Sync: Last Successful 5/29/2026 2:08 AM EST
- Staging: Last Successful 5/29/2026 4:00 AM EST
- Intermediate: Last Successful 5/29/2026 7:57 AM EST

---

### Out-of-Sync Conditions and Follow-up

| Condition | What it means | Action |
|-----------|--------------|--------|
| Any stage is **red** | Problem at that stage | Escalate to Bitwerx |
| Intermediate is green but timestamp is **stale** (not today) | Claims were processed but not recently re-run | File a Jira ticket with Bitwerx to resend claims |
| Intermediate is green + today's timestamp, but **no snapshot in GoldenEye** | Should not happen — indicates a potential API issue | Investigate InsideDesk snapshot ingestion |
| Connectivity is red | Server heartbeat lost | Notify office IT to check the sync client / server |

### Filing a Jira Ticket with Bitwerx
When Intermediate is stale or a stage is stuck, a Jira ticket is filed to Bitwerx requesting
they resend claims for the affected practice. (Workflow TBD — to be documented separately.)

---

## Summary Flow

```
Check GoldenEye snapshots (last 24h)
    │
    ├── Snapshots present → ✅ IN SYNC
    │
    └── No snapshots → Check PMS type
            │
            ├── Non-Bitwerx (OpenDental, Denticon, Ascend, etc.)
            │       → ❌ OUT OF SYNC — investigate server/IT side
            │
            └── Bitwerx (Dentrix, Dentrix Enterprise, Eaglesoft)
                    → Check Dataco (support.dataco.dental)
                            │
                            ├── Status: Muted → not a concern, check stages
                            ├── Connectivity red → ❌ no heartbeat
                            ├── Sync/Staging red → ❌ problem at that stage
                            ├── Intermediate green + today's timestamp → verify GoldenEye
                            └── Intermediate stale → file Jira ticket to Bitwerx
```

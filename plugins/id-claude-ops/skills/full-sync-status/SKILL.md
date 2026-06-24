---
name: full-sync-status
description: >
  Get a complete sync status overview for a dental office — GoldenEye snapshots, Dataco pipeline
  stages (if Bitwerx PMS), and HubSpot/Gmail ticket history — synthesized into a single verified
  report. Use this skill whenever the user wants a full picture of whether an office is in sync
  and why, not just a quick snapshot check. Trigger on phrases like "full sync status for [office]",
  "what's going on with [office]'s sync", "is [office] syncing and are there any open issues",
  or "give me a complete sync overview for [office]". Prefer this over the standalone sync-status
  skill when the user needs to troubleshoot or make a decision about an office.
---

# Full Sync Status

Orchestrates a complete sync health check for a dental office by calling three sub-skills in
sequence and synthesizing their results into a single verified report.

> **Read first:** Read `references/full-sync-status.md` (bundled in this skill) for the
> full domain context and decision logic behind this workflow before proceeding.

## Sub-skills called (in order)

1. `sync-status` — GoldenEye snapshot check
2. `dataco-sync-status` — Dataco pipeline stages *(Bitwerx PMS only)*
3. `office-ticket-history` — HubSpot tickets + Gmail activity

---

## Step 1: GoldenEye snapshot check

Run the `sync-status` skill for the named facility. Collect the `SYNC_STATUS_RESULT` block.

Key fields to branch on:
- `status` — IN_SYNC | OUT_OF_SYNC | NEVER_SYNCED
- `pms` — determines whether to proceed to Dataco

---

## Step 2: Determine if Dataco check is needed

**Bitwerx PMSs** (proceed to Step 3):
- Dentrix (= Dentrix Core)
- Dentrix Enterprise
- Eaglesoft

**Non-Bitwerx PMSs** (skip to Step 4):
- OpenDental, Denticon, Ascend API, and all others

If `SYNC_STATUS_RESULT.status` is `IN_SYNC` **and** PMS is non-Bitwerx → skip Steps 3,
proceed to Step 4, then synthesize. The office is confirmed in sync.

If `SYNC_STATUS_RESULT.status` is `IN_SYNC` **and** PMS is Bitwerx → still run Step 3
to confirm pipeline health (Intermediate may be green even when snapshots are present).

---

## Step 3: Dataco pipeline check (Bitwerx only)

Run the `dataco-sync-status` skill for the same facility. Collect the `DATACO_STATUS_RESULT` block.

Key fields:
- `overall` — ALL_GREEN | STALE | FAILED | PARTIAL
- `intermediate_today` — whether the final stage ran today
- `connectivity` — whether the server heartbeat is alive

---

## Step 4: Ticket history check

Run the `office-ticket-history` skill for the same facility. Collect the `TICKET_HISTORY_RESULT` block.

---

## Step 5: Synthesize and report

Combine all three result blocks into a final verdict and report. Use the following logic:

### Verdict logic

| GoldenEye | Dataco (if applicable) | Verdict |
|-----------|----------------------|---------|
| IN_SYNC | ALL_GREEN | ✅ Fully in sync |
| IN_SYNC | STALE | ⚠️ Snapshots present but Dataco Intermediate is stale — monitor |
| IN_SYNC | FAILED | ⚠️ Snapshots present but a Dataco stage is failing — may degrade |
| IN_SYNC | N/A (non-Bitwerx) | ✅ In sync |
| OUT_OF_SYNC | ALL_GREEN | ⚠️ Dataco all green but no snapshot — possible InsideDesk ingestion issue |
| OUT_OF_SYNC | STALE | ❌ Out of sync — Intermediate stale, file Jira ticket to Bitwerx |
| OUT_OF_SYNC | FAILED | ❌ Out of sync — stage failure in Dataco pipeline |
| OUT_OF_SYNC | PARTIAL | ❌ Out of sync — pipeline still running, check back later |
| OUT_OF_SYNC | N/A (non-Bitwerx) | ❌ Out of sync — investigate server/IT side |
| NEVER_SYNCED | any | 🔴 Never synced — likely a new or misconfigured office |

### Report format

```
FULL_SYNC_STATUS_REPORT:
  facility: <name>
  client: <client>
  pms: <pms>
  verdict: <emoji + plain-language verdict>

  GoldenEye:
    status: IN_SYNC | OUT_OF_SYNC | NEVER_SYNCED
    last_snapshot: <timestamp or never>

  Dataco (if checked):
    practice_status: Live | Muted
    connectivity: OK | FAILED
    sync_today: true | false
    staging_today: true | false
    intermediate_today: true | false
    overall: ALL_GREEN | STALE | FAILED | PARTIAL

  DOS Status:
    last_service_date: <value from GoldenEye Service Date column, or null>
    dos_status: ✅ Recent (<days> days ago) | ⚠️ <days> days since last claim (syncing OK) | ❓ No service date on record

  Ticket History:
    open_tickets: <count>
    context: <summary>

  Recommended action: <one clear next step, or "no action needed">
```

### DOS status logic

Use `SYNC_STATUS_RESULT.days_since_dos` to populate the DOS Status block:
- `days_since_dos` ≤ 14, or null → ✅ Recent
- `days_since_dos` > 14 **and** `status` is IN_SYNC → ⚠️ flag with day count
- `last_service_date` is null → ❓ No service date on record

Only flag ⚠️ when the office is IN_SYNC — if the office is already OUT_OF_SYNC, the sync issue takes priority and the DOS flag is not meaningful.

### Recommended action guidance

- ✅ All green → "No action needed."
- ⚠️ Intermediate stale → "File a Jira ticket to Bitwerx requesting claims resend for [office]."
- ❌ Stage failed → "Escalate to Bitwerx — [stage name] is failing."
- ❌ Connectivity red → "Notify office IT — server heartbeat lost, sync client may be down."
- ❌ Non-Bitwerx, no snapshots → "Contact office IT to check the sync agent / server."
- ⚠️ GoldenEye in sync but Dataco Intermediate stale → "Monitor — snapshots present but pipeline may fall behind."
- Already an open ticket → "Open ticket exists ([subject], created [date]) — update it rather than creating a new one."

---

## Notes

- Always run all three sub-skills even if GoldenEye shows IN_SYNC — the ticket history adds
  valuable context and the Dataco check confirms pipeline health.
- If the user just wants a quick snapshot check (no troubleshooting context needed), direct
  them to the `sync-status` skill instead.
- When called on a Dentrix Enterprise office, note that all Dentrix Enterprise locations in
  a group share one Dataco record — the pipeline stages reflect the whole server, not just
  this one office.

---

## Step 6 — Log the run

After Step 5, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `full-sync-status` |
| `status` | `success` if the full report was synthesized · `partial` if any sub-skill failed or was skipped · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: office name, final verdict (e.g. "fully in sync", "out of sync — Intermediate stale"), and whether any open tickets were found. |
| `inputs` | `office_name={name}` |
| `outputs` | `verdict={verdict text}` · `goldeneye_status={IN_SYNC/OUT_OF_SYNC/NEVER_SYNCED}` · `open_tickets={N}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `dataco_checked={true/false}` · `dataco_overall={ALL_GREEN/STALE/FAILED/PARTIAL/n/a}` |

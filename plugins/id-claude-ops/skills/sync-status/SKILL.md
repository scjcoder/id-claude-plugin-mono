---
name: sync-status
description: >
  Check whether a dental facility is currently syncing with InsideDesk by looking up its most recent
  snapshot in GoldenEye. Use this skill whenever you need to know if a location is in sync, out of sync,
  or has never synced — whether that's answering Sean's question directly ("is Monroe Perio syncing?"),
  as a diagnostic step before creating a support ticket, or as a check within a larger workflow like
  offboarding, troubleshooting, or generating a status report. Trigger on phrases like "check sync for",
  "is [location] syncing", "last snapshot for", "sync status of", or whenever a workflow needs to verify
  a facility's connection health before taking action.
---

# Sync Status Check

Check whether a facility has synced with InsideDesk in the last 24 hours by inspecting its GoldenEye
snapshots. Returns a structured result that downstream workflows can branch on.

## Step 1: Search for the facility

Navigate to the GoldenEye facility search page:

```
https://<GOLDENEYE_HOST>/production/admin/facility?search=<URL-encoded facility name>
```

Read the page text and scan the results table for matching facilities. While reading the table, also capture the **Service Date** column value for the matched facility — this is the last date a claim was submitted. Record it as-is (e.g. "4 days ago", an absolute date, or null if the column is blank).

## Step 2: Handle search results

**If exactly one match:** proceed directly to Step 3.

**If multiple matches:** present them to the user as a numbered list including both the client name
and facility name for each result (the user needs the client context to pick the right one). Example:

```
I found multiple facilities matching "[name]":
1. Smile-Partners-USA — Monroe Perio (Monroe, MI)
2. MB2 — Monroe Family Dental (Monroe, LA)

Which one did you mean?
```

Wait for the user to select before continuing.

**If no matches:** report that no facility was found and ask the user to try a different search term
or check the spelling.

## Step 3: Navigate to the facility's snapshots tab

Once you have the facility ID (the number in the leftmost column of the search results), navigate to
its snapshots page with a 2-day date window (yesterday + today) to reliably catch overnight snapshots:

```
https://<GOLDENEYE_HOST>/production/admin/facility/<FACILITY_ID>/snapshots?dateFrom=<YESTERDAY>&dateTo=<TODAY>&pageSize=10
```

Calculate yesterday and today's dates in YYYY-MM-DD format using the current date.

## Step 4: Determine sync status

Read the page text and look at the snapshot table.

- **In sync**: at least one snapshot row appears in the table (any status counts)
- **Out of sync**: the table shows "0–0 of 0" (no rows)

Also note the most recent snapshot's timestamp and the PMS version if visible.

## Step 5: Output the result

Always output **both** a structured result block and a human-readable summary.

### Structured result block (for downstream workflows to parse)

```
SYNC_STATUS_RESULT:
  facility_id: <id>
  facility_name: <name>
  client: <client>
  status: IN_SYNC | OUT_OF_SYNC | NEVER_SYNCED
  last_snapshot_date: <date and time, or "never">
  hours_since_last_snapshot: <number, or null if never>
  pms: <pms type and version if visible, or null>
  last_service_date: <value from Service Date column, or null if blank>
  days_since_dos: <integer if calculable from relative text, or null>
```

Use `NEVER_SYNCED` if the facility has no snapshots at all (you can verify by checking the broader
facility list page which shows "Never" for the snapshot column on facilities that have never synced).

### Human-readable summary

A single concise line, for example:

- ✅ **Monroe Perio** (Smile-Partners-USA) is **in sync** — last snapshot today at 9:04 AM
- ⚠️ **Monroe Perio** (Smile-Partners-USA) is **out of sync** — last snapshot was 3 days ago (May 26)
- 🔴 **Monroe Perio** (Smile-Partners-USA) has **never synced**

## Notes

- The GoldenEye facility list page shows a "Snapshot" column with relative times like "15 days ago"
  or "3 days ago". Do not use this as your source of truth — always check the snapshots tab with the
  explicit date window for a precise answer.
- If you are called as a sub-skill from another workflow, emit the structured result block so the
  calling skill can branch on `status` without having to parse the human summary.
- The snapshots tab defaults to today only if you navigate to it without URL params. Always supply
  the `dateFrom` and `dateTo` params explicitly.

---

## Step 6 — Log the run

After Step 5, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `sync-status` |
| `status` | `success` if the sync status was determined · `error` if the facility was not found or the page failed to load |
| `summary` | 1–3 sentences: facility name checked, sync status result (in_sync/out_of_sync/never_synced), and the last snapshot date. |
| `inputs` | `facility_name={name}` |
| `outputs` | `status={IN_SYNC/OUT_OF_SYNC/NEVER_SYNCED}` · `last_snapshot_date={date or "never"}` · `facility_id={id}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `pms={pms type or null}` · `last_service_date={date or null}` |

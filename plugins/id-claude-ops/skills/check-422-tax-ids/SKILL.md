---
name: check-422-tax-ids
description: >
  Check whether a TIN (Tax ID) that triggered a GoldenEye 422 "Unexpected tax id" snapshot error is
  already present in a facility's approved Expected TaxIds list. Use this skill whenever you need to
  verify if a 422-error TIN is a legitimate unknown or just missing from the configuration — whether
  called automatically from the 422-tax-id-report workflow or manually by Sean. Trigger on phrases
  like "is this TIN approved for facility X", "check if [TIN] is in the expected list for [facility]",
  "why is facility [ID] getting a 422 for [TIN]", or "check-422-tax-ids". Also trigger automatically
  when the 422-tax-id-report skill needs to cross-reference a TIN against facility configuration.
---

# Check 422 Tax ID Against Facility Configuration

Given a GoldenEye facility ID and a TIN that caused a 422 snapshot error, navigate to the facility's
details page and check whether that TIN is already in the approved Expected TaxIds list.

This answers the question: *Is this a configuration gap, or is this TIN genuinely not supposed to be there?*

---

## Step 1: Get inputs

**If called from the 422-tax-id-report workflow**, the caller will pass `facility_id` and `unknown_tin`
directly — use them and skip to Step 2.

**If run manually with no inputs**, ask the user for both pieces:
1. The GoldenEye facility ID (numeric, e.g. `3264`)
2. The TIN that caused the 422 error (e.g. `223783216`)

Use `AskUserQuestion` if available, or ask inline. Wait for the answer before proceeding.

---

## Step 2: Navigate to the facility details page

Open the facility details page using the Claude-controlled browser:

```
https://<GOLDENEYE_HOST>/production/admin/facility/{facility_id}/details
```

The Details tab is the default — no tab switching needed.

---

## Step 3: Extract the Expected TaxIds

Read the page content and locate the **"Expected TaxIds"** section. It lists one TIN per line. Also note
the **"Blank TaxId Allowed"** checkbox (checked = blank TINs are permitted for this facility).

Extract:
- `expected_tins` — list of all TINs shown (digits only, strip any formatting)
- `blank_allowed` — true if the checkbox is checked, false otherwise
- `facility_name` — the facility name shown at the top of the page
- `client_name` — the client/group name shown at the top (the linked text before the colon)

If the page fails to load or the Expected TaxIds section is missing, report the error and stop.

---

## Step 4: Check the TIN

Normalize both sides before comparing: strip hyphens, spaces, and leading zeros, then compare as strings.

`is_already_approved = unknown_tin (normalized) in expected_tins (normalized)`

---

## Step 5: Output the result

Always emit **both** a structured result block and a human-readable summary.

### Structured result block

```
TAXID_CHECK_RESULT:
  facility_id: <id>
  facility_name: <name>
  client: <client name>
  unknown_tin: <the TIN that caused the 422>
  is_already_approved: true | false
  expected_tins: [<list of TINs currently in the approved list>]
  blank_allowed: true | false
```

### Human-readable summary

**If the TIN is already approved:**
```
✅ TIN [unknown_tin] IS already in the Expected TaxIds list for [facility_name] ([client]).
   This 422 may indicate a sync timing issue or a bug — the TIN is configured correctly.
   Expected TaxIds: [list]
```

**If the TIN is NOT approved:**
```
⚠️ TIN [unknown_tin] is NOT in the Expected TaxIds list for [facility_name] ([client]).
   The approved TINs are: [list]
   Blank TaxId Allowed: yes | no
   Action needed: add [unknown_tin] to the facility's Expected TaxIds in GoldenEye, or
   investigate why this TIN is appearing in claims.
```

**If the Expected TaxIds list is empty:**
```
ℹ️ [facility_name] ([client]) has no Expected TaxIds configured at all.
   TIN [unknown_tin] cannot be checked because there is no approved list configured.
   Blank TaxId Allowed: yes | no
```

---

## Notes

- Always use the Claude-controlled browser (`mcp__Control_Chrome__open_url` + `mcp__Control_Chrome__get_page_content`). Do not attempt API calls to GoldenEye.
- The GoldenEye URL always uses the **production** environment: `<GOLDENEYE_HOST>/production/...`
- Normalization matters: TINs may be stored with or without hyphens. Strip all non-digit characters before comparing.
- When called as a sub-skill, emit the `TAXID_CHECK_RESULT:` block so the parent workflow can parse `is_already_approved` without string-matching the human summary.
- This skill does NOT modify the facility configuration — it only reads and reports. If a TIN needs to be added, flag it in the output and let Sean decide.

---

## Step 6 — Close the tab

After Step 5, close the GoldenEye tab that was opened in Step 2 using the **`chrome-cleanup`** helper skill.
Pass the `tabId` from the browser navigation response in Step 2.

---

## Step 7 — Log the run

After Step 6, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `check-422-tax-ids` |
| `status` | `success` if the TIN check completed · `error` if the facility page failed to load or the skill failed entirely |
| `summary` | 1–3 sentences: facility name checked, the TIN that was looked up, and whether it was found in the approved Expected TaxIds list. |
| `inputs` | `facility_id={id}` · `facility_name={name}` · `unknown_tin={tin}` |
| `outputs` | `is_already_approved={true/false}` · `expected_tins_count={N}` · `blank_allowed={true/false}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{}` |

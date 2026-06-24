---
name: 422-tax-id-report
description: >
  Generate a per-client 422 Tax ID Error Report from GoldenEye snapshot errors.
  Reads the GoldenEye Snapshots page in the browser, extracts all 422 "Unexpected
  tax id" errors, groups them by client -> facility -> tax ID, and produces an HTML
  report and a PDF report for each affected client. The PDF is delivered to Sean's
  Slack DM when complete.
  Use this skill whenever Sean asks for a tax ID report, wants to know which
  facilities have unexpected tax ID errors, says "run the tax ID report",
  "which clients have 422 tax ID errors", "tax ID mismatch report", or provides
  a date range and asks about tax ID errors in snapshots. Also trigger when
  preparing fix workflows for 422 errors or building client-facing tax ID reports.
---

# 422 Tax ID Error Report

Reads the GoldenEye Snapshots page, collects all 422 "Unexpected tax id" errors,
and produces two deliverables per affected client:
1. **HTML report** — clean, client-shareable version
2. **PDF report** — formatted version sent to Sean's Slack DM

---

## Step 0 — Prerequisites

Run the **`get-secret`** skill with name `slack-bot-token` to retrieve the Slack bot token.
Store the returned value — it will be passed to `slack-upload.py` in Step 5.

---

## Step 0b — Date range

**Default: today.** Use today's date for both `dateFrom` and `dateTo` unless Sean
explicitly provides a different range. Do not ask — just proceed with today.

---

## Step 1 — Open the GoldenEye Snapshots page

Navigate the Claude-controlled browser to:

```
https://<GOLDENEYE_HOST>/production/admin/snapshots?page=1&errorsOnly=true&dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD&pageSize=100
```

Substitute correct `dateFrom` and `dateTo` (format: `YYYY-MM-DD`).

Wait 3 seconds for the page to fully load, then **force-set the date fields via JavaScript**
to guarantee the correct date range is active — the UI can remember old date ranges from
previous sessions, and the URL params alone are not always enough to override React's
internal state:

```javascript
// Force-set date inputs — overrides any cached/remembered date range
const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
const dateFromInput = document.querySelector('input[name="dateFrom"]');
const dateToInput   = document.querySelector('input[name="dateTo"]');

// Use MM/DD/YYYY format (e.g. "05/19/2026") — substitute actual dates
setter.call(dateFromInput, 'MM/DD/YYYY_FROM');
dateFromInput.dispatchEvent(new Event('input',  { bubbles: true }));
dateFromInput.dispatchEvent(new Event('change', { bubbles: true }));

setter.call(dateToInput, 'MM/DD/YYYY_TO');
dateToInput.dispatchEvent(new Event('input',  { bubbles: true }));
dateToInput.dispatchEvent(new Event('change', { bubbles: true }));

// After setting both date fields, press Enter on the dateTo field to trigger a data reload
dateToInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
dateToInput.dispatchEvent(new KeyboardEvent('keyup',   { key: 'Enter', bubbles: true }));

// Also click a Search/Apply/Filter button if one exists
const searchBtn = [...document.querySelectorAll('button')].find(
  b => /search|apply|filter|go/i.test(b.innerText?.trim())
);
if (searchBtn) searchBtn.click();
```

Wait **4 seconds** for the data to reload after the JS update (increased from 2s to allow full re-fetch).

Take a screenshot to confirm:
- **Date From** and **Date To** fields show the correct dates
- The **Errors only** toggle is active (blue)

⛔ **If either date field does not show the correct date, STOP. Do not proceed with data extraction — the results would include data from the wrong date range. Log an error and exit.**

Note the total row count at the bottom (e.g. "1-100 of 340"). Calculate page count:
`ceil(total / 100)`. **Important:** `pageSize=100` is the maximum the backend
supports — values above 100 return 0 results, so always use exactly 100.

---

## Step 2 — Extract all 422 rows via JavaScript (compact format)

For each page (incrementing the `page` parameter), run this JavaScript in the browser.
The `systemMessage` lives in React component props, accessible via `__reactFiber`.

This extraction builds a **compact grouped object** directly in JavaScript, so output
size stays bounded regardless of claim volume. Each tax ID stores `{count, ids[≤20]}`
rather than a full claim array — this prevents buffer truncation on large datasets.

Also capture the **GoldenEye facility ID** from the facility cell's link href — this is
needed in Step 3b to look up the facility's Expected TaxIds configuration.

```javascript
const rows = document.querySelectorAll('tbody tr');
const grouped = {};

for (const row of rows) {
  const cells = row.querySelectorAll('td');
  if (cells.length < 7) continue;

  const client     = cells[1]?.innerText?.trim();
  const facility   = cells[2]?.innerText?.trim();
  const statusText = cells[3]?.innerText?.trim();
  const pms        = cells[6]?.innerText?.trim();

  if (!statusText?.includes('422')) continue;

  // Capture the GoldenEye facility ID from the facility link href
  const facilityLink = cells[2]?.querySelector('a');
  const facilityHref = facilityLink?.href || '';
  const facilityIdMatch = facilityHref.match(/\/facility\/(\d+)/);
  const facilityId = facilityIdMatch ? facilityIdMatch[1] : null;

  let systemMessage = null;
  for (const el of row.querySelectorAll('*')) {
    const rk = Object.keys(el).find(k => k.startsWith('__reactFiber'));
    if (rk) {
      try {
        let curr = el[rk];
        for (let i = 0; i < 15; i++) {
          if (curr?.memoizedProps?.systemMessage) {
            systemMessage = curr.memoizedProps.systemMessage;
            break;
          }
          curr = curr?.return;
        }
      } catch(e) {}
    }
    if (systemMessage) break;
  }

  if (!systemMessage || !systemMessage.includes('Unexpected tax id')) continue;

  const matches = [...systemMessage.matchAll(/Unexpected tax id (\d+) for claim (\d+)/g)];
  for (const [_, taxId, claimId] of matches) {
    if (!grouped[client]) grouped[client] = {};
    if (!grouped[client][facility]) grouped[client][facility] = { pms, facilityId, taxIds: {} };
    if (!grouped[client][facility].taxIds[taxId])
      grouped[client][facility].taxIds[taxId] = { count: 0, ids: [] };
    const entry = grouped[client][facility].taxIds[taxId];
    entry.count++;
    if (entry.ids.length < 20) entry.ids.push(claimId);
  }
}

JSON.stringify(grouped);
```

Run on every page. Each call returns a compact grouped object for that page.

---

## Step 3 — Merge per-page compact objects

Merge the per-page objects from Step 2 into a single structure. For each
`client → facility → taxId`, accumulate `count` and extend `ids` (keeping
only the first 20 unique IDs across all pages). Preserve `facilityId` in the
merged structure — it is needed for Step 3b.

```python
merged = {}
for page_grouped in all_page_results:
    for client, facilities in page_grouped.items():
        if client not in merged:
            merged[client] = {}
        for facility, info in facilities.items():
            if facility not in merged[client]:
                merged[client][facility] = {
                    "pms": info["pms"],
                    "facilityId": info.get("facilityId"),
                    "taxIds": {}
                }
            for tax_id, entry in info["taxIds"].items():
                if tax_id not in merged[client][facility]["taxIds"]:
                    merged[client][facility]["taxIds"][tax_id] = {"count": 0, "ids": []}
                existing = merged[client][facility]["taxIds"][tax_id]
                existing["count"] += entry["count"]
                for cid in entry["ids"]:
                    if cid not in existing["ids"] and len(existing["ids"]) < 20:
                        existing["ids"].append(cid)
```

Final structure per client:
```json
{
  "Eastern-Dental-Management": {
    "Acme Dental of Howell": {
      "pms": "Denticon",
      "facilityId": "3265",
      "taxIds": {
        "111224444": {"count": 12, "ids": ["2867849", "2867852", "...up to 20"]},
        "111223333": {"count": 3,  "ids": ["2868207", "2868209", "2868210"]}
      }
    }
  }
}
```

`count` is the true total; `ids` holds only the first 20. `generate_report.py`
handles both plain arrays and this `{count, ids}` compact format via its
`CompactClaims` class.

---

## Step 3b — Filter TINs already approved in GoldenEye config

Before generating any reports, check each 422 TIN against the facility's
**Expected TaxIds** list in GoldenEye. A TIN that is already in the approved
list triggered a 422 due to a sync timing issue or bug — it is not a real
configuration gap and should not appear in the client-facing report.

This step can silently eliminate entire facilities or even entire clients from
the report if all their 422 TINs are already configured correctly.

### For each facility in the merged data:

Navigate the Claude-controlled browser to:
```
https://<GOLDENEYE_HOST>/production/admin/facility/{facilityId}/details
```

Then run this JavaScript to extract the Expected TaxIds:

```javascript
// Find the "Expected TaxIds:" label and collect the TINs listed beneath it
const allEls = [...document.querySelectorAll('*')];
const label = allEls.find(el =>
  el.childElementCount === 0 && el.innerText?.trim() === 'Expected TaxIds:'
);
if (!label) return JSON.stringify({ tins: [], error: 'section not found' });

const tins = [];
let node = label.parentElement?.nextElementSibling || label.nextElementSibling;
while (node) {
  // Stop when we hit the Blank TaxId Allowed checkbox area
  if (node.querySelector('input[type="checkbox"]') || node.querySelector('label')) break;
  const text = node.innerText?.trim().replace(/-/g, '');
  if (/^\d+$/.test(text)) tins.push(text);
  node = node.nextElementSibling;
}
JSON.stringify({ tins });
```

### Normalization and comparison

Strip all non-digit characters from both the 422 TIN and each Expected TaxId
before comparing (GoldenEye may store TINs with or without hyphens):

```python
def normalize_tin(tin):
    return re.sub(r'\D', '', str(tin))

# For each facility, filter out already-approved TINs
filtered_out = {}  # track what was dropped for the summary log

for client in list(merged.keys()):
    for facility in list(merged[client].keys()):
        facility_id = merged[client][facility].get("facilityId")
        if not facility_id:
            continue  # can't check without an ID — leave in the report

        approved_tins = set(normalize_tin(t) for t in ge_expected_tins[facility_id])
        original_tins = list(merged[client][facility]["taxIds"].keys())

        for tin in original_tins:
            if normalize_tin(tin) in approved_tins:
                del merged[client][facility]["taxIds"][tin]
                filtered_out.setdefault(client, {}).setdefault(facility, []).append(tin)

        # Drop the facility if no TINs remain
        if not merged[client][facility]["taxIds"]:
            del merged[client][facility]

    # Drop the client if no facilities remain
    if not merged[client]:
        del merged[client]
```

### Log the filter results before proceeding

Always print a summary of what was filtered, even if nothing was dropped — this
makes it easy to spot misconfiguration or unexpected data:

```
GoldenEye Config Pre-filter
  Acme Dental of Laurel Springs (3265): 111225555 already approved — dropped
  Acme Dental of Marlton (3264):        111225555 already approved — dropped
  Acme Dental (1122):                      no TINs filtered (0 of 2 approved)

After filter: 1 client · 2 facilities · 5 TINs remaining
              1 client fully filtered out (all TINs already in GoldenEye config) — no report generated
```

If **all** TINs across all clients were filtered out, stop here and report that
to Sean — no reports need to be generated or sent.

---

## Step 4 — Generate reports for each client

> ⛔ **MANDATORY — NEVER write HTML or PDF generation code inline.**
>
> The report template is defined entirely in `generate_report.py` in this skill directory.
> You MUST call that script for every client. Do NOT write an HTML template. Do NOT write
> reportlab code. Do NOT produce any output files by any method other than running
> `generate_report.py`. Every 422 report must look identical to prior runs.

Install dependencies if needed:
```bash
pip install reportlab --break-system-packages -q
```

For each client remaining after Step 3b (at least one TIN not already in GoldenEye config), run:

```bash
python3 "/Users/sean/CODE/id-claude-reporting/skills/422-tax-id-report/generate_report.py" \
  --client "CLIENT-NAME" \
  --dates  "YYYY-MM-DD_DD" \
  --outdir "/Users/sean/CODE/id-claude-reporting" \
  --data   '<JSON string of facility data for this client>'
```

This produces per client:
- `tax_id_report_{client_slug}_{date_range}.html`
- `tax_id_report_{client_slug}_{date_range}.pdf`

Where `{client_slug}` is the client name lowercased with spaces replaced by
underscores, and `{date_range}` follows the format `2026-05-14_15`.

---

## Step 5 — Send each PDF to Sean via Slack DM

For each generated PDF:

```bash
python3 "/Users/sean/CODE/id-claude-reporting/skills/_shared/slack-upload.py" \
  --token   "<slack-bot-token from get-secret>" \
  --file    "/Users/sean/CODE/id-claude-reporting/tax_id_report_{slug}_{dates}.pdf" \
  --filename "tax_id_report_{slug}_{dates}.pdf" \
  --title   "Tax ID Error Report - {client_display} - {date_range_display}" \
  --comment "*Tax ID Error Report* - {client_display} - {date_range_display}"
```

Verify success: script prints `ok=True  permalink=https://...`.
If it fails, surface the raw error — do not proceed silently.

---

## Step 6 — Deliver links to Sean

After all PDFs are sent, provide links for each client:

```
[{Client} - HTML](computer:///Users/sean/CODE/id-claude-reporting/tax_id_report_{slug}_{dates}.html)
[{Client} - PDF](computer:///Users/sean/CODE/id-claude-reporting/tax_id_report_{slug}_{dates}.pdf)
```

Follow with a brief summary:
- How many clients had 422 tax ID errors
- Per client: facilities affected, unique tax IDs, total claims
- Flag any facility where tax ID `123` appears (likely a placeholder/bad value)

---

## Report format

**Header:** client name, "422 Tax ID errors" badge, "Claim Batches Received" as source label, date range

**Summary cards (3):** facilities affected | unique tax IDs | total claims affected

**One section per facility:**
- Header: facility name + PMS pill + total claims badge
- Table: Tax ID | # Claims | Claim IDs
  - Sorted descending by claim count
  - Claim lists > 20: show first 20 + "... and X more"
  - Claim lists <= 20: show all IDs

See `generate_report.py` in this skill directory for full HTML and PDF implementation.

---

## Key constraints

- **Browser only** — never use API calls or curl to fetch snapshot data.
- **pageSize=100** exactly — higher values silently return 0 results.
- **Only 422 rows with "Unexpected tax id"** — skip 400s, 201s, and 422s with
  different error messages.
- **Deduplicate claim IDs per facility** across multiple snapshot rows (use a Set).
- Flag any tax ID that appears to be an **invalid EIN** with an amber ⚠ **Invalid EIN** badge.
  - EINs are exactly 9 digits. GoldenEye stores them without dashes (digits only).
  - Flag if: wrong digit count, all-same-digit (`000000000`, `111111111`, etc.), or obviously sequential (`123456789`, `987654321`).
  - We cannot cryptographically verify an EIN — flag only structurally/obviously invalid values.
  - **Still add flagged EINs to GoldenEye config** so the next sync accepts the full batch. The office must also find and fix the bad claim in their PMS.
- The HTML report may be shared with clients — keep language professional and
  avoid internal tool names. Use "Claim Batches Received" not "GoldenEye Snapshots".

---

## Step 7 — Create HubSpot tickets (auto-triggered after reports)

After all PDFs are generated and delivered (Steps 4–6), automatically invoke
the **create-422-tickets** skill for each affected client.

Read the skill at:
```
/Users/sean/Library/Application Support/Claude/local-agent-mode-sessions/5cfffa96-a751-4a35-b82e-46d05da61787/fc45abbe-e1c2-4ec2-a88a-7510fe52b1d9/rpm/plugin_01DxUs1QUUP8tK61GESxsZXy/skills/create-422-tickets/SKILL.md
```

For each client in the grouped data, invoke the skill once, passing:

| Field | Source |
|---|---|
| `client_name` | Client key from Step 3 grouped data (display name) |
| `client_data` | The facilities dict for this client from Step 3 |
| `pdf_path` | Absolute path to the PDF generated in Step 4 for this client |
| `date_range` | Human-readable date range (e.g. `"May 14–15, 2026"`) |
| `date_slug` | File-safe date slug used in filenames (e.g. `"2026-05-14_15"`) |

The create-422-tickets skill handles its own HubSpot auth — no token needs
to be passed explicitly.

Collect the result dict returned per client (see Step 10 of create-422-tickets).
After all clients are processed, append a ticketing summary to the chat output:

```
HubSpot Tickets
  ✅ [Client] → [ticket URL]   (N facilities · N tax IDs · N claims)
  ⚠️  [Client] — skipped, ticket already exists
  ❌ [Client] — error: [reason]
```

---

## Step 8 — Check open 422 tickets for reminders and inactivity

After Step 7, search HubSpot for **all open 422 Tax ID tickets** (not just those created in
this run — check the full open backlog). The goals are:
1. Send a 10-day follow-up reminder draft to clients who haven't responded yet
2. Close tickets where there has been no client response for 21+ days

### 8a — Find open 422 tickets

Use the HubSpot MCP (`get_crm_objects` or `search_crm_objects`) to retrieve all tickets
in the **Install Pipeline** with:
- Subject containing `"422 Tax ID"` (or equivalent label used by create-422-tickets)
- Pipeline stage: any **open** stage (i.e., not closed/won/lost)

Retrieve each ticket's:
- `hs_ticket_id`
- `subject`
- `hs_lastmodifieddate`
- `hubspot_owner_id`
- `createdate`
- Associated company name (for display)

### 8b — Send 10-day reminder email drafts

For each open ticket where **all** of the following are true:
- Ticket age is **10–20 days** (created 10+ days ago but not yet 21 days old)
- No inbound client engagement in the last 10 days (use `hs_lastmodifieddate` as proxy if
  engagement detail is unavailable)
- The Claude context note does **not** already contain `reminder_sent: true` (check via
  Step 1a of `draft-422-client-email` — reading the context note before drafting)

Do the following for each qualifying ticket:

1. Pull the PDF already attached to the ticket. Retrieve file attachments via:
   ```python
   resp = requests.get(
       f"https://api.hubapi.com/crm/v4/objects/tickets/{ticket_id}/associations/attachments",
       headers=H
   )
   attachment_ids = [a["toObjectId"] for a in resp.json().get("results", [])]
   # Then fetch each attachment's metadata to find the PDF filename and download URL
   ```
   If no PDF is found on the ticket, skip this ticket and log a warning.

2. Invoke **`draft-422-client-email`** with `mode="reminder"`, passing:
   - `ticket_id` — the HubSpot ticket ID
   - `pdf_path` — local path to the PDF (download to a temp path if needed)
   - `client_name` — derived from the ticket subject or associated company
   - `mode` — `"reminder"`

3. Update the Claude context note on the ticket to add:
   - `reminder_sent: true`
   - `reminder_date: YYYY-MM-DD` (today)

Report in chat:
```
10-Day Reminder Drafts
  📧 [Client] → draft created   (ticket age: N days, last activity: YYYY-MM-DD)
  ⏭  [Client] → skipped, reminder already sent on YYYY-MM-DD
  ⚠️  [Client] → skipped, no PDF attachment found on ticket
```

### 8c — Identify inactive tickets

A ticket is **inactive** if:
- Its `hs_lastmodifieddate` is **more than 21 days ago** from today's date, AND
- There is no engagement (email reply, note, or meeting) from a contact (client-side) in the
  last 21 days.

To check engagements: use `get_crm_objects` with `associations=engagements` or query the
engagements endpoint for each ticket. Look for the most recent engagement where the source
is inbound (from the contact, not from the owner). If the most recent inbound engagement
is older than 21 days — or there are no inbound engagements at all — the ticket is inactive.

If engagement-level detail is not available via MCP, fall back to using `hs_lastmodifieddate`
as a proxy (conservative: flags tickets where nothing happened from either side in 21 days).

---

## Step 9 — Close inactive tickets

For each inactive ticket identified in Step 8:

### 9a — Add an inactivity note

Create a note engagement on the ticket using `manage_crm_objects` (objectType: `notes`) with
the following body:

```
Closed for inactivity — No client response received for 21+ days.

Ticket created: {createdate}
10-day reminder sent: {reminder_date if reminder_sent else "not sent"}
Last activity: {hs_lastmodifieddate}
Closed: {today's date}

This ticket was automatically closed because no response was received from the client
within 21 days of the original outreach (including a follow-up reminder at 10 days).
If the client responds or the issue resurfaces, please reopen or create a new ticket.
```

Associate the note to the ticket via the engagements association.

### 9b — Close the ticket

Update the ticket using `manage_crm_objects`:
- `hs_pipeline_stage`: set to the pipeline's **Closed** stage ID
- `hs_ticket_category` (or equivalent close-reason field): `"Closed for inactivity"`

If the exact stage ID for "Closed" is not known, query `get_properties` for the ticket
pipeline to find the correct stage ID before updating.

### 9c — Report inactivity closures

After processing all inactive tickets, append an **Inactive Tickets** section to the
chat summary:

```
Inactive 422 Tickets — Closed for Inactivity (21-day threshold)
  🔒 [Client] → [ticket URL]   last activity: YYYY-MM-DD  (created YYYY-MM-DD, reminder: YYYY-MM-DD)
  🔒 [Client] → [ticket URL]   last activity: YYYY-MM-DD  (created YYYY-MM-DD, reminder: not sent)
  — None found (all open tickets have recent activity)
```

---

## Step 10 — Update Claude context notes with final disposition

For every ticket that was **closed for inactivity** in Step 9, invoke the
**hubspot-context-note** skill (or write the note directly) with a summary of:

- Why the ticket was created (422 tax ID errors for which client/facilities)
- When it was created and what outreach was done
- Why it was closed (no client response in 21+ days, 10-day reminder was sent if applicable)
- Date closed and by whom (Claude, automated)
- What to do if the client re-engages: reopen the ticket or create a new one referencing this one

This ensures that anyone picking up the ticket history in the future has full context on
the lifecycle without needing to piece it together from the activity feed.

The hubspot-context-note skill is at:
```
/Users/sean/Library/Application Support/Claude/local-agent-mode-sessions/5cfffa96-a751-4a35-b82e-46d05da61787/fc45abbe-e1c2-4ec2-a88a-7510fe52b1d9/rpm/plugin_01DxUs1QUUP8tK61GESxsZXy/skills/hubspot-context-note/SKILL.md
```

Pass:
- `ticket_id`: the HubSpot ticket ID
- Context summary as described above, covering the full ticket lifecycle

---

## Step 11 — Log the run

After Step 10 (context notes), call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `422-tax-id-report` |
| `status` | `success` if all PDFs delivered · `partial` if some clients had errors · `error` if no reports generated due to failure |
| `summary` | 1–3 sentences: date range, how many clients affected, how many TINs filtered vs reported, whether any inactive tickets were closed |
| `inputs` | `date_from={date}` · `date_to={date}` · `total_422_rows={N}` |
| `outputs` | `clients_reported={N}` · `clients_filtered={N}` · `total_tins={N}` · `total_claims={N}` · `hubspot_tickets_created={N}` · `reminder_drafts_created={N}` · `inactive_tickets_closed={N}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `pre_filter_client_count={N}` · `post_filter_client_count={N}` · `tins_already_approved={N}` |

This step is always last — logging happens after all primary deliverables and HubSpot context notes are complete.

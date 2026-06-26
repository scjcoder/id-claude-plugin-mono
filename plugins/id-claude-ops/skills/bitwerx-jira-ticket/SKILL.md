---
name: bitwerx-jira-ticket
description: >
  Create a Bitwerx DataCo JIRA Service Desk ticket for a Bitwerx-synced location
  (Dentrix, Dentrix Enterprise, or Eaglesoft). Handles all issue types: [Check Sync],
  [Server Swap], [Disable Location], [Reactivate Location], [new location], [New Install],
  and [Password Request]. Navigates the browser to gather required data (fingerprint from
  DataCo SupportCo, API key and facility details from GoldenEye), fills out the JIRA
  form, submits it, and shares the ticket with David Herrera. Trigger when Sean says
  "create a Bitwerx ticket", "open a DataCo ticket", "file a JIRA for [location]",
  "check sync ticket for [location]", "new install ticket for [location]",
  "[issue type] ticket for [location]", or any similar request to contact Bitwerx about
  a location.
---

# Bitwerx JIRA Ticket Creation

Create a DataCo technical support ticket on behalf of InsideDesk at:
`https://bitwerx.atlassian.net/servicedesk/customer/portal/6/create/246`

> **Read first:** Read `references/bitwerx-jira-ticket.md` (bundled in this skill) now
> for the complete issue type list, description templates, and field guidance before
> proceeding.

---

## Step 1: Gather inputs

If not already provided, ask Sean:
1. **Issue type** — [Check Sync], [Server Swap], [Disable Location], [Reactivate Location], [new location], [New Install], or [Password Request]
2. **Facility name** — exact name as it appears in GoldenEye / DataCo

If the issue type is obvious from context (e.g. "file a check sync for Creekview", "new install ticket for HDO Hoffman"), infer it without asking.

> **[new location] vs [New Install] — these are NOT interchangeable:**
> - **[new location]** = DataCo account doesn't exist yet; Bitwerx needs to CREATE it. Use BEFORE the installer runs.
> - **[New Install]** = Installer has already run; verify the agent is phoning home (telemetry). Use AFTER the installer runs.

---

## Step 2: Get the fingerprint (for Check Sync / Server Swap / Disable Location)

For **[Check Sync]**, **[Server Swap]**, and **[Disable Location]**, you need the Bitwerx fingerprint (instanceId) from DataCo SupportCo.

**2a. Navigate to DataCo SupportCo and search for the facility:**

Navigate to `https://support.dataco.dental` in Chrome. Click the search icon, type the facility name, click the search button, then click the matching result.

**2b. Extract the fingerprint via JavaScript:**

```javascript
// Get the Azure B2C token from sessionStorage
const KEY = '3559999c-c487-402e-8053-72d73e605635-b2c_1a_signup_signin_dental'
          + '.72742b36-fbc0-48f0-a661-63d6f6aafecb-bitwerxinc.b2clogin.com'
          + '-accesstoken-216adce3-003d-40f9-9e53-d12d83fb7e50'
          + '--https://bitwerxinc.onmicrosoft.com/supportcoapi/read';
const token = JSON.parse(sessionStorage.getItem(KEY)).secret;

// Search for the practice by name
const resp = await fetch(
  `https://supportcodentalapi.azurewebsites.net/api/v2/practices?pageSize=10&filter=${encodeURIComponent('<FACILITY_NAME>')}`,
  { headers: { 'Authorization': 'Bearer ' + token } }
);
const list = await resp.json();
```

If multiple results, present them and ask Sean to confirm the right one.

```javascript
// Get the fingerprint from the first (or selected) result
const fingerprint = list[0].instanceId?.toUpperCase();
const partnerGroup = list[0].groupName; // e.g. "MB2 Dental"
```

> If the token is missing, ask Sean to log into `support.dataco.dental` first.

---

## Step 3: Get facility details from GoldenEye (for Reactivate Location / new location / New Install)

For **[Reactivate Location]**, **[new location]**, and **[New Install]**, navigate to the GoldenEye facility detail page to collect the required fields.

**3a.** Navigate to GoldenEye production and search for the facility, or go directly if you have the facility ID:
`https://<GOLDENEYE_HOST>/production/admin/facility/{id}/details`

**3b.** Read the following from the facility detail page:
- **Client / Practice group** — shown as a link at the top (e.g. "MB2")
- **PMS** — shown next to the database icon (e.g. "dentrix", "dentrix_enterprise", "eaglesoft")
- **GoldenEye API key** — shown next to the 🔑 key icon (40-character hex string). This is the "InsideDesk Api Key" — it is only readable here; it is masked in DataCo.
- **GoldenEye Facility ID** — the numeric ID in the URL (`/facility/{id}/details`). This is called "Partner ID" in DataCo.
- **Address** — shown next to the 📍 map pin icon
- **Phone** — shown next to the 📞 phone icon
- **Last service** — shown as "Last service: {date}"
- **Last submitted** — shown as "Last submitted: {date}"

---

## Step 4: Build the ticket content

Use the appropriate template from the reference doc. Quick reference:

### [Check Sync]
```
Summary:  [Check Sync] {Client} - {Facility Name}

Description:
{fingerprint}

Please check for any errors
```

### [Resend Claims]
```
Summary:  [Resend Claims] {Client} - {Facility Name}

Description:
{fingerprint}

Staging last ran: {stagingLast}
Intermediate last ran: {intermediateLast}

Please resend claims.
```

### [Server Swap]
```
Summary:  [Server Swap] {Client} - {Facility Name}

Description:
{fingerprint}

Please check for telemetry
```

### [Disable Location]
```
Summary:  [Disable Location] {Client} - {Facility Name}

Description:
{fingerprint}

This location has cancelled, please disable in DataCo.
```

### [Reactivate Location]
```
Summary:  [Reactivate Location] {Client} - {Facility Name}

Description:
Can you reactivate the following location and trigger a new sync if it has a heartbeat

{Facility Name}
{Client}
{pms}
Partner ID: {GoldenEye Facility ID}
API: {GoldenEye API key}
{Address}
{Phone or "No phone number"}
Last service: {MM/DD/YYYY}
Last submitted: {MM/DD/YYYY}
```

### [new location]
Use when the DataCo account does not yet exist and Bitwerx needs to CREATE it. Filed BEFORE the installer runs.
```
Summary:  [new location] {Client} - {Facility Name}

Description:
{Facility Name}
{Client}
{pms}
Partner ID: {GoldenEye Facility ID}
{GoldenEye API key}
{Address}
{Phone}

{Any additional context}
```

### [New Install]
Use AFTER the installer has run. Bitwerx verifies the agent is phoning home (telemetry). DataCo account already exists.
```
Summary:  [New Install] {Client} - {Facility Name}

Description:
{Facility Name}
{Client}
{pms}
Partner ID: {GoldenEye Facility ID}
{GoldenEye API key}
{Address}
{Phone}

{Context — e.g. "Office self installed, check for telemetry." or "Installer just ran, please verify telemetry."}
```

**Before filling in the form**, show Sean the proposed Summary and Description and ask for confirmation. Wait for approval.

---

## Step 5: Fill out and submit the JIRA form

Navigate to: `https://bitwerx.atlassian.net/servicedesk/customer/portal/6/create/246`

> ⚠️ **Fill Description BEFORE Summary.** The Summary field triggers "Suggested articles"
> which push the Description editor down the page. If you click the Description area after
> filling Summary, you may accidentally click one of those article links and navigate away.
> Always enter the description first while the page layout is stable.

1. Click inside the **Description** rich-text editor and type the full description
2. Use `form_input` (or click the **Summary** field) and enter the summary line — suggested articles will appear but the description is already filled so layout shifts don't matter
3. Use the `find` tool to locate the **Send** button by ref and click it — do NOT scroll near the suggested articles area to find Send, as scrolling can cause accidental clicks on article links
4. Leave **Share with** as "Share with InsideDesk" (default — do not change)
5. Wait for the confirmation page — note the ticket number (e.g. DATA-48452)

---

## Step 6: Share with David Herrera

On the newly created ticket page:

1. Under "Shared with" in the right panel, click **+ Share**
2. Type "David Herrera" in the participant field
3. Select David Herrera from the dropdown
4. Click **Add**

---

## Step 7: Add a human-readable note to the HubSpot ticket (if a ticket URL was provided)

Skip this step silently if no HubSpot ticket URL was provided.

Read `skills/hubspot-human-note/SKILL.md` and run it. Pass:

- `ticket_id`: the HubSpot ticket ID (extracted from the URL)
- `sections`: one table per JIRA ticket filed, with a header text block and a
  divider between each ticket if multiple were filed

**Single ticket:**
```python
[
  {
    "type": "text",
    "body": "<strong>Bitwerx JIRA ticket filed {YYYY-MM-DD}</strong>"
  },
  {
    "type": "table",
    "rows": [
      ["Ticket",      "<a href=\"https://bitwerx.atlassian.net/servicedesk/customer/portal/6/{TICKET_NUMBER}\">{TICKET_NUMBER}</a>"],
      ["Issue type",  "{Issue Type}"],
      ["Description", "{One-sentence description of what was requested.}"]
    ]
  }
]
```

**Multiple tickets** — add a `{"type": "divider"}` between each ticket block:
```python
[
  {"type": "text", "body": "<strong>Bitwerx JIRA tickets filed {YYYY-MM-DD}</strong>"},
  {"type": "table", "rows": [
    ["Ticket",      "<a href=\"...DATA-XXXXX\">DATA-XXXXX</a>"],
    ["Issue type",  "{Issue Type 1}"],
    ["Description", "{Description 1}"]
  ]},
  {"type": "divider"},
  {"type": "table", "rows": [
    ["Ticket",      "<a href=\"...DATA-YYYYY\">DATA-YYYYY</a>"],
    ["Issue type",  "{Issue Type 2}"],
    ["Description", "{Description 2}"]
  ]}
]
```

The `hubspot-token` is already in scope — no need to retrieve it again.

---

## Step 8: Report back to Sean

Confirm completion with:
- Ticket number and direct URL (e.g. `https://bitwerx.atlassian.net/servicedesk/customer/portal/6/DATA-48452`)
- Summary line used
- Confirmation that David Herrera was added

---

## Step 9 — Close the tabs

Before logging, close any browser tabs that were opened during Steps 2-8 using the **`chrome-cleanup`** helper skill.
Pass the `tabId` from your browser navigation responses (DataCo SupportCo and JIRA forms).
If multiple tabs were opened, call chrome-cleanup for each one.

---

## Step 10 — Log the run

After Step 9, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `bitwerx-jira-ticket` |
| `status` | `success` if the JIRA ticket was submitted and confirmed · `partial` if submitted but David Herrera share failed · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: issue type and facility name ticketed, JIRA ticket number created, and whether David Herrera was added as a participant. |
| `inputs` | `facility_name={name}` · `issue_type={type}` · `fingerprint={fingerprint or "n/a"}` |
| `outputs` | `ticket_number={e.g. DATA-48452}` · `ticket_url={url}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{}` |

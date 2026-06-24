---
name: verify-claim-ticket
description: >
  End-to-end verification of the InsideDesk Claim Feedback pipeline: reads the
  latest Slack #claim_feedback message (or a user-specified one), confirms the
  enqueuer Lambda received it in CloudWatch, confirms the processor Lambda
  created the HubSpot ticket, and validates key properties and associations.
  Use whenever you need to check whether a new Slack claim feedback message was
  processed correctly — e.g. after a deployment, after noticing a message with
  no corresponding ticket, or on a routine spot-check. Also use when the user
  says things like "check the latest claim", "did that message get processed",
  "verify the ticket was created", or pastes a Slack ts / claim ID and asks you
  to look it up.
---

# Skill: verify-claim-ticket

Verify that a Slack #claim_feedback message flowed all the way through the
pipeline to a HubSpot ticket.

## Pipeline overview

```
Slack #claim_feedback (CNQDHU3N3)
  → SQS FIFO
  → Enqueuer Lambda  (/aws/lambda/hubspot-feedback-tickets-slack-enqueuer)
  → Processor Lambda (/aws/lambda/hubspot-feedback-tickets-slack-processor)
  → HubSpot Tickets (portal 19834291, pipeline 892787555)
```

---

## Step 0 — Authenticate AWS

Before making any CloudWatch calls, run the **aws-login** skill
(`skills/aws-login/SKILL.md`) automatically — do not ask the user first.
If credentials are already valid it completes silently; if not, it refreshes
them before continuing.

---

## Step 1 — Identify the Slack message

If the user provided a Slack `ts` (e.g. `1776880246.644429`) or a claim ID,
use that directly. Otherwise read the latest messages from #claim_feedback:

```
Tool: mcp__a0fdd3cf-15f6-464f-b6da-95e9ff898737__slack_read_channel
  channel_id: CNQDHU3N3
  limit: 5
```

Pick the most recent bot message (the structured one with "Claim ID:", "User:",
etc.). Record:
- `ts` — the dedup key, e.g. `1776880246.644429`
- `claim_id` — from the opening URL (e.g. `/claim/MB2/58377497` → `58377497`)
- `submitter_email` — "User Email:" line
- `office_id` — "Office ID:" line
- `issue_type` — text before the first ": " in the "Feedback:" line
- `category` — "Category:" line (if present)

---

## Step 2 — Check enqueuer CloudWatch logs

Convert the ts to milliseconds for the `--start-time` filter:
  `start_ms = int(float(ts)) * 1000 - 60000`  (1 minute before the message)

```
Tool: mcp__AWS_API_MCP_Server__call_aws
  service: logs
  operation: filter_log_events
  parameters:
    logGroupName: /aws/lambda/hubspot-feedback-tickets-slack-enqueuer
    filterPattern: "<ts>"           # e.g. "1776880246.644429"
    startTime: <start_ms>
    region: us-east-1
    profile: install-982534385600
```

Look for a log line that contains the ts. A successful enqueue shows the
message was received and written to SQS. Record:
- ✅ Enqueuer received: YES / NO
- Any error messages

If the result is too large (> token limit), save it to a temp file and use
Python to extract lines containing the ts:
```bash
python3 -c "
import json, sys
data = json.load(open('/tmp/enqueuer_logs.json'))
for e in data.get('events', []):
    if '<ts>' in e.get('message',''):
        print(e['message'])
"
```

---

## Step 3 — Check processor CloudWatch logs

Same approach as Step 2, but use the processor log group:

```
Tool: mcp__AWS_API_MCP_Server__call_aws
  service: logs
  operation: filter_log_events
  parameters:
    logGroupName: /aws/lambda/hubspot-feedback-tickets-slack-processor
    filterPattern: "<ts>"
    startTime: <start_ms>
    region: us-east-1
    profile: install-982534385600
```

A successful run contains lines like:
- `"Processing SQS event"` with the ts in the payload
- `"Created ticket"` or `"Ticket already exists"` (dedup)
- A HubSpot ticket ID (e.g. `"ticket_id": "12345"`)

Record:
- ✅ Processor ran: YES / NO
- ✅ Ticket created or deduplicated: YES / NO / DEDUP
- HubSpot ticket ID if logged

---

## Step 4 — Verify HubSpot ticket

Search for the ticket using the Slack ts as the dedup key:

```
Tool: mcp__eba53d3c-d280-4218-ba07-d9e0e4624ed7__search_crm_objects
  objectType: tickets
  filterGroups:
    - filters:
        - propertyName: claim_slack_message_id
          operator: EQ
          value: "<ts>"
  properties:
    - subject
    - claim_slack_message_id
    - claim_id
    - claim_office_id
    - claim_user_email
    - claim_issue_type
    - claim_feedback_category
    - claim_office_name_raw
    - claim_pms
    - claim_collector
    - hs_pipeline
    - hs_pipeline_stage
    - createdate
```

A correctly processed ticket will have:
- `hs_pipeline` = `892787555`
- `hs_pipeline_stage` = `1345908024` (New)
- `claim_slack_message_id` = the ts
- `claim_id`, `claim_office_id`, `claim_user_email` populated
- `claim_issue_type` populated (from Assist form dropdown, e.g. "Claim is on File with Payer")

Record:
- ✅ Ticket found: YES / NO
- ✅ In correct pipeline/stage: YES / NO
- Key property values to spot-check against the Slack message

---

## Step 5 — Check associations (optional but recommended)

If a ticket was found, verify the Contact and Location associations:

```
Tool: mcp__eba53d3c-d280-4218-ba07-d9e0e4624ed7__get_crm_objects
  objectType: tickets
  objectId: <ticket_id>
  associations: [contacts, 2-14718097]    # Contacts + Locations
```

Expected:
- At least one Contact association (matched on `claim_user_email`)
- At least one Location association (matched on `claim_office_id` = Locations.facility_id)

---

## Output format

Always report results as a clear pass/fail checklist:

```
## Claim Feedback Verification — ts: 1776880246.644429

**Message details**
  Claim ID:     58377497
  Submitter:    user@example.com
  Office ID:    3103
  Issue Type:   Claim is on File with Payer

**Pipeline check**
  ✅ Enqueuer Lambda received message
  ✅ Processor Lambda ran successfully
  ✅ HubSpot ticket created (ID: 12345)

**Ticket properties**
  ✅ Pipeline:  892787555 (Claim Feedback)
  ✅ Stage:     1345908024 (New)
  ✅ claim_issue_type:  Claim is on File with Payer
  ✅ claim_office_id:   3103
  ✅ claim_user_email:  user@example.com

**Associations**
  ✅ Contact associated
  ✅ Location associated

**Summary: All checks passed.**
```

Use ❌ for any step that failed, and include the relevant error detail inline.
For a deduplication hit (ticket already existed), note it as:
  `ℹ️ Processor: DEDUP — ticket already existed (ID: 12345)`

---

---

## Step 6 — Log the run

After Step 5, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `verify-claim-ticket` |
| `status` | `success` if all pipeline checks passed · `partial` if some checks passed but others failed (e.g. ticket found but missing associations) · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: the Slack ts or claim ID checked, whether the enqueuer and processor Lambdas confirmed receipt, and whether the HubSpot ticket was found and validated. |
| `inputs` | Slack message ts or claim ID (user-supplied or auto-selected from latest #claim_feedback message) |
| `outputs` | Lambda receipt confirmed (yes/no), HubSpot ticket created (yes/no), ticket ID and URL if found |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{ "ts": "<slack_ts>", "claim_id": "<claim_id>", "ticket_id": "<hubspot_ticket_id or null>", "enqueuer_ok": <true|false>, "processor_ok": <true|false> }` |

Call skill-logger even on failure — the log should capture what went wrong.

---

## Key constants (do not change without updating handler.py)

| Constant | Value |
|----------|-------|
| Slack channel | `CNQDHU3N3` (#claim_feedback) |
| Enqueuer log group | `/aws/lambda/hubspot-feedback-tickets-slack-enqueuer` |
| Processor log group | `/aws/lambda/hubspot-feedback-tickets-slack-processor` |
| HubSpot portal | `19834291` |
| Pipeline ID | `892787555` |
| Stage: New | `1345908024` |
| Stage: In Review | `1345908025` |
| Stage: Escalated to JIRA | `1345908026` |
| Stage: Closed | `1345908027` |
| AWS profile | `install-982534385600` |
| AWS region | `us-east-1` |
| Dedup property | `claim_slack_message_id` (= Slack message `ts`) |

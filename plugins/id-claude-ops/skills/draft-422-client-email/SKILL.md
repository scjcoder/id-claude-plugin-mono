---
name: draft-422-client-email
description: >
  Draft client-facing emails to Account POCs about 422 Tax ID errors. Attaches
  the client's PDF report directly to a Gmail draft, logs the email as a HubSpot
  engagement on the ticket (activity feed), and posts a Slack summary. Designed
  to be called after create-422-tickets, or manually by Sean for any client.
  Trigger when Sean says "draft the 422 emails", "email the POCs the report",
  "send the 422 reports to clients", "draft client emails for the tax ID errors",
  "email [client] about the 422 report", or similar.
---

# Skill: Draft 422 Client Email

Attaches each client's 422 Tax ID Error PDF directly to a Gmail draft addressed
to the client's Account POC contacts, logs the email as a HubSpot engagement on
the ticket (activity feed), and posts a Slack summary. Saves as a draft — Sean
reviews and sends manually.

---

## Prerequisites

Run the `get-secret` skill with name `hubspot-token` to retrieve the HubSpot API token.
See `id-claude-shared` plugin: `skills/_shared/hubspot-setup.md` — Steps B and C are handled by the `get-secret` skill.

---

## Key constants

| Item | Value |
|---|---|
| Slack DM channel | `D0B0YUWV1UK` |


---

## Inputs

This skill accepts two calling modes:

### Mode A — Called from `create-422-tickets` (batch)

Iterate over each client result dict from that skill's Step 11 and call this skill
once per client. The result dict already contains everything needed:

| Field | Type | Example |
|---|---|---|
| `client_name` | string | `"Acme Dental Management"` |
| `ticket_id` | string | `"12345678"` |
| `pdf_path` | string | `/Users/sean/CODE/.../Eastern_Dental_422_2026-05-14.pdf` |
| `date_range` | string | `"May 14–15, 2026"` |
| `poc` | list[str] | `["Pati Vasquez", "Jane Smith"]` |
| `ticket_url` | string | `"https://app.hubspot.com/contacts/.../ticket/..."` |
| `client_data` | dict | see `create-422-tickets` for schema |
| `mode` | string | `"initial"` (default) or `"reminder"` |

### Mode B — Called manually by Sean

Sean provides `client_name` and `pdf_path` (or a HubSpot ticket URL). Derive
`ticket_id` from the URL if provided, and look up any missing fields from HubSpot.
`mode` defaults to `"initial"` unless Sean specifies `"reminder"`.

---

## Step 1 — Retrieve POC email addresses from the HubSpot ticket

Fetch the contacts associated to the ticket (set during `create-422-tickets` Step 6a):

```python
import requests

token     = "<hubspot_token>"
ticket_id = "<ticket_id>"
H         = {"Authorization": f"Bearer {token}"}

resp = requests.get(
    f"https://api.hubapi.com/crm/v4/objects/0-5/{ticket_id}/associations/contacts",
    headers=H
)
contact_ids = [str(a["toObjectId"]) for a in resp.json().get("results", [])]

poc_contacts = []
for cid in contact_ids:
    r = requests.get(
        f"https://api.hubapi.com/crm/v3/objects/contacts/{cid}",
        headers=H,
        params={"properties": "firstname,lastname,email"}
    )
    props = r.json().get("properties", {})
    email = props.get("email", "")
    name  = f"{props.get('firstname','')} {props.get('lastname','')}".strip() or email
    if email:
        poc_contacts.append({"name": name, "email": email})
        print(f"  ✅ {name} <{email}>")
    else:
        print(f"  ⚠️  Contact {cid} has no email — skipping")

poc_emails = [c["email"] for c in poc_contacts]
poc_names  = [c["name"]  for c in poc_contacts]
```

**If no emails are found**: log a warning, skip this client entirely.
Do not create a draft with no recipients.


---

## Step 1a — Read Claude Context note from the ticket (if available)

Before drafting, check the ticket for a Claude Context note. If found, surface it
so any flagged decisions or follow-up items are visible before the email goes out.

```python
import base64, json as _json

notes_resp = requests.get(
    f"https://api.hubapi.com/crm/v4/objects/tickets/{ticket_id}/associations/notes",
    headers=H
)
note_ids = [a["toObjectId"] for a in notes_resp.json().get("results", [])]

claude_context = None
for nid in note_ids:
    nr = requests.get(
        f"https://api.hubapi.com/crm/v3/objects/notes/{nid}",
        headers=H,
        params={"properties": "hs_note_body"}
    )
    body = nr.json().get("properties", {}).get("hs_note_body", "") or ""
    if body.startswith("🤖 CLAUDE CONTEXT"):
        try:
            b64 = body.split("\n", 1)[1].strip()
            claude_context = _json.loads(base64.b64decode(b64))
        except Exception:
            pass
        break

if claude_context:
    print(f"\n📋 Claude Context found for {client_name}:")
    print(f"  Origin:    {claude_context.get('origin', '—')}")
    print(f"  Checked:   {claude_context.get('checked', '—')}")
    print(f"  Decisions: {claude_context.get('decisions', '—')}")
    print(f"  Next:      {claude_context.get('next', '—')}")
else:
    print(f"  ℹ️  No Claude Context note found on ticket {ticket_id}")
```

**Surface any warnings to Sean before proceeding.** If the context note flags an
unresolved decision or a "next" action that affects the email, pause and ask Sean
whether to continue.

---

## Step 2 — Base64-encode the PDF

```python
import base64, os

filename = os.path.basename(pdf_path)
with open(pdf_path, "rb") as f:
    pdf_b64 = base64.b64encode(f.read()).decode("utf-8")
print(f"  ✅ PDF encoded: {filename} ({len(pdf_b64)} base64 chars)")
```

**If `pdf_path` does not exist**: skip this client entirely and log as an error.
Never create a draft without the report attached.


---

## Step 3 — Create the Gmail draft with PDF attachment

Use `mcp__bdbc2263-f755-4531-b2b3-91da919069f8__create_draft`.

### Logo

Load and base64-encode the InsideDesk logo from the skill directory:

```python
import base64 as _b64

logo_path = "/Users/sean/CODE/id-claude-ops/skills/draft-422-client-email/insidedesk-logo.png"
with open(logo_path, "rb") as f:
    logo_b64 = _b64.b64encode(f.read()).decode("utf-8")
```

### Build the body

```python
first_name = poc_names[0].split()[0] if poc_names else "there"
is_reminder = (mode == "reminder")

office_names = []
if client_data:
    # client_data is a dict keyed by facility name
    office_names = list(client_data.keys())

office_list_html = "".join(f"<p>{name}</p>" for name in office_names) if office_names else ""

signature_html = """<p style="margin-top:24px;color:#555;font-size:13px;line-height:1.6">
--<br>
<strong>Sean Johnson</strong><br>
Data Integrations Manager<br>
<a href="https://insidedesk.pro" style="color:#7b3fa0">InsideDesk</a> | T: 830-402-5524<br>
<img src="cid:insidedesk_logo" alt="InsideDesk" style="height:32px;margin-top:6px;">
</p>"""

if is_reminder:
    html_body = f"""<p>Hi {first_name},</p>

<p>I wanted to follow up on our previous email regarding unrecognized tax IDs for
your locations. We haven't heard back yet and wanted to make sure this didn't slip
through the cracks. I've re-attached the report for reference.</p>

{office_list_html}
<p>Once we hear from you on which TINs are valid, we can get these added to your
configuration and the affected claims will process correctly.</p>

<p>Please let us know if you have any questions.</p>

{signature_html}"""
else:
    html_body = f"""<p>Hi {first_name},</p>

{office_list_html}
<p>While reviewing incoming claims for your locations, we flagged some tax IDs we
don't have on file. Until these are resolved, the affected claims won't process
correctly on our end. I've attached a report with the details, including a quick
FAQ on next steps.</p>

<p>Please review and let us know which TINs are valid and should be added to your
configuration. If any are incorrect, flag those and we'll coordinate from there.</p>

{signature_html}"""

subject = (
    "Following Up: Unrecognized Tax IDs on Incoming Claims"
    if is_reminder else
    "Action Needed: Unrecognized Tax IDs on Incoming Claims"
)
```

### Call parameters

- `to`: `poc_emails` (list — all POC emails in `to`, not CC)
- `cc`: `["install@insidedesk.com"]` (always CC on every draft)
- `subject`: `subject` (set above — varies by mode)
- `htmlBody`: `html_body`
- `attachments`:
  ```python
  [
      {"content": pdf_b64,   "filename": filename,          "mimeType": "application/pdf"},
      {"content": logo_b64,  "filename": "insidedesk-logo.png", "mimeType": "image/png", "inline": True},
  ]
  ```

**Subject is fixed** — do not include `client_name` in the subject line.

**Multi-POC greeting**: Use only the first POC's first name. All POC emails go in
the `to` field.

**`client_data` unavailable** (manual mode): omit the office list block entirely.


---

## Step 3a — Log email engagement on the HubSpot ticket

After creating the Gmail draft, log the email as a HubSpot engagement so it appears
in the ticket's activity feed.

Use Desktop Commander to run this via Python:

```python
import time, json as _json

headers_val = _json.dumps({
    "from": {"email": "sean.johnson@insidedesk.com", "firstName": "Sean", "lastName": "Johnson"},
    "to":   [{"email": e} for e in poc_emails],
    "cc":   [{"email": "install@insidedesk.com"}],
    "sender": {"email": "sean.johnson@insidedesk.com"},
})

email_payload = {
    "properties": {
        "hs_email_direction": "EMAIL",
        "hs_email_status":    "DRAFT",
        "hs_email_subject":   subject,  # set in Step 3 — varies by mode
        "hs_email_html":      html_body,
        "hs_email_headers":   headers_val,
        "hs_timestamp":       int(time.time() * 1000),
    }
}

email_resp = requests.post(
    "https://api.hubapi.com/crm/v3/objects/emails",
    headers={**H, "Content-Type": "application/json"},
    json=email_payload,
)
email_id = email_resp.json().get("id")
print(f"  ✅ HubSpot email engagement created: {email_id}")

# Note: v4 associations endpoint fails with USER_DOES_NOT_HAVE_PERMISSION —
# use v3 (ticket→email direction) which works with existing app permissions.
assoc_resp = requests.put(
    f"https://api.hubapi.com/crm/v3/objects/tickets/{ticket_id}/associations/emails/{email_id}/ticket_to_email",
    headers=H,
)
if assoc_resp.status_code in (200, 201, 204):
    print(f"  ✅ Associated with ticket {ticket_id}")
else:
    print(f"  ⚠️  Association failed: {assoc_resp.status_code} — {assoc_resp.text[:200]}")
```

**If this step fails**: log a warning but do not fail the skill. The Gmail draft is
the primary deliverable — the HubSpot association is supplementary.


---

## Step 4 — Post Slack notification

Post to `D0B0YUWV1UK` via Slack Web API using Desktop Commander.

Run the `get-secret` skill with name `slack-bot-token` to retrieve the Slack bot token.
See `id-claude-shared` plugin: `skills/_shared/slack-setup.md` — Section A (token retrieval) is handled by the `get-secret` skill.

```python
poc_display = ", ".join(poc_names)
label = "422 Reminder Draft Created" if is_reminder else "422 Draft Created"

message = (
    f":email: *{label} — {client_name}*\n"
    f"POC(s): {poc_display}\n"
    f"<https://mail.google.com/mail/#drafts|Open Gmail Drafts>"
)

resp = requests.post(
    "https://slack.com/api/chat.postMessage",
    headers={"Authorization": f"Bearer {bot_token}", "Content-Type": "application/json"},
    json={"channel": "D0B0YUWV1UK", "text": message, "mrkdwn": True}
)
if not resp.json().get("ok"):
    print(f"Slack error: {resp.json().get('error')}")
```

If Slack fails, note it but do not fail the skill — the Gmail draft is primary.

---

## Step 5 — Return result to caller

```python
{
    "client":        client_name,
    "status":        "drafted",    # "drafted" | "skipped" | "error"
    "draft_created": True,
    "poc_emails":    poc_emails,
}
```

---

## Final summary (standalone or batch)

After processing all clients, print:

```
Drafts Created (N)
  ✅ [Client Name]
      POCs: [name(s)]
      Draft: ✓ (saved to Gmail Drafts, PDF attached)

Skipped — No POC Emails (N)
  ⚠️  [Client Name] — no email found for associated contacts

Errors (N)
  ❌ [Client Name]: [reason]
```


---

## Edge cases

- **No POC emails found**: skip this client. Log as skipped. Never create a draft
  with no recipients.
- **PDF file not found at `pdf_path`**: skip draft creation for this client. A draft
  with no attachment would confuse the recipient — flag for manual follow-up.
- **`client_data` unavailable** (manual mode): omit the office list from the email
  body. The email works without it.
- **Multiple POCs**: all go in `to`. Greeting uses only the first POC's first name.
- **Ticket has no associated contacts**: log as skipped. This was already flagged
  in `create-422-tickets` — do not attempt to guess or substitute contacts.

---

## Step 6 — Log the run

After Step 5, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `draft-422-client-email` |
| `status` | `success` if all drafts were created · `partial` if any clients were skipped (no POC emails or PDF not found) · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: number of Gmail drafts created, client names drafted for, and whether HubSpot email engagements were logged. |
| `inputs` | `client_name={name}` · `ticket_id={id}` |
| `outputs` | `draft_created={true/false}` · `poc_emails={comma-separated emails}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `hubspot_engagement_logged={true/false}` |

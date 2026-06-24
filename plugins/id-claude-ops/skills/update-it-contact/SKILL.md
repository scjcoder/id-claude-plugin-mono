---
name: update-it-contact
description: Add or update an IT contact for a location in HubSpot, then associate them with a support ticket. Use this skill whenever the user says "update IT contact", pastes a HubSpot ticket URL along with contact details, or needs to add a new support or helpdesk contact for a customer location. Also trigger when the user provides an email, phone number, and company name together and asks to link them to a ticket.
---

# Update IT Contact

This skill adds or updates an IT contact for a customer location in HubSpot and associates them with a support ticket. Use it when a location's IT support contact has changed, a new helpdesk address needs to be on file, or a support ticket needs the right contact attached.

## What to collect before starting

You need three things from the user before doing anything:

1. **HubSpot ticket URL** — extract the ticket ID from the URL (the last numeric segment, e.g. `44087123576` from `.../record/0-5/44087123576/`)
2. **Contact details** — email address and phone number
3. **Job title** — ask explicitly, since this varies. Common values: `IT Support`, `Helpdesk`, or an individual's actual title. Do not default to anything.

If any of these are missing, ask before proceeding.

## Step-by-step process

### 1. Search for the contact by email
Run `search_crm_objects` on `contacts` using the provided email address.

- If found: note the contact ID and skip to Step 4.
- If not found: continue to Step 2.

### 2. Search by company domain or name
Search `contacts` using the email domain or company name. This surfaces related contacts and confirms the company exists in HubSpot — useful for catching near-matches (e.g. `support@` vs `sunsetsupport@`).

Show the user any matches found and ask if any of them is the right contact. If the user confirms none match, continue to Step 3.

### 3. Look up the company record
Search `companies` by name to retrieve the HubSpot company ID. You'll need this for the association.

### 4. Confirm with the user before writing
Always show a confirmation table before making any changes:

| Action | Object Type | Property | Value |
|--------|-------------|----------|-------|
| Create/Update | Contact | Email | ... |
| Create/Update | Contact | Phone | ... |
| Create/Update | Contact | Job Title | ... |
| Create/Update | Contact | Company | ... |
| Associate | Contact → Company | Company ID | ... |
| Associate | Contact → Ticket | Ticket ID | ... |

Wait for explicit approval before proceeding.

### 5. Create or update the contact
Use `manage_crm_objects` to create (or update) the contact. In the same call, include associations to:
- The HubSpot company ID
- The ticket ID extracted from the URL

### 6. Confirm success
Return the HubSpot contact URL and confirm both associations succeeded. Format:

> ✅ Contact created/updated: [support@example.net](link)
> - Linked to: **Sunset Technologies**
> - Linked to: **Ticket 44087123576**

### 7. Write Claude context note

Read `skills/hubspot-context-note/SKILL.md` and run it. Pass the following:

| Field | What to pass |
|---|---|
| `ticket_id` | The ticket ID extracted from the URL in Step 1 |
| `origin` | `"IT contact update requested by user"` |
| `what_was_checked` | Contact search result (e.g. "Searched by email it-contact@example.com — matched existing contact ID 12345. Company: MB2 Dental.") |
| `decisions` | Any near-matches surfaced and resolved, job title clarifications, or company-not-found handling. Write `"None."` if everything was clean. |
| `next_steps` | Omit unless something is unresolved. |

---

## Edge cases to handle

- **Contact exists, wrong job title**: offer to update the job title as part of the same operation.
- **Company not found**: let the user know and ask if they want to create the company first or proceed with just the contact and ticket association.
- **Multiple company matches**: surface them and ask the user to confirm which one.
- **Ticket ID not in URL**: ask the user to paste the full HubSpot ticket URL.

---

## Step 8 — Log the run

After Step 7, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `update-it-contact` |
| `status` | `success` if the contact was created/updated and associated to the ticket · `partial` if any association failed · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: contact email and action taken (created or updated), company associated, and ticket the contact was linked to. |
| `inputs` | `contact_email={email}` · `ticket_url={url}` · `job_title={title}` |
| `outputs` | `contact_created_or_updated={created/updated}` · `ticket_associated=true` · `hubspot_contact_url={url}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `company_name={name}` |

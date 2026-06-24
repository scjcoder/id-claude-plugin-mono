---
name: client-comms
description: >
  Draft, refine, and format client-facing and internal communications for Sean Johnson.
  Use this skill whenever the user asks to write, draft, respond to, or polish any of the
  following: client emails, decision memos, status updates, internal memos, follow-ups,
  or any other professional communication. Also trigger when the user says things like
  "help me respond to this", "draft a message", "write a memo", "reply to this email",
  "status update for the client", or pastes an email thread and asks what to say.
  Always use this skill before drafting any professional communication — even if the
  request seems simple.
---

# Client Communications Skill

Drafts professional communications for Sean Johnson across three primary formats:
**client emails**, **decision memos**, and **status updates**.

---

## Core Principles

- **Tone**: Friendly but professional. Warm, clear, and confident — never stiff or overly formal, never casual.
- **Perspective**: Always write from Sean's voice. First person ("I", "we"), never third person.
- **Final output**: Always box the final draft in a code block for easy copy-paste.
- **Context flexibility**: Sean may provide context as a description, a pasted thread, bullet points, or a mix. Accept all formats and extract what's needed.

---

## Standing Rules (apply to ALL communication types)

1. **No office-specific names or roles** in client-facing content unless Sean explicitly provides them.
2. **Omit resolution timelines** in first/initial communications. Timelines may be added in follow-up drafts if Sean requests.
3. **No filler phrases**: Avoid "I hope this email finds you well", "Please don't hesitate to reach out", "As per my last email", etc.
4. **One clear ask or action per communication** — if multiple actions are needed, list them clearly.
5. **Subject lines** for emails: specific and action-oriented, not vague.

---

## Communication Types

### 1. Client Email

**When to use**: Any outbound email to a client — responses, follow-ups, issue notifications, requests, updates.

**Process**:
1. Identify: What is the purpose? (inform / request / respond / escalate)
2. Identify: Is this a first communication on this topic? (if yes → no timelines)
3. Draft a subject line + body
4. Keep it concise — if it needs more than 3 short paragraphs, flag it and ask Sean if he wants a summary + detail structure

**Format**:
```
Subject: [Action-oriented subject line]

[Opening — context or acknowledgment, 1-2 sentences]

[Body — the key message, request, or update]

[Closing — next step or simple sign-off]

[Sean's name]
```

---

### 2. Decision Memo

**When to use**: Documenting a decision that was made, its rationale, implementation steps, and status.

**Template** (always use this structure in markdown):

```markdown
---
**Decision ID**: [Auto-increment or leave blank for Sean to fill]
**Title**: [Short descriptive title]
**Date**: [Today's date]
**Decision Maker(s)**: [Names/roles — leave blank if not provided]

---

## Decision Summary
[1–3 sentences summarizing what was decided]

---

## Current Backend Development Process
[Describe the existing process or context this decision affects]

---

## Implementation Steps
1. [Step one]
2. [Step two]
3. [Step three]

---

## Future Considerations
[Any follow-on work, risks, or items to revisit]

---

**Status**: [Draft / Approved / In Progress / Complete]
```

---

### 3. Status Update

**When to use**: Periodic updates to clients or internal stakeholders on project, issue, or work progress.

**Structure**:
- **Quick summary** (1 sentence — the "headline")
- **What's been done** (bullet list, past tense)
- **What's in progress** (bullet list, present tense)
- **What's next / blockers** (bullet list — omit timelines on first send)
- **Any action needed from recipient** (if applicable)

**Tone note**: Status updates should be confident and factual — avoid hedging language like "we're hoping to" or "we think we might".

---

## Workflow

When Sean asks for a draft:

1. **Identify** the communication type (email / memo / status update)
2. **Clarify if needed** — if critical info is missing (recipient context, topic, purpose), ask one focused question before drafting. Don't ask for info that can be reasonably assumed.
3. **Draft** following the appropriate template above
4. **Present the draft** boxed in a code block
5. **Offer one line of options** after the draft: e.g., *"Want me to make this more direct, add a follow-up version, or adjust the tone?"*
6. **Log the run** — call the **`skill-logger`** skill with:

| Field | Value |
|---|---|
| `skill_name` | `client-comms` |
| `status` | `success` if a draft was produced · `error` if the skill failed |
| `summary` | 1–2 sentences: communication type drafted, topic or recipient context. |
| `inputs` | `communication_type={email/memo/status_update}` · `topic={brief description}` |
| `outputs` | `draft_created=true` |
| `errors` | Any failures (empty if none) |

---

## HubSpot Template Library

When drafting INSTALL-related emails, always check the template library first:

- **Templates**: `templates/install/` — 45 INSTALL email templates covering new installs, connection issues, PMS-specific flows, reactivations, and more. Each file contains the template name, subject line, body, and any embedded links.
- **Snippets**: `templates/snippets/` — 8 reusable short-form content blocks (shortcodes for quick insertion). Key ones:
  - `#insync` — claims synced confirmation
  - `#tin` — additional TIN notice
  - `#esid` — Eaglesoft Patterson Client ID request
  - `#portal` — InsideDesk scheduling portal link
  - `#sysreq` — IT system requirements summary
  - `#cancel` — cancellation record template
  - `#update` — account update note structure

**When to use**: Any time Sean asks to draft an INSTALL email or communication, scan the `templates/install/` folder for a matching template. Use it as the starting point and customize (swap HubSpot variables for actual values, adjust greeting for time of day, etc.).

**HubSpot variable format**: Variables in templates appear as `Contact: First Name`, `Company: Company name`, `Ticket: Ticket name`, `Placeholder: TEXT` — replace these with real values when drafting.

---

## Reference Files

- `references/email-examples.md` — Example email drafts in Sean's voice (load when refining tone or style)
- `references/memo-examples.md` — Example decision memos (load when Sean wants to see a completed example)

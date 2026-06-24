---
name: monday-account-update
description: >
  Post an update note on a dental office item in the MB2 Inside Desk Install List Monday Board.
  Use this skill whenever Sean needs to add a comment, status note, or progress update to a
  client office's Monday Board item. Trigger on phrases like "add a note to Monday for [office]",
  "post an update on [office] in Monday", "leave a comment on [office]'s Monday item",
  "update Monday for [office]", or any time a workflow produces an actionable status that should
  be logged on the Monday Board (e.g., after filing a sync ticket, completing an install step,
  or resolving an issue). Default @mentions are @Karina Mendoza, @Tye Powell, and @David Herrera
  unless the caller specifies otherwise. Always use this skill when Monday Board visibility is
  needed — even if the user doesn't say "Monday" explicitly and just says "log this" or "make a note".
---

# Monday Account Update

Post an update note on an office item in the MB2 Inside Desk Install List Monday Board.

## Inputs

- **office_name** — the name of the dental office to find on the board (required)
- **message** — the update text to post (required)
- **tags** — @mentions to include (default: `@Karina Mendoza`, `@Tye Powell`, `@David Herrera`)
- **board_url** — optional override; defaults to the Inside Desk Install List board

## Board reference

- **Board:** Inside Desk Install List
- **Board ID:** 1911559021
- **Default URL:** `https://mb2dental-team.monday.com/boards/1911559021`
- **Default @mentions:** @Karina Mendoza, @Tye Powell, @David Herrera

## Step 1: Navigate to the board and filter for the office

Navigate to the board:

```
https://mb2dental-team.monday.com/boards/1911559021
```

Once loaded, use the search/filter box at the top of the board to filter by the office name.
Type the name and press Return.

**Important — collapsed groups:** After searching, board groups that contain matches show a
filtered count in their header (e.g. "Full Access – Active Office List  1 Item") but stay
collapsed. Click the group header's expand arrow to reveal the matching rows inside. Do not
assume "no results" until you have expanded all non-empty group headers.

**If multiple rows match:** present them to the user with any group/section context and ask
which one to update.

**If no rows match (after expanding all groups):** report back and ask the user to confirm
the spelling or provide the exact Monday item name.

## Step 2: Open the item's side panel

**Critical:** Do NOT click the office name text — this activates inline row editing, not the
item panel. Press Escape immediately if this happens.

Instead:
1. Hover your cursor over the matching row until the expand icon (↗) appears at the left edge
2. Click the expand icon to open the item's full side panel on the right

If hovering doesn't reveal the icon, use the `…` row context menu and choose "Open item".

Once the panel opens, confirm the displayed item name matches the intended office.

## Step 3: Navigate to the Updates tab

In the side panel, click the **Updates** tab (may show a count, e.g. "Updates / 2").

The update editor ("Write an update and mention others with @") should be visible at the top.

## Step 4: Write the update

### 4a — Copy body text to clipboard

Before touching the editor, build the full message body (everything **except** the @mention line)
as a JavaScript string and write it to the clipboard using `javascript_tool`. This avoids
Monday's `@` autocomplete triggering on any `@` characters in the body (e.g., email addresses,
CPU specs like "@ 2.20GHz").

```javascript
await navigator.clipboard.writeText(`<full message body here — all lines except @mentions>`);
'copied'
```

Confirm the call returns `'copied'` before proceeding.

### 4b — Paste into the editor

1. Click the update editor ("Write an update and mention others with @") to focus it
2. Press **Cmd+V** to paste — the full body text appears in one operation
3. Press **Enter** once to move to a new line for the @mentions

### 4c — Type @mentions with autocomplete

Type each @mention **manually** (do not paste these — Monday must resolve them to real users):

1. Type `@Karina Mendoza` → autocomplete appears → select the correct entry → confirm it turns blue
2. Type a space, then `@Tye Powell` → select → confirm
3. Type a space, then `@David Herrera` → select → confirm

**If autocomplete does not appear:** click away to reset, click back into the editor, and retype
the `@First` portion slowly.

**Note:** If the body text itself contained an `@` and the paste still triggered autocomplete
(rare), press **Escape** once to dismiss it — the pasted text will remain intact.

### Content rules

- Do not name internal third-party sync vendors (e.g., Bitwerx, DataCo) in the note text —
  these notes may be visible to client staff. Use generic language ("sync issue", "out of sync")
  and reference internal ticket IDs where applicable (e.g., DATA-48453)
- For **editing an existing update**: use the `…` menu on the update → Edit. Select all existing
  content (Cmd+A inside the editor), delete it, then follow steps 4a–4c above to paste fresh
  content. Do not attempt to surgically edit lines in place — full replace is more reliable.

## Step 5: Save

Click the **Save** button. Confirm the new update appears in the feed with the correct two-line
format.

## Output

Report back to the user:
- Which office was updated
- The full text of the posted update
- Confirmation it saved successfully

**Example:**
> ✅ Posted update on **Cuero Dental** in the MB2 Monday Board:
>
> Working on out of sync: DATA-48453
> @Karina Mendoza @Tye Powell @David Herrera

---

## Step 6 — Log the run

After the Output step, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `monday-account-update` |
| `status` | `success` if the update was posted and confirmed · `error` if the office item was not found or the save failed |
| `summary` | 1–3 sentences: office name updated, board item found, and confirmation the update was saved successfully. |
| `inputs` | `office_name={name}` · `message={first 100 chars of message}` |
| `outputs` | `monday_item_updated=true` · `board_url={url}` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{}` |

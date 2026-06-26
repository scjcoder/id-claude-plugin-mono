---
name: chrome-cleanup
description: >
  Close a Chrome browser tab. Lightweight helper for skills that use the Claude in Chrome
  tools and need to clean up after themselves. Pass the tabId from your Chrome navigation,
  and the tab will be closed. If no tabId is provided, the skill silently succeeds —
  perfect for skills that may or may not use Chrome.
---

# Chrome Cleanup Helper Skill

Closes a Chrome browser tab opened during skill execution. Designed as an optional cleanup utility for skills that use the Claude in Chrome MCP server.

---

## Overview

This skill provides a single, reusable cleanup step for any skill that:
- Opens a Chrome tab via `mcp__Claude_in_Chrome__navigate`
- Wants to clean up that tab after use
- Needs graceful handling when no tab was opened

**Design principle:** This is a *helper* skill, not a standalone tool. Skills call it at the end of their workflows if they used Chrome.

---

## Usage

### In a skill workflow:

```
1. Load Chrome tools (navigate, get_page_text)
2. Navigate to URL
3. [do work]
4. Call chrome-cleanup helper with tabId from step 2
5. Report results
```

### Parameters

- **tabId** (optional number): The browser tab ID to close
  - From `mcp__Claude_in_Chrome__navigate` response
  - If omitted or null, skill silently succeeds (safe for non-Chrome skills)

### Return

- **success** (boolean): Always true
  - True if tab was closed
  - True if no tabId provided (graceful no-op)
- **tabId** (number or null): The tab that was closed (or null if none provided)
- **message** (string): Descriptive status

---

## Workflow

1. **Check for tabId**
   - If tabId is provided (not null, not undefined), proceed to close
   - If tabId is missing, return success immediately (graceful no-op)

2. **Close the tab**
   - Load `mcp__Claude_in_Chrome__tabs_close_mcp` tool
   - Call with the tabId
   - Handle any errors gracefully

3. **Report status**
   - Return success status
   - Include the tabId that was closed (for logging)
   - Include a message describing what happened

---

## Examples

### Chrome skill calling chrome-cleanup

```
Step 1: Navigate to URL
  Response: tabId = 1302821189

Step 2: Do work with the tab
  [extract content, etc]

Step 3: Call chrome-cleanup
  Input: tabId = 1302821189
  Output: {success: true, tabId: 1302821189, message: "Tab 1302821189 closed"}

Step 4: Log results
  Includes cleanup status in final report
```

### Non-Chrome skill (graceful no-op)

```
Step 1: Do work without Chrome
  [no tab opened]

Step 2: Call chrome-cleanup
  Input: tabId = null (or omitted)
  Output: {success: true, tabId: null, message: "No tab to close"}

Step 3: Continue
  Cleanup succeeded, skill proceeds normally
```

---

## Best Practices

1. **Call at the end** — Place chrome-cleanup as the final step before reporting results
2. **Pass tabId from navigation** — Always use the tabId returned by `navigate()`
3. **Handle gracefully** — If your skill conditionally uses Chrome, always call chrome-cleanup (it will silently succeed if no tabId)
4. **Log the result** — Include cleanup status in your final skill report or context note

---

## Implementation Notes

- **Safe for all skills** — Non-Chrome skills can call this with no tabId and it succeeds
- **Idempotent** — Closing an already-closed tab is handled gracefully
- **Quick** — Completes in milliseconds
- **Focuses on cleanup only** — Does not log, report, or modify state; just closes the tab

---

## When to Use This Skill

✅ **After** you use Chrome tools in your skill
✅ **At the end** of your skill workflow, before final reporting
✅ **For any skill** that conditionally uses Chrome (graceful no-op for non-Chrome execution)
✅ **As a standard pattern** in multi-step skills that may or may not touch the browser

❌ **Don't use** as a standalone diagnostic tool — use `chrome-test` instead
❌ **Don't use** for permanent tab management — this is for cleanup after skill work only

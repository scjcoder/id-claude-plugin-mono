---
name: chrome-test
description: >
  Test that the Claude in Chrome tool suite is available and functional.
  Verifies browser navigation and page content extraction capabilities.
  Use when you need to confirm Chrome automation tools are ready or as a diagnostic
  check for browser connectivity. Trigger on "test Chrome", "check Chrome availability",
  "is the browser working", or "chrome test".
---

# Chrome Test Skill

Validates that the Claude in Chrome tool suite is operational by executing core browser operations: navigation and content extraction.

---

## Overview

This skill performs an end-to-end test of the Claude in Chrome MCP server integration:

1. **Navigate** to a public test URL (https://example.com)
2. **Extract** page text content to verify the page loaded correctly
3. **Report** results with status and any errors encountered

The test is minimal, non-destructive, and safe to run multiple times.

---

## Workflow

1. **Load Chrome tools** by fetching their schemas via ToolSearch:
   - `mcp__Claude_in_Chrome__navigate`
   - `mcp__Claude_in_Chrome__get_page_text`

2. **Navigate** to https://example.com
   - Check for successful navigation response
   - Capture the tab ID from the response

3. **Extract page text** from the loaded tab
   - Use the tab ID from step 2
   - Verify page content is readable

4. **Close the test tab** via chrome-cleanup helper
   - Call the `chrome-cleanup` skill with the tabId from step 2
   - This is a lightweight helper that handles tab closure
   - Ensure no persistent browser state is left behind

5. **Report results** with:
   - Tool availability status ✅ or ❌
   - Tab context (tab ID, URL, title)
   - Extracted page title and content snippet
   - Cleanup status (tab closed)
   - Any errors or connection issues

---

## Success Criteria

✅ **Core Chrome tools are available** — ToolSearch successfully loaded navigate and get_page_text
✅ **Navigation succeeds** — Tab created and URL loaded without errors
✅ **Content extraction works** — Page text retrieved and contains expected content (e.g., "Example Domain")
✅ **Cleanup succeeds** — chrome-cleanup helper closes the test tab without errors

---

## Failure Modes

❌ **Tools not available** — ToolSearch fails to load Chrome tool schemas (MCP server offline or disconnected)
❌ **Navigation fails** — Browser tab creation fails or network error on navigate
❌ **Content extraction fails** — get_page_text returns empty or error response
❌ **Page content missing** — Page loaded but title/content is empty or malformed

---

## Implementation Notes

- **Clean cleanup** — Uses the chrome-cleanup helper skill to close the test tab; no browser state left behind
- **No side effects** — Test URL is public and read-only; no data is created or modified
- **Idempotent** — Safe to run multiple times without impact
- **Quick execution** — Completes in under 5 seconds (including tab cleanup)
- **Follows pattern** — Demonstrates best practice for Chrome skills: test → cleanup → report

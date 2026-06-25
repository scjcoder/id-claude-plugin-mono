# Documentation

Comments explain *why*, not *what* — the code already shows what.

## Script headers

- **MUST** give every standalone script a header block:

```python
# Author:       Sean Johnson <sean.johnson@insidedesk.com>
# Purpose:      One-line description of what this script does.
# Last updated: 2026-05-30 14:30
# Version:      1.0.0
```

## Comments

- **MUST NOT** write comments that restate the code (`# increment counter` over `counter += 1`).
- **SHOULD** add WHY comments where a business rule, trade-off, or workaround isn't obvious.
- **MUST** format TODOs with owner and deadline: `# TODO(sean): remove after claims migration — 2026-Q3`.
- **MUST NOT** leave commented-out code.

```
✅ # Batch every 100 requests to stay under the Waystar rate limit (100 req/min)
   if request_count >= 100:
       flush_batch()
```

## API docs

- **MUST** give every public function/class a docstring or JSDoc (purpose, params, return, raises).
- **SHOULD** keep a paper trail: changelogs, logs, and decision records for non-obvious choices.

## Project docs

- **SHOULD** keep a `README.md` (what + how to run) and, for AI agents, a `CLAUDE.md` per repo.
- **SHOULD** document architecture decisions where they aren't derivable from the code.

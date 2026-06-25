# Agent Instructions

Manage AI agent instruction files to avoid drift and duplication.

## Canonical source

**SHOULD** keep one canonical source of agent rules and generate/sync the others, or keep them thin and point at the `coding-quality` plugin.

Evidence: Every repo carries `AGENTS.md` + `CLAUDE.md` + `GEMINI.md` with overlapping content.

## Per-repo stubs

**SHOULD** add a per-repo `CLAUDE.md` stub that imports the standards:

```markdown
# Claude Instructions

This repo uses the coding-quality plugin for standards.

@coding-quality

Repo-specific overrides:
- [Any repo-specific rules here]
```

Alternatively, link to this repo:

```markdown
# Claude Instructions

See https://github.com/scj/ai-coding-quality for the full standards.

Repo-specific overrides:
- [Any repo-specific rules here]
```

## Sync strategy

If maintaining multiple agent instruction files:

- Keep one source of truth (e.g., `CLAUDE.md`)
- Use a script or manual process to sync changes to `AGENTS.md` / `GEMINI.md`
- Document the sync process in the repo

❌ Three separate files with divergent rules
✅ One canonical source + thin stubs for other agents

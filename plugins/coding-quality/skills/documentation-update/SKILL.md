---
name: documentation-update
description: >
  Systematic, git-history-driven documentation sync: reviews recent commits, detects
  project type, ensures the essential docs exist, sets up Architecture Decision
  Records when architectural changes are found, and lints/cross-references everything
  before handoff to a commit. Use this skill when the user asks to "update the docs",
  "sync documentation with code", says docs feel out of date, before a release, or
  after a batch of significant code changes. Language/framework-agnostic — detects
  project type instead of assuming it.
---

# Documentation update

Brings `/docs`, `README.md`, and ADRs back in sync with what the code actually does,
driven by git history rather than guesswork.

## When to run

- After a batch of significant code changes
- Before a release (pair with the `git-release` skill)
- When the user says documentation feels stale or out of date
- When a new feature shipped without doc updates

## Steps

### 1. Detect project type

Don't ask the user — infer it from the repo, then confirm if ambiguous:

| Signal | Project type |
|--------|--------------|
| `package.json`, `Cargo.toml`, `requirements.txt`, `go.mod` | software |
| `astro.config.mjs`, `next.config.js`, `gatsby-config.js`, `vue.config.js` | documentation/content site |
| `terraform/`, `docker-compose.yml`, `Dockerfile`, `kubernetes/` | infrastructure |
| none of the above | general |

### 2. Review recent changes

```bash
git log --since="2 weeks ago" --pretty=format:"%h %ad %s" --date=short
```

Default lookback is 2 weeks; ask the user for a different range (e.g. "since last
release") if this is a pre-release sweep. Categorize commits by type — features,
fixes, refactors, breaking changes — and note anything that touches public
interfaces or architecture.

### 3. Set up ADRs if the project needs them

Architecture Decision Records are worth proposing once a repo has non-trivial design
choices worth recording — typically software and infrastructure projects.

- If `docs/adr/` doesn't exist and the commit history contains architectural,
  breaking, or system-level changes, propose creating it (don't create it
  unprompted on a project that's never used ADRs before — ask first).
- ADR index template (`docs/adr/README.md`):

  ```markdown
  # Architecture Decision Records (ADRs)

  | ADR | Title | Status | Date |
  |-----|-------|--------|------|
  ```

- Per-ADR template (`docs/adr/NNN-title.md`, zero-padded, sequential):

  ```markdown
  # ADR-NNN: [Title]

  ## Status
  Proposed

  ## Context
  [Driving forces and constraints]

  ## Decision
  [The architectural decision]

  ## Consequences
  ### Positive
  - [...]
  ### Negative
  - [...]
  ### Neutral
  - [...]
  ```

### 4. Check essential docs exist

Base set for every project: `README.md`, `docs/getting-started.md`,
`docs/installation.md`, `docs/contributing.md`, `docs/changelog.md`.

Add by project type:

| Project type | Additional docs |
|---------------|------------------|
| software | `api-reference.md`, `architecture.md`, `testing.md` |
| documentation/content site | `user-guide.md`, `glossary.md`, `index.md` |
| infrastructure | `deployment.md`, `security.md`, `configuration.md` |
| general | `user-guide.md`, `faq.md` |

For anything missing, create a stub with `## Overview`, `## Details` (or the
type-appropriate sections), and `## Examples` — don't invent content; mark it
`[TODO: fill in]` and flag it to the user rather than fabricating specifics.

### 5. Update content against the git log

For each significant change identified in step 2: confirm the relevant doc reflects
it (new feature → user-facing doc + changelog; new endpoint → API reference; new
infra resource → deployment/configuration docs). Update code samples that no longer
match the current API.

### 6. Cross-reference

- Link ADRs to the features/docs they affect, and vice versa
- Add "related docs" links between sections that reference each other
- Build or update a docs index/table of contents if more than ~5 files exist

### 7. Lint and validate

```bash
# one-time setup if missing
npm install -g markdownlint-cli
pip install proselint --break-system-packages

# run
markdownlint docs/*.md README.md
proselint docs/*.md README.md
```

Fix flagged issues. Check for broken internal links.

### 8. Hand off to commit

Documentation changes still go through the same commit discipline as code — use
the `git-save` skill in this plugin to stage and commit with a proper conventional
commit message (`docs(scope): ...`). Don't bundle doc commits with unrelated code
changes.

## Notes

- This skill is stateless by design — it re-detects project type and re-scans docs
  each run rather than maintaining a persisted config file. That avoids drift between
  a cached config and the actual repo state.
- Never invent specifics for a stub doc. An honest `[TODO]` beats a plausible-looking
  fabrication.

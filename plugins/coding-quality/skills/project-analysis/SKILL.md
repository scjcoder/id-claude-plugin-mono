---
name: project-analysis
description: >
  Systematic project health and status assessment — structure, documentation
  freshness, git activity patterns, code quality signals, and security hygiene —
  without requiring any external tooling. Use this skill when the user asks "what's
  the state of this project", "give me a status report", or wants prioritized next
  steps for an unfamiliar or long-running codebase.
---

# Project analysis and status assessment

A read-only survey to build a status picture before recommending next steps. Run
the relevant sections below, then synthesize — don't just dump command output.

## Structure

```bash
find . -type d -maxdepth 2 -not -path "*/.*" | sort
find . -maxdepth 2 -type f \( -name "*.json" -o -name "*.yaml" -o -name "*.yml" \) | sort
```

Look for `README.md`, `CONTRIBUTING.md`, `LICENSE` at the root — their absence is
itself a finding.

## Documentation

```bash
find . -name "*.md" -mtime -30 | sort           # touched in the last 30 days
find . -name "*.md" | grep -i "adr\|architecture\|decision"
```

Check freshness against the active components found in the git history section
below — stale docs for actively-changing code is the gap worth flagging, not raw
doc count.

## Git history

```bash
git log --since="30 days ago" --pretty=format:"%h %ad %s" --date=short
git log --since="90 days ago" --name-only --pretty=format: | sort | uniq -c | sort -nr | head -15
git log --since="60 days ago" --pretty=format:"%an" | sort | uniq -c | sort -nr
git log --name-only --until="180 days ago" --pretty=format: | sort | uniq | grep -v "^$" | head -20
```

These four answer: what's been happening, what's the hot spot, who's active, and
what hasn't been touched in 6 months and may need a deliberate look (not
necessarily a problem — could just be stable).

## Code quality signals

```bash
grep -rn "TODO\|FIXME" --include="*.{js,ts,py,go,rb,java}" . | grep -v node_modules
find . -type f -not -path "*/node_modules/*" -not -path "*/.git/*" \
  \( -name "*.js" -o -name "*.ts" -o -name "*.py" -o -name "*.go" \) \
  -exec wc -l {} \; | sort -nr | head -10
```

The largest files by line count are complexity-hotspot candidates worth a closer
look, not an automatic problem — judge by what the file actually does.

## Security hygiene

```bash
find . -iname "*secret*" -o -iname "*.env*" -not -path "*/node_modules/*" | grep -v node_modules
git log --all -p | grep -i "api[_-]key\|password\s*=\|secret\s*=" | head -20   # rough scan, not a substitute for a real secret scanner
```

If the project has a `.pre-commit-config.yaml`, check whether a secret-scanning
hook (`detect-secrets`, `gitleaks`) is actually enabled — see this plugin's
`rules/03-security.md` rather than treating ad-hoc grep as sufficient coverage.

## Dependencies

```bash
[ -f package.json ] && npm ls --depth=0
[ -f requirements.txt ] && cat requirements.txt | sort
[ -f pyproject.toml ] && cat pyproject.toml
```

## Synthesize, don't dump

After running the above, produce a short status summary covering: the 3–5 most
active areas of the codebase right now, documentation gaps in those active areas
specifically (not project-wide), any security findings, and a prioritized list of
next steps — ordered by risk, not by convenience. Write it to
`docs/project-status.md` if the user wants a persistent record; otherwise present
it directly in chat. A dated status file accumulates value over repeated analyses,
so prefer keeping the file (with a new dated section appended) over overwriting it
each time.

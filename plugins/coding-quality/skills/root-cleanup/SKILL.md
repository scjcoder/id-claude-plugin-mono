---
name: root-cleanup
description: >
  Categorize and relocate files cluttering a project's root directory into their
  proper subdirectories (tests/, data/, scripts/, docs/, etc.), without breaking
  imports, CI, or entry points. Use this skill when the user asks to "clean up the
  root", "organize the repo", or when a project's root directory has accumulated
  loose scripts, data files, or logs that don't belong there.
---

# Root directory cleanup

## File categories

### Tier 1 — required, never move

Files Git, package managers, or the language toolchain expect at the repo root:
`.gitignore`, `.gitmodules`, `.gitattributes`, `.pre-commit-config.yaml`,
`.gitleaks.toml`, `README.md`, `SECURITY.md`, `LICENSE`, and the package manifest
for the project's language (`requirements.txt`/`pyproject.toml`, `package.json`,
`Cargo.toml`, `go.mod`, `composer.json`), plus `.env.example`, `Dockerfile`,
`docker-compose.yml`.

### Tier 2 — root-preferred, conventionally kept in root

Numbered or named pipeline entry points (e.g. `00_run_pipeline.py`, `main.js`,
`app.py`) if they're the actual primary entry point; main config files
(`webpack.config.js`, `tsconfig.json`); CI/CD config (`.gitlab-ci.yml`,
`.github/workflows/`); `ARCHITECTURE.md`, `CONTRIBUTING.md`, `CHANGELOG.md`.

### Tier 3 — relocate

| Pattern | Destination |
|---|---|
| `test_*.py`, `*_test.py`, `*.test.js`, `*.spec.js`, `__tests__/` | `tests/` |
| `*.xlsx`, `*.csv`, `*.sqlite`, `*.db`, non-config `*.json` | `data/` |
| Non-entry `*.py`, `*.js`, `*.ts`, `*.jsx`, `*.tsx` | `src/` or the relevant module |
| `build/`, `dist/`, `out/`, `*.min.js` | `dist/` |
| Debug dumps, `*.log` | `debug/` or `logs/` |
| One-off utility scripts | `scripts/` or `bin/` |
| `images/`, `css/`, `fonts/` | `assets/` or `static/` |
| Old/deprecated versions | `archive/` |

## Procedure

1. **Pre-flight**: `git status` must be clean before starting; create a branch
   (`git checkout -b cleanup/root-cleanup-$(date +%Y%m%d)`) so the cleanup is
   reviewable and revertible as a unit.
2. **Inventory**: list every root file, tag it Tier 1/2/3, and for each Tier 3 file
   decide its destination.
3. **Create destination directories**: `mkdir -p tests data scripts docs` (only the
   ones actually needed).
4. **Move file-by-file, not in bulk**: `mv <file> <dest>/`, then grep the codebase
   for any reference to the old path and update it, then test/run the affected
   code, then commit (`git add -A && git commit -m "chore: move X to Y"`). One file
   or one logical group per commit — a bulk mv-everything commit is unreviewable
   and unrevertible.
5. **Update `.gitignore`** while you're in here — a root cleanup is also the moment
   to catch missing ignore patterns (build outputs, IDE files, OS files, logs,
   `.env*`). Verify with `git status --ignored`.
6. **Validate**: re-run the project's actual entry points/tests to confirm nothing
   broke (don't assume — run them), check that moved Python files still
   `python -m py_compile` cleanly, and confirm doc links that pointed at old paths
   still resolve.
7. **Update README** to reflect the new directory layout if it documents one.

## Decision tree for ambiguous files

```
Required by Git/package manager/pre-commit?        → Tier 1, keep in root
Primary pipeline entry point?                        → Tier 2, keep in root
Test file?                                           → tests/
Data file (.xlsx/.csv/.json, non-config)?            → data/
Utility/one-off script?                              → scripts/
Temporary or debug output?                           → debug/ or temp/
Documentation (not README)?                          → docs/
Anything else                                        → review manually, likely archive/
```

## Common pitfalls

- **Breaking imports**: search for every reference to a file's old path before
  moving it, not after.
- **Moving `.env` files**: these belong in root or wherever the app's config
  loader actually looks — don't move them without checking the loader.
- **Breaking CI**: update pipeline config that references moved paths.
- **Moving too much in one commit**: makes a bad move impossible to cleanly revert.

## Summary report

After the cleanup, produce a short table of what moved, what directories were
created, and a count of files needing manual review — this becomes the PR/MR
description, and gives the user something to sanity-check before merging:

```markdown
## Files moved
| File | From | To |
|---|---|---|
| <file> | / | <dest>/ |

## Directories created
- <dir>/ — <purpose>

## Needs manual review
- <file> — <why it didn't fit a clear category>
```

## Rollback

If a moved file turns out to be load-bearing somewhere unexpected:
`git revert <commit>` for the specific move commit (this is why moves are committed
individually), or `git reset --hard <pre-cleanup-commit>` to abandon the whole
cleanup and start over.

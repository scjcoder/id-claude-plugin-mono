---
name: git-whitespace-hooks
description: >
  Diagnose and fix commit failures caused by pre-commit hooks rewriting staged
  files (trailing whitespace, EOF fixes) after `git add` but before the commit
  lands, plus related hook hygiene — preventing duplicate hook execution and
  migrating legacy `.git/hooks/` scripts (including Git LFS hooks) into the
  pre-commit framework. Use this skill when a commit fails right after pre-commit
  "fixes" something, or when hooks appear to run twice during push/checkout.
---

# Git whitespace & hook hygiene

## The root problem

Pre-commit hooks like `trailing-whitespace` and `end-of-file-fixer` rewrite files
*after* they're staged but *before* the commit completes:

1. `git add` stages files
2. `git commit` runs
3. The hook rewrites a file to fix whitespace
4. Git refuses the commit because the staged content no longer matches the working
   tree
5. You have to `git add` again and re-commit

This is annoying but not a bug — it's the hook doing its job. The fix is to make the
re-stage-and-retry step automatic.

## Fix 1 — `git commit-safe` (primary, already standard)

This plugin already documents a global `commit-safe` alias in `rules/02-git.md`
that detects hook-modified files after a failed commit, re-stages them, and
retries automatically. Use that alias for every commit — it's the canonical fix and
works regardless of which hooks are installed.

If a global alias isn't viable (e.g., a CI runner with no user `.gitconfig`), the
same logic can live as a local script (`scripts/git-commit-safe.sh`) with a
repo-local alias instead:

```bash
git config --local alias.commit-safe '!./scripts/git-commit-safe.sh'
```

Don't maintain both a global alias and a local script with the same name in the
same project — pick one per repo to avoid confusing which one actually runs.

## Fix 2 — scope the hook to the right stage

Sometimes the real issue is a hook configured to run at the wrong git lifecycle
stage. Pin it explicitly:

```yaml
# .pre-commit-config.yaml
- id: trailing-whitespace
  args: [--markdown-linebreak-ext=md]   # preserves intentional MD line-break whitespace
  stages: [pre-commit]
  fail_fast: false
```

`fail_fast: false` lets remaining hooks run even after one finds an issue, so you
see every fix needed in one pass instead of fixing them one at a time across
multiple failed commits.

## Preventing duplicate hook execution

If a hook appears to run twice (e.g., a validation step running once during commit
and again during push), the project likely has both a legacy script in
`.git/hooks/` *and* an equivalent hook registered in `.pre-commit-config.yaml`.

```bash
ls -la .git/hooks/             # check for legacy, non-pre-commit-managed scripts
```

Resolve by consolidating into the pre-commit framework, not by keeping both:

1. Confirm the `.pre-commit-config.yaml` hook covers the same check
2. Back up the legacy hook before removing it: `cp .git/hooks/<name> .git/hooks-backup/`
3. Remove the legacy hook: `rm .git/hooks/<name>`
4. Verify the pre-commit-managed equivalent still fires at the right `stages`

## Migrating Git LFS hooks into pre-commit

Git LFS installs its own legacy hooks (`post-checkout`, `post-commit`,
`post-merge`) by default. If the project already uses pre-commit for everything
else, fold LFS in too rather than running two hook systems side by side:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/git-lfs/git-lfs
  rev: v3.4.1
  hooks:
    - id: git-lfs-pre-push
    - id: git-lfs-post-checkout
    - id: git-lfs-post-commit
    - id: git-lfs-post-merge
```

Then remove the legacy LFS hooks the same way as any other duplicate (back up,
then delete from `.git/hooks/`).

## Why this matters for one repo in particular

This project's COLE trading-journal repo uses Git LFS for screenshot storage — if
that repo (or any repo using LFS for binary assets) migrates to pre-commit-managed
hooks, use this section rather than re-deriving the LFS hook IDs from scratch.

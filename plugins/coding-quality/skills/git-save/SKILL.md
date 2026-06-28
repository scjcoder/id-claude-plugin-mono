---
name: git-save
description: >
  End-to-end commit procedure for repos with submodules: sync with remote, commit
  and push submodule changes before the parent repo, group remaining changes by
  purpose, commit each group separately, then push. Use this skill when the user
  says "save my changes", "commit this", "git save", or when a repo has dirty
  submodules that need committing before the parent. Defers to the `coding-quality`
  skill's `rules/02-git.md` for commit message format, types, and scopes — this
  skill is the *procedure*, that rule file is the *convention*.
---

# Git save

The full sequence for landing a clean commit in a repo that may have submodules,
without leaving the tree dirty or the submodule pointer stale.

## 1. Sync with remote

```bash
git fetch --all
git status -uno
git pull
```

Do this even if you're confident nothing changed upstream — submodule content can
change outside your local session (CI, another contributor, automation). If `pull`
conflicts: resolve each file, `git add <file>`, then `git commit -m "Merge remote
changes"`.

## 2. Sync and inspect submodules

```bash
git submodule foreach git fetch --all
git submodule foreach git status
```

Note which submodules have local changes or are behind their remote.

## 3. Commit submodules first — always

For each submodule with changes:

```bash
cd <submodule_path>
git status
git add <files>
git commit-safe -m "<type>(<scope>): <subject>"   # see rules/02-git.md for format
git push
cd ..
```

**Never** update the parent's submodule reference before the submodule commit is
pushed — the parent only stores a commit hash pointer, and a pointer to an unpushed
commit is broken for everyone else who pulls.

## 4. Update the submodule reference in the parent

```bash
git submodule update --remote <submodule_path>
```

This is its own commit later, in step 6 — don't fold it into an unrelated change.

## 5. Group remaining changes by purpose

```bash
git status
git diff
```

Split into logical groups: docs, feature, fix, refactor, style, test, perf, chore,
submodule reference update. One group = one commit.

## 6. Stage and commit each group

```bash
git add <files for this group>
git commit-safe -m "<type>(<scope>): <subject>

<body>"
```

Use `git commit-safe` (not plain `git commit`) so pre-commit hook modifications
(whitespace/formatting fixes) get re-staged automatically instead of failing the
commit. Format, commit types, and scopes are defined in `rules/02-git.md` —
follow that table, don't improvise a new one here.

A submodule-reference-update commit should always cite the target commit hash:

```
submod(submodules): update gitlab-oidc to latest

- Bumped submodule pointer to abc1234
- Updated trust policy for GitLab CI least-privilege roles
```

## 7. Push

```bash
git push
```

## Checklist

- [ ] Pulled latest before starting; conflicts resolved if any
- [ ] Every dirty submodule committed and pushed *before* the parent
- [ ] Parent's submodule reference updated and committed separately
- [ ] Remaining changes grouped logically, not dumped into one commit
- [ ] Each commit uses `git commit-safe` and follows `rules/02-git.md` format
- [ ] `git status` clean, everything pushed

# Git Workflow

## Commits

- **MUST** use Conventional Commits: `type(scope): short summary`.
  - Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `perf`, `build`, `style`, `tweak`, `hotfix`, `wip`, `revert`, `submod`.
- **MUST** write verbose, full-context bodies — not just the one-line summary.
- **SHOULD** group changes into logical commits; don't dump unrelated changes into one.

```
feat(oidc): pin GitLab trust policy to namespace_id and project_id

- Path-based `sub` claims alone are reclaimable if a GitLab group/project
  is deleted and re-created by another party (AWS IAM security advisory).
- Add StringEquals conditions on gitlab.com:namespace_id and :project_id,
  which are stable and non-reusable identifiers.
- Verified by re-running the pipeline's AssumeRoleWithWebIdentity call.
```

### Commit message format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Subject line rules:**
- Imperative mood: "Add feature" not "Added feature"
- Capitalize the first word
- No period at the end
- ≤72 characters

**Body guidelines:**
- Explain *what* changed and *why* (not how)
- Wrap at 72 characters
- Use bullet points for lists of changes
- Describe motivation, impact on the system, and any side effects
- Include examples or context where helpful
- Reference related commits, issues, or docs

### Available scopes

Scopes are project-specific — customize this list per repo:

| Scope | Applies to |
|-------|------------|
| `api` | API changes |
| `auth` | Authentication |
| `ui` | User interface |
| `infra` | Infrastructure |
| `deps` | Dependencies |
| `submodules` | Submodule config/references |
| `organization` | Folder structure |
| `i18n` | Internationalization/translations |
| `recipes` | Recipe-related changes |

## Clean tree

- **MUST** leave no untracked files after any git operation — commit, ignore, or remove them.
- **MUST** verify `git status` is clean before declaring work done.
- **MUST NOT** commit secrets, `.env` files, credentials, or large binaries (use Git LFS for screenshots/assets).

## Submodules

- **MUST** commit and push submodules **before** the parent repo, then update the parent's pointer.
- **MUST** verify the parent references the intended submodule commit after pushing.

### Why submodules must go first

The parent repository stores submodule state as a commit hash pointer — not the actual code. If you commit the parent before pushing the submodule, anyone else who pulls the parent will get a pointer to a commit that doesn't exist on the remote yet.

### Submodule commit workflow

1. Check submodule status: `git submodule foreach git status`
2. For each submodule with changes:
   - `cd <submodule_path>`
   - Stage and commit following conventional commit format
   - `git push`
   - `cd ..`
3. Update submodule references in parent: `git submodule update --remote <submodule_path>`
4. Commit the parent with the updated submodule references

## Branches & history

- **SHOULD** use short-lived feature branches; rebase or squash to keep history readable.
- **MUST NOT** force-push to shared/protected branches.

## Pre-commit hook handling

When pre-commit hooks auto-fix whitespace or formatting, they modify files after staging, which causes a plain `git commit` to fail with unstaged changes.

### `git commit-safe` alias

Add this alias to `~/.gitconfig` or your project's `.git/config`:

```bash
git config --global alias.commit-safe '!f() {
  git commit "$@"
  EXIT_CODE=$?
  if [ $EXIT_CODE -ne 0 ]; then
    MODIFIED=$(git diff --name-only)
    if [ -n "$MODIFIED" ]; then
      echo "Pre-commit hooks modified files. Re-staging and retrying..."
      git add $MODIFIED
      git commit "$@"
    fi
  fi
}; f'
```

If `commit-safe` isn't available, fall back to:

```bash
git commit -m "your message"
# If it fails due to hook modifications:
git add -u        # re-stage hook-modified files
git commit -m "your message"
```

## Best practices

- **Small, focused commits** over large sweeping ones — easier to review and revert
- **`git diff` before staging** — review what you're actually committing
- **Submodule hash in body** — always include the target commit hash when writing a `submod` commit message
- **Separate `submod` commits** — don't mix submodule reference updates with unrelated changes
- **Test after submodule updates** — verify the parent project works correctly with the new submodule state

---
name: merge-to-production
description: >
  Safely merge a development branch into production, with explicit attention to
  environment-specific config files (OAuth client IDs, API endpoints, callback
  URLs) that differ between branches and silently break auth/integration if not
  swapped after the merge. Use this skill when the user asks to "merge to
  production", "deploy main", or "promote development to prod".
---

# Merge to production

The dangerous part of a dev→production merge usually isn't the code merge — it's
forgetting that some config files intentionally differ between branches (different
OAuth app IDs, different API base URLs, different callback URLs) and need to be
re-set to production values *after* the merge brings in development's copy.

## 1. Verify the source branch is ready

```bash
git checkout <dev-branch>
git pull <remote> <dev-branch>
npm test          # or the project's actual test command
npm run build     # or the project's actual build command
git status        # must be clean — "nothing to commit, working tree clean"
```

## 2. Review what's about to merge

```bash
git log <remote>/<production-branch>..<dev-branch> --oneline
git diff <remote>/<production-branch>..<dev-branch> --name-only
```

Specifically check whether any environment-specific config file appears in the
diff — that's the signal to expect step 4 below.

## 3. Merge

```bash
git fetch <remote>
git checkout <production-branch>
git pull <remote> <production-branch>
git merge <dev-branch>
```

Resolve conflicts normally (`git add <file>`, then `git commit`), but if a
conflict is in an environment-specific config file, resolve it toward
*development's* values for now — step 4 fixes it to production values
deliberately and traceably, rather than guessing the right value mid-conflict.

## 4. Restore production environment config — do this every time

If the project has files that intentionally hold different values per branch
(OAuth client/app IDs, callback/redirect URLs, API base URLs, target repo/branch
references for a CMS backend, etc.), check them immediately after merging:

```bash
git diff <remote>/<production-branch> -- <path-to-env-config-file>
```

Confirm every environment-specific value is set to its production value, not
development's. Never commit real client IDs, secrets, or tokens into the skill,
script, or commit message used to fix this — reference them by name
("production OAuth app ID") and pull the actual value from wherever the project
stores it (password manager, secrets manager, `.env` not committed to git).

Commit the fix on its own, separate from the merge commit:

```bash
git add <path-to-env-config-file>
git commit -m "fix(config): restore production values after merge from <dev-branch>"
```

## 5. Build, push, and watch CI

```bash
npm run build       # confirm no build errors before pushing
git push <remote> <production-branch>
git log <remote>/<production-branch> -1   # confirm the push landed
```

Watch the CI/CD pipeline for the push through to a clean deploy — don't consider
the merge done until the pipeline is green.

## 6. Post-merge verification

Visit the live production site/app and confirm: it loads without console errors,
all pages/views render, any third-party auth flow (OAuth login, SSO) completes
end-to-end — not just that the login button is present, but that a real login
succeeds and lands you in the expected authenticated state.

Then switch back to the development branch and confirm development still works
with its own (development) config values — the production config fix in step 4
should never have touched the development branch.

## Rollback

**Revert (preferred — keeps history, safe to push without force):**

```bash
git checkout <production-branch>
git revert -m 1 HEAD
git push <remote> <production-branch>
```

**Hard reset (only if revert isn't viable, requires force-push — coordinate with
anyone else who might pull this branch first):**

```bash
git log --oneline -5                       # find the commit before the merge
git reset --hard <commit-before-merge>
git push <remote> <production-branch> --force
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Auth/OAuth "invalid redirect URI" after merge | Environment config still holds development values | Step 4 — restore production config, recommit |
| Build fails after merge | Conflicting dependency versions or lockfile drift | Clean install (`rm -rf node_modules package-lock.json && npm install`), rebuild |
| Unexpected merge conflicts | Same file touched on both branches independently | Resolve manually, favor traceable manual review over auto-merge for config files specifically |

## Best practices

Merge during low-traffic periods, have the rollback command ready *before*
starting (not looked up mid-incident), keep the merge commit focused — don't bundle
unrelated feature work into a merge — and monitor for a period after the merge
rather than walking away immediately once the pipeline goes green.

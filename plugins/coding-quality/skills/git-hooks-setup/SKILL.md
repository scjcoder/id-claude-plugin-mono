---
name: git-hooks-setup
description: >
  Install Sean's centralized pre-commit hooks submodule into a new or existing
  project, instead of hand-rolling a one-off `.pre-commit-config.yaml`. Use this
  skill when starting a new repo, when the user asks to "set up git hooks" or "add
  pre-commit", or when `checklists/new-project.md` calls for hook installation.
  Falls back to the plugin's own `.pre-commit-config.yaml` template
  (`resources/templates/`) for projects that shouldn't depend on the shared
  submodule.
---

# Git hooks setup

Two ways to get pre-commit hooks into a project — pick based on whether the project
should track Sean's shared, centrally-maintained hook set or stay self-contained.

## Option A — shared submodule (default for InsideDesk/SCJ projects)

```bash
# 1. Add the submodule
git submodule add git@gitlab.com:scj-modules/submod-git-hooks.git .submodules/git-hooks

# 2. Initialize
git submodule update --init --recursive

# 3. Install hooks (creates its own venv, doesn't pollute the project's)
cd .submodules/git-hooks && ./scripts/install-hooks-updated.sh
cd -

# 4. Commit
git add .gitmodules .submodules/git-hooks
git commit -m "feat(infra): add standardized git hooks submodule"
```

Optional Rollbar error-tracking integration, if the project uses it:

```bash
echo "ROLLBAR_ACCESS_TOKEN=<token>" >> .env
echo "ROLLBAR_ENVIRONMENT=production" >> .env
```

Reference docs live inside the submodule once installed:
`.submodules/git-hooks/docs/setup-guide.md`, `migration-guide.md`, `README.md`.

## Option B — standalone config (no submodule dependency)

For projects that shouldn't pull in a shared submodule (e.g. open-source, or a repo
that will outlive this tooling), copy the plugin's own template instead:

```bash
cp resources/templates/.pre-commit-config.yaml ./.pre-commit-config.yaml
pre-commit install
```

This template covers ruff (lint+format), trailing-whitespace/EOF fixes, large-file
and YAML/TOML/JSON checks, and `detect-secrets` baseline scanning — see
`rules/03-security.md` for why secret scanning is mandatory.

## Troubleshooting notes (from real installs)

- If `.pre-commit-config.yaml` ends up referencing a `configs/` subdirectory instead
  of the repo root, the copy step in the install script targeted the wrong path —
  re-run with `--force` to overwrite.
- Add a gitleaks/detect-secrets allowlist entry for `.gitmodules` — submodule URLs
  containing `git@gitlab.com:...` paths can false-positive as credentials.
- If a hook fails because AWS credentials aren't present in CI, configure the
  `detect-aws-credentials` hook to allow missing credentials rather than disabling
  the hook outright.
- Conventional-commit-message hooks need the exact argument format the hook
  expects — a mismatched flag silently no-ops instead of erroring, so verify it's
  actually linting commit messages after install.

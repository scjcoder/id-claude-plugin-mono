# New Project Checklist

Run when starting a new repo so the standards are in place from line one.

## Repo setup

- [ ] `git init`, remote created, default branch protected.
- [ ] `.gitignore` covers `.env`, secrets, build artifacts, OS files.
- [ ] Git LFS configured if the repo will hold screenshots/binaries.
- [ ] `README.md` (what + how to run) and `CLAUDE.md` (agent rules, link to this repo) created.

## Toolchain

- [ ] Language version pinned (`.python-version`, `.nvmrc`, etc.).
- [ ] Dependency manager + lockfile committed (`uv`, `npm`, etc.).
- [ ] Formatter + linter configured and runnable with one command.
- [ ] Test framework wired up; one passing smoke test exists.
- [ ] Copy canonical templates from `resources/templates/`:
  - `pyproject.toml` (Python projects)
  - `.pre-commit-config.yaml`
  - `.gitignore`

## CI / infra

- [ ] CI pipeline runs format + lint + test on every push/MR.
- [ ] If deploying to AWS: OIDC federation with trust policy pinned to `namespace_id`/`project_id` (see [GitLab CI](../stacks/gitlab-ci.md)).
- [ ] Secrets sourced from a manager, never CI plaintext or code.

## Legal (if user-facing)

- [ ] Privacy Policy published before collecting any personal data.
- [ ] Terms of Service if accounts/payments.

## Paper trail

- [ ] CHANGELOG or commit discipline established.
- [ ] Architecture decisions get a record where non-obvious.

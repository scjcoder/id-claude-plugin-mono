# Approved Toolchain

Prefer tools I control over external dependencies I can't. Defaults below; deviate only with reason.

**Canonical templates:** See `resources/templates/` for reference `pyproject.toml`, `.pre-commit-config.yaml`, and `.gitignore` files.

## Python

| Concern | Tool |
|---------|------|
| Version mgmt | `pyenv` |
| Deps / venv | `uv` |
| Format | `ruff format` |
| Lint | `ruff check` |
| Types | `mypy` / `pyright` |
| Test | `pytest` |

## JS / Web

| Concern | Tool |
|---------|------|
| Format | `prettier` |
| Lint | `eslint` |
| Types | TypeScript (`tsc`) |
| Test | `jest` / `vitest` |

## Infra

| Concern | Tool |
|---------|------|
| IaC | Terraform (`fmt`, `validate`, `tflint`) |
| Cloud | AWS (SSO via Administrator profiles) |
| CI/CD | GitLab CI with OIDC federation |
| Secrets | AWS Secrets Manager / SSM Parameter Store |

## Workflow skills (this environment)

- `clean-code-pass` — 13-pass review before any PR.
- `git-commit-workflow` — submodule-aware conventional commits.
- `gitlab-ci-pipeline` — pipeline + OIDC + Secrets Manager patterns.
- `security-review` — diff security pass.
- `aws-sso-scj` / `aws-sso-insidedesk` — AWS auth (dev vs prod).

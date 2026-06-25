# Coding Quality

A Claude-friendly library of coding guidelines, rules, and best practices that govern
how code is written across my projects. It exists so any AI agent (or human) picks up
the same standards without re-deriving them each session.

## Overview

This repository provides a comprehensive set of coding standards organized as:

- **Core rules** — Universal clean-code, git, security, error-handling, testing, and documentation rules
- **Stack overlays** — Technology-specific rules that layer on top of core rules (Python, AWS, Terraform, GitLab CI, web)
- **Checklists** — Gate checklists for commit, PR, and new-project setup
- **Canonical templates** — Reference configurations for `pyproject.toml`, `.pre-commit-config.yaml`, and `.gitignore`
- **Claude plugin** — Distributed via the `insidedesk-tools` marketplace for automatic loading

All rules use **MUST / SHOULD / MAY** tiers (RFC 2119 style) so enforcement level is explicit.
Stack overlays can only tighten core rules — they never relax a MUST.

## Layout

| Path | What it is |
|------|------------|
| `CLAUDE.md` | Entry point. Auto-loaded by Claude; links every rule. Start here. |
| `rules/` | Language-agnostic core rules. Apply to every task. |
| `stacks/` | Stack-specific overlays (Python, Python on AWS/boto3, Terraform/AWS, AWS environment, AWS Lambda, GitLab CI, web). Layered on top of core. |
| `checklists/` | Gate checklists for commit, PR, and new-project setup. |
| `resources/` | Approved toolchain, canonical templates, and external references. |
| `skills/` | Claude skill definitions for automatic rule loading. |
| `.claude-plugin/` | Claude plugin metadata (name, version, description). |

## Core Rules

- [Conventions](rules/00-conventions.md) — MUST/SHOULD/MAY tier definitions and precedence
- [Clean code](rules/01-clean-code.md) — naming, function design, complexity, the 300-line limit, DRY, dead code
- [Git workflow](rules/02-git.md) — conventional commits, verbose messages, clean tree, submodule order
- [Security](rules/03-security.md) — secrets, input validation, parameterized queries, least privilege, secret scanning
- [Error handling](rules/04-error-handling.md) — no silent failures, specific exceptions, boundary validation
- [Testing](rules/05-testing.md) — prove it works; coverage of risk surface; 90% coverage threshold; moto/responses mocking
- [Documentation](rules/06-documentation.md) — script headers, why-not-what comments, docstrings
- [Agent instructions](rules/07-agent-instructions.md) — manage AI agent instruction files to avoid drift

## Stack Overlays

- [Python](stacks/python.md) — pyenv/uv, type hints, ruff, modern typing migration, logging discipline, uv+hatchling packaging
- [Python on AWS (boto3)](stacks/python-aws.md) — client reuse, region discipline, retry config, pagination, ClientError handling
- [Terraform / AWS](stacks/terraform-aws.md) — state, least-privilege IAM, tagging
- [AWS environment](stacks/aws-environment.md) — S3 security (Block Public Access, encryption, TLS), CloudWatch log retention, cost guardrails (infracost), secrets caching
- [AWS Lambda (Node.js)](stacks/aws-lambda.md) — latest Node runtime, AWS SDK v3 only, async handlers
- [GitLab CI](stacks/gitlab-ci.md) — OIDC to AWS, pinned `namespace_id`/`project_id`, secrets handling
- [Web frontend](stacks/web-frontend.md) — error boundaries, loading states, privacy/GDPR

## Canonical Templates

Located in `resources/templates/`:

- [pyproject.toml](resources/templates/pyproject.toml) — Canonical Python project config with hatchling, ruff, black, pytest, coverage (90% threshold)
- [.pre-commit-config.yaml](resources/templates/.pre-commit-config.yaml) — Pre-commit hooks with ruff, black, detect-secrets
- [.gitignore](resources/templates/.gitignore) — Comprehensive .gitignore for Python, venv, .env, Terraform, Node, IDE files

These templates ship with the plugin and can be copied directly to new projects.

## Checklists

- [Pre-commit](checklists/pre-commit.md) — Run before every commit
- [Pre-PR](checklists/pre-pr.md) — Run before opening a pull request
- [New project](checklists/new-project.md) — Run when starting a new repository

## Skills

- [coding-quality](skills/coding-quality/SKILL.md) — entry point that auto-triggers on any coding task and loads the rules above as binding.
- [clean-code-pass](skills/clean-code-pass/SKILL.md) — 13-pass systematic code review workflow. Covers naming, function design, complexity, error handling, security, DRY, dead code, dependencies, type safety, comments, formatting, test coverage, and verification. Use before PRs or when code "feels messy".

## Distribution

This plugin lives in the `id-claude-plugin-mono` monorepo and is distributed via the
`insidedesk-tools` marketplace. The marketplace serves `plugins/coding-quality/` straight
from source — there is no `.plugin` build step. Edit files in place; ship a change with
the repo-root release helper:

```bash
./release.sh coding-quality <new-version> "<changelog message>" [Added|Changed|Fixed|Removed|Security]
```

That bumps `version` in `.claude-plugin/plugin.json`, prepends a changelog entry to
`docs/changelog.md`, commits, and pushes. Teammates pick it up on their next
**Customize → Plugins → Update**.

The `coding-quality` skill auto-loads when you:
- Start any coding task
- Ask to review code or check standards
- Start a new project
- Write IAM/OIDC trust policies, GitLab CI pipelines, Python, Terraform, or web frontend code

## Version History

See [docs/changelog.md](docs/changelog.md) for detailed change history.

## Conventions

- Every rule has a tier (**MUST** / **SHOULD** / **MAY**) and, where useful, a rationale and a good/bad example
- Files stay under 300 lines, same as the code standard they describe
- Changes follow the [git workflow](rules/02-git.md) in this repo: conventional commits, verbose messages, clean tree

## Origin

Seeded from the `clean-code-pass` 13-pass review workflow and hardened with real incidents
(e.g. the AWS/GitLab OIDC path-reclaim advisory — see [`stacks/gitlab-ci.md`](stacks/gitlab-ci.md)).

## License

MIT

# Changelog

All notable changes to the Coding Quality plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.5.0] - 2026-06-28

### Added
- 10 new skills converted from the `aws-email-wizard` repo's Windsurf/Devin
  workflows (`.devin/workflows/`), genericized and de-duplicated against existing
  plugin content: `documentation-update`, `git-release`, `git-save`,
  `git-hooks-setup`, `git-whitespace-hooks`, `gitlab-ci-best-practices`,
  `root-cleanup`, `test-suite-bootstrap`, `project-analysis`,
  `merge-to-production`. Full conversion record, including what was genericized
  and what was learned from each, is in `docs/workflow-skill-conversions.md`.

### Changed
- Migrated from the standalone `ai-coding-quality` repo into the `id-claude-plugin-mono`
  monorepo as the `coding-quality` plugin, distributed via the `insidedesk-tools`
  marketplace. Retired the per-plugin `build-plugin.sh`/`coding-quality.plugin` archive
  flow — the marketplace now serves `plugins/coding-quality/` directly from source, and
  releases ship via the repo-root `release.sh` helper instead. Fixed the canonical-repo
  fallback path in `skills/coding-quality/SKILL.md` and a broken `stacks/gitlab.md` link
  in `README.md`.

## [1.4.1] - 2026-05-31

### Fixed
- Corrected plugin.json version field after accidental rollback to 1.3.0 during build session; no content changes — identical to 1.4.0

## [1.4.0] - 2026-05-30

### Added
- `skills/clean-code-pass/SKILL.md` — 13-pass systematic code review workflow (naming, function design, complexity, error handling, security, DRY, dead code, dependencies, type safety, comments, formatting, test coverage, verification)
- Enhanced `rules/02-git.md` with git-commit-workflow content: commit message format details, commit types (tweak, hotfix, wip, revert, submod), subject line rules, body guidelines, available scopes table, submodule commit workflow, pre-commit hook handling with `git commit-safe` alias, best practices
- Expanded `stacks/gitlab-ci.md` with comprehensive GitLab CI/CD pipeline practices: core principles, OIDC authentication in `.gitlab-ci.yml`, AWS Secrets Manager parsing with jq, Terraform pipeline workflow, heredoc and script rules, variable expansion rules, security scanning with Trivy, pipeline structure template, verification checklist

### Changed
- Deprecated `scj-dev-workflows` plugin in favor of `coding-quality` plugin (all skills migrated)
- Linked clean-code-pass skill from CLAUDE.md and README.md

## [1.3.0] - 2026-05-30

### Added
- `stacks/aws-environment.md`: AWS environment practices overlay on terraform-aws.md. Enforces S3 bucket security (Block Public Access, encryption, TLS policy), CloudWatch log retention (explicit retention, never "Never expire"), cost guardrails (infracost in CI, mandatory resource tagging), and secrets retrieval discipline (default credential chain, init-time caching with TTL, Lambda Powertools reference).
- `resources/templates/.pre-commit-config.yaml`: Canonical pre-commit config with ruff, black, pre-commit hooks, and detect-secrets (baseline-friendly).
- `resources/templates/.gitignore`: Canonical .gitignore covering Python, venv, .env, Terraform, Node, and IDE files.
- `rules/07-agent-instructions.md`: Guidance on managing AI agent instruction files to avoid drift and duplication.
- Updated `rules/03-security.md`: MUST run secret scanner in pre-commit/CI, MUST NOT commit venv dirs, cross-linked templates.
- Updated `rules/05-testing.md`: SHOULD keep ≥ 90% line coverage, MUST mock AWS with moto, MUST mock HTTP with responses, cross-linked pyproject.toml.
- Updated `resources/tools.md`: Reference to templates directory.
- Updated `checklists/new-project.md`: Template copy step added.
- Extended `build-plugin.sh` to pack .toml, .yaml, .yml, .gitignore, .cfg from resources/templates/ (templates usable as real files when copied).

### Changed
- Linked `stacks/aws-environment.md` from CLAUDE.md, README.md, and the coding-quality skill.
- Linked `rules/07-agent-instructions.md` from CLAUDE.md.

## [1.2.0] - 2026-05-30

### Added
- `stacks/python-aws.md`: Python on AWS (boto3) overlay. Mandates module-scope client
  reuse (no clients built inside handlers/loops), region from session/env (no hardcoded
  `region_name`), a `botocore.config.Config` with adaptive retries and explicit timeouts
  on every client, pagination of all `list_*`/`describe_*`/`scan` calls via paginators,
  and catching `botocore.exceptions.ClientError` with error-code branching instead of
  bare `except Exception`. Adds secrets/credential-chain guidance (no ad-hoc credential
  files; cache Secrets Manager/SSM at init).
- Linked the new overlay from `CLAUDE.md`, `README.md`, and the `coding-quality` skill.

## [1.1.0] - 2026-05-30

### Added
- `stacks/aws-lambda.md`: AWS Lambda (Node.js) overlay. Targets the latest Lambda
  runtime (`nodejs24.x`) with a one-step downgrade to active LTS (`nodejs22.x`)
  allowed only on dependency conflict; mandates AWS SDK v3 (`@aws-sdk/client-*`)
  only and bans the EOL v2 `aws-sdk`; requires async handlers (Node 24 dropped
  callbacks), per-client imports, client reuse across warm invocations, least-
  privilege execution roles, and lean dependencies.
- Linked the new overlay from `CLAUDE.md` and the `coding-quality` skill.

## [1.0.0] - 2026-05-30

### Added
- Initial release. Packages the Coding Quality standards repo as a Claude plugin.
- `coding-quality` skill: entry point that loads the bundled rule set when the user
  asks to review code, check standards, or start a new project.
- Core rules: conventions (MUST/SHOULD/MAY tiers), clean-code, git, security,
  error-handling, testing, documentation.
- Stack overlays: python, terraform-aws, gitlab-ci (AWS/GitLab OIDC trust-policy
  pinning to `namespace_id`/`project_id`), web-frontend (error boundaries, GDPR).
- Checklists: pre-commit, pre-pr, new-project. Resources: tools, references.
- `build-plugin.sh`: version-disciplined packer adapted from id-claude-reporting.

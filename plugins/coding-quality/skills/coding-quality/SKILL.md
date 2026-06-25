---
name: coding-quality
description: >
  Load Sean's binding coding standards before writing, reviewing, or refactoring
  code. AUTOMATICALLY trigger this skill — without waiting to be asked — whenever:
  (1) starting any coding task in any language; (2) the user says "review my code",
  "clean up", "refactor", "code quality", or "is this ready to commit/PR";
  (3) starting a new project or repo; (4) writing IAM/OIDC trust policies, GitLab
  CI pipelines, Python, Terraform, or web frontend code; (5) preparing a commit or
  pull request. These rules are binding — apply the MUST tier as hard requirements.
---

# Skill: coding-quality

Sean's single source of truth for how code gets written. The rules below are binding:
**MUST** = hard requirement, **SHOULD** = strong default, **MAY** = optional. A stack
overlay can only tighten a core rule, never relax it.

## How to apply

1. **Read the conventions first** — `rules/00-conventions.md` (tier definitions + precedence).
2. **Apply the core rules** on every task: `rules/01-clean-code.md`, `02-git.md`,
   `03-security.md`, `04-error-handling.md`, `05-testing.md`, `06-documentation.md`.
3. **Layer the matching stack overlay** when the task touches it:
   `stacks/python.md`, `stacks/python-aws.md`, `stacks/terraform-aws.md`,
   `stacks/aws-environment.md`, `stacks/aws-lambda.md`, `stacks/gitlab-ci.md`,
   `stacks/web-frontend.md`.
4. **Run the matching checklist** before the gate: `checklists/pre-commit.md`,
   `checklists/pre-pr.md`, `checklists/new-project.md`.

Read these files from the plugin bundle (`${CLAUDE_PLUGIN_ROOT}` / this skill's repo).
If they are not found in the bundle, read them from the canonical repo at
`/Users/sean/CODE/id-claude-plugin-mono/plugins/coding-quality/`.

## The non-negotiables (always, even without reading further)

1. **Fix root causes, not symptoms** — no band-aids presented as fixes.
2. **"Done" means committed, tested, and verified** — never "it should work".
3. **Files stay under 300 lines** — refactor proactively near the limit.
4. **No secrets in code** — env vars or a secret manager, always.
5. **Prove it works** — run the linter, formatter, and tests before claiming success.

## For a full review

Run the companion `clean-code-pass` skill (13-pass review) — it is the audit procedure
that enforces the standing rules in this plugin. Use it before every PR.

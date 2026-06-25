# Coding Quality — Operating Rules for AI-Assisted Development

> 📦 **This plugin lives in the InsideDesk plugin monorepo — the single source of truth.**
>
> Path: `/Users/sean/CODE/id-claude-plugin-mono/plugins/coding-quality/`
> Distributed via the `insidedesk-tools` marketplace (`git@gitlab.com:insidedesk/id-claude-plugin-mono.git`).
>
> Edit rules/stacks/checklists/skills in place here. To ship a change to the team, run the repo-root
> release helper — there is **no `.plugin` build step** (the marketplace serves this
> directory directly):
>
> ```
> ./release.sh coding-quality <new-version> "<changelog message>" [Added|Changed|Fixed|Removed|Security]
> ```

This repo is the single source of truth for how code gets written in my projects.
When you (Claude / any AI agent) work on my code, these rules are binding.

## How to use this file

1. Read [`rules/00-conventions.md`](rules/00-conventions.md) first — it defines the MUST/SHOULD/MAY tiers used everywhere.
2. Apply the **core rules** (`rules/`) on every task, in every language.
3. Layer the relevant **stack overlay** (`stacks/`) on top when the task touches that stack.
4. Run the matching **checklist** (`checklists/`) before committing, opening a PR, or starting a project.

Core rules are universal. Stack overlays add or tighten rules — they never relax a core MUST.

## Core rules (always apply)

- [Clean code](rules/01-clean-code.md) — naming, function design, complexity, the 300-line limit, DRY, dead code.
- [Git workflow](rules/02-git.md) — conventional commits, verbose messages, clean tree, submodule order.
- [Security](rules/03-security.md) — secrets, input validation, parameterized queries, least privilege.
- [Error handling](rules/04-error-handling.md) — no silent failures, specific exceptions, boundary validation.
- [Testing](rules/05-testing.md) — prove it works; coverage of risk surface; no "it should work".
- [Documentation](rules/06-documentation.md) — script headers, why-not-what comments, docstrings.
- [Agent instructions](rules/07-agent-instructions.md) — manage AI agent instruction files to avoid drift.

## Stack overlays (apply when relevant)

- [Python](stacks/python.md) — pyenv/uv, type hints, ruff.
- [Python on AWS (boto3)](stacks/python-aws.md) — client reuse, region discipline, retry config, pagination, ClientError handling.
- [Terraform / AWS](stacks/terraform-aws.md) — state, least-privilege IAM, tagging.
- [AWS environment](stacks/aws-environment.md) — S3 security, log retention, FinOps, secrets caching.
- [AWS Lambda (Node.js)](stacks/aws-lambda.md) — latest Node runtime, AWS SDK v3 only, async handlers.
- [GitLab CI](stacks/gitlab-ci.md) — OIDC to AWS, pinned `namespace_id`/`project_id`, secrets handling.
- [Web frontend](stacks/web-frontend.md) — error boundaries, loading states, privacy/GDPR.

## Checklists

- [Pre-commit](checklists/pre-commit.md)
- [Pre-PR](checklists/pre-pr.md)
- [New project](checklists/new-project.md)

## Skills

- [coding-quality](skills/coding-quality/SKILL.md) — entry point that auto-triggers on any coding task and loads the rules above as binding.
- [clean-code-pass](skills/clean-code-pass/SKILL.md) — 13-pass systematic code review workflow (naming, function design, complexity, error handling, security, DRY, dead code, dependencies, type safety, comments, formatting, test coverage, verification). Use before PRs or when code "feels messy".

## Resources

- [Approved tools](resources/tools.md)
- [References](resources/references.md)

## Non-negotiables (the short version)

1. **Fix root causes, not symptoms.** No band-aids, no workarounds presented as fixes.
2. **"Done" means committed, tested, and verified** — not just written.
3. **Files stay under 300 lines.** Refactor proactively when approaching the limit.
4. **No secrets in code.** Ever. Environment variables or a secret manager.
5. **Prove it works.** Never claim success without running the thing.

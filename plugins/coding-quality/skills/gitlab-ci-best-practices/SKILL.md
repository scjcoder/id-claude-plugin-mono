---
name: gitlab-ci-best-practices
description: >
  Structure, write, and verify `.gitlab-ci.yml` configuration — stage organization,
  rules vs only/except, DAG dependencies via `needs`, anchors/includes for DRY
  config, secret handling, and a pre-commit lint/validation pass. Use this skill
  when creating or reviewing a GitLab CI pipeline, or when the user asks to "set up
  CI", "fix the pipeline", or "review .gitlab-ci.yml".
---

# GitLab CI/CD best practices

## Structure

- **Array syntax for scripts** — `script: ['cmd1', 'cmd2']` avoids YAML parsing
  ambiguity for short script lists.
- **`before_script` / `after_script`** to keep `script:` focused on the actual job,
  not setup/teardown.
- **Explicit `stages:`** at the top of the file so the pipeline's flow is visible at
  a glance.
- **Anchors (`&name`) and aliases (`<<: *name`)** for config blocks repeated across
  jobs (e.g. a shared image + before_script for all jobs in one language).
- **`rules:` instead of `only`/`except`** — `only`/`except` are legacy and don't
  compose; `rules:` supports conditional logic cleanly:

  ```yaml
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
      when: always
    - if: $CI_COMMIT_BRANCH =~ /^feature\/.*/
      when: manual
  ```

- **`needs:`** to build an explicit DAG instead of relying only on stage ordering —
  lets independent jobs run in parallel rather than waiting on the whole previous
  stage.
- **Heredoc for multiline file generation** inside `script:` blocks, to avoid YAML
  escaping issues:

  ```yaml
  script:
    - |
      cat > config.json << EOF
      {"version": "${CI_COMMIT_SHORT_SHA}"}
      EOF
  ```

- **`include:`** to split config into per-concern files (`build.yml`, `test.yml`,
  `deploy.yml`) and keep the root `.gitlab-ci.yml` short.
- **Explicit `timeout:`** on any job that calls an external service or could hang.

## Verification before committing

```bash
glab ci lint .gitlab-ci.yml
```

Then check by hand:

- Every variable used is defined somewhere (job, global, or GitLab CI/CD settings)
  with a sensible default for optional ones: `${VAR_NAME:-default}`
- Sensitive variables are masked/protected in GitLab CI/CD settings — never
  hardcoded in the YAML
- `needs:` relationships match the actual artifact/dependency flow
- Image versions are pinned, not floating on `latest`
- Cache keys are scoped correctly (don't cache across incompatible branches/jobs)

## Common failure modes

| Symptom | Likely cause |
|---|---|
| YAML parse error | Tab indentation instead of spaces, or an unquoted string with a colon |
| Job exits 0 but did nothing | Missing `set -e` — a failed command mid-script didn't stop the job |
| Variable empty in script | Wrong scope (global vs. job-level) or expansion timing |
| Missing artifact in downstream job | `artifacts:` not defined, wrong path, or already expired |
| Cache not helping | Cache key too specific (changes every run) or path mismatch |

## Stack-specific notes

**Node.js**: pin the Node version in the image, cache `node_modules`, use `npm ci`
(not `npm install`) for reproducible installs.

**Deployment targets**: prefer IAM roles / OIDC federation over long-lived tokens
when deploying to AWS (this plugin's `opentofu-secure` skill sets up the OIDC trust
relationship). For Netlify/Vercel-style deploys, use non-interactive flags and pass
the target explicitly (site ID, project name) rather than relying on interactive
prompts that will hang a CI job.

## Continuous improvement

Periodically review pipeline duration and success rate, identify the slowest jobs
and whether they can run in parallel via `needs:`, and check for newly-deprecated
GitLab CI syntax (`only`/`except`, old artifact syntax) during routine maintenance.

# Stack Overlay — GitLab CI/CD

Layered on top of all core rules. Adds pipeline + AWS OIDC requirements.

## Core principles

- **MUST** use OIDC-first authentication — never store long-lived AWS credentials in CI variables
- **MUST** use array syntax for scripts — prefer `['cmd1', 'cmd2']` over heredoc blocks
- **MUST** start every multi-line script block with `set -euo pipefail` for fail-fast behavior
- **MUST** scope IAM roles per job — least privilege (deploy jobs ≠ lint jobs)
- **MUST** make jobs idempotent — safe to re-run without side effects

## OIDC federation to AWS — pin stable identifiers

**Why this rule exists:** On GitLab.com SaaS, deleted group and project *paths* can be
reclaimed by other users. A trust policy that authorizes only on the path-based `sub`
claim (`project_path:mygroup/myproject:...`) could grant access to an unintended actor
if your project is deleted and the path re-created by someone else. (AWS IAM security
advisory, GitLab + AWS joint recommendation.)

- **MUST** add a condition on a stable, non-reusable identifier — `namespace_id` and/or `project_id` — to every IAM role trust policy that federates GitLab.com.
- **MUST NOT** rely on the path-based `sub` claim alone for access control.
- **SHOULD** also constrain `ref` / `ref_protected` so only the intended branch (e.g. protected `main`) can assume the role.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::123456789012:oidc-provider/gitlab.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "gitlab.com:sub": "project_path:mygroup/myproject:ref_type:branch:ref:main",
        "gitlab.com:namespace_id": "12345",
        "gitlab.com:project_id": "67890"
      }
    }
  }]
}
```

### Supported GitLab.com custom claims (validated by AWS STS)

`namespace_id`, `project_id`, `user_id`, `user_login`, `user_email`,
`user_access_level` (`maintainer`/`developer`/`owner`), `ref_protected` (`true`/`false`),
`pipeline_source` (`push`/`web`/`schedule`/`api`/`merge_request_event`).

- **SHOULD** tighten high-privilege roles further with `user_access_level` and/or `pipeline_source`
  (e.g. only `pipeline_source: push` on a protected ref for a deploy role).

### Auditing existing roles

- **MUST** check the AWS Health Dashboard "Affected resources" tab for roles trusting the GitLab IdP and remediate each.
- For each role: Trust relationships → Edit trust policy → add the `namespace_id`/`project_id` conditions.

> Find your IDs in GitLab: project_id on the project's main page / **Settings → General**;
> namespace_id via the group settings or the API (`/api/v4/projects/:id`).

## OIDC authentication in `.gitlab-ci.yml`

- **MUST** use `id_tokens` with AWS `assume-role-with-web-identity` — never long-lived credentials
- **MUST** set `AWS_WEB_IDENTITY_TOKEN_FILE` and `AWS_ROLE_ARN` for SDK auto-detection

```yaml
.aws_oidc_auth:
  id_tokens:
    GITLAB_OIDC_TOKEN:
      aud: https://gitlab.com
  before_script:
    - |
      set -euo pipefail
      export AWS_WEB_IDENTITY_TOKEN_FILE=$(mktemp)
      echo "${GITLAB_OIDC_TOKEN}" > "${AWS_WEB_IDENTITY_TOKEN_FILE}"
      export AWS_ROLE_ARN="${AWS_ROLE_ARN}"
      export AWS_ROLE_SESSION_NAME="gitlab-ci-${CI_JOB_NAME}-${CI_JOB_ID}"

.aws_auth_dev:
  extends: .aws_oidc_auth
  variables:
    AWS_ROLE_ARN: "arn:aws:iam::111111111111:role/gitlab-ci-dev"

.aws_auth_prod:
  extends: .aws_oidc_auth
  variables:
    AWS_ROLE_ARN: "arn:aws:iam::222222222222:role/gitlab-ci-prod"
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

## AWS Secrets Manager — parsing nested JSON

Secrets are stored as stringified JSON. Always use `--query SecretString --output text` to get the raw string, then parse with jq.

- **MUST** use `--query SecretString --output text` to get raw secret string
- **MUST** parse nested JSON with `jq -r` for raw values
- **MUST NOT** interpolate secrets into shell variables before parsing

```yaml
fetch_secrets:
  extends: .aws_oidc_auth
  script:
    - |
      set -euo pipefail

      # Get the raw secret string
      SECRET_STRING=$(aws secretsmanager get-secret-value \
        --secret-id prod/database \
        --query 'SecretString' \
        --output text)

      # Parse nested JSON with jq -r
      DB_HOST=$(echo "${SECRET_STRING}" | jq -r '.database.host')
      DB_PORT=$(echo "${SECRET_STRING}" | jq -r '.database.port')
      API_KEY=$(echo "${SECRET_STRING}" | jq -r '.services.api.key')

      # Export for downstream use
      echo "DB_HOST=${DB_HOST}" >> "${CI_PROJECT_DIR}/.env"
```

## Terraform pipeline workflow

- **MUST** set `TF_IN_AUTOMATION: "true"` and `TF_INPUT: "false"` to prevent hanging
- **MUST** use cache for `.terraform` directory
- **SHOULD** separate `plan` (on MR) from `apply` (manual, on protected branch)

```yaml
.terraform_base:
  extends: .aws_oidc_auth
  image: hashicorp/terraform:1.9
  variables:
    TF_ROOT: ${CI_PROJECT_DIR}/terraform
    TF_IN_AUTOMATION: "true"
    TF_INPUT: "false"
  cache:
    key:
      files:
        - ${TF_ROOT}/.terraform.lock.hcl
    paths:
      - ${TF_ROOT}/.terraform
    policy: pull-push

terraform_validate:
  extends: .terraform_base
  stage: validate
  script:
    - ['cd ${TF_ROOT}', 'terraform init -backend=false', 'terraform validate']

terraform_plan:
  extends: .terraform_base
  stage: plan
  script:
    - |
      set -euo pipefail
      cd "${TF_ROOT}"
      terraform init
      terraform plan -out=tfplan -lock=true
  artifacts:
    paths:
      - ${TF_ROOT}/tfplan
    expire_in: 1 day

terraform_apply:
  extends: .terraform_base
  stage: apply
  script:
    - |
      set -euo pipefail
      cd "${TF_ROOT}"
      terraform init
      terraform apply -lock=true -auto-approve tfplan
  dependencies:
    - terraform_plan
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
      when: manual
  timeout: 30m
```

## Heredoc and script rules

Heredocs are the #1 source of CI parsing failures.

- **MUST** prefer array syntax for scripts: `['cmd1', 'cmd2']` or separate list items
- **MUST** use `|` (literal) not `>` (folded) when using heredocs
- **MUST** quote heredoc delimiters to prevent variable expansion unless intentional
- **MUST** include `set -euo pipefail` in every multi-line script block

```yaml
# ✅ GOOD — each command is a separate list item
script:
  - terraform init
  - terraform validate
  - terraform fmt -check

# ✅ ACCEPTABLE — multi-line block with fail-fast
script:
  - |
    set -euo pipefail
    terraform init
    terraform validate

# ❌ BAD — folded scalar (>) joins lines with spaces
script:
  - >
    terraform init
    terraform validate

# ✅ CORRECT — use | (literal) not > (folded)
script:
  - |
    set -euo pipefail
    cat <<'EOF' > config.json
    {
      "region": "us-east-1",
      "environment": "production"
    }
    EOF
    cat config.json
```

### Variable expansion rules

```yaml
script:
  - |
    # GitLab CI variables expand BEFORE shell runs
    cat << EOF > env.txt
    COMMIT=${CI_COMMIT_SHA}   # Expands at GitLab processing time
    EOF

    # For shell-level variables, quote the delimiter:
    MY_VAR="hello"
    cat << 'EOF' > template.sh
    echo "Value is $MY_VAR"    # Stays literal until shell runs
    EOF
```

### Alternative: source external scripts

For complex logic, store scripts in the repo instead of inline YAML:

```yaml
script:
  - chmod +x ./ci/deploy.sh
  - ./ci/deploy.sh
```

## Security scanning

- **SHOULD** include GitLab SAST and Secret-Detection templates
- **SHOULD** use Trivy for Terraform security scanning (replaces deprecated tfsec)

```yaml
include:
  - template: Security/SAST.gitlab-ci.yml
  - template: Security/Secret-Detection.gitlab-ci.yml

tfsec:
  stage: validate
  image: aquasec/trivy:latest
  script:
    - trivy config ${TF_ROOT} --exit-code 1 --severity HIGH,CRITICAL
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

## Pipeline structure template

```yaml
stages:
  - validate
  - plan
  - apply
  - deploy

default:
  image: amazonlinux:2023
  retry:
    max: 1
    when:
      - runner_system_failure
      - stuck_or_timeout_failure

variables:
  AWS_DEFAULT_REGION: us-east-1
  TF_IN_AUTOMATION: "true"
  TF_INPUT: "false"
```

## Verification checklist

Before committing `.gitlab-ci.yml` changes:

- [ ] Lint: `glab ci lint .gitlab-ci.yml`
- [ ] YAML: `yamllint .gitlab-ci.yml`
- [ ] No hardcoded secrets: grep for API keys, tokens, passwords
- [ ] All variables defined: check CI/CD settings + job variables
- [ ] `set -euo pipefail` in every multi-line script block
- [ ] Artifacts: verify paths and expiration for job dependencies
- [ ] Rules: confirm job triggers match intended branches/events
- [ ] Timeouts: set explicit `timeout:` for jobs that could hang
- [ ] OIDC: confirm `id_tokens` on every AWS-authenticated job
- [ ] jq: verify `-r` on all `jq` calls parsing secrets

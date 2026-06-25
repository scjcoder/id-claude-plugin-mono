# Stack Overlay — Terraform / AWS

Layered on top of all core rules. Adds IaC and AWS requirements.

## State & structure

- **MUST** use remote state (S3 backend + DynamoDB lock or S3 native locking). Never local state for shared infra.
- **MUST** run `terraform plan` and review the diff before any `apply`.
- **SHOULD** separate environments (dev/prod) by workspace or directory, never by editing in place.
- **MUST** keep modules small and reusable; one responsibility per module.

## IAM — least privilege

- **MUST** grant the narrowest actions and resources that work — no `"Action": "*"` / `"Resource": "*"` in real policies.
- **MUST** scope trust policies to stable identifiers (see [GitLab CI OIDC](gitlab-ci.md)).
- **SHOULD** prefer roles over long-lived access keys; prefer OIDC federation over stored credentials.

## Accounts (this environment)

- Dev / SCJ account: `Administrator-<SCJ_AWS_ACCOUNT_ID>` — default for non-prod work. Resolve `<SCJ_AWS_ACCOUNT_ID>` from `config/scj.local.json`.
- Prod / InsideDesk account: `Administrator-<AWS_ACCOUNT_ID>` — apply the production safety checklist before any mutating command. Resolve `<AWS_ACCOUNT_ID>` from `config/insidedesk.local.json`.
- **MUST** confirm which account is targeted before `apply`; never assume prod.

## Hygiene

- **MUST** tag resources (owner, project, environment) for traceability.
- **MUST NOT** hardcode secrets in `.tf` — use AWS Secrets Manager / SSM, referenced as data sources.
- **MUST** format with `terraform fmt` and validate with `terraform validate` before committing.
- **SHOULD** run `tflint` / a policy scanner on the plan for security regressions.

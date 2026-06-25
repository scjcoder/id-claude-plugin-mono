# Pre-apply security checklist

Run before every `tofu apply`. Maps to the binding `coding-quality` Terraform/AWS
and GitLab-CI overlays.

## State & structure
- [ ] Remote S3 backend with `use_lockfile = true` (no local state for shared infra).
- [ ] Correct `backend.<env>.hcl` selected; `key` namespaced by project + environment.
- [ ] `tofu fmt -recursive` clean.
- [ ] `tofu validate` passes.
- [ ] `tofu plan` reviewed — diff matches intent, no surprise destroys.

## IAM — least privilege
- [ ] No `Action = "*"` or `Resource = "*"` in any real policy statement.
- [ ] GitLab trust policy conditions on **`namespace_id` AND `project_id`** (numeric, stable).
- [ ] `sub` / ref scoping limits which branches/pipelines may assume the role.
- [ ] `max_session_duration` is the minimum that works (default 3600s).
- [ ] Permissions boundary applied to high-privilege roles where available.
- [ ] OIDC federation preferred over any long-lived access key.

## Data protection
- [ ] S3: public-access block on (all four flags), versioning on, KMS or SSE-S3 encryption.
- [ ] S3: TLS-only bucket policy present; deny-unencrypted-PUT present.
- [ ] KMS keys have rotation enabled.
- [ ] CloudWatch log groups encrypted with a CMK; retention set per environment.
- [ ] No secrets in `.tf`, `.tfvars` committed, or state read into plaintext outputs.

## Tagging & traceability
- [ ] `Project`, `Environment`, `Owner`, `ManagedBy` present (via default_tags).
- [ ] `Name` tag on each named resource.

## Account safety
- [ ] Target account confirmed: dev `<SCJ_AWS_ACCOUNT_ID>` vs prod `<AWS_ACCOUNT_ID>`.
- [ ] For prod: InsideDesk production safety checklist applied before any mutating command.

## Detective controls (baseline configs)
- [ ] AWS Config recorder enabled with a delivery bucket.
- [ ] CloudWatch alarms route to the CMK-encrypted SNS topic.
- [ ] Trivy `config` scan returns no HIGH/CRITICAL.
- Note: WAF / Security Hub / GuardDuty are intentionally excluded on cost grounds —
  do not add them.

## Done means done
- [ ] Committed (conventional commit, full context), `git status` clean.
- [ ] Validated and planned — never "it should work".

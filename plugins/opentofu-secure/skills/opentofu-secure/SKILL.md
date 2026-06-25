---
name: opentofu-secure
description: >
  Generate new OpenTofu/Terraform AWS configuration from Sean's hardened,
  security-baked templates. AUTOMATICALLY trigger this skill — without waiting to
  be asked — whenever the user wants to: create or scaffold new .tf/.tofu config,
  stand up an S3 bucket, an IAM role / GitLab CI OIDC federation, Route53 DNS +
  ACM certificates, or a CloudWatch/AWS-Config monitoring baseline; add a
  new resource to an existing Tofu project; or asks for "infra", "terraform",
  "opentofu", "tofu", a "backend", "state bucket", or "a secure bucket/role/cert".
  Every output ships with remote S3 native-lock state, least-privilege IAM,
  encryption, blocked public access, mandatory tagging, and an OIDC CI pipeline
  already wired in. Prefer this over hand-writing .tf from scratch.
---

# Skill: opentofu-secure

Generate production-ready OpenTofu config for AWS where security, state, tagging,
and CI are already correct — so a new resource is a fill-in-the-blanks job, not a
from-scratch security review. Templates encode Sean's conventions and the binding
`coding-quality` Terraform/OIDC rules.

Pair this with the `coding-quality` skill (it is binding for Terraform and IAM/OIDC
work). This skill is the *generator*; `coding-quality` is the *standard* it obeys.

## Conventions every generated config follows

- **State**: remote `s3` backend with **native locking** (`use_lockfile = true`, no
  DynamoDB). Partial config via `backend.<env>.hcl` — dev = account
  `<SCJ_AWS_ACCOUNT_ID>` (resolved from `config/scj.local.json`), prod =
  `<AWS_ACCOUNT_ID>` (resolved from `config/insidedesk.local.json`). `new-config.sh`
  resolves both placeholders automatically when it scaffolds a project. Never
  local state for shared infra.
- **Provider**: `hashicorp/aws ~> 5.0`, `random ~> 3.5`, `required_version >= 1.10`,
  adaptive retries, credential/region validation on.
- **Tags**: mandatory `Project / Environment / Owner / ManagedBy` applied via
  `default_tags`; resource tags merge on top of `local.tags`. Naming = `local.name_prefix`
  (`<project>-<environment>`).
- **CI**: `.gitlab-ci.yml` with OIDC auth (no static keys), `validate → plan(MR) →
  apply(manual,main)`, and a Trivy HIGH/CRITICAL config scan.
- **Header block** on every `.tf` file (author, purpose, last-updated, version).
- **Files stay under 300 lines** — split by concern (`main.tf`, `variables.*.tf`,
  `outputs.*.tf`, `monitoring.tf`, `config.tf`, …).

## Available templates

Each lives in `assets/templates/`. `_base/` is the shared scaffold; the others are
the resource bodies that combine with it.

| Template | Produces | Security baked in |
|---|---|---|
| `_base/` | versions, providers, backend (+dev/prod hcl), variables, tags, outputs, .gitignore, .gitlab-ci.yml | S3 native-lock state, default_tags, validated inputs, OIDC CI + Trivy |
| `s3-secure-bucket/` | S3 bucket | Dedicated rotating KMS key, versioning, full public-access block, BucketOwnerEnforced, TLS-only + deny-unencrypted-PUT policy, lifecycle |
| `iam-gitlab-oidc/` | GitLab→AWS OIDC provider + CI role | Trust policy pinned to **stable** `namespace_id` + `project_id` (not the reusable path), `sub`/ref scoping, least-privilege inline policy, optional permissions boundary |
| `route53-acm/` | ACM cert + Route53 records | DNS-validated cert in us-east-1 (CloudFront-ready), automated validation records, alias/standard app records |
| `observability-baseline/` | CloudWatch + AWS Config | KMS-encrypted logs w/ env retention, CMK-encrypted SNS alerts, billing alarm, AWS Config recorder + baseline managed rules |
| `vpc-network/` | VPC, public/private subnets, IGW, optional NAT, route tables | Default SG locked to deny-all, no auto public IPs, VPC flow logs to a CMK-encrypted log group |
| `lambda-api/` | Lambda + API Gateway v2 (HTTP API) | Least-privilege exec role (own log group only), CMK-encrypted env + logs, stage access logging + throttling, scoped invoke permission. No WAF. Defaults to latest Node.js LTS (`nodejs24.x`, bundles AWS SDK v3) |
| `dynamodb-table/` | DynamoDB table | CMK encryption, point-in-time recovery, deletion protection, on-demand billing, optional TTL |
| `state-bootstrap/` | The S3 remote-state bucket itself (run once per account) | Versioned, KMS-encrypted, public-access blocked, TLS-only, `prevent_destroy`. **Standalone** — uses a LOCAL backend, not `_base` |

### Shared state bucket — one bucket per account, keys by prefix

State is **not** one bucket per project. `state-bootstrap` creates a single bucket
per account+region named `<account-id>-tfstate-<region>`; every project/environment
stores its state under a key prefix (`<project>/<env>/terraform.tfstate`, set in
`backend.<env>.hcl`). This keeps state-bucket management to one hardened bucket per
account instead of one per repo.

## Workflow — generating a new config

1. **Confirm intent**: which resource(s), `project_name`, `environment`, region,
   target account (dev `<SCJ_AWS_ACCOUNT_ID>` vs prod `<AWS_ACCOUNT_ID>`). If unclear, ask.
2. **Assemble the directory**. Always copy `_base/` first, then each chosen resource
   template *into the same directory* (full standalone config — no module indirection):

   ```bash
   SKILL=assets/templates
   DEST=/path/to/new-config            # e.g. CODE/<project>/infra
   mkdir -p "$DEST"
   cp "$SKILL"/_base/. "$DEST"/ -r
   cp "$SKILL"/s3-secure-bucket/*.tf "$DEST"/   # repeat per chosen template
   ```

   Multiple resource templates can co-exist in one directory — their files are
   namespaced (`variables.s3.tf`, `outputs.oidc.tf`, …) so they never collide.
3. **Fill placeholders**: replace `PROJECT_NAME` in `backend.dev.hcl` /
   `backend.prod.hcl`; copy `terraform.tfvars.example` → `terraform.tfvars` and set
   real values. Never commit `terraform.tfvars`.
4. **Header blocks**: update the `Last updated` date on any file you modify.
5. **Verify before declaring done** (this is binding — "done" = validated, not "should work"):

   ```bash
   tofu fmt -recursive
   tofu init -backend=false
   tofu validate
   trivy config .            # expect no HIGH/CRITICAL
   ```
6. **Plan, never blind-apply**: `tofu init -backend-config=backend.dev.hcl` then
   `tofu plan` and review the diff. Confirm the target account first.

See `references/security-checklist.md` for the full pre-apply gate and
`references/customization.md` for how to extend a template (new resource, tighter
IAM, extra Config rules).

## Guardrails — do not regress these

These are the reason the templates exist; if a request conflicts, surface it rather
than silently weakening the config:

- Never set `Resource = "*"` / `Action = "*"` in a real IAM policy.
- Never rely on the path-based `sub` claim alone for GitLab trust — keep the
  `namespace_id` + `project_id` conditions. A reclaimed path is an account-takeover path.
- Never disable the S3 public-access block or the TLS-only bucket policy.
- Never hardcode secrets in `.tf` — use SSM/Secrets Manager data sources.
- Never use local state for anything shared.
- Always confirm dev vs prod account before `apply`; prod = InsideDesk safety checklist.
- **Never** add WAF (`aws_wafv2_*`), AWS Security Hub, or GuardDuty to any template or
  recommendation — they cost too much for this budget. For detective controls use the
  cheap/free options only: AWS Config rules, CloudWatch alarms, CloudTrail.

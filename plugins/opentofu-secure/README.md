# opentofu-secure

A hardened AWS toolkit, packaged as a **Claude plugin**, with two complementary
skills:

- **`opentofu-secure`** (generator) — a skill + template library for generating
  hardened OpenTofu/Terraform AWS config. Security, remote state, tagging, and OIDC
  CI are baked in, so adding a resource is fill-in-the-blanks rather than a
  from-scratch security review.
- **`aws-drift-cost`** (detective) — a report-only loop that audits the SCJ dev
  account for cost anomalies, untagged resources, public-access/encryption drift,
  and idle/orphaned resources. It checks the exact guardrails the generator sets,
  and never modifies a resource.

Built from a scan of ~25 Terraform/OpenTofu projects under `~/CODE` — the templates
cover the resources actually managed most (S3, IAM/OIDC, Route53/ACM, CloudWatch/
AWS Config). WAF, Security Hub, and GuardDuty are intentionally excluded on cost grounds.

The skills live at `skills/opentofu-secure/` and `skills/aws-drift-cost/`.

## Distribution

This plugin lives in the `id-claude-plugin-mono` monorepo and is distributed via the
`insidedesk-tools` marketplace. The marketplace serves `plugins/opentofu-secure/` straight
from source — there is no `.plugin` build step. Edit files in place; ship a change with
the repo-root release helper:

```bash
./release.sh opentofu-secure <new-version> "<changelog message>" [Added|Changed|Fixed|Removed|Security]
```

That bumps `version` in `.claude-plugin/plugin.json`, prepends a changelog entry to
`docs/changelog.md`, commits, and pushes. Teammates pick it up on their next
**Customize → Plugins → Update**.

The `opentofu-secure` skill triggers automatically when you ask to create/scaffold Tofu
config, an S3 bucket, an IAM/GitLab-OIDC role, DNS + ACM, or a monitoring baseline. See
`skills/opentofu-secure/SKILL.md`.

## Use the scaffolder directly

```bash
skills/opentofu-secure/scripts/new-config.sh -d ~/CODE/myproject/infra -p myproject \
  -t s3-secure-bucket -t iam-gitlab-oidc
```

Templates: `s3-secure-bucket`, `iam-gitlab-oidc`, `route53-acm`,
`observability-baseline`, `vpc-network`, `lambda-api`, `dynamodb-table`. `_base` is
always included. `state-bootstrap` is the exception — run it alone to create the
shared state bucket:

```bash
skills/opentofu-secure/scripts/new-config.sh -d ~/CODE/_state-bootstrap -p platform -t state-bootstrap
```

Then:

```bash
cd ~/CODE/myproject/infra
cp terraform.tfvars.example terraform.tfvars   # fill in
tofu fmt -recursive
tofu init -backend=false && tofu validate
trivy config .
tofu init -backend-config=backend.dev.hcl && tofu plan
```

## Layout

```
opentofu-secure/
├── .claude-plugin/plugin.json    # plugin manifest (name, version, author)
├── CLAUDE.md                     # monorepo banner + runtime-identifier resolution
├── docs/changelog.md             # Keep a Changelog
├── README.md
├── skills/opentofu-secure/       # GENERATOR skill
│   ├── SKILL.md                  # skill definition + workflow + guardrails
│   ├── references/
│   │   ├── security-checklist.md # pre-apply gate
│   │   └── customization.md      # how to extend without regressing
│   ├── scripts/
│   │   └── new-config.sh         # assemble _base + chosen templates
│   └── assets/templates/
│       ├── _base/                # versions, providers, backend(+hcl), variables, tags, outputs, CI
│       ├── s3-secure-bucket/     # s3.tf, variables.s3.tf, outputs.s3.tf
│       ├── iam-gitlab-oidc/      # oidc.tf, variables.oidc.tf, outputs.oidc.tf
│       ├── route53-acm/          # dns.tf, variables.dns.tf, outputs.dns.tf
│       ├── observability-baseline/   # monitoring.tf, config.tf, variables.obs.tf, outputs.obs.tf
│       ├── vpc-network/          # vpc.tf, flowlogs.tf, variables.vpc.tf, outputs.vpc.tf
│       ├── lambda-api/           # lambda.tf, apigw.tf, variables.lambda.tf, outputs.lambda.tf
│       ├── dynamodb-table/       # dynamodb.tf, variables.ddb.tf, outputs.ddb.tf
│       └── state-bootstrap/      # standalone: versions/providers/bootstrap/variables/outputs (local backend)
└── skills/aws-drift-cost/        # DETECTIVE skill (report-only)
    ├── SKILL.md                  # loop workflow + output routing + guardrails
    ├── references/checks.md      # thresholds, env, cost model, SSO/scheduling
    └── scripts/
        ├── run-loop.sh           # orchestrate checks -> report JSON + digest
        ├── lib/                  # common.sh, cost_anomalies.py, render_digest.py
        ├── checks/               # cost-anomalies, untagged, public-encryption-drift, idle-orphaned
        └── test/                 # selftest.sh + fixtures (offline verify gate)
```

Resource bodies are namespaced (`s3.tf`, `oidc.tf`, `dns.tf`, …) so multiple
templates combine into one standalone config without file collisions.

## Drift & cost loop

The `aws-drift-cost` skill runs four read-only checks against the SCJ dev account
and routes a dated digest to a Markdown log, email, and chat. It never mutates a
resource. Verify it offline anytime:

```bash
skills/aws-drift-cost/scripts/test/selftest.sh   # lint + mock run + assertions
```

Run it for real (needs an active `aws-sso-scj` session):

```bash
skills/aws-drift-cost/scripts/run-loop.sh \
  --json ~/CODE/_ops/aws-drift/$(date -u +%F).json \
  --digest ~/CODE/_ops/aws-drift/$(date -u +%F).md
```

To run it unattended (no SSO), scaffold a read-only OIDC role with
`skills/opentofu-secure/scripts/new-config.sh -t iam-gitlab-oidc` and wire a GitLab
scheduled pipeline to call `run-loop.sh` — the live, account-specific deployment of
that config is not part of this plugin (it's generated per-account, not shippable
source).

## What "secure" means here

- S3 native-lock remote state; never local state for shared infra.
- Least-privilege IAM; GitLab trust policies pinned to stable `namespace_id` +
  `project_id` (a reclaimed path is an account-takeover vector).
- KMS encryption + rotation; S3 public access fully blocked; TLS-only policies.
- Mandatory `Project/Environment/Owner/ManagedBy` tagging.
- OIDC-only CI (no static keys) with `validate → plan → apply` and a Trivy scan.

## Validation status

All four templates, combined into a single config via `new-config.sh` (27 resource
types), pass against **OpenTofu 1.12.3**:

- `tofu fmt -check -recursive` — clean
- `tofu init -backend=false` — provider `hashicorp/aws ~> 5.0` resolved
- `tofu validate` — **Success! The configuration is valid**
- `trivy config . --severity HIGH,CRITICAL --exit-code 1` (Trivy 0.71.2) — **0 findings, gate passes**

The only remaining Trivy finding is LOW (S3 server access logging), which is opt-in
via `log_target_bucket` and below the CI gate. The same `trivy config` scan runs in
the bundled `.gitlab-ci.yml` on every merge request.

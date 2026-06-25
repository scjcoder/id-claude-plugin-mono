---
name: aws-drift-cost
description: >
  Run Sean's report-only AWS drift & cost loop against the SCJ dev account
  (resolved from config/scj.local.json, placeholder <SCJ_AWS_ACCOUNT_ID>).
  AUTOMATICALLY trigger this skill — without waiting to be asked
  — whenever the user wants to: check for AWS cost spikes or anomalies, find
  untagged resources, detect public-access or encryption drift (S3 public-access
  blocks, unencrypted volumes), find idle/orphaned resources (unattached EIPs,
  detached EBS volumes, idle NAT gateways), run an "AWS drift check", a "cost
  check", an "AWS audit", or a "daily AWS report". Detective counterpart to the
  opentofu-secure generator: it audits the exact guardrails those templates
  enforce. Report-only — it never modifies a single AWS resource.
---

# Skill: aws-drift-cost

A report-only agentic loop that audits the SCJ dev account for the four things
that quietly cost money or weaken the security baseline, then routes the findings
to a Markdown log, an email digest, and chat. It is the detective counterpart to
the `opentofu-secure` generator — it checks the guardrails those templates set.

**Report-only by design.** Every check reads; none writes. The scripts never tag,
delete, or remediate. Promotion to auto-remediation is a deliberate future step,
not a default.

## What it checks

| Check | Looks for | AWS source |
|---|---|---|
| `cost-anomalies` | Per-service daily spend exceeding the trailing baseline by both a % and a $ threshold | Cost Explorer (`ce get-cost-and-usage`) |
| `cost-trend` | Per-service last-full-month vs trailing-3-month baseline, plus an excluded-services watchlist (Security Hub/GuardDuty/WAF spend) | Cost Explorer (monthly) |
| `untagged` | Resources missing any mandatory tag (`Project/Environment/Owner/ManagedBy`) | Resource Groups Tagging API |
| `public-encryption-drift` | S3 buckets without a full public-access block (correlated with Route53 — DNS-backed = intentional public site; no DNS = review candidate); unencrypted EBS volumes | `s3api`, `route53`, `ec2 describe-volumes` |
| `idle-orphaned` | Unattached EIPs, detached (`available`) EBS volumes, running NAT gateways | `ec2 describe-addresses/volumes/nat-gateways` |
| `out-of-region` | Any resource outside the home regions (region guardrail — detective, since the mgmt account can't be SCP/region-locked) | Tagging API across all enabled regions |

See `references/checks.md` for thresholds, env overrides, and the cost model.

## Workflow — running the loop

1. **Ensure credentials.** The account is SSO-only. Resolve the profile from
   `config/scj.local.json` (`scj_aws_profile`, e.g. `Administrator-<SCJ_AWS_ACCOUNT_ID>`).
   If `aws sts get-caller-identity --profile <that-profile>` fails, trigger the
   `aws-sso-scj` skill first (`aws sso login --profile <that-profile>`). The loop's
   own preflight exits `2` with this instruction when no session is active.

2. **Run the loop**, writing both the report JSON and a Markdown digest:

   ```bash
   SKILL=skills/aws-drift-cost
   STAMP=$(date -u +%Y-%m-%d)
   "$SKILL"/scripts/run-loop.sh \
     --json   "$HOME/CODE/_ops/aws-drift/$STAMP.json" \
     --digest "$HOME/CODE/_ops/aws-drift/$STAMP.md"
   ```

3. **Route the digest** (the three outputs Sean chose):
   - **Markdown log** — append the digest to `~/CODE/_ops/aws-drift/findings.md`
     (the rolling paper trail). Each run is its own dated `##` section.
   - **Email digest** — send the digest body to `sean@scj.net` via the
     `scj-workmail` skill. Subject: `AWS drift & cost — <date> — N finding(s)`.
   - **Chat digest** — post a short summary in chat: total findings, top cost
     anomaly, and total potential idle savings, then link the JSON/MD files.

4. **Add judgement on top of the data.** The scripts are deterministic; you supply
   the interpretation — call out anything that looks like a real regression
   (a new public bucket, a cost line that doubled) versus expected noise.

## Offline self-test (no AWS needed)

```bash
skills/aws-drift-cost/scripts/test/selftest.sh
```

Runs `bash -n` + `shellcheck`, then drives the whole loop in mock mode against
fixtures and asserts the report JSON and digest render with the expected finding
counts. Use this after any edit before declaring done.

## Guardrails

- **Never** add a mutating action to a check. This loop is read-only; remediation
  is out of scope until explicitly promoted.
- **Never** widen scope to production (`<AWS_ACCOUNT_ID>`, resolved from
  `config/insidedesk.local.json`) without switching to the `aws-sso-insidedesk`
  skill and applying the prod safety checklist.
- Stdout of every script is reserved for JSON — diagnostics go to stderr. Do not
  print anything else to stdout or you will corrupt the report.
- Keep WAF / Security Hub / GuardDuty out of recommendations (cost grounds) — the
  cheap detective controls (Config, CloudWatch, CloudTrail) are the answer here,
  consistent with `opentofu-secure`.

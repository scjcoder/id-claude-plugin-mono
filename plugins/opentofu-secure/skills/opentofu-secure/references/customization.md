# Customizing a generated config

How to extend a template without regressing its guarantees.

## Adding a resource to an existing config
1. Add a new `*.tf` (or section in `main.tf`) with a header block.
2. Tag it: `tags = { Name = "${local.name_prefix}-<thing>" }` — `local.tags` is already
   applied account-wide via `default_tags`, so only add a `Name`.
3. Reference `local.name_prefix` for naming; `var.environment` for env-conditional
   behavior (e.g. retention, instance size).
4. Keep the file under 300 lines; split by concern if it grows.

## Tightening IAM further
- Replace the example statements in `iam-gitlab-oidc/main.tf`
  (`data.aws_iam_policy_document.permissions`) with the exact actions/resources the
  job needs. Start from zero and add, never start from `*`.
- For high-privilege deploy roles, add `user_access_level` and/or `pipeline_source`
  conditions to the trust policy (supported GitLab.com custom claims). Example: only
  `pipeline_source: push` on a protected ref.
- Set `permissions_boundary_arn` to cap effective permissions.

## S3 variants
- Static website / CloudFront origin: keep the public-access block ON and serve via
  CloudFront + OAC, not bucket-public. Add `aws_s3_bucket_website_configuration` only
  behind CloudFront.
- Cross-account access: prefer a bucket policy with a specific principal ARN and an
  `aws:PrincipalOrgID` condition over broad principals.
- Access logging: point a second bucket's `aws_s3_bucket_logging` at a log bucket.

## Route53 / ACM
- Wildcard cert: put `*.example.com` in `subject_alternative_names`.
- CloudFront alias: pass the distribution's `domain_name` + the fixed CloudFront zone
  id `Z2FDTNDATAQYW2` in `app_records[*].alias_target`.

## Observability baseline
- Add app alarms by duplicating `aws_cloudwatch_metric_alarm.billing` with real
  namespaces/metrics, all pointing at `aws_sns_topic.alerts`.
- Add Config rules by copying an `aws_config_config_rule` block with a new
  `source_identifier` from the AWS managed-rule catalog.
- Multi-account: this template is account-local. For org-wide, delegate AWS Config to
  a security account and aggregate — out of scope here.
- Do NOT add WAF, Security Hub, or GuardDuty here or anywhere — excluded on cost grounds.

## When a request conflicts with a guardrail
Surface the tradeoff explicitly (e.g. "making this bucket public defeats the
public-access block; the safe pattern is CloudFront + OAC"). Offer the secure
alternative first. Only relax a guardrail with an explicit, logged decision.

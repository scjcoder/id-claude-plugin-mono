# Changelog

All notable changes to the opentofu-secure plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.10.0] - 2026-06-24

### Changed
- Migrated from the standalone `opentofu-secure` repo into the `id-claude-plugin-mono`
  monorepo, distributed via the `insidedesk-tools` marketplace. Retired the
  per-plugin `build-plugin.sh`/`opentofu-secure.plugin` archive flow — the
  marketplace now serves `plugins/opentofu-secure/` directly from source, and
  releases ship via the repo-root `release.sh` helper instead. The live
  `infra/aws-drift-cost/` deployment config was not migrated (it is a generated,
  account-specific artifact, not part of the shippable plugin).

### Security
- Replaced the literal SCJ dev AWS account id — previously hardcoded in
  `lib/common.sh`'s defaults, the `_base/backend.dev.hcl` template, doc
  references, and a test fixture — with the `<SCJ_AWS_ACCOUNT_ID>` placeholder,
  resolved at runtime from the gitignored `config/scj.local.json` via the new
  `skills/_shared/config-resolve.sh` helper (mirrors the existing
  `<AWS_ACCOUNT_ID>` / `config/insidedesk.local.json` convention used elsewhere in
  this repo). Also aligned the InsideDesk prod account references to the
  existing `<AWS_ACCOUNT_ID>` placeholder. `new-config.sh` now resolves both
  placeholders automatically when scaffolding `backend.dev.hcl` /
  `backend.prod.hcl`, so generated configs are unaffected. Necessary because this
  monorepo is mirrored to a public GitHub repo, unlike the standalone
  `opentofu-secure` repo.

## [1.9.0] - 2026-06-24

### Changed
- `untagged` check (v1.2.0) now honors an `UNTAGGED_EXCLUDE` allowlist
  (extended-regex matched on the ARN) so structurally un-taggable resources no
  longer inflate the count. Defaults exclude Amplify-managed CloudFormation
  stacks (`:stack/amplify-` — regenerated with a fresh suffix on every deploy,
  untaggable via the tagging API) and AWS-managed billing payment-instruments
  (`arn:aws:payments::`). Overridable at runtime (`UNTAGGED_EXCLUDE=""` to
  re-include); genuinely new untagged resources are still flagged.

### Context
- After the 2026-06-24 tag-drift cleanup of account `<SCJ_AWS_ACCOUNT_ID>` (deleted dead
  2017–2019 CloudFormation/Serverless/Amplify stacks, archived + tagged the
  keepers), untagged findings dropped from 224 to a residual 11 that cannot be
  tagged. This allowlist lets the report floor at zero while still catching new
  drift.

## [1.8.0] - 2026-06-23

### Added
- New `out-of-region` detective check: scans every enabled region except the home
  set (`AWS_DRIFT_REGIONS`) via the tagging API and flags any resource found there,
  tagged with its region. Region calls run in parallel (≈3s across ~15 regions).
- This is the deliberate, safe alternative to a hard region lock: account
  `<SCJ_AWS_ACCOUNT_ID>` is the Org management account (exempt from SCPs) and its SSO
  permission sets are shared with InsideDesk/Audit/Log-archive, so an
  `aws:RequestedRegion` deny would risk locking those out. Detection instead of
  prevention.
- Verified live: 0 out-of-region resources after the us-west-2 cleanup.

## [1.7.0] - 2026-06-23

### Changed
- Expanded the excluded-services watchlist default to the high-cost services that
  should normally be $0 for this account: + Macie, Detective, SageMaker, Redshift,
  OpenSearch, Kafka (MSK), ElastiCache, EMR, Kendra, Neptune, DocumentDB,
  AppStream, WorkSpaces, Managed Grafana/Prometheus, Comprehend, Rekognition,
  Transcribe.
- Deliberately **excluded from the watchlist** services Sean uses or may use —
  Bedrock and Config (in use), and Glue/Athena/Kinesis/QuickSight (pay-per-use he
  may legitimately run); cost spikes on those are covered by `cost-anomalies` /
  `cost-trend` rather than a $0 watchlist. Verified live: no watched service has
  recent spend (0 false positives).

## [1.6.1] - 2026-06-23

### Changed
- Cost watchlist now triggers on **recent** spend (current + last full month)
  instead of the 4-month window total, so a watched service that gets turned off
  self-clears next cycle instead of nagging for months. (Found while confirming
  Security Hub was already disabled — $0/day for 14 days — yet the window-total
  rule would have kept flagging it.)

## [1.6.0] - 2026-06-23

### Added
- New `cost-trend` check with two long-horizon signals from monthly Cost Explorer
  data: (1) per-service deviation of the last full month vs the trailing 3-month
  average (catches gradual creep the daily anomaly check misses); (2) an
  excluded-services watchlist (`AWS_DRIFT_COST_WATCH`, default Security Hub /
  GuardDuty / WAF / Inspector / Shield Advanced) that flags ANY spend, since the
  opentofu policy's intended spend on those is $0.
- `lib/cost_trend.py` transform; reports gain a "Cost trend & watchlist" section
  with the excluded-services block highlighted as a leak.
- Verified live on SCJ dev: the watchlist immediately flagged AWS Security Hub
  ($2.61 last month, $26.16 over 4 months) — a service the policy excludes.
- Env: `AWS_DRIFT_TREND_PCT` (40), `AWS_DRIFT_TREND_USD` (10),
  `AWS_DRIFT_TREND_MONTHS` (4), `AWS_DRIFT_COST_WATCH`.

## [1.5.0] - 2026-06-23

### Added
- Multi-region scanning. The regional checks (`untagged`, `public-encryption-drift`
  EBS, `idle-orphaned`) now iterate every region in `AWS_DRIFT_REGIONS`
  (default `us-east-1 eu-west-1`) and tag each finding with its `region`; the
  Markdown and HTML reports gained a Region column. Cost Explorer / Route53 / S3
  listing stay global (S3 findings marked `region: global`).
- Verified live on SCJ dev: untagged went 211 → 224 by adding eu-west-1 (13
  resources the single-region scan was missing).

## [1.4.0] - 2026-06-23

### Added
- `scripts/lib/render_html.py`: a styled, email-safe HTML report (inline styles,
  zebra tables, review candidates highlighted in amber, summary chips). `run-loop.sh`
  gains `--html`. The Markdown digest remains the permanent record; HTML is the
  notification format.
- Notifications now use HTML: email sends the HTML body (with a plain-text
  fallback), and Telegram attaches `aws-drift-cost.html` alongside the summary
  message. `AWS_DRIFT_HTML_MAX_ROWS` (default 50) caps rows per table for email
  readability.
- CI publishes `report.html` as an artifact in addition to the JSON and Markdown.

### Changed
- `notify.sh` takes `--html` instead of `--digest`; the text summary is still
  derived from the report JSON.

## [1.3.0] - 2026-06-23

### Added
- `scripts/notify.sh`: channel-agnostic delivery of the digest to personal
  channels — Telegram (summary message + the digest attached as a document) and
  email via SES — selected by environment. Best-effort: a failing channel warns
  but never fails the report job. Wired into `.gitlab-ci.yml` after the loop.
- OIDC role: scoped `ses:SendEmail` for notification delivery, restricted to the
  already-verified `scj.net` identity in eu-west-1 (managed by aws-email-wizard).
  No new SES identity or DNS records are created — the role reuses existing infra.

### Notes
- Email sends from the eu-west-1 `scj.net` SES identity; the loop itself stays in
  us-east-1. `notify.sh` uses `SES_REGION` (default eu-west-1) independently.

## [1.2.0] - 2026-06-23

### Added
- `public-encryption-drift` now correlates each S3 public-access-block finding with
  Route53. A bucket whose name matches a DNS record, or that a record's alias/CNAME
  target references, is flagged `dns_backed` (intentional public site, listed for
  info). Buckets with **no** matching DNS record are surfaced first as the review
  queue. Verified live on SCJ dev: 66 open-PAB buckets split into 12 DNS-backed
  (auto.scj.net, code.scj.net, …) and 54 review candidates.
- The digest's drift section now leads with "Review — no DNS record" and lists
  "DNS-backed S3" separately.
- OIDC monitor role gains `route53:ListHostedZones` + `route53:ListResourceRecordSets`
  (and drops the now-unused `s3:GetEncryptionConfiguration`).

### Changed
- `public-encryption-drift` (perf): the per-bucket public-access-block calls fan out
  with `xargs -P` (`AWS_DRIFT_S3_PARALLELISM`, default 12); the slow, near-always
  clean per-bucket `get-bucket-encryption` call was dropped (SSE-S3 is account-wide).
  Verified: 119 buckets audited in ~13s vs a prior multi-minute timeout.

## [1.1.0] - 2026-06-22

### Added
- New `aws-drift-cost` skill: a report-only agentic loop that audits the SCJ dev
  account (`<SCJ_AWS_ACCOUNT_ID>`) for the four things that quietly cost money or weaken the
  security baseline. The detective counterpart to the `opentofu-secure` generator —
  it checks the exact guardrails those templates enforce. The plugin now ships two
  skills.
- Four checks, all read-only: `cost-anomalies` (Cost Explorer daily spend per
  service vs a trailing baseline, gated on both a % and a $ threshold), `untagged`
  (resources missing any mandatory `Project/Environment/Owner/ManagedBy` tag via
  the Resource Groups Tagging API), `public-encryption-drift` (S3 buckets without a
  full public-access block or default encryption, and unencrypted EBS volumes), and
  `idle-orphaned` (unattached EIPs, detached EBS volumes, running NAT gateways, with
  rough monthly-cost estimates).
- `run-loop.sh` orchestrator assembles one report JSON and renders a dated Markdown
  digest (`lib/render_digest.py`) for routing to a findings log, an email digest,
  and chat. `lib/common.sh` centralizes config, an AWS-or-mock JSON fetch, an SSO
  credential preflight, and the check-result emitter. `lib/cost_anomalies.py` is the
  isolated, testable cost transform.
- Offline verification gate `scripts/test/selftest.sh`: lints every script
  (`bash -n` + `shellcheck`), then drives the full loop in mock mode against
  fixtures and asserts the report JSON and digest match expected finding counts
  (7 across the four checks; ~$44.00/mo idle savings).
- `references/checks.md`: thresholds, env overrides, the cost model, the SSO vs.
  unattended-scheduling tradeoff, and the multi-region extension note.

### Notes
- Report-only by design: no check ever modifies an AWS resource. Promotion to
  auto-remediation is a deliberate future step, gated on the verify step.
- Consistent with the existing cost stance — detective controls use Cost Explorer +
  Tagging API + describe calls only; no WAF/Security Hub/GuardDuty.

## [1.0.0] - 2026-06-22

### Added
- Initial release. Packages the `opentofu-secure` skill: a generator that scaffolds
  hardened OpenTofu/Terraform AWS configuration from security-baked templates.
- `_base` scaffold: versions (>=1.10), AWS provider ~>5.0 + random, S3 native-lock
  backend (`use_lockfile`, dev/prod `.hcl`), mandatory `default_tags`, validated
  variables, outputs, `.gitignore`, and an OIDC `.gitlab-ci.yml` (validate → plan →
  apply + Trivy HIGH/CRITICAL gate).
- `s3-secure-bucket`: rotating KMS CMK, versioning, four-flag public-access block,
  BucketOwnerEnforced, TLS-only + deny-unencrypted-PUT policy, lifecycle, opt-in
  server access logging.
- `iam-gitlab-oidc`: GitLab IdP + CI role with trust policy pinned to stable
  `namespace_id` + `project_id` (not the reclaimable path), `sub`/ref scoping,
  least-privilege inline policy, optional permissions boundary.
- `route53-acm`: DNS-validated ACM certificate in us-east-1 (CloudFront-ready),
  automated validation records, alias/standard app records.
- `observability-baseline`: CMK-encrypted CloudWatch logs + SNS alerts, billing
  alarm, AWS Config recorder + baseline managed rules. No Security Hub/GuardDuty.
- `vpc-network`: VPC + public/private subnets across AZs, IGW, optional NAT,
  default SG locked to deny-all, no auto public IPs, VPC flow logs to a
  CMK-encrypted log group.
- `lambda-api`: Lambda + API Gateway v2 HTTP API (no WAF), least-privilege exec
  role, CMK-encrypted env + logs, stage access logging + throttling. Runtime
  defaults to the latest Node.js LTS on Lambda (`nodejs24.x`, bundles AWS SDK v3).
- `dynamodb-table`: CMK encryption, point-in-time recovery, deletion protection,
  on-demand billing, optional TTL.
- `state-bootstrap`: creates the shared remote-state S3 bucket (one
  `<account>-tfstate-<region>` per account, per-project state separated by key
  prefix). Standalone with a LOCAL backend.
- `scripts/new-config.sh`: assembles `_base` + chosen templates into a standalone
  config; resource bodies are namespaced so templates combine without collisions.
- `references/`: pre-apply security checklist + customization guide.
- `build-plugin.sh`: version-discipline build (adapted from the InsideDesk plugin
  scaffolding) — packs all skill file types, enforces a changelog entry, runs a zip
  integrity check, optional Slack release via `SLACK_NOTIFY=1`.

### Security
- All templates verified on OpenTofu 1.12.3: `tofu fmt`/`validate` clean and the
  Trivy `config` HIGH/CRITICAL gate passes with zero findings (individually and
  fully combined).
- WAF, AWS Security Hub, and GuardDuty are intentionally excluded across every
  template on cost grounds; detective controls use AWS Config + CloudWatch +
  CloudTrail only.

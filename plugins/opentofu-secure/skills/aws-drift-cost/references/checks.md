# aws-drift-cost — checks, thresholds, and operating model

Report-only loop for the SCJ dev account (`<SCJ_AWS_ACCOUNT_ID>`, resolved from
`config/scj.local.json`). Every value below is an environment override with a
sane default; the loop runs with zero config once `config/scj.local.json` exists.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `AWS_DRIFT_PROFILE` | `scj_aws_profile` from config (e.g. `Administrator-<SCJ_AWS_ACCOUNT_ID>`) | AWS CLI profile (SSO) |
| `AWS_DRIFT_ACCOUNT` | `scj_aws_account_id` from config | Account ID stamped into findings |
| `AWS_DRIFT_REGION` | `us-east-1` | Region for regional checks |
| `AWS_DRIFT_REQUIRED_TAGS` | `Project Environment Owner ManagedBy` | Mandatory tag keys |
| `AWS_DRIFT_COST_PCT` | `50` | Cost anomaly: min % increase vs baseline |
| `AWS_DRIFT_COST_USD` | `5` | Cost anomaly: min absolute USD increase |
| `AWS_DRIFT_COST_WINDOW` | `8` | Days of Cost Explorer history (last day vs prior) |
| `AWS_DRIFT_S3_PARALLELISM` | `12` | Concurrent per-bucket public-access-block calls |
| `AWS_DRIFT_REGIONS` | `us-east-1 eu-west-1` | Regions the regional checks iterate |
| `AWS_DRIFT_TREND_PCT` | `40` | Cost trend: min % above the 3-month baseline |
| `AWS_DRIFT_TREND_USD` | `10` | Cost trend: min absolute USD above baseline |
| `AWS_DRIFT_TREND_MONTHS` | `4` | Months of monthly CE history (3 baseline + current) |
| `AWS_DRIFT_COST_WATCH` | Security Hub/GuardDuty/WAF/Inspector/Shield + Macie/Detective/SageMaker/Redshift/OpenSearch/Kafka/ElastiCache/EMR/Kendra/Neptune/DocumentDB/AppStream/WorkSpaces/Grafana/Prometheus/Comprehend/Rekognition/Transcribe | Excluded-service substrings flagged on recent spend. Deliberately excludes services Sean uses or may use (Bedrock, Config, Glue, Athena, Kinesis, QuickSight) — cost spikes on those are covered by `cost-anomalies`/`cost-trend` instead. |
| `AWS_DRIFT_EIP_USD` | `3.60` | Assumed monthly cost of an unattached EIP |
| `AWS_DRIFT_NAT_USD` | `32.40` | Assumed monthly cost of a NAT gateway |
| `AWS_DRIFT_EBS_GB_USD` | `0.08` | Assumed gp3 per-GB-month rate |
| `AWS_DRIFT_MOCK` / `AWS_DRIFT_MOCK_DIR` | `0` / — | Offline fixture mode |

## The four checks

### cost-anomalies
Pulls daily `UnblendedCost` grouped by service over the window. For each service
it compares the **last day** against the **average of the prior days**, and flags
the service only when the increase clears **both** thresholds (% and USD) — so a
service jumping from $0.10 to $0.40 (300%) is ignored on the dollar gate, and a
large-but-flat bill is ignored on the percent gate. Findings are sorted by dollar
delta. Tune sensitivity with `AWS_DRIFT_COST_PCT` / `AWS_DRIFT_COST_USD`.

### cost-trend
Two long-horizon signals from monthly Cost Explorer data (global, no region loop):
(1) per-service deviation of the **last full month** vs the **trailing 3-month
average** — flags services that stepped up (gradual creep the daily anomaly check
misses); (2) an **excluded-services watchlist** — any spend on services the
opentofu policy excludes (Security Hub, GuardDuty, WAF, Inspector, Shield Advanced)
is flagged regardless of amount, since the intended spend is $0. Tune via
`AWS_DRIFT_TREND_PCT/USD` and `AWS_DRIFT_COST_WATCH`.

### out-of-region
A detective region guardrail: scans **every enabled region except the home set**
(`AWS_DRIFT_REGIONS`) via the Resource Groups Tagging API and flags any resource it
finds, tagged with its region. This is the safe substitute for a hard region lock —
account `<SCJ_AWS_ACCOUNT_ID>` is the Org **management account** (exempt from SCPs) and its
SSO permission sets are shared with other accounts, so a hard `aws:RequestedRegion`
deny would risk locking out InsideDesk/Audit/Log-archive. Report-only: it tells you
when something lands in a stray region so you can remove it. Runs the regional
tagging calls in parallel (seconds even across ~15 regions).

### untagged
Lists every resource the Resource Groups Tagging API can see and reports those
missing one or more mandatory tag keys, with the specific keys absent. This is the
detective half of the `default_tags` block the opentofu-secure `_base` enforces.

### public-encryption-drift
For each S3 bucket: confirms all four public-access-block flags are `true`. The
per-bucket calls are fanned out with `xargs -P` (`AWS_DRIFT_S3_PARALLELISM`) so the
check finishes in seconds even on accounts with 100+ buckets. Per-bucket
`get-bucket-encryption` is intentionally **not** called — SSE-S3 default encryption
is on account-wide, making it slow (cross-region redirects) and almost always
clean. For EBS: flags any volume with `Encrypted=false`.

**Route53 correlation.** A bucket with an open public-access block is often a public
website *on purpose*. Each S3 finding is annotated `dns_backed` by matching it
against every Route53 record: either the record name equals the bucket name (the
FQDN-named-bucket pattern, e.g. `auto.scj.net`) or a record's alias/CNAME target
references the bucket name (CNAME/alias fronting). `dns_backed` buckets are listed
for information; the **review candidates are the buckets with no matching DNS
record** — the digest puts those first. Caveat: a bucket fronted by CloudFront
(record points at the distribution, not the bucket) can show as a review candidate,
so treat the list as a short review queue, not a verdict.

### idle-orphaned
Three common silent cost leaks: Elastic IPs with no `AssociationId`, EBS volumes in
`available` (detached) state, and NAT gateways in `available` state (flagged for
review — confirm still needed). Each finding carries a rough `est_monthly_usd`; the
digest sums them into a "potential idle savings" line.

## Operating model — the agentic loop

`observe → decide → act → verify → record`, where **act is report-only**:

- **observe** — the four checks gather read-only facts.
- **decide** — thresholds turn facts into findings; the agent adds judgement.
- **act** — route the digest to log + email + chat. No AWS mutation.
- **verify** — `scripts/test/selftest.sh` is the gate; CI/`bash -n`/`shellcheck`.
- **record** — append the dated digest to the rolling `findings.md` log.

Promote a check from report-only to auto-remediation only after the verify gate is
trusted, and only for unambiguous actions (e.g. applying a missing `Owner` tag) —
never for public-access or encryption changes.

## Scheduling & the SSO constraint

The account is SSO-only, so a fully unattended 6am run cannot complete an
interactive `aws sso login`. Options, cleanest first:

1. **Run while a session is valid** — trigger the loop during a working session
   (SSO tokens last ~1h; refreshable). Best for report-only today.
2. **Cached-session window** — run shortly after a morning `aws sso login`.
3. **Dedicated read-only IAM role** — generate a least-privilege read role with the
   `opentofu-secure` `iam-gitlab-oidc` template and run the loop from CI via OIDC
   (no static keys). This is the clean unattended path; adopt it when moving the
   loop off the laptop.

## Multi-region

The regional checks (`untagged`, `public-encryption-drift` EBS, `idle-orphaned`)
iterate every region in `AWS_DRIFT_REGIONS` (default `us-east-1 eu-west-1`) and tag
each finding with its `region`. Cost Explorer, Route53, and S3 bucket listing are
global and ignore the list (S3 findings are marked `region: global`). Add or remove
regions by overriding `AWS_DRIFT_REGIONS`.

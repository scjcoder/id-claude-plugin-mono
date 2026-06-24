# Security Review — `id-claude-integrations`

_Generated 2026-06-22 03:37 UTC by security-scan v1.0.0 (static code + IaC scan)._

**Overall risk: LOW**

## Severity summary

| Critical | High | Medium | Low | Info |
|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 |

> Coverage note: gitleaks, trivy unavailable in this run; secrets covered by detect-secrets + git-history grep, deps by pip-audit/npm-audit.

## Secrets & credentials

_No findings._

## Infrastructure as Code (checkov)

_No findings._

## Application code (semgrep SAST)

_No findings._

## Dependencies (CVEs)

_No findings._

## Web hardening (CSP / CORS / headers / network)

_No findings._


---

# Remediation Playbook — step-by-step hardening

Apply in order. Each step is independently shippable. Items marked **[verify]**
must be proven working (curl/headers check or `terraform plan`), not assumed.

## 1. Secrets (do first — highest blast radius)

1. For every `CRITICAL`/`HIGH` secret finding above, **rotate the credential now**
   (AWS key, API token, DB password). A secret in git history is compromised even
   after deletion.
2. Remove the value from the working tree; replace with a reference:
   - Terraform: move to `aws_secretsmanager_secret` / SSM Parameter Store, read via
     `data` source. Never `default = "<value>"` in `variables.tf`.
   - Lambda/app: read from env injected at deploy, not committed `.env`.
3. Purge from history if the repo is shared: `git filter-repo --invert-paths --path <file>`
   (or BFG), then force-push and have collaborators re-clone. **[verify]** re-run
   `detect-secrets scan` → 0 results.
4. Add a pre-commit guard: `detect-secrets` hook in `.pre-commit-config.yaml`.

## 2. Content-Security-Policy (CSP)

Goal: no `unsafe-inline`/`unsafe-eval`, explicit allow-list, report-only first.

**Static site on CloudFront** — attach a Response Headers Policy:

```hcl
resource "aws_cloudfront_response_headers_policy" "secure" {
  name = "secure-headers"
  security_headers_config {
    content_security_policy {
      override = true
      content_security_policy = join("; ", [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "connect-src 'self' https://api.yourdomain.com",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "upgrade-insecure-requests",
      ])
    }
    strict_transport_security { override = true; access_control_max_age_sec = 63072000; include_subdomains = true; preload = true }
    content_type_options      { override = true }
    frame_options             { override = true; frame_option = "DENY" }
    referrer_policy           { override = true; referrer_policy = "strict-origin-when-cross-origin" }
  }
}
```

Reference it from the distribution's `default_cache_behavior.response_headers_policy_id`.

**Rollout:** ship as `Content-Security-Policy-Report-Only` first, watch for
violations, then flip to enforcing. Replace any inline `<script>` with external
files or SRI-hashed sources so you can drop `unsafe-inline`. **[verify]**
`curl -sI https://site | grep -i content-security-policy`.

## 3. CORS (lock down wildcards)

For every `CORS_WILDCARD` finding:

1. Replace `Access-Control-Allow-Origin: *` with an explicit origin allow-list.
2. API Gateway (HTTP API):

```hcl
cors_configuration {
  allow_origins     = ["https://app.yourdomain.com"]
  allow_methods     = ["GET", "POST", "OPTIONS"]
  allow_headers     = ["authorization", "content-type"]
  allow_credentials = true        # NEVER combine with "*" origin
  max_age           = 600
}
```

3. Lambda/app returning CORS headers: echo the request `Origin` only if it is in
   your allow-list; otherwise omit the header. Never reflect arbitrary origins.
4. S3+CloudFront: set CORS on the bucket only for the assets that need it; prefer
   serving through CloudFront same-origin. **[verify]** preflight with
   `curl -H "Origin: https://evil.com" -I https://api/...` → no ACAO echoed.

## 4. Transport & network

- Force HTTPS: CloudFront `viewer_protocol_policy = "redirect-to-https"`; ALB
  redirect 80→443; S3 bucket policy denying `aws:SecureTransport = false`.
- Replace every `INSECURE_HTTP` finding's `http://` with `https://`.
- For each `OPEN_NETWORK_OR_ACL` (`0.0.0.0/0`, public-read, disabled
  block-public-access): scope the CIDR to known ranges, set
  `block_public_acls/ignore_public_acls/block_public_policy/restrict_public_buckets = true`,
  and front public content with CloudFront + OAC instead of public S3.

## 5. IaC misconfig (checkov findings)

Work top-down by severity. Common high-value fixes:
- Enable encryption at rest (S3 SSE-KMS, EBS, RDS, DynamoDB) and in transit.
- Turn on access logging (S3, CloudFront, ALB, API Gateway) and CloudTrail.
- Scope IAM to least privilege — replace `Action: "*"`/`Resource: "*"`; prefer
  OIDC role assumption over long-lived keys (you already use GitLab OIDC).
- Enable versioning + MFA-delete on state/asset buckets; lock Terraform state in
  S3 + DynamoDB with encryption.

## 6. Dependencies (CVEs)

- Python: bump pinned versions to the fixed release from each `pip-audit` finding;
  re-run `pip-audit` → clean. **[verify]**
- Node: `npm audit fix`; for breaking advisories, upgrade the direct dependency.
  Avoid `--force` without testing.
- Add a scheduled re-scan (this scanner) so new CVEs surface automatically.

## 7. Application code (semgrep findings)

Triage `HIGH` first: command/SQL injection, SSRF, path traversal, weak crypto,
unvalidated input reaching `eval`/`os.system`/template rendering. Fix the root
cause (parameterize, validate, allow-list) — not the symptom.

## 8. Wire it into CI

Add a CI stage that runs this scanner and fails the pipeline on new `CRITICAL`/
`HIGH` findings (compare against a committed baseline). Keep `SECURITY_REVIEW.md`
under version control as the audit trail.

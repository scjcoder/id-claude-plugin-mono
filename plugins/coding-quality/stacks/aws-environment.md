# AWS Environment Practices

Overlay on `terraform-aws.md`. Enforces operational hygiene for AWS deployments.

## S3 bucket security baseline

**MUST** enable S3 Block Public Access at both account and bucket level.

**MUST** enable default encryption (SSE-S3 or SSE-KMS) on all buckets.

**SHOULD** enable versioning on buckets holding state or important data.

**SHOULD** enforce TLS-only access via a bucket policy:

```hcl
resource "aws_s3_bucket_policy" "enforce_tls" {
  bucket = aws_s3_bucket.example.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnforceTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.example.arn,
          "${aws_s3_bucket.example.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}
```

❌ Public bucket with no encryption
✅ Block Public Access enabled + SSE-KMS + TLS policy

## CloudWatch log retention

**MUST** set an explicit retention on every log group — never "Never expire".

**SHOULD** default to a sane retention (e.g. 30/90/365 days by environment) and centralize it.

```hcl
resource "aws_cloudwatch_log_group" "example" {
  name              = "/aws/lambda/example"
  retention_in_days = 30  # Never leave unset (defaults to Never expire)
}
```

Centralize via a locals map or variable:

```hcl
locals {
  log_retention = {
    dev  = 7
    test = 30
    prod = 365
  }
}
```

❌ Log group with no retention (defaults to Never expire)
✅ Explicit retention_in_days set

## Cost guardrails / FinOps

**SHOULD** run `infracost` in CI on Terraform plans and surface the diff on PRs.

**MUST** tag resources for cost allocation (owner, project, environment).

Cross-link: See the tagging rule in `terraform-aws.md`.

```hcl
resource "aws_instance" "example" {
  tags = {
    Owner     = var.owner
    Project   = var.project_name
    Environment = var.environment
    CostCenter = var.cost_center
  }
}
```

Recommended tags:
- `Owner` — person or team responsible
- `Project` — project name
- `Environment` — dev/test/prod
- `CostCenter` — billing allocation

❌ Untagged resources
✅ Consistent tagging across all resources

## Secrets retrieval + caching

**MUST** use the default credential chain (SSO profile / role), never ad-hoc credential files.

**MUST** fetch Secrets Manager / SSM values once at init and cache (TTL if they rotate); never per request.

**SHOULD** reference AWS Lambda Powertools `parameters` util (Python) as the sanctioned helper.

Cross-link: See `python-aws.md` for credential patterns.

```python
# ❌ Bad: per-request fetch
def get_secret():
    client = boto3.client('secretsmanager')
    return client.get_secret_value(SecretId='my-secret')['SecretString']

# ✅ Good: cache at init with TTL
class SecretCache:
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = ttl_seconds

    def get(self, secret_id):
        if secret_id in self.cache:
            data, timestamp = self.cache[secret_id]
            if time.time() - timestamp < self.ttl:
                return data
        client = boto3.client('secretsmanager')
        secret = client.get_secret_value(SecretId=secret_id)['SecretString']
        self.cache[secret_id] = (secret, time.time())
        return secret
```

For Lambda, use AWS Lambda Powertools:

```python
from aws_lambda_powertools.utilities.parameters import get_secret

# Cached automatically with TTL
secret = get_secret('my-secret')
```

❌ Per-request secret fetches
✅ Init-time caching with TTL or Powertools

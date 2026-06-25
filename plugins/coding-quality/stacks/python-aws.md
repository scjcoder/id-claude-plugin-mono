# Stack Overlay — Python on AWS (boto3)

Layered on top of the [Python](python.md) and [Terraform/AWS](terraform-aws.md) overlays.
Governs how Python code talks to AWS via `boto3`/`botocore`. For Node-based Lambdas see
[AWS Lambda (Node.js)](aws-lambda.md); the same client-reuse principle applies here.

## Client reuse

- **MUST** create `boto3` clients/resources once at module scope and reuse them — never
  inside a function that runs repeatedly (request handlers, loops, Lambda handlers).
  Client construction loads config, resolves credentials, and sets up connection pools;
  recreating it per call wastes time and, in Lambda, repeats on every warm invocation.

```python
❌ def lambda_handler(event, context):
       logs = boto3.client("logs")        # rebuilt every invocation
       ...

✅ logs = boto3.client("logs")            # built once, reused while warm
   def lambda_handler(event, context):
       ...
```

## Region discipline

- **MUST NOT** hardcode `region_name="us-east-1"` (or any region) in client constructors.
  Let the region come from the environment / profile so the same code runs in any region
  and across dev vs prod without edits.
- **SHOULD** centralize client creation behind a small factory or a shared module-level
  `boto3.Session()` rather than scattering `boto3.client(...)` calls.

```python
❌ s3 = boto3.client("s3", region_name="us-east-1")

✅ session = boto3.Session()              # region from AWS_REGION / profile / instance
   s3 = session.client("s3")
```

## Retry & timeout configuration

- **MUST** pass a `botocore.config.Config` with adaptive retries and explicit timeouts to
  every client. Without it a transient throttle or network blip becomes a hard failure.
- **SHOULD** tune `max_attempts` and timeouts to the workload (short for interactive, more
  generous for batch).

```python
from botocore.config import Config

AWS_CFG = Config(
    retries={"max_attempts": 5, "mode": "adaptive"},
    connect_timeout=5,
    read_timeout=30,
)
s3 = boto3.client("s3", config=AWS_CFG)
```

## Pagination

- **MUST** paginate every `list_*` / `describe_*` / `scan` call — single calls return only
  the first page (often capped at 50–1000 items), so un-paginated code silently misses data.
- **SHOULD** use `get_paginator(...)` rather than hand-rolling `NextToken` loops.

```python
❌ groups = logs.describe_log_groups()["logGroups"]      # first page only

✅ groups = []
   for page in logs.get_paginator("describe_log_groups").paginate():
       groups.extend(page.get("logGroups", []))
```

## Error handling

- **MUST** catch `botocore.exceptions.ClientError` (not bare `Exception`) for AWS calls and
  branch on the error code — this complements the core [error-handling](../rules/04-error-handling.md) rules.
- **MUST NOT** swallow AWS errors silently; log the operation, the resource, and the code.
- **SHOULD** treat expected codes deliberately (e.g. `NoSuchKey`, `ResourceNotFoundException`,
  `ThrottlingException`) and re-raise the rest.

```python
from botocore.exceptions import ClientError

try:
    obj = s3.get_object(Bucket=bucket, Key=key)
except ClientError as e:
    code = e.response["Error"]["Code"]
    if code == "NoSuchKey":
        return None
    logger.error("get_object failed for s3://%s/%s: %s", bucket, key, code)
    raise
```

## Secrets & credentials

- **MUST NOT** hardcode credentials or load them from ad-hoc files; rely on the default
  credential chain (SSO profile, role, or instance/task role).
- **SHOULD** fetch Secrets Manager / SSM values once at module init and cache them (with a
  TTL if they rotate) rather than calling on every request.

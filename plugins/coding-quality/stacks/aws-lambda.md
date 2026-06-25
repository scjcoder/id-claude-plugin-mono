# Stack Overlay — AWS Lambda (Node.js)

Layered on top of all core rules and the [Terraform/AWS](terraform-aws.md) overlay.

## Runtime version

- **MUST** target the latest Node.js runtime AWS Lambda offers — currently **`nodejs24.x`**.
- **MAY** downgrade one step to the active LTS (**`nodejs22.x`**) *only* when a required
  dependency does not yet support the latest — and **MUST** record why in the changelog/PR.
- **MUST NOT** deploy to deprecated/EOL runtimes (`nodejs18.x` and earlier).
- **MUST** pin the runtime explicitly in IaC (no implicit default) and keep local Node
  aligned to the runtime major via `.nvmrc`.

```hcl
resource "aws_lambda_function" "claims_sync" {
  runtime = "nodejs24.x"   # latest; drop to nodejs22.x only on dependency conflict
  handler = "index.handler"
  # ...
}
```

## AWS SDK — v3 only

- **MUST** use AWS SDK for JavaScript **v3** (`@aws-sdk/client-*`) exclusively.
- **MUST NOT** add or import SDK v2 (`aws-sdk`) — it reached end-of-support and gets no fixes.
- **MUST** import per-client, not the whole SDK, to keep cold starts and bundle size down.
- **SHOULD NOT** bundle the SDK into the deployment package — the runtime provides v3.
  Pin it as a `devDependency` for local/type parity and reproducible builds instead.

```js
❌ const AWS = require("aws-sdk");                 // v2, EOL
   const s3 = new AWS.S3();

✅ import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
   const s3 = new S3Client({});                    // region from env
```

## Handler design

- **MUST** use `async`/`await` handlers — Node 24 no longer supports callback-style handlers.
- **MUST** validate and narrow the `event` at the top of the handler before use (boundary input — see [security](../rules/03-security.md)).
- **MUST** initialize SDK clients and other reusable resources *outside* the handler so they survive across warm invocations.
- **SHOULD** keep the handler thin: parse → delegate to named functions → return. One responsibility per module, under 300 lines.
- **SHOULD** make handlers idempotent where the trigger can redeliver (SQS, EventBridge, S3).

```js
import { S3Client } from "@aws-sdk/client-s3";
const s3 = new S3Client({});            // reused across warm invocations

export const handler = async (event) => {
  const record = parseEvent(event);     // validate at boundary, fail fast
  return processRecord(s3, record);
};
```

## Config, secrets, observability

- **MUST NOT** hardcode secrets — read from environment, or fetch from Secrets Manager / SSM at init and cache.
- **MUST NOT** log secrets, tokens, or PII; **SHOULD** emit structured JSON logs for CloudWatch.
- **MUST** scope the execution role to least privilege — only the actions/resources the function uses.
- **SHOULD** set an explicit `timeout` and `memory_size` sized to the workload, not the defaults.
- **SHOULD** configure a dead-letter queue or `onFailure` destination for async invocations.

## Dependencies & build

- **MUST** keep `package.json` lean — every dependency ships in the cold-start path.
- **SHOULD** use ES modules (`"type": "module"`) to match modern Node and enable tree-shaking.
- **SHOULD** run the same Node major locally as the deployed runtime when testing.

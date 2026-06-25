# Testing & Verification

"Done" means committed, tested, and verified — not just written. No "it should work".

## Verify, don't assert

- **MUST** run the code before claiming it works — execute the linter, formatter, and test suite.
- **MUST** trace the entire flow end-to-end when debugging; don't guess where it breaks.
- **MUST NOT** declare success on a partial implementation or with failing tests.

## Coverage of risk surface

- **SHOULD** have a test for every public function, method, and API endpoint.
- **MUST** prioritize tests for: error-handling paths, security boundaries, and business-critical calculations.
- **SHOULD** flag untested public interfaces as TODOs with a risk level rather than silently shipping.

## Coverage threshold

- **SHOULD** keep ≥ 90% line coverage on new/changed modules.
- **SHOULD** wire coverage gating into CI so the threshold is enforced, not aspirational.

Cross-link: See `resources/templates/pyproject.toml` for the canonical coverage config (`fail_under = 90`).

## Mocking external dependencies

- **MUST** mock AWS with `moto` in unit tests — no live AWS calls.
- **MUST** mock outbound HTTP with `responses` (or equivalent) — no live network in unit tests.
- **SHOULD** keep tests deterministic by avoiding external dependencies.

```python
# ❌ Bad: live AWS call
def test_s3_upload():
    s3 = boto3.client('s3')
    s3.upload_file(...)

# ✅ Good: moto mock
import boto3
from moto import mock_aws

@mock_aws
def test_s3_upload():
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-bucket')
    s3.upload_file(...)
```

```
TEST COVERAGE GAPS
- process_claim_record() — no test. Touches payment logic. HIGH.
- validate_npi()         — no test. Regulatory boundary.   HIGH.
- format_output()        — no test. Format-only.           LOW.
```

## Test quality

- **SHOULD** follow the project's existing framework and patterns (pytest, jest, go test).
- **SHOULD** keep tests deterministic — no reliance on wall-clock time, network, or ordering.
- **MUST** make a failing test fail for the right reason before you make it pass.

## Post-flight (every change)

1. Formatter passes (`ruff format`, `prettier --write`, `gofmt`).
2. Linter passes (`ruff check`, `eslint`, `golint`).
3. Test suite is green.
4. If anything fails, identify the cause and fix it before reporting complete.

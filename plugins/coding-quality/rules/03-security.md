# Security

Prevent common vulnerabilities before they reach production. Apply with extra care to
auth, payments, data ingestion, and external API boundaries.

## Secrets

- **MUST NOT** hardcode secrets, credentials, API keys, or tokens. Use env vars or a secret manager (AWS Secrets Manager).
- **MUST NOT** commit `.env`, key files, credential dumps, or virtualenv directories. Add them to `.gitignore` first.
- **MUST NOT** log passwords, tokens, or PII.
- **MUST** run a secret scanner (`detect-secrets` or `gitleaks`) in pre-commit and CI.
- **SHOULD** rotate any secret that has ever touched a commit, log, or chat — assume it's burned.

Cross-link: See `resources/templates/.gitignore` and `resources/templates/.pre-commit-config.yaml` for canonical templates.

```javascript
❌ const API_KEY = "sk_live_12345";
✅ const API_KEY = process.env.API_KEY;
```

## Credential storage pattern for plugins/skills

**MUST** use local OS credential storage as primary for rapid accessibility in cloud environments.

**MUST** use AWS Secrets Manager as fallback when local storage is unavailable or for cross-platform consistency.

**SHOULD** prioritize least-friction access: local OS storage (Keyring/Credential Manager) → AWS Secrets Manager.

### macOS (Apple Keyring)

```python
import keyring

# Store credential
keyring.set_password("my-plugin", "api-key", "sk_live_12345")

# Retrieve credential
api_key = keyring.get_password("my-plugin", "api-key")
```

### Windows (Credential Manager)

```python
import keyring

# Store credential
keyring.set_password("my-plugin", "api-key", "sk_live_12345")

# Retrieve credential
api_key = keyring.get_password("my-plugin", "api-key")
```

### Fallback to AWS Secrets Manager

```python
import boto3
import keyring

def get_credential(service_name, credential_name, secret_id=None):
    # Try local OS credential storage first (fast, no SSO required)
    credential = keyring.get_password(service_name, credential_name)
    if credential:
        return credential

    # Fallback to AWS Secrets Manager (requires SSO login)
    if secret_id:
        client = boto3.client('secretsmanager')
        secret = client.get_secret_value(SecretId=secret_id)
        return secret['SecretString']

    raise ValueError(f"Credential not found in local storage or AWS Secrets Manager")

# Usage
api_key = get_credential("my-plugin", "api-key", secret_id="my-plugin/api-key")
```

❌ Hardcoded credentials or AWS-only access (high friction)
✅ Local OS storage primary, AWS Secrets Manager fallback (low friction)

## Input handling

- **MUST** validate and sanitize all external input at the boundary before use.
- **MUST** use parameterized queries — never interpolate user input into SQL.
- **MUST** escape output to prevent XSS in web contexts.

```javascript
❌ db.query(`SELECT * FROM users WHERE id = ${userId}`);
✅ db.query("SELECT * FROM users WHERE id = ?", [userId]);
```

## AuthN / AuthZ

- **MUST** enforce authentication and authorization at every boundary, not just the UI.
- **MUST** apply least privilege — grant the narrowest scope/role that works.
- **SHOULD** pin trust relationships to stable, non-reusable identifiers (see [GitLab CI OIDC](../stacks/gitlab-ci.md)).

## Crypto & randomness

- **MUST** use cryptographically secure RNGs for anything security-sensitive (tokens, salts).
- **MUST NOT** roll custom crypto — use vetted libraries.

## Dependencies

- **SHOULD** check manifests (`requirements.txt`, `package.json`) for outdated/vulnerable deps when in scope.
- **MUST** remove dependencies that aren't used.

## Before shipping

Run a security pass (the `security-review` command) on the diff for anything touching
auth, money, PII, or infrastructure trust policies.

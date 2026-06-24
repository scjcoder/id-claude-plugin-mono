---
name: export-secrets-bundle
description: >
  Export all shared InsideDesk credentials from AWS Secrets Manager into a
  password-encrypted bundle file (.bundle) that can be safely shared with a
  new team member for offline import — no AWS access required on their end.
  Use this skill whenever Sean needs to set up a new team member's machine
  without requiring them to install AWS CLI or configure SSO. Trigger on
  phrases like "create a secrets bundle", "export secrets for [name]",
  "set up [name]'s machine", "generate an install bundle", or "I need to
  onboard someone without AWS access".
---

# Skill: export-secrets-bundle

Fetches all shared InsideDesk credentials from AWS Secrets Manager and writes
them to a single password-encrypted `.bundle` file on Sean's Desktop. Sean
then shares the file (e.g., via Slack DM or AirDrop) and communicates the
passphrase separately (e.g., via a different channel or verbally).

The recipient runs the **import-secrets-bundle** skill to load the credentials
onto their machine — no AWS CLI, no SSO, no Python setup required on their end.

---

## Prerequisites

This skill runs on **Sean's machine** only. Run the **aws-login** skill first.
All commands use `mcp__Desktop_Commander__start_process`, NOT
`mcp__workspace__bash`.

---

## Step 1 — Run aws-login

Invoke the **aws-login** skill silently. If credentials are already valid it
completes immediately.

---

## Step 2 — Ask Sean for a passphrase

Ask Sean in chat:

> "What passphrase should I use to encrypt the bundle? (You'll need to share
> this with your team member separately — e.g., tell them verbally or via a
> different message than the file.) Or I can generate a strong one for you."

If Sean asks you to generate one, create a 4-word passphrase using random
common English words (e.g., "maple-river-desk-cloud") — memorable but
unguessable. Show it to Sean before proceeding.

---

## Step 3 — Run the export script

Run the following Python script via Desktop Commander as a **single
`start_process` call**. Pass the passphrase as `argv[1]`.

```python
import subprocess, json, sys, base64, os, platform
from datetime import datetime

# ── Install cryptography if needed ────────────────────────────────────────────
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    print("Installing cryptography package...")
    subprocess.run([sys.executable, "-m", "pip", "install", "cryptography",
                    "--quiet", "--break-system-packages"], check=True)
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PASSPHRASE = sys.argv[1]
PROFILE    = "Install-<AWS_ACCOUNT_ID>"
REGION     = "us-east-1"
ACCOUNT    = "insidedesk"

# ── Secrets map: (keychain-name, aws-secret-id, json-path) ───────────────────
# Mirrors populate-local-secrets exactly (personal secrets excluded).
SECRETS = [
    ("gitlab-token",             "gitlab-oauth-token",              ["token"]),
    ("netlify-token",            "kb_insidedesk/netlify/auth_token",["NETLIFY_AUTH_TOKEN"]),
    ("slack-webhook-url",        "insidedesk-all",                  ["slack","webhook_url"]),
    ("slack-signing-secret",     "insidedesk-all",                  ["slack","signing_secret"]),
    ("pinecone-api-key",         "insidedesk-all",                  ["mcp","pinecone_api_key"]),
    ("context7-api-key",         "insidedesk-all",                  ["mcp","context7_api_key"]),
    ("turnstile-site-key",       "insidedesk-all",                  ["turnstile","site_key"]),
    ("turnstile-secret-key",     "insidedesk-all",                  ["turnstile","secret_key"]),
    ("hubspot-token",            "insidedesk-all",                  ["hubspot","access_token"]),
    ("hubspot-client-secret",    "insidedesk-all",                  ["hubspot","client_secret"]),
    ("hubspot-app-id",           "insidedesk-all",                  ["hubspot","app_id"]),
    ("zoho-client-id",           "insidedesk-all",                  ["zoho","client_id"]),
    ("zoho-client-secret",       "insidedesk-all",                  ["zoho","client_secret"]),
    ("zoho-refresh-token",       "insidedesk-all",                  ["zoho","refresh_token"]),
    ("apify-api-key",            "communication-tools/credentials", ["apify","api_key"]),
    ("slack-bot-token",          "communication-tools/credentials", ["slack","bot_token"]),
    ("atlassian-api-token",      "communication-tools/credentials", ["atlassian","bitwerx_api_token"]),
    ("insidedesk-422-reports-signer-key-id",
                                 "insidedesk/422-reports/signer",   ["access_key_id"]),
    ("insidedesk-422-reports-signer-secret",
                                 "insidedesk/422-reports/signer",   ["secret_access_key"]),
    ("secup-hubspot-token",      "insidedesk-secup/secrets",        ["hubspot","access_token"]),
    ("secup-hubspot-client-secret",
                                 "insidedesk-secup/secrets",        ["hubspot","client_secret"]),
    ("secup-slack-signing-secret",
                                 "insidedesk-secup/secrets",        ["slack","signing_secret"]),
    ("secup-slack-webhook-url",  "insidedesk-secup/secrets",        ["slack","webhook_url"]),
]

# ── Fetch unique AWS secrets ──────────────────────────────────────────────────
secret_ids = list({s[1] for s in SECRETS})
cache = {}

print(f"Fetching {len(secret_ids)} secrets from AWS...\n")
for secret_id in secret_ids:
    r = subprocess.run([
        "aws", "secretsmanager", "get-secret-value",
        "--secret-id", secret_id,
        "--profile", PROFILE, "--region", REGION,
        "--query", "SecretString", "--output", "text"
    ], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ✗ Could not fetch {secret_id}: {r.stderr.strip()}")
        cache[secret_id] = None
    else:
        try:
            cache[secret_id] = json.loads(r.stdout.strip())
        except json.JSONDecodeError:
            cache[secret_id] = r.stdout.strip()

# ── Resolve each credential value ─────────────────────────────────────────────
def drill(data, path):
    val = data
    for key in path:
        if not isinstance(val, dict) or key not in val:
            return None
        val = val[key]
    return str(val) if val else None

payload = {}
skipped = []
failed  = []

for name, secret_id, path in SECRETS:
    data = cache.get(secret_id)
    if data is None:
        failed.append(name)
        continue
    value = drill(data, path) if isinstance(data, dict) else data
    if not value or value == "None":
        skipped.append(f"{name} (empty in AWS)")
        continue
    payload[name] = value
    print(f"  ✓ {name}")

# ── Encrypt ───────────────────────────────────────────────────────────────────
print("\nEncrypting bundle...")
salt = os.urandom(16)
kdf  = PBKDF2HMAC(
    algorithm  = hashes.SHA256(),
    length     = 32,
    salt       = salt,
    iterations = 480_000,
)
key       = base64.urlsafe_b64encode(kdf.derive(PASSPHRASE.encode()))
fernet    = Fernet(key)
encrypted = fernet.encrypt(json.dumps(payload).encode())

bundle = {
    "version": 1,
    "created": datetime.utcnow().isoformat() + "Z",
    "count":   len(payload),
    "salt":    base64.b64encode(salt).decode(),
    "data":    encrypted.decode(),
}

# ── Save to Desktop ───────────────────────────────────────────────────────────
date_str  = datetime.utcnow().strftime("%Y%m%d")
home      = os.path.expanduser("~")
out_path  = os.path.join(home, "Desktop", f"insidedesk-secrets-{date_str}.bundle")
with open(out_path, "w") as f:
    json.dump(bundle, f, indent=2)

print(f"\n{'='*55}")
print(f"Bundle saved:  {out_path}")
print(f"Secrets:       {len(payload)} stored, {len(skipped)} skipped, {len(failed)} failed")
if skipped: print(f"Skipped:       {skipped}")
if failed:  print(f"Failed:        {failed}")
print(f"\nShare the file and passphrase SEPARATELY.")
print(f"File: {out_path}")
```

Pass the passphrase as the first argument when launching the process. For
example, if Sean chose "maple-river-desk-cloud", the command would be:

```
python3 /path/to/script.py "maple-river-desk-cloud"
```

Or write the script to a temp file first (`/tmp/export_bundle.py`), then run it.

---

## Step 4 — Report to Sean

After the script completes, report:

- ✅ The full file path (e.g., `~/Desktop/insidedesk-secrets-20260610.bundle`)
- The passphrase (if you generated it — remind Sean he needs to share it
  separately from the file)
- How many secrets were bundled and if anything was skipped

Suggest Sean share the file via Slack DM (attach the file) and the passphrase
in a separate Slack message or verbally.

---

## Security notes

- The bundle uses AES-128 (Fernet) with a PBKDF2-derived key (480,000 iterations
  of SHA-256). It's safe to share over Slack as long as the passphrase travels
  separately.
- The bundle file does **not** contain AWS credentials — it contains only the
  resolved token values, just like the local Keychain entries.
- Safe to regenerate any time credentials rotate — just re-run and share the
  new file.

---

## Step 5 — Log the run

After Step 4, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `export-secrets-bundle` |
| `status` | `success` if the bundle file was created · `partial` if some secrets were skipped or failed · `error` if the script failed entirely |
| `summary` | 1–3 sentences: describe the bundle file path, how many secrets were exported, and whether any were skipped or failed. |
| `inputs` | Recipient name (if provided), output file path |
| `outputs` | Bundle file path, count of secrets exported |
| `errors` | Any secrets that failed to fetch or were skipped (empty dict if none) |
| `metadata` | `{"secrets_count": N, "skipped_count": N, "failed_count": N}` |

Call skill-logger even on failure — the log should capture what went wrong.

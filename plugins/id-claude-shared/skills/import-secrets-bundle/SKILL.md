---
name: import-secrets-bundle
description: >
  Import InsideDesk credentials from an encrypted .bundle file into the local
  machine's secure credential store (macOS Keychain or Windows Credential
  Manager). This is the zero-AWS-setup alternative to populate-local-secrets —
  the only inputs needed are the bundle file and the passphrase Sean provides.
  Use this skill whenever a team member needs to set up their local credentials
  from a bundle file. Trigger on phrases like "import the secrets bundle",
  "I have a .bundle file from Sean", "set up my credentials from the file",
  "load the InsideDesk tokens", or "I got sent an insidedesk-secrets file".
  Does NOT require AWS CLI, Python, SSO configuration, or any developer tooling.
---

# Skill: import-secrets-bundle

Decrypts a `.bundle` file created by the **export-secrets-bundle** skill and
writes every credential into the machine's native secure store — macOS Keychain
or Windows Credential Manager. After this runs, the **get-secret** skill works
exactly the same as it would after `populate-local-secrets`.

This skill is designed for non-technical team members. It has no prerequisites
beyond Cowork being installed.

---

## Step 1 — Locate the bundle file

Ask the team member:

> "Where is the bundle file? You can either:
> - Drag it into this chat window to upload it, **or**
> - Tell me the path on your computer (e.g., `~/Desktop/insidedesk-secrets-20260610.bundle`)"

Once you have the location, proceed to Step 2.

---

## Step 2 — Ask for the passphrase

Ask:

> "What's the passphrase Sean gave you for this bundle?"

The passphrase is case-sensitive. Get it exactly as Sean provided.

---

## Step 3 — Read the bundle file

**If the file was uploaded to the chat session:**
Read the file content using the Read tool from the uploads path
(`/Users/.../uploads/<filename>` — the exact path appears when the user uploads).

**If the user gave a local file path:**
Read the file via Desktop Commander:
```
mcp__Desktop_Commander__read_file with the path they provided
```

The bundle file is a JSON file — parse its contents.

---

## Step 4 — Decrypt the bundle in the sandbox

Run this Python script via `mcp__workspace__bash` (NOT Desktop Commander) to
decrypt the bundle and produce a flat JSON dict of `{keychain-name: value}`:

```python
import base64, json, subprocess, sys

# ── Install cryptography if needed ────────────────────────────────────────────
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    subprocess.run(["pip", "install", "cryptography", "--quiet",
                    "--break-system-packages"], check=True)
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

BUNDLE_JSON = sys.argv[1]   # full JSON string of the bundle file
PASSPHRASE  = sys.argv[2]   # passphrase from the user

bundle    = json.loads(BUNDLE_JSON)
salt      = base64.b64decode(bundle["salt"])
kdf       = PBKDF2HMAC(
    algorithm  = hashes.SHA256(),
    length     = 32,
    salt       = salt,
    iterations = 480_000,
)
key       = base64.urlsafe_b64encode(kdf.derive(PASSPHRASE.encode()))
fernet    = Fernet(key)

try:
    decrypted = fernet.decrypt(bundle["data"].encode())
    secrets   = json.loads(decrypted)
    print(json.dumps(secrets))
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
```

Pass the bundle file content (as a string) and the passphrase as arguments.
In practice, write the script to `/tmp/decrypt_bundle.py` and call it:

```bash
python3 /tmp/decrypt_bundle.py '<bundle_json_content>' '<passphrase>'
```

The output is a JSON dict like:
```json
{"hubspot-token": "pat-na-...", "slack-bot-token": "xoxb-...", ...}
```

If you get an error (wrong passphrase, corrupted file), stop and tell the user.
Common mistakes: extra space in passphrase, wrong file, passphrase is
case-sensitive.

---

## Step 5 — Detect the operating system

Run via Desktop Commander:
```python
import platform; print(platform.system())
```
- `Darwin` → macOS (use `security` command)
- `Windows` → Windows (use `cmdkey`)

---

## Step 6 — Write secrets to the credential store

For each key-value pair in the decrypted dict, run the appropriate command via
Desktop Commander. Run them one at a time and track successes and failures.

**macOS (Darwin) — for each secret:**
```bash
security add-generic-password \
  -a "insidedesk" \
  -s "<keychain-name>" \
  -w "<value>" \
  -U
```
The `-U` flag means "update if exists" — safe to re-run.

**Windows — for each secret:**
```cmd
cmdkey /generic:insidedesk/<keychain-name> /user:insidedesk /pass:<value>
```

Track which ones succeed (`returncode == 0`) and which fail.

---

## Step 7 — Verify a spot-check

After all secrets are written, confirm one entry was stored correctly.

**macOS:**
```bash
security find-generic-password -a "insidedesk" -s "hubspot-token" -w
```
Should print the token value (a long string starting with `pat-`).

**Windows:**
```cmd
cmdkey /list:insidedesk/hubspot-token
```
Should show the credential target.

---

## Step 8 — Report results

Report back:
- ✅ How many credentials were written successfully
- ❌ Any that failed (with the error, so Sean can investigate)
- Confirmation that the machine is ready to use Cowork skills

If everything worked, say something like:
> "All [N] credentials are loaded and ready. You're all set — Cowork skills
> like the sync checker, report generator, and ticket tools will work on this
> machine now."

---

## Edge cases

- **Wrong passphrase:** The decrypt step fails with a `cryptography.fernet.InvalidToken`
  error. Ask the user to double-check the passphrase (spaces, capitalisation,
  hyphens all matter).
- **Outdated bundle:** If credentials have rotated since the bundle was created,
  some tokens may be expired. The import will still succeed — Sean just needs
  to re-export a fresh bundle.
- **Re-running:** Fully safe. macOS uses `-U` (upsert) and `cmdkey` overwrites
  matching entries automatically.
- **Missing Desktop Commander:** If Desktop Commander is not connected, the
  `security` / `cmdkey` steps cannot run. Ask the user to make sure the
  Desktop Commander extension is active in Cowork.

---

## Step 9 — Log the run

After Step 8, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `import-secrets-bundle` |
| `status` | `success` if all secrets were written · `partial` if some failed · `error` if decryption failed or the skill could not complete |
| `summary` | 1–3 sentences: describe how many credentials were imported, which OS was targeted, and any failures encountered. |
| `inputs` | Bundle file path |
| `outputs` | Count of secrets successfully imported |
| `errors` | Any secrets that failed to write to the credential store (empty dict if none) |
| `metadata` | `{"secrets_imported": N, "secrets_failed": N, "os": "macOS" or "Windows"}` |

Call skill-logger even on failure — the log should capture what went wrong.

---
name: get-secret
description: >
  Retrieve a named secret (API token, credential) from the OS-native secure
  credential store — macOS Keychain or Windows Credential Manager — without
  touching AWS. Call this skill any time another skill needs a token such as
  hubspot-token, slack-bot-token, gitlab-token, or any other InsideDesk
  credential. Pass the secret name and this skill returns the value. Also
  handles one-time setup (storing a secret) when the named secret does not
  yet exist.
---

# Skill: get-secret

Retrieve a named credential from the operating system's secure credential store.
Abstracts away the OS difference so all other skills just call `get-secret`
with a name and receive a token back — no AWS, no SSO, no network round-trip.

---

## Supported secret names

All entries use account `insidedesk` in macOS Keychain.

| Secret name | Kind | What it holds |
|---|---|---|
| `hubspot-token` | HubSpot Private App Access Token | Main HubSpot access token (insidedesk-all) |
| `hubspot-client-secret` | HubSpot App Client Secret | HubSpot app client secret |
| `hubspot-app-id` | HubSpot App ID | HubSpot private app identifier |
| `slack-bot-token` | Slack Bot Token | InsideDesk Slack bot (`xoxb-...`) |
| `slack-webhook-url` | Slack Incoming Webhook URL | Slack incoming webhook for notifications |
| `slack-signing-secret` | Slack Signing Secret | Verifies Slack event payloads |
| `gitlab-token` | GitLab Personal Access Token | GitLab PAT for Terraform backend auth |
| `netlify-token` | Netlify Auth Token | Netlify auth for InsideDesk KB |
| `pinecone-api-key` | Pinecone API Key | Pinecone vector database |
| `context7-api-key` | Context7 API Key | Context7 MCP service |
| `turnstile-site-key` | Cloudflare Turnstile Site Key | Public CAPTCHA site key |
| `turnstile-secret-key` | Cloudflare Turnstile Secret Key | Server-side CAPTCHA verification |
| `zoho-client-id` | Zoho OAuth Client ID | Zoho Assist OAuth app |
| `zoho-client-secret` | Zoho OAuth Client Secret | Zoho Assist OAuth app |
| `zoho-refresh-token` | Zoho OAuth Refresh Token | Zoho Assist refresh token |
| `telegram-bot-token` | Telegram Bot Token | Telegram bot (@seancjohnson) |
| `anthropic-api-key` | Anthropic API Key | Anthropic API key |
| `apify-api-key` | Apify API Key | Apify scraping/automation |
| `atlassian-api-token` | Atlassian API Token | Bitwerx Jira/Atlassian account |
| `422-reports-aws-key-id` | AWS IAM Access Key ID | IAM key for signing 422 report S3 URLs |
| `secup-hubspot-token` | HubSpot Private App Access Token | HubSpot token for insidedesk-secup project (different from main) |
| `secup-hubspot-client-secret` | HubSpot App Client Secret | HubSpot client secret for insidedesk-secup |
| `secup-slack-signing-secret` | Slack Signing Secret | Slack signing secret for insidedesk-secup |
| `secup-slack-webhook-url` | Slack Incoming Webhook URL | Slack webhook for insidedesk-secup |
| `kolla-api-key` | Kolla API Key | Kolla integration API key |
| `cloudflare-account-id` | Cloudflare Account ID | Cloudflare account identifier |
| `cloudflare-api-token` | Cloudflare API Token | Cloudflare API token (R2 + general access) |
| `cloudflare-r2-access-key-id` | Cloudflare R2 Access Key ID | S3-compatible access key for R2 |
| `cloudflare-r2-secret-access-key` | Cloudflare R2 Secret Access Key | S3-compatible secret for R2 |
| `cloudflare-r2-endpoint` | Cloudflare R2 S3 Endpoint URL | `https://<account-id>.r2.cloudflarestorage.com` |

Add new names here as new integrations are added.

---

## Step 1 — Detect the operating system

Run the following via **Desktop Commander** (`mcp__Desktop_Commander__start_process`):

```bash
uname -s 2>/dev/null || echo "Windows"
```

- Output starts with `Darwin` → macOS. Use the **macOS path** below.
- Command not found / output is `Windows` → Windows. Use the **Windows path** below.

⚠️ **All commands in this skill must run via Desktop Commander
(`mcp__Desktop_Commander__start_process`), NOT `mcp__workspace__bash`.**
The sandbox is an isolated Linux VM with no access to the host credential stores.

---

## Step 2a — Retrieve on macOS (Keychain)

```bash
security find-generic-password -a "insidedesk" -s "<secret-name>" -w
```

Replace `<secret-name>` with the requested name (e.g. `hubspot-token`).

- Returns the token value on stdout → done, return the value to the calling skill.
- Returns `security: SecKeychainSearchCopyNext: The specified item could not be found.`
  → secret not yet stored. Go to **Step 3 (Setup)**.

---

## Step 2b — Retrieve on Windows (Credential Manager)

```powershell
$cred = Get-StoredCredential -Target "insidedesk/<secret-name>"
if ($cred) { $cred.GetNetworkCredential().Password } else { "NOT_FOUND" }
```

Replace `<secret-name>` with the requested name (e.g. `hubspot-token`).

- Returns the token value → done, return the value to the calling skill.
- Returns `NOT_FOUND` or throws → secret not yet stored. Go to **Step 3 (Setup)**.
- If `Get-StoredCredential` is not recognized, the `CredentialManager` module is
  not installed. Run: `Install-Module -Name CredentialManager -Scope CurrentUser -Force`
  then retry.

---

## Step 3 — First-time setup (secret not found)

The secret doesn't exist yet on this machine. Ask the user:

> "I don't have `<secret-name>` stored on this machine yet. Please paste the
> value and I'll save it securely to your OS keychain so you won't be asked again."

Once the user provides the value, store it:

### macOS:
```bash
security add-generic-password -a "insidedesk" -s "<secret-name>" -w "<value>"
```

### Windows:
```cmd
cmdkey /generic:insidedesk/<secret-name> /user:insidedesk /pass:<value>
```

After storing, re-run Step 2a or 2b to confirm retrieval works, then return the
value to the calling skill.

---

## Returning the value

Never echo the token in chat output or write it to any file visible to the user.
Pass it in-memory to the calling skill's next step only. If the calling skill is
running a Desktop Commander Python script, inject it as a variable:

```python
token = "<value-from-get-secret>"
```

---

## Edge cases

- **Wrong value stored:** User can correct it by running the store command again —
  `add-generic-password` on macOS overwrites with `-U` flag:
  `security add-generic-password -U -a "insidedesk" -s "<secret-name>" -w "<new-value>"`
  On Windows, re-running `cmdkey /generic:insidedesk/<secret-name> /user:insidedesk /pass:<new-value>` overwrites automatically.
- **Multiple users on same machine:** Each OS user has their own keychain/credential
  store — no cross-user leakage.
- **Secret needed mid-task:** Retrieve it inline, inject into the script, continue.
  Do not surface the token in the conversation.

# Shared: Slack API Setup for InsideDesk Skills

These steps are reused across InsideDesk skills that need to deliver content to
Slack — especially **file uploads** (PDFs, images), since the available Slack MCP
tools in this environment do **not** expose `files.upload` /
`files.completeUploadExternal`. For anything more than a plain text or canvas
message, hit the Slack Web API directly using the bot token from the OS keychain.

---

## A. Retrieve the Slack bot token

Run the **get-secret** skill with secret name `slack-bot-token`.

`get-secret` will:
- Detect whether the current machine is macOS or Windows
- Retrieve the token from the OS-native credential store (Keychain or
  Credential Manager)
- Prompt the user to enter the token on first run, then store it securely

The token format is `xoxb-...`. Treat it as a secret — never echo it in chat
output, never write it into a file inside the project folder, never include it
in a tool response visible to the user.

If a Slack call returns `not_authed` or `invalid_auth`, re-run `get-secret`
to confirm the stored value is correct, then retry.

⚠️ **All Desktop Commander calls that use the token must run via
`mcp__Desktop_Commander__start_process` — NOT `mcp__workspace__bash`.**

---

## B. Sean's Slack user ID

| Property | Value |
|---|---|
| User ID | `<SLACK_USER_SEAN>` |
| Email | `sean.johnson@insidedesk.com` |
| Workspace | `dentalflow.slack.com` (Team ID `T3CR61URH`) |

To DM Sean, open a DM channel first:

```
POST https://slack.com/api/conversations.open
Authorization: Bearer <bot_token>
Content-Type: application/json

{"users": "<SLACK_USER_SEAN>"}
```

Use the returned `channel.id` for all subsequent calls in this DM.

---

## C. Upload a file (PDF, image, etc.) to Slack

The modern flow is three calls: `files.getUploadURLExternal` → PUT the bytes to
the returned upload URL → `files.completeUploadExternal` to publish the file into
the target channel with an optional title and initial comment.

⚠️ **Run this script via Desktop Commander (`mcp__Desktop_Commander__start_process`)
— NOT `mcp__workspace__bash`.** The sandbox cannot reach the host credential store.

```python
import os, json, subprocess, sys, urllib.request, urllib.parse

FILE_PATH       = "/absolute/path/to/file.pdf"
FILENAME        = "Report.pdf"          # filename Slack shows
TITLE           = "Report — <date>"
INITIAL_COMMENT = "Report — <date>"
USER_ID         = "<SLACK_USER_SEAN>"        # Sean's DM target

# Token is injected by get-secret — do not hard-code or echo it
TOKEN = "<value from get-secret slack-bot-token>"

def slack_post(url, token, data, form=False):
    if form:
        body = urllib.parse.urlencode(data).encode()
        ctype = "application/x-www-form-urlencoded"
    else:
        body = json.dumps(data).encode()
        ctype = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {token}", "Content-Type": ctype
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def main():
    size = os.path.getsize(FILE_PATH)

    # 1. Open DM channel
    j = slack_post("https://slack.com/api/conversations.open", TOKEN, {"users": USER_ID})
    if not j.get("ok"): sys.exit(f"open failed: {j}")
    channel = j["channel"]["id"]

    # 2. Get upload URL
    j = slack_post(
        "https://slack.com/api/files.getUploadURLExternal", TOKEN,
        {"filename": FILENAME, "length": str(size)}, form=True
    )
    if not j.get("ok"): sys.exit(f"getUploadURL failed: {j}")
    upload_url, file_id = j["upload_url"], j["file_id"]

    # 3. PUT bytes to the upload URL
    with open(FILE_PATH, "rb") as f: data = f.read()
    req = urllib.request.Request(upload_url, data=data,
                                 headers={"Content-Type": "application/octet-stream"})
    with urllib.request.urlopen(req) as resp:
        if resp.status != 200: sys.exit(f"binary upload failed: {resp.status}")

    # 4. Complete upload — publishes the file into the channel
    j = slack_post("https://slack.com/api/files.completeUploadExternal", TOKEN, {
        "files": [{"id": file_id, "title": TITLE}],
        "channel_id": channel,
        "initial_comment": INITIAL_COMMENT,
    })
    if not j.get("ok"): sys.exit(f"completeUpload failed: {j}")
    print("Slack delivery OK:", j["files"][0]["permalink"])

if __name__ == "__main__":
    main()
```

Verify success by checking that `completeUploadExternal` returns `ok: true` and a
`permalink`. If anything in the chain fails, surface the raw error to the user —
do not retry silently and do not proceed with archive/cleanup steps that are gated
on successful Slack delivery.

---

## D. When you only need a text/markdown DM

If the deliverable is plain text (no file attached), the available Slack MCP
(`mcp__a0fdd3cf-...__slack_send_message`) handles it natively — pass Sean's user
ID `<SLACK_USER_SEAN>` as the `channel_id`. Skip the token retrieval entirely. The
API path above is only required for file uploads.

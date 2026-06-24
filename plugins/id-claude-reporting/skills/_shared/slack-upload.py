#!/usr/bin/env python3
"""
Shared Slack file uploader for InsideDesk skills.
Accepts the bot token as a CLI argument (retrieved by the caller via the get-secret skill).

IMPORTANT: Run this via Desktop Commander (mcp__Desktop_Commander__start_process),
NOT via the sandbox bash tool. The sandbox has no network access to Slack.
Desktop Commander runs directly on the user's Mac.

Usage:
  python3 /path/to/skills/_shared/slack-upload.py \\
      --token "xoxb-..." \\
      --file /absolute/path/to/file.pdf \\
      --filename display-name.pdf \\
      --title "File Title in Slack" \\
      [--comment "Initial comment (defaults to title)"] \\
      [--user <slack-user-id>] \\
      [--channel <dm-channel-id>]

Options:
  --token   Slack bot token (required — retrieve via get-secret skill, name: slack-bot-token)
  --user    Slack user ID to open a DM with (default: resolved from config/insidedesk.local.json)
  --channel Direct channel ID — skip conversations.open if you already know it

On success, prints:  ok=True  permalink=https://...
On failure, exits non-zero with an error message.
"""
import argparse, json, os, sys, urllib.request, urllib.parse

def _id_config():
    """Resolve non-secret runtime identifiers. Lookup order per key: env var, then
    config/insidedesk.local.json (walking up to the repo root), then the macOS Keychain
    (account "insidedesk", service "insidedesk-runtime-config"), then the placeholder.
    The Keychain fallback lets scripts resolve values even when run from an installed
    plugin location outside the monorepo. Real values never live in the public source."""
    cfg, d = {}, os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        p = os.path.join(d, "config", "insidedesk.local.json")
        if os.path.isfile(p):
            try:
                cfg = json.load(open(p))
            except Exception:
                pass
            break
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    if not cfg:
        try:
            import subprocess
            out = subprocess.run(
                ["security", "find-generic-password", "-a", "insidedesk",
                 "-s", "insidedesk-runtime-config", "-w"],
                capture_output=True, text=True)
            if out.returncode == 0 and out.stdout.strip():
                cfg = json.loads(out.stdout.strip())
        except Exception:
            pass
    return lambda key, env, default: os.environ.get(env) or cfg.get(key) or default

_idc = _id_config()

SEAN_USER_ID = _idc("slack_user_sean", "SLACK_USER_SEAN", "<SLACK_USER_SEAN>")


def slack_post(url: str, token: str, data: dict, form: bool = False) -> dict:
    """POST to the Slack Web API. Uses form-encoding or JSON depending on `form`."""
    if form:
        body  = urllib.parse.urlencode(data).encode()
        ctype = "application/x-www-form-urlencoded"
    else:
        body  = json.dumps(data).encode()
        ctype = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type":  ctype,
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a file to a Slack DM")
    parser.add_argument("--token",    required=True, help="Slack bot token (xoxb-...) from get-secret skill")
    parser.add_argument("--file",     required=True, help="Absolute path to the file to upload")
    parser.add_argument("--filename", required=True, help="Filename displayed in Slack")
    parser.add_argument("--title",    required=True, help="File title in Slack")
    parser.add_argument("--comment",  default=None,  help="Initial comment (defaults to --title)")
    parser.add_argument("--user",     default=SEAN_USER_ID, help="Slack user ID to DM")
    parser.add_argument("--channel",  default=None,  help="Channel ID — skips conversations.open")
    args = parser.parse_args()

    comment = args.comment or args.title
    token   = args.token
    size    = os.path.getsize(args.file)

    # 1. Open DM channel (or use the one provided directly)
    if args.channel:
        channel = args.channel
    else:
        j = slack_post("https://slack.com/api/conversations.open", token, {"users": args.user})
        if not j.get("ok"):
            sys.exit(f"conversations.open failed: {j}")
        channel = j["channel"]["id"]

    # 2. Get upload URL + file ID
    j = slack_post(
        "https://slack.com/api/files.getUploadURLExternal", token,
        {"filename": args.filename, "length": str(size)}, form=True,
    )
    if not j.get("ok"):
        sys.exit(f"getUploadURLExternal failed: {j}")
    upload_url, file_id = j["upload_url"], j["file_id"]

    # 3. PUT the raw file bytes to the upload URL
    with open(args.file, "rb") as f:
        data = f.read()
    req = urllib.request.Request(
        upload_url, data=data,
        headers={"Content-Type": "application/octet-stream"},
    )
    req.get_method = lambda: "POST"
    with urllib.request.urlopen(req) as resp:
        if resp.status not in (200, 204):
            sys.exit(f"Binary upload failed: HTTP {resp.status}")

    # 4. Complete upload — publishes the file into the channel
    j = slack_post("https://slack.com/api/files.completeUploadExternal", token, {
        "files":           [{"id": file_id, "title": args.title}],
        "channel_id":      channel,
        "initial_comment": comment,
    })
    if not j.get("ok"):
        sys.exit(f"completeUploadExternal failed: {j}")

    permalink = j["files"][0]["permalink"]
    print(f"ok=True  permalink={permalink}")


if __name__ == "__main__":
    main()

---
name: kolla-health-check
description: >
  Sweep all ACTIVE Kolla linked accounts and report any that are down. Pings
  every active linked account via the Kolla Integration Metadata API and, when
  one or more fail (ping not alive, or auth_state not VALID), DMs Sean on Slack;
  it stays quiet when everything is healthy. Use this skill when Sean asks
  things like "run the Kolla health check", "are all Kolla accounts up", "check
  Kolla connections", "any Kolla accounts down", or when the kolla-health-check
  scheduled task fires. For looking up / managing a single account (list, ping
  one, disable, create invite link), use the kolla-account-management skill
  instead. Out of scope: the Unify data API (owned by the dev team).
---

# Kolla — Linked Account Health Check

Daily-style sweep that pings every **ACTIVE** Kolla linked account and alerts
Sean on Slack **only when something is down**. Healthy runs are silent.

This skill reuses the same management API and auth as
[`kolla-account-management`](../kolla-account-management/SKILL.md)
(`https://api.getkolla.com/connect/v1`, bearer `kolla-api-key`). It adds a Slack
notification when failures are found.

A linked account is flagged **DOWN** if its ping returns `is_alive=false` (or
errors) **or** its `auth_state` is not `VALID`. Accounts in `DISABLED` state are
skipped — they're intentionally off.

---

## How to run (Desktop Commander only)

Everything runs on the **host** via Desktop Commander
(`mcp__Desktop_Commander__start_process`), never the sandbox — both secrets live
in the host keychain.

### Step 1 — Materialize the script

The installed plugin only ships `*.md`, so the authoritative script is the
embedded block in [§ Script source](#script-source). Write it to a temp file:

```bash
mkdir -p /tmp/kolla && cat > /tmp/kolla/kolla_healthcheck.py <<'PYEOF'
# (paste the entire code block from the "Script source" section)
PYEOF
```

(When working from the repo, run
`skills/kolla-health-check/kolla_healthcheck.py` directly instead.)

### Step 2 — Get both secrets

Via the **get-secret** skill (account `insidedesk`):

- `kolla-api-key` → Kolla management API key
- `slack-bot-token` → Slack bot token (`xoxb-...`) for the alert DM

### Step 3 — Run the sweep

Inject both into the environment (never echo them into chat):

```bash
KOLLA_API_KEY="$(security find-generic-password -a insidedesk -s kolla-api-key -w)" \
SLACK_BOT_TOKEN="$(security find-generic-password -a insidedesk -s slack-bot-token -w)" \
  python3 /tmp/kolla/kolla_healthcheck.py
```

The script:
1. Lists all linked accounts (`/connectors/-/linkedaccounts`, auto-paginated)
   and keeps the `ACTIVE` ones.
2. Pings each (`/connectors/{connector}/consumers/{consumer}:ping`).
3. If any are down, opens a DM to Sean (`U068C9UNX6U`) and posts a summary via
   `chat.postMessage`. If all healthy, it prints a line and exits without
   messaging.

### Unattended (scheduled) runs

When triggered by the `kolla-health-check` scheduled task, do exactly the above
without asking for confirmation. If `slack-bot-token` is missing, the run still
completes and prints the result; surface that the alert could not be sent.

---

## Behaviour summary

| Outcome | Action |
|---|---|
| All active accounts alive + auth VALID | Print summary, **no Slack message** |
| One or more down | DM Sean a bulleted list of the down accounts + reasons |
| `KOLLA_API_KEY` missing | Exit non-zero with an error |
| `SLACK_BOT_TOKEN` missing but accounts down | Print the down list; note alert not sent |

Slack alert format (only sent when something is down):

```
🚨 Kolla health check — 1 of 18 active account(s) DOWN

• P4D - Loves Park (eaglesoft/6033) — ping failed
```

---

## Notes

- **Quiet by design.** No news is good news; you only hear from this when a
  connection needs attention.
- **On-prem reality.** Eaglesoft/OpenDental connectors run an agent on the
  customer's server — a failed ping usually means that machine is off, asleep,
  or offline, not a Kolla outage.
- **Secrets** are passed via env only; never written to files or chat.
- **Scope:** account health only. PMS data lives behind the Unify data API,
  owned by the dev team.

---

## Step 4 — Log the run

After Step 3, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `kolla-health-check` |
| `status` | `success` if the sweep completed and all accounts are healthy · `partial` if one or more accounts are down but the sweep finished · `error` if the skill failed entirely (e.g. missing API key) |
| `summary` | 1–3 sentences: total accounts checked, number down, and whether a Slack DM was sent to Sean. |
| `inputs` | (none — sweeps all active Kolla linked accounts automatically) |
| `outputs` | Total accounts checked, failures count, Slack DM sent (yes/no), list of down account names |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{ "total_checked": <n>, "down_count": <n>, "slack_alert_sent": <true|false> }` |

Call skill-logger even on failure — the log should capture what went wrong.

---

## Script source

Authoritative script for the installed skill. Keep `kolla_healthcheck.py` in
this folder in sync with it.

```python
#!/usr/bin/env python3
"""Kolla linked-account health sweep. Stdlib only.

Env: KOLLA_API_KEY (required), SLACK_BOT_TOKEN (optional).
DOWN = ping not alive (or error) OR auth_state != VALID. Alerts only on DOWN.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

KOLLA_BASE = "https://api.getkolla.com/connect/v1"
SLACK_USER_ID = "U068C9UNX6U"  # Sean (dentalflow.slack.com)
TIMEOUT = 30


def _kolla_get(path: str, key: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = KOLLA_BASE + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        if clean:
            url += "?" + urllib.parse.urlencode(clean)
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def list_active(key: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    token: Optional[str] = None
    while True:
        page = _kolla_get("/connectors/-/linkedaccounts", key, {"page_token": token})
        for a in page.get("linked_accounts", []) or []:
            if (a.get("state") or "").upper() == "ACTIVE":
                out.append(a)
        token = page.get("next_page_token")
        if not token:
            break
    return out


def ping(key: str, connector: str, consumer: str) -> bool:
    try:
        r = _kolla_get(f"/connectors/{connector}/consumers/{consumer}:ping", key)
        return bool(r.get("is_alive"))
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
        return False


def _slack_post(url: str, token: str, data: Dict[str, Any], form: bool = False) -> Dict[str, Any]:
    if form:
        body = urllib.parse.urlencode(data).encode()
        ctype = "application/x-www-form-urlencoded"
    else:
        body = json.dumps(data).encode()
        ctype = "application/json; charset=utf-8"
    req = urllib.request.Request(
        url, data=body, headers={"Authorization": f"Bearer {token}", "Content-Type": ctype}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def notify(token: str, down: List[str], checked: int) -> None:
    j = _slack_post("https://slack.com/api/conversations.open", token, {"users": SLACK_USER_ID})
    if not j.get("ok"):
        sys.exit(f"slack conversations.open failed: {j.get('error')}")
    channel = j["channel"]["id"]
    msg = (
        f":rotating_light: *Kolla health check — {len(down)} of {checked} "
        f"active account(s) DOWN*\n\n" + "\n".join(down) +
        "\n\n_Check the Kolla portal / customer connection. "
        "On-prem agents (Eaglesoft/OpenDental) often mean the server is off or offline._"
    )
    j = _slack_post(
        "https://slack.com/api/chat.postMessage", token,
        {"channel": channel, "text": msg, "mrkdwn": True},
    )
    if not j.get("ok"):
        sys.exit(f"slack chat.postMessage failed: {j.get('error')}")


def main() -> int:
    key = os.environ.get("KOLLA_API_KEY")
    if not key:
        print("KOLLA_API_KEY not set", file=sys.stderr)
        return 1
    slack = os.environ.get("SLACK_BOT_TOKEN")

    accounts = list_active(key)
    down: List[str] = []
    for a in accounts:
        parts = (a.get("name") or "").split("/")
        connector = parts[1] if len(parts) > 1 else ""
        consumer = a.get("consumer_id", "")
        title = (a.get("consumer_metadata") or {}).get("title") or consumer
        auth = (a.get("auth_state") or "").upper()
        alive = ping(key, connector, consumer)
        if not alive or auth != "VALID":
            reasons = []
            if not alive:
                reasons.append("ping failed")
            if auth != "VALID":
                reasons.append(f"auth={auth or 'UNKNOWN'}")
            down.append(f"• *{title}* ({connector}/{consumer}) — {', '.join(reasons)}")

    print(f"Checked {len(accounts)} active account(s); {len(down)} down.")
    for d in down:
        print(d)

    if down and slack:
        notify(slack, down, len(accounts))
        print("Slack alert sent to Sean.")
    elif down and not slack:
        print("SLACK_BOT_TOKEN not set — alert NOT sent.", file=sys.stderr)
    else:
        print("All healthy — quiet mode, no alert sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

#!/usr/bin/env python3
"""
Kolla linked-account health sweep.

Lists all ACTIVE Kolla linked accounts, pings each one, and DMs Sean on Slack
**only if** one or more accounts are down (quiet on all-healthy runs). Designed
for an unattended weekday-morning scheduled run.

Stdlib only — no third-party dependencies.

Environment
-----------
  KOLLA_API_KEY    required — Kolla management API key (keychain: kolla-api-key)
  SLACK_BOT_TOKEN  optional — Slack bot token (keychain: slack-bot-token).
                   If absent, results are printed but no Slack alert is sent.

A linked account is considered DOWN if its ping returns is_alive=false (or
errors) OR its auth_state is not VALID.
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

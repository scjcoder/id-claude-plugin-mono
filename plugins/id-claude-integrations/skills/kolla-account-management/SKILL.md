---
name: kolla-account-management
description: >
  Manage Kolla linked customer accounts via the Kolla Integration Metadata
  (connect) API. Use this skill whenever Sean or David need to list linked
  accounts, check whether a linked account is alive (ping), disable a linked
  account, or generate a KollaConnect invite link to onboard a customer's
  practice management software. Trigger on requests like "list Kolla linked
  accounts", "is [customer] still connected in Kolla", "ping the Kolla account
  for [customer]", "disable the Kolla connection for [customer]", "create a
  Kolla invite link for [customer]", or "send [customer] a Kolla connect link".
  This skill covers ONLY account management — the Unify data API
  (appointments, contacts, claims, etc.) is owned by the dev team and is out of
  scope here.
---

# Kolla — Account Management API Reference

## Scope

This skill manages **linked accounts** on Kolla's Integration Metadata API only.
It does **not** read or write PMS data (patients, appointments, claims). That
Unify data API lives at `https://unify.kolla.dev/...` and is built/owned by the
dev team.

Four operations are supported:

| Operation | Purpose |
|---|---|
| List Linked Accounts | See every customer connection and its state/health |
| Ping Linked Account | Confirm a single connection is alive and responding |
| Disable Linked Account | Tear down a connection (e.g. on cancellation) |
| Create Invite Link | Generate a KollaConnect URL to onboard a new customer |

---

## API basics

**Base URL:** `https://api.getkolla.com/connect/v1`

**Auth:** every call sends `Authorization: Bearer <KOLLA_API_KEY>`.

The Kolla docs render this management API's security scheme as OAuth2, but in
practice the same API key you create under **Portal → Settings → API Keys** is
used as a bearer token. If a call returns `401`/`403`, the key is missing,
wrong, or lacks management/connect permissions — re-check the keychain value.

### Key concepts

| Term | Meaning |
|---|---|
| **Connector ID** | Identifies the integration/PMS type (e.g. an OpenDental connector). Use `"-"` as a wildcard to span all connectors. |
| **Consumer ID** | *Your* identifier for the customer being linked — typically the HubSpot company / facility id you already use. You choose this when creating the invite. |
| **Linked Account ID** | Kolla's id for an established connection, found in the `name` field (`connectors/{connector}/linkedaccounts/{linked_account_id}`). |
| **Invite Link** | A secure KollaConnect URL the customer opens (on their server for on-prem PMS) to authorize the connection. |

---

## How to run (Desktop Commander only)

All steps run on the **host** via Desktop Commander
(`mcp__Desktop_Commander__start_process`), never the sandbox — the API key lives
in the host keychain and the sandbox cannot reach it.

### Step 1 — Materialize the client

The build script only packs `*.md` into the installed plugin, so the
authoritative client source is the embedded block in
[§ Client source](#client-source) below. Write it to a temp file once per run:

```bash
mkdir -p /tmp/kolla && cat > /tmp/kolla/kolla_client.py <<'PYEOF'
# (paste the entire code block from the "Client source" section)
PYEOF
```

(When working from the repo at `/Users/sean/CODE/id-claude-integrations`, you can
instead just run `skills/kolla-account-management/kolla_client.py` directly.)

### Step 2 — Get the API key

Retrieve it with the **get-secret** skill (account `insidedesk`, name
`kolla-api-key`):

```bash
security find-generic-password -a insidedesk -s kolla-api-key -w
```

### Step 3 — Run a command

Inject the key into the environment (never echo it into chat):

```bash
KOLLA_API_KEY="$(security find-generic-password -a insidedesk -s kolla-api-key -w)" \
  python3 /tmp/kolla/kolla_client.py list
```

---

## CLI

```bash
# List all linked accounts (across all connectors)
python3 kolla_client.py list

# List for a specific connector, raw JSON
python3 kolla_client.py list -c opendental-12345 --raw

# Ping one linked account
python3 kolla_client.py ping -c opendental-12345 -u 2876

# Disable a linked account (prompts for confirmation; -y to skip)
python3 kolla_client.py disable -c opendental-12345 -l location25 -y

# Create an invite link — connector "-" lets the customer pick from the catalog
python3 kolla_client.py invite -u 2876 -t "Coosa Dental" -e office@coosa.example
```

### As a module

```python
from kolla_client import KollaManagementClient

client = KollaManagementClient()  # reads $KOLLA_API_KEY

for acct in client.iter_linked_accounts():          # auto-paginates
    print(acct["consumer_id"], acct.get("state"))

alive = client.ping_linked_account("opendental-12345", "2876")["is_alive"]

link = client.create_invite_link(consumer_id="2876", title="Coosa Dental")
print(link["uri"])
```

---

## Endpoint reference

### 1. List Linked Accounts
```
GET /connectors/{connector_id}/linkedaccounts
```
- `connector_id` — connector id, or `"-"` for all connectors.
- Optional `page_size`, `page_token` query params; response includes
  `next_page_token` when more pages exist. The client's
  `iter_linked_accounts()` / `all_linked_accounts()` follow this automatically.

Response shape:
```json
{
  "linked_accounts": [
    {
      "name": "connectors/<connector>/linkedaccounts/<id>",
      "consumer_id": "2876",
      "consumer_metadata": { "title": "Coosa Dental", "email": "..." },
      "state": "INITIALIZED",
      "auth_state": "UNAVAILABLE",
      "create_time": "2019-08-24T14:15:22Z",
      "update_time": "2019-08-24T14:15:22Z",
      "expire_time": "2019-08-24T14:15:22Z"
    }
  ],
  "next_page_token": "..."
}
```

### 2. Ping Linked Account
```
GET /connectors/{connector_id}/consumers/{consumer_id}:ping
```
Returns `{ "name": "...", "is_alive": true }`. Use for health checks.

### 3. Disable Linked Account
```
POST /connectors/{connector_id}/linkedaccounts/{linked_account_id}:disable
```
Returns `{}` on success. **Destructive** — confirm the customer/connection
before running. Note the path uses the **linked_account_id** (from the `name`
field), not the consumer_id.

### 4. Create Invite Link
```
POST /connectors/{connector_id}/links
```
Body:
```json
{
  "consumer_id": "2876",
  "consumer_metadata": { "title": "Coosa Dental", "email": "office@coosa.example" }
}
```
- `connector_id = "-"` → customer chooses the connector from the catalog.
- Response includes a `uri` (the link to send) and an `expire_time`.
- For on-prem PMS (OpenDental, Eaglesoft, Dentrix), the customer must open the
  link **on the server / data host machine**, where KollaConnect downloads a
  data-bridge agent to install.

---

## Recipes

**Audit all connections and flag dead ones**
```python
client = KollaManagementClient()
for a in client.iter_linked_accounts():
    cid, conn = a["consumer_id"], a["name"].split("/")[1]
    alive = client.ping_linked_account(conn, cid)["is_alive"]
    if not alive:
        print("DOWN:", a.get("consumer_metadata", {}).get("title", cid))
```

**Onboard a new customer** — create an invite with their HubSpot facility id as
`consumer_id`, send them the returned `uri`. The linked account appears in the
list once they complete KollaConnect.

**Offboard a customer** — find their linked account id from `list`, then
`disable -c <connector> -l <linked_account_id>`.

---

## Notes & edge cases

- **Key never printed.** Pass it via `$KOLLA_API_KEY`; don't write it to files
  or echo it in chat.
- **Wildcard connector.** `"-"` works for `list`; for `ping`/`disable` you need
  the real connector id (get it from the `name` field returned by `list`).
- **Disable is by linked_account_id, ping is by consumer_id** — don't mix them.
- **Auth scheme uncertainty.** If bearer auth unexpectedly fails on the
  management API despite a valid key, check the Kolla Portal for an OAuth2
  client-credentials flow; the docs show that scheme even though the API key
  works as a bearer token in the explorer.
- **Out of scope:** anything under `https://unify.kolla.dev` (Unify Dental/Vet
  data). Hand those requests to the dev team's integration.

---

## Step 4 — Log the run

After completing the requested account management operation, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `kolla-account-management` |
| `status` | `success` if the operation completed without errors · `partial` if the API responded but results were incomplete · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: describe the operation performed (list/ping/disable/invite), the customer or account targeted, and the outcome (e.g. invite link generated, account confirmed alive, account disabled). |
| `inputs` | Action type (list, ping, disable, invite), customer name or consumer ID |
| `outputs` | Operation result (account list, ping alive status, disable confirmation, invite link URI) |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{ "action": "<list|ping|disable|invite>", "consumer_id": "<value or null>" }` |

Call skill-logger even on failure — the log should capture what went wrong.

---

## Client source

This is the authoritative client for the installed skill. Keep
`kolla_client.py` in this folder in sync with it.

```python
#!/usr/bin/env python3
"""Kolla Integration Metadata (account management) client. Stdlib only."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterator, List, Optional

BASE_URL = "https://api.getkolla.com/connect/v1"
DEFAULT_TIMEOUT = 30


class KollaError(Exception):
    def __init__(self, message: str, status: Optional[int] = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


class KollaManagementClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = BASE_URL,
                 timeout: int = DEFAULT_TIMEOUT):
        self.api_key = api_key or os.environ.get("KOLLA_API_KEY")
        if not self.api_key:
            raise KollaError(
                "No API key. Set KOLLA_API_KEY or pass api_key=. "
                "Retrieve it with the get-secret skill (name: kolla-api-key)."
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str,
                 params: Optional[Dict[str, Any]] = None,
                 body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url = f"{url}?{urllib.parse.urlencode(clean)}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8") or "{}"
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            hint = ""
            if exc.code in (401, 403):
                hint = (" — check the kolla-api-key value and that this key has "
                        "management/connect permissions.")
            elif exc.code == 404:
                hint = " — check the connector_id / consumer_id / linked_account_id."
            raise KollaError(f"HTTP {exc.code} {exc.reason} on {method} {path}{hint}",
                             status=exc.code, body=raw) from exc
        except urllib.error.URLError as exc:
            raise KollaError(f"Network error calling {url}: {exc.reason}") from exc

    def list_linked_accounts(self, connector_id: str = "-",
                             page_size: Optional[int] = None,
                             page_token: Optional[str] = None) -> Dict[str, Any]:
        return self._request("GET", f"/connectors/{connector_id}/linkedaccounts",
                             params={"page_size": page_size, "page_token": page_token})

    def iter_linked_accounts(self, connector_id: str = "-",
                             page_size: Optional[int] = None) -> Iterator[Dict[str, Any]]:
        token: Optional[str] = None
        while True:
            page = self.list_linked_accounts(connector_id, page_size, token)
            for acct in page.get("linked_accounts", []) or []:
                yield acct
            token = page.get("next_page_token")
            if not token:
                break

    def all_linked_accounts(self, connector_id: str = "-",
                            page_size: Optional[int] = None) -> List[Dict[str, Any]]:
        return list(self.iter_linked_accounts(connector_id, page_size))

    def find_linked_account(self, consumer_id: str,
                            connector_id: str = "-") -> Optional[Dict[str, Any]]:
        for acct in self.iter_linked_accounts(connector_id):
            if acct.get("consumer_id") == consumer_id:
                return acct
        return None

    def ping_linked_account(self, connector_id: str, consumer_id: str) -> Dict[str, Any]:
        return self._request("GET",
                             f"/connectors/{connector_id}/consumers/{consumer_id}:ping")

    def disable_linked_account(self, connector_id: str,
                               linked_account_id: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/connectors/{connector_id}/linkedaccounts/{linked_account_id}:disable")

    def create_invite_link(self, connector_id: str = "-",
                           consumer_id: Optional[str] = None,
                           title: Optional[str] = None,
                           email: Optional[str] = None) -> Dict[str, Any]:
        metadata: Dict[str, str] = {}
        if title is not None:
            metadata["title"] = title
        if email is not None:
            metadata["email"] = email
        body: Dict[str, Any] = {}
        if consumer_id is not None:
            body["consumer_id"] = consumer_id
        if metadata:
            body["consumer_metadata"] = metadata
        return self._request("POST", f"/connectors/{connector_id}/links", body=body)


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=False))


def _cmd_list(client: KollaManagementClient, args: argparse.Namespace) -> None:
    accounts = client.all_linked_accounts(connector_id=args.connector)
    if args.raw:
        _print(accounts)
        return
    if not accounts:
        print("No linked accounts found.")
        return
    print(f"{len(accounts)} linked account(s):\n")
    for a in accounts:
        meta = a.get("consumer_metadata") or {}
        print(f"  consumer_id : {a.get('consumer_id', '')}")
        print(f"  title       : {meta.get('title', '')}")
        print(f"  email       : {meta.get('email', '')}")
        print(f"  state       : {a.get('state', '')}  auth: {a.get('auth_state', '')}")
        print(f"  name        : {a.get('name', '')}")
        print()


def _cmd_ping(client: KollaManagementClient, args: argparse.Namespace) -> None:
    _print(client.ping_linked_account(args.connector, args.consumer))


def _cmd_disable(client: KollaManagementClient, args: argparse.Namespace) -> None:
    if not args.yes:
        confirm = input(f"Disable linked account {args.linked_account} on connector "
                        f"{args.connector}? [y/N] ")
        if confirm.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return
    client.disable_linked_account(args.connector, args.linked_account)
    print("Disabled.")


def _cmd_invite(client: KollaManagementClient, args: argparse.Namespace) -> None:
    result = client.create_invite_link(connector_id=args.connector,
                                       consumer_id=args.consumer,
                                       title=args.title, email=args.email)
    uri = result.get("uri")
    if uri and not args.raw:
        print(f"Invite link: {uri}")
        if result.get("expire_time"):
            print(f"Expires:     {result['expire_time']}")
    else:
        _print(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Kolla account management (Integration Metadata API).")
    parser.add_argument("--api-key", default=None,
                        help="Kolla API key (defaults to $KOLLA_API_KEY).")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List linked accounts.")
    p_list.add_argument("-c", "--connector", default="-",
                        help='Connector ID (default "-" = all).')
    p_list.add_argument("--raw", action="store_true", help="Print raw JSON.")
    p_list.set_defaults(func=_cmd_list)

    p_ping = sub.add_parser("ping", help="Health-check a linked account.")
    p_ping.add_argument("-c", "--connector", required=True, help="Connector ID.")
    p_ping.add_argument("-u", "--consumer", required=True, help="Consumer ID.")
    p_ping.set_defaults(func=_cmd_ping)

    p_dis = sub.add_parser("disable", help="Disable a linked account.")
    p_dis.add_argument("-c", "--connector", required=True, help="Connector ID.")
    p_dis.add_argument("-l", "--linked-account", required=True, dest="linked_account",
                       help="Linked account ID.")
    p_dis.add_argument("-y", "--yes", action="store_true",
                       help="Skip confirmation prompt.")
    p_dis.set_defaults(func=_cmd_disable)

    p_inv = sub.add_parser("invite", help="Create a KollaConnect invite link.")
    p_inv.add_argument("-c", "--connector", default="-",
                       help='Connector ID (default "-" = customer chooses).')
    p_inv.add_argument("-u", "--consumer", default=None,
                       help="Your customer identifier (e.g. HubSpot facility id).")
    p_inv.add_argument("-t", "--title", default=None, help="Customer name for portal.")
    p_inv.add_argument("-e", "--email", default=None, help="Optional contact email.")
    p_inv.add_argument("--raw", action="store_true", help="Print raw JSON.")
    p_inv.set_defaults(func=_cmd_invite)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = KollaManagementClient(api_key=args.api_key)
        args.func(client, args)
    except KollaError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        if exc.body:
            print(exc.body, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

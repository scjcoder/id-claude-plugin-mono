#!/usr/bin/env python3
"""
Kolla Integration Metadata (account management) client.

Wraps the four Kolla "connect" management endpoints InsideDesk uses to manage
linked customer accounts:

    1. List Linked Accounts    GET  /connectors/{connector_id}/linkedaccounts
    2. Ping Linked Account     GET  /connectors/{connector_id}/consumers/{consumer_id}:ping
    3. Disable Linked Account  POST /connectors/{connector_id}/linkedaccounts/{linked_account_id}:disable
    4. Create Invite Link      POST /connectors/{connector_id}/links

This module deliberately covers ONLY the management API
(https://api.getkolla.com/connect/v1). The Unify data API
(https://unify.kolla.dev/...) is owned by the dev team and is out of scope here.

Auth
----
The Kolla API key is read from the KOLLA_API_KEY environment variable (or passed
to KollaManagementClient(api_key=...)). On an InsideDesk machine, retrieve it via
the `get-secret` skill (keychain entry: account "insidedesk", name "kolla-api-key")
and inject it into the environment before running, e.g.:

    KOLLA_API_KEY="$(security find-generic-password -a insidedesk -s kolla-api-key -w)" \
        python3 kolla_client.py list

Stdlib only — no third-party dependencies.

NOTE: The build script only packs *.md into the .plugin archive, so the
authoritative copy of this code for the installed skill is the embedded block in
SKILL.md. Keep the two in sync when editing.
"""

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
    """Raised when the Kolla API returns an error or auth is missing."""

    def __init__(self, message: str, status: Optional[int] = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


class KollaManagementClient:
    """Thin client for the Kolla Integration Metadata (management) API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key or os.environ.get("KOLLA_API_KEY")
        if not self.api_key:
            raise KollaError(
                "No API key. Set KOLLA_API_KEY or pass api_key=. "
                "Retrieve it with the get-secret skill (name: kolla-api-key)."
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ----------------------------------------------------------------- core

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url = f"{url}?{urllib.parse.urlencode(clean)}"

        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method, headers=self._headers()
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8") or "{}"
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            hint = ""
            if exc.code in (401, 403):
                hint = (
                    " — check the kolla-api-key value and that this key has "
                    "management/connect permissions."
                )
            elif exc.code == 404:
                hint = " — check the connector_id / consumer_id / linked_account_id."
            raise KollaError(
                f"HTTP {exc.code} {exc.reason} on {method} {path}{hint}",
                status=exc.code,
                body=raw,
            ) from exc
        except urllib.error.URLError as exc:
            raise KollaError(f"Network error calling {url}: {exc.reason}") from exc

    # ------------------------------------------------------------ endpoints

    def list_linked_accounts(
        self,
        connector_id: str = "-",
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return one page of linked accounts for a connector.

        Use connector_id="-" to list across all connectors. Response shape:
        {"linked_accounts": [...], "next_page_token": "..."}.
        """
        return self._request(
            "GET",
            f"/connectors/{connector_id}/linkedaccounts",
            params={"page_size": page_size, "page_token": page_token},
        )

    def iter_linked_accounts(
        self, connector_id: str = "-", page_size: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        """Yield every linked account, transparently following pagination."""
        token: Optional[str] = None
        while True:
            page = self.list_linked_accounts(connector_id, page_size, token)
            for acct in page.get("linked_accounts", []) or []:
                yield acct
            token = page.get("next_page_token")
            if not token:
                break

    def all_linked_accounts(
        self, connector_id: str = "-", page_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Collect every linked account into a list."""
        return list(self.iter_linked_accounts(connector_id, page_size))

    def find_linked_account(
        self, consumer_id: str, connector_id: str = "-"
    ) -> Optional[Dict[str, Any]]:
        """Find a single linked account by consumer_id (scans the list)."""
        for acct in self.iter_linked_accounts(connector_id):
            if acct.get("consumer_id") == consumer_id:
                return acct
        return None

    def ping_linked_account(
        self, connector_id: str, consumer_id: str
    ) -> Dict[str, Any]:
        """Health-check a linked account. Returns {"name":..., "is_alive": bool}."""
        return self._request(
            "GET",
            f"/connectors/{connector_id}/consumers/{consumer_id}:ping",
        )

    def disable_linked_account(
        self, connector_id: str, linked_account_id: str
    ) -> Dict[str, Any]:
        """Disable a linked account. Returns {} on success."""
        return self._request(
            "POST",
            f"/connectors/{connector_id}/linkedaccounts/{linked_account_id}:disable",
        )

    def create_invite_link(
        self,
        connector_id: str = "-",
        consumer_id: Optional[str] = None,
        title: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a KollaConnect invite link.

        connector_id="-" lets the customer pick the connector from the catalog.
        consumer_id should be your own customer identifier (e.g. HubSpot company
        / facility id). title/email populate consumer_metadata for portal display.
        Returns an object with a "uri" to send to the customer.
        """
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

        return self._request(
            "POST", f"/connectors/{connector_id}/links", body=body
        )


# --------------------------------------------------------------------- CLI


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
        confirm = input(
            f"Disable linked account {args.linked_account} on connector "
            f"{args.connector}? [y/N] "
        )
        if confirm.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return
    client.disable_linked_account(args.connector, args.linked_account)
    print("Disabled.")


def _cmd_invite(client: KollaManagementClient, args: argparse.Namespace) -> None:
    result = client.create_invite_link(
        connector_id=args.connector,
        consumer_id=args.consumer,
        title=args.title,
        email=args.email,
    )
    uri = result.get("uri")
    if uri and not args.raw:
        print(f"Invite link: {uri}")
        if result.get("expire_time"):
            print(f"Expires:     {result['expire_time']}")
    else:
        _print(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Kolla account management (Integration Metadata API)."
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Kolla API key (defaults to $KOLLA_API_KEY).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List linked accounts.")
    p_list.add_argument(
        "-c", "--connector", default="-", help='Connector ID (default "-" = all).'
    )
    p_list.add_argument("--raw", action="store_true", help="Print raw JSON.")
    p_list.set_defaults(func=_cmd_list)

    p_ping = sub.add_parser("ping", help="Health-check a linked account.")
    p_ping.add_argument("-c", "--connector", required=True, help="Connector ID.")
    p_ping.add_argument("-u", "--consumer", required=True, help="Consumer ID.")
    p_ping.set_defaults(func=_cmd_ping)

    p_dis = sub.add_parser("disable", help="Disable a linked account.")
    p_dis.add_argument("-c", "--connector", required=True, help="Connector ID.")
    p_dis.add_argument(
        "-l", "--linked-account", required=True, dest="linked_account",
        help="Linked account ID.",
    )
    p_dis.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation prompt."
    )
    p_dis.set_defaults(func=_cmd_disable)

    p_inv = sub.add_parser("invite", help="Create a KollaConnect invite link.")
    p_inv.add_argument(
        "-c", "--connector", default="-",
        help='Connector ID (default "-" = customer chooses).',
    )
    p_inv.add_argument(
        "-u", "--consumer", default=None,
        help="Your customer identifier (e.g. HubSpot facility/company id).",
    )
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

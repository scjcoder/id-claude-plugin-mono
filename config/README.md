# `config/` — runtime identifiers

The public source carries **placeholders** (`<AWS_ACCOUNT_ID>`, `<GOLDENEYE_HOST>`,
`<SLACK_USER_SEAN>`, …). Real values live only in `insidedesk.local.json`, which is
**gitignored** and never committed.

## Setup on a machine

```bash
cp config/insidedesk.example.json config/insidedesk.local.json
# edit insidedesk.local.json and fill in the real values
```

## Backup / restore via macOS Keychain

The real values are also stored in the login Keychain (account `insidedesk`,
service `insidedesk-runtime-config`) so they can be restored if the local file is
lost. This is the same secure store the `get-secret` skill uses.

```bash
# Back up the current local config into the Keychain (compact JSON; -U updates if it exists):
security add-generic-password -a insidedesk -s insidedesk-runtime-config \
  -w "$(python3 -c 'import json;print(json.dumps(json.load(open("config/insidedesk.local.json"))))')" -U

# Restore the local config from the Keychain (pretty-printed back to the file):
security find-generic-password -a insidedesk -s insidedesk-runtime-config -w \
  | python3 -m json.tool > config/insidedesk.local.json
```

> Stored as compact single-line JSON so `security -w` returns it as plain text
> (a value containing newlines comes back hex-encoded).

## How it's resolved

- **Scripts** (`*.py`, `release.sh`) load `config/insidedesk.local.json` at runtime
  (walking up from the script to the repo root), with environment-variable overrides
  (`AWS_ACCOUNT_ID`, `SLACK_USER_SEAN`, etc.). If the file is absent they fall back to
  the placeholder and print a hint.
- **Skill instructions** (`SKILL.md`, `CLAUDE.md`) use the placeholder tokens. Each
  plugin's `CLAUDE.md` has a *Runtime identifiers* section telling the agent to resolve
  them from `config/insidedesk.local.json` before acting.

## Not secrets

These are **non-secret** operational identifiers (account number, hostnames, portal id,
Slack ids). Real credentials — API tokens, keys, passwords — are not kept here; they live
in AWS Secrets Manager / macOS Keychain and are fetched via the `get-secret` skill.

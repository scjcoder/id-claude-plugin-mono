# id-claude-shared

Shared authentication and utility skills for InsideDesk Claude plugins.

## Purpose

This repository provides common foundations used across all InsideDesk Claude plugins:

- AWS SSO authentication
- OS-native secret retrieval (macOS Keychain / Windows Credential Manager)
- Encrypted credential bundle export and import for onboarding new team members
- Skill activity logging to a local git repo

Every other InsideDesk plugin depends on this one.

## Skills

| Skill | Description |
|---|---|
| `aws-login` | SSO login to the InsideDesk AWS account (<AWS_ACCOUNT_ID>). Auto-triggers on any credential error across all plugins. |
| `get-secret` | OS-aware credential retrieval from macOS Keychain or Windows Credential Manager. Called by other skills — no AWS or network round-trip needed. |
| `export-secrets-bundle` | Export all shared InsideDesk credentials from AWS Secrets Manager into a password-encrypted `.bundle` file for sharing with a new team member. |
| `import-secrets-bundle` | Import a `.bundle` file into the local credential store. No AWS, CLI tools, or developer setup required on the recipient's machine. |
| `skill-logger` | Append a structured run log to the InsideDesk skill activity log repo (`~/CODE/id-sean-logs`). Writes a human-readable summary + fenced JSON block to a dated markdown file and commits. Self-bootstrapping — creates and `git init`s the repo on first use. |

## Integration with Other Plugins

This shared plugin is a dependency of:

- **id-claude-ops** — client management, install ticketing, sync diagnostics
- **id-claude-reporting** — PMS OOS report, 422 Tax ID report, Ascend activity report, and more
- **id-claude-integrations** — Kolla, DataCo, and other third-party integrations

Each dependent plugin calls `aws-login`, `get-secret`, and `skill-logger` by name — no logic is duplicated.

## Structure

```
id-claude-shared/
├── .claude-plugin/
│   └── plugin.json                # Plugin metadata and version
├── docs/
│   └── changelog.md               # Version history
└── skills/
    ├── _shared/
    │   ├── hubspot-setup.md       # HubSpot API token retrieval reference
    │   └── slack-setup.md         # Slack bot token retrieval reference
    ├── aws-login/                 # SSO login — auto-triggers on credential errors
    ├── export-secrets-bundle/     # Export encrypted bundle for sharing with new team members
    ├── get-secret/                # OS-aware secret retrieval (Keychain / Credential Manager)
    ├── import-secrets-bundle/     # Import bundle on a new machine — no AWS required
    └── skill-logger/              # Append run logs to ~/CODE/id-sean-logs git repo
```

## Installation

This plugin is distributed through the `insidedesk-tools` marketplace — there is no
`.plugin` file to build or install by hand.

1. In Cowork: Customize → Plugins → add the marketplace `gitlab.com/insidedesk/id-claude-plugin-mono`
2. Install `id-claude-shared` from that marketplace
3. Receive updates via "Update" in Customize → Plugins

## Shipping Changes

Releases are handled by the monorepo-root `release.sh` — there is no `.plugin` build step:

```
./release.sh id-claude-shared <version> "<message>" [Added|Changed|Fixed|Removed|Security]
```

It bumps the version in `.claude-plugin/plugin.json`, prepends a changelog entry to
`docs/changelog.md`, commits, and pushes. The team receives the update on their next
plugin update.

See `CLAUDE.md` for the full developer workflow.

## Versioning

Follows semantic versioning. See `docs/changelog.md` for release history.


## Configuration

Non-secret runtime identifiers (AWS account id, hostnames, HubSpot portal id, Slack ids)
are read from `config/insidedesk.local.json` at the monorepo root (gitignored). Source
files use placeholders like `<AWS_ACCOUNT_ID>`; copy `config/insidedesk.example.json` to
`config/insidedesk.local.json` and fill in the real values. Secrets (API tokens/keys) are
never stored here — they come from the macOS Keychain / AWS Secrets Manager via the
`get-secret` skill. See the repo-root `README.md` and `config/README.md`.

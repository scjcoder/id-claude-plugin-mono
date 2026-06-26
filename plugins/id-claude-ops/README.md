# id-claude-ops

A Cowork plugin for InsideDesk client operations workflows. Skills automate HubSpot
ticketing, client offboarding, install coordination, communications, and AWS authentication.

## Skills

| Skill | Description |
|---|---|
| `aws-login` | SSO login to the InsideDesk AWS account. Auto-triggers on credential errors. |
| `chrome-cleanup` | Helper skill to close a Chrome browser tab after use. Gracefully handles missing tabId for non-Chrome skills. |
| `chrome-test` | Test that the Claude in Chrome tool suite is available and functional. Validates browser automation capabilities. |
| `client-comms` | Draft client emails, decision memos, and status updates in Sean's voice. |
| `client-offboarding` | End-to-end cancellation workflow from a HubSpot cancellation ticket URL — full and partial, with Ascend API REMOVE tab output. |
| `client-pms-summary` | Count active locations grouped by PMS type for a client. |
| `hubspot-context-note` | Write or update a structured Claude context note on a HubSpot ticket — called as a final step by other skills. |
| `list-client-locations` | Retrieve and display all active locations for a client as a formatted table with PMS info. |
| `mb2-install-ticket` | Create HubSpot Install Pipeline tickets from Monday Board approval emails, with IT contact resolution and Slack notification. |
| `update-it-contact` | Add or update an IT contact for a location in HubSpot and associate them with a support ticket. |

## Structure

```
id-claude-ops/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata and version
├── docs/
│   └── changelog.md             # Version history
└── skills/
    ├── _shared/                 # Shared HubSpot/Slack helpers
    ├── aws-login/
    ├── chrome-cleanup/          # Helper to close Chrome tabs after use
    ├── chrome-test/             # Test Chrome tool availability
    ├── client-comms/
    ├── client-offboarding/
    ├── client-pms-summary/
    ├── hubspot-context-note/
    ├── list-client-locations/
    ├── mb2-install-ticket/
    └── update-it-contact/
```

## Distribution

This plugin ships through the `insidedesk-tools` marketplace, which serves it
directly from `plugins/id-claude-ops/` in the monorepo. There is no `.plugin` build step.

**Install:** in Cowork, go to Customize → Plugins → add the marketplace
`gitlab.com/insidedesk/id-claude-plugin-mono`, then install `id-claude-ops`.

**Ship a change:** from the monorepo root, run the release helper:

```bash
./release.sh id-claude-ops <new-version> "<changelog message>" [Added|Changed|Fixed|Removed|Security]
```

It bumps the version in `.claude-plugin/plugin.json`, updates `docs/changelog.md`,
commits, and pushes. Teammates receive the update on their next "Update" in
Customize → Plugins.

See `CLAUDE.md` for full developer docs.


## Configuration

Non-secret runtime identifiers (AWS account id, hostnames, HubSpot portal id, Slack ids)
are read from `config/insidedesk.local.json` at the monorepo root (gitignored). Source
files use placeholders like `<AWS_ACCOUNT_ID>`; copy `config/insidedesk.example.json` to
`config/insidedesk.local.json` and fill in the real values. Secrets (API tokens/keys) are
never stored here — they come from the macOS Keychain / AWS Secrets Manager via the
`get-secret` skill. See the repo-root `README.md` and `config/README.md`.

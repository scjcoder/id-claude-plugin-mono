# id-claude-ops

A Cowork plugin for InsideDesk client operations workflows. Skills automate HubSpot
ticketing, client offboarding, install coordination, communications, and AWS authentication.

## Skills

| Skill | Description |
|---|---|
| `aws-login` | SSO login to the InsideDesk AWS account. Auto-triggers on credential errors. |
| `bitwerx-jira-ticket` | Create a Bitwerx DataCo JIRA Service Desk ticket for a Bitwerx-synced location (Dentrix, Dentrix Enterprise, or Eaglesoft). Handles Check Sync, Server Swap, Disable/Reactivate, New Install, and Password Request issue types. |
| `cancellation-ticket` | Create HubSpot CANCELLATIONS custom object records from Monday Board cancellation-mention emails. Reads Gmail for the last 7 days. |
| `check-422-tax-ids` | Check whether a TIN that triggered a GoldenEye 422 "Unexpected tax id" error is already in a facility's approved Expected TaxIds list. |
| `chrome-cleanup` | Helper skill to close a Chrome browser tab after use. Gracefully handles missing tabId for non-Chrome skills. |
| `chrome-test` | Test that the Claude in Chrome tool suite is available and functional. Validates browser automation capabilities. |
| `client-comms` | Draft client emails, decision memos, and status updates in Sean's voice. |
| `client-offboarding` | End-to-end cancellation workflow from a HubSpot cancellation ticket URL — full and partial, with Ascend API REMOVE tab output. |
| `client-pms-summary` | Count active locations grouped by PMS type for a client. |
| `create-422-tickets` | Create HubSpot Install Pipeline tickets from 422 Tax ID Error Report data. One ticket per client, with company/contact/location associations and PDF attachment. |
| `create-kolla-invite` | Generate a Kolla KollaConnect invite link for a new InsideDesk facility and log the result to the HubSpot install ticket. |
| `dataco-health-check` | Check the Bitwerx DataCo public status page for active or unresolved incidents. Returns a structured status block for use by downstream skills. |
| `dataco-sync-status` | Check the Bitwerx DataCo sync stage status (Connectivity, Sync, Staging, Intermediate) for a Dentrix/Eaglesoft facility. |
| `draft-422-client-email` | Draft client-facing emails to Account POCs about 422 Tax ID errors, attaching the PDF report and logging a HubSpot engagement. |
| `full-sync-status` | Get a complete sync status overview for a dental office — GoldenEye snapshots, DataCo pipeline stages, and HubSpot/Gmail ticket history. |
| `goldeneye-tin-normalization` | Normalize a pasted list of TINs (strip non-digits, deduplicate, comma-separated) for entry into GoldenEye's Expected Tax IDs field. |
| `hubspot-context-note` | Write or update a structured Claude context note on a HubSpot ticket — called as a final step by other skills. |
| `hubspot-human-note` | Add a formatted HTML note (key/value data, section tables, or free-text) to a HubSpot ticket's activity feed. |
| `hubspot-ticket-generator` | Create a HubSpot Install Pipeline ticket from a GoldenEye facility URL — extracts location data, resolves company and IT contact, creates and associates the ticket. |
| `insidedesk-facility-entry` | Bulk-enter facility/office records into the InsideDesk Operations Dashboard from a spreadsheet (Excel/CSV). |
| `list-client-locations` | Retrieve and display all active locations for a client as a formatted table with PMS info. |
| `mb2-install-ticket` | Create HubSpot Install Pipeline tickets from Monday Board approval emails, with IT c
ntact resolution and Slack notification. |
| `mb2-monday-to-ge` | Read the MB2 Monday Board "To Be Installed" group via Chrome and create GoldenEye facility records for any office not yet in GoldenEye. |
| `monday-account-update` | Post an update note on a dental office item in the MB2 InsideDesk Install List Monday Board. |
| `office-ticket-history` | Look up recent HubSpot support tickets and Gmail activity for a dental office — used to check for known issues before creating new tickets. |
| `sync-status` | Check whether a dental facility is currently syncing with InsideDesk by looking up its most recent GoldenEye snapshot. |
| `update-it-contact` | Add or update an IT contact for a location in HubSpot and associate them with a support ticket. |

## Structure

```
id-claude-ops/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata and version
├── docs/
│   └── changelog.md             # Version history
└── skills/
    ├── _shared/                   # Shared HubSpot/Slack helpers
    ├── aws-login/
    ├── bitwerx-jira-ticket/
    ├── cancellation-ticket/
    ├── check-422-tax-ids/
    ├── chrome-cleanup/            # Helper to close Chrome tabs after use
    ├── chrome-test/               # Test Chrome tool availability
    ├── client-comms/
    ├── client-offboarding/
    ├── client-pms-summary/
    ├── create-422-tickets/
    ├── create-kolla-invite/
    ├── dataco-health-check/
    ├── dataco-sync-status/
    ├── draft-422-client-email/
    ├── full-sync-status/
    ├── goldeneye-tin-normalization/
    ├── hubspot-context-note/
    ├── hubspot-human-note/
    ├── hubspot-ticket-generator/
    ├── insidedesk-facility-entry/
    ├── list-client-locations/
    ├── mb2-install-ticket/
    ├── mb2-monday-to-ge/
    ├── monday-account-update/
    ├── office-ticket-history/
    ├── sync-status/
    └── update-it-contact/
```

## Distribution

This plugin ships through the `insidedesk-tools` marketplace, which serves it
directly from `plugins/id-claude-ops/` in the monorepo. There is no `.plugin` build step.

**Install:** in Cowork, go to Customize → Plugins → add the marketplace
`https://github.com/scjcoder/id-claude-plugin-mono`, then install `id-claude-ops`.

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

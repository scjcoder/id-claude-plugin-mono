# id-claude-reporting

A Cowork plugin for InsideDesk reporting workflows. Skills automate PMS sync
reporting, Power BI exports, 422 Tax ID audits, Ascend activity reporting,
GoldenEye snapshot audits, full client history reports, and install team
summaries — all delivered to Slack.

Depends on **id-claude-shared** for AWS auth, secret retrieval, and skill logging.

## Skills

| Skill | Description |
|---|---|
| `aws-login` | SSO login to the InsideDesk AWS account. Auto-triggers on credential errors. Delegates to id-claude-shared. |
| `pms-oos-report` | Generates the PMS Out-of-Sync PDF report from a Power BI Excel export. Includes DataCo health check, full-sync-status enrichment per OOS location, and HubSpot context capture. Delivered to Slack DM and archived. Logs run via `skill-logger`. |
| `powerbi-export` | Downloads the PMS Snapshot Monitoring report from Power BI as a date-stamped Excel file. Auto-invoked by `pms-oos-report` if no file is attached. |
| `422-tax-id-report` | Reads the GoldenEye Snapshots page for 422 "Unexpected tax id" errors, filters TINs already approved in GoldenEye config, generates per-client HTML and PDF reports, creates HubSpot Install Pipeline tickets, closes inactive tickets, and writes context notes. Logs run via `skill-logger`. |
| `ascend-activity-report` | Generates the monthly Ascend API activity report. Uses GoldenEye snapshot data as the billing baseline. Produces an Excel data file and PDF summary delivered to Slack DM. |
| `dos-report` | Generates the Date of Service (DOS) Inactivity Report from a Power BI Excel export. Flags locations that are syncing but haven't submitted a claim in 14+ days. PDF delivered to Slack DM and archived. |
| `snapshot-error-report` | Reads the GoldenEye Snapshots page and produces an Excel data table and PDF summary of all 400/422 errors for today, delivered to Slack. |
| `full-historical-client-report` | Generates a complete client history PDF covering all locations, snapshot activity (18 months), cancellation records, HubSpot tickets, key contacts, and Gmail email trail. Works for active, at-risk, and churned clients. Delivered to Slack DM. |
| `install-team-summary` | Weekday morning digest of Gmail and HubSpot Install pipeline activity, delivered as an image to Slack. |
| `morning-brief` | Weekday morning brief for Sean — calendar, unread emails, HubSpot install tickets cross-referenced with GoldenEye sync status and Slack #installs, and action items. Delivered as a self-contained HTML report. |

## Structure

```
id-claude-reporting/
├── .claude-plugin/
│   └── plugin.json                    # Plugin metadata and version
├── docs/
│   └── changelog.md                   # Version history
└── skills/
    ├── _shared/                       # Shared Slack/HubSpot helpers and upload script
    ├── aws-login/                     # Delegates to id-claude-shared
    ├── 422-tax-id-report/             # 422 Tax ID error report + HubSpot tickets
    ├── ascend-activity-report/        # Monthly Ascend API billing report
    ├── dos-report/                    # Date of Service inactivity report
    ├── full-historical-client-report/ # Full client relationship history PDF
    ├── install-team-summary/          # Morning install pipeline digest
    ├── morning-brief/                 # Weekday morning brief (calendar, email, installs, action items)
    ├── pms-oos-report/                # PMS Out-of-Sync report
    ├── powerbi-export/                # Power BI Excel export
    └── snapshot-error-report/         # GoldenEye snapshot error report
```

## Releasing

This plugin lives in the InsideDesk plugin monorepo and is distributed through the
`insidedesk-tools` marketplace, which serves it directly from
`plugins/id-claude-reporting/`. **There is no `.plugin` build step.**

To ship a change, run the monorepo-root release helper:

```bash
./release.sh id-claude-reporting <version> "<message>" [Added|Changed|Fixed|Removed|Security]
```

It bumps the version in `.claude-plugin/plugin.json`, prepends a changelog entry to
`docs/changelog.md`, commits, and pushes. Teammates receive the update on their next
"Update" in Customize → Plugins.

See `CLAUDE.md` for full developer docs.

## Installation

1. Install **id-claude-shared** first (this plugin depends on it)
2. Add the `insidedesk-tools` marketplace: Customize → Plugins → add
   `https://github.com/scjcoder/id-claude-plugin-mono`
3. Install **id-claude-reporting** from that marketplace

## Versioning

Follows semantic versioning. See `docs/changelog.md` for release history.
## Configuration

Non-secret runtime identifiers (AWS account id, hostnames, HubSpot portal id, Slack ids)
are read from `config/insidedesk.local.json` at the monorepo root (gitignored).

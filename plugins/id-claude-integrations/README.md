# id-claude-integrations

A Cowork plugin for InsideDesk third-party integrations. Skills cover Kolla linked-account
management and health monitoring, Bitwerx DataCo fingerprint lookups, claim-feedback
pipeline verification, and AWS authentication.

## Skills

| Skill | Description |
|---|---|
| `aws-login` | SSO login to the InsideDesk AWS account. Auto-triggers on credential errors. |
| `kolla-account-management` | List, ping, and disable Kolla linked customer accounts, and generate KollaConnect invite links, via the Kolla Integration Metadata (connect) API. |
| `kolla-health-check` | Sweep all active Kolla linked accounts, and DM Sean on Slack when any are down (stays quiet when everything is healthy). |
| `dataco-supportco-api` | Reference for the Bitwerx DataCo SupportCo portal — look up a practice and retrieve its Bitwerx fingerprint (instanceId) by name, Facility ID, or group. |
| `verify-claim-ticket` | End-to-end verification of the Claim Feedback pipeline — Slack message → enqueuer Lambda → processor Lambda → HubSpot ticket and associations. |

## Structure

```
id-claude-integrations/
├── .claude-plugin/
│   └── plugin.json            # Plugin metadata and version
├── docs/
│   └── changelog.md           # Version history
└── skills/
    ├── _shared/               # Shared HubSpot/Slack setup + upload helpers
    ├── aws-login/
    ├── kolla-account-management/
    ├── kolla-health-check/
    ├── dataco-supportco-api/
    └── verify-claim-ticket/
```

## Distribution

Install by adding the `insidedesk-tools` marketplace in Customize → Plugins → add
`gitlab.com/insidedesk/id-claude-plugin-mono`. The marketplace serves this plugin
directly from `plugins/id-claude-integrations/` — there is no `.plugin` build step.

Ship changes from the monorepo root with the release helper:

```bash
./release.sh id-claude-integrations <version> "<message>" [Added|Changed|Fixed|Removed|Security]
```

It bumps the version in `.claude-plugin/plugin.json`, updates the changelog, commits,
and pushes. Teammates receive the update on their next "Update" in Customize → Plugins.

See `CLAUDE.md` for full developer docs.

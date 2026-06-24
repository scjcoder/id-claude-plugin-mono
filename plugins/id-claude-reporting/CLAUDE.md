# ID Claude Reporting Plugin

> 📦 **This plugin lives in the InsideDesk plugin monorepo — the single source of truth.**
>
> Path: `/Users/sean/CODE/id-claude-plugin-mono/plugins/id-claude-reporting/`
> Distributed via the `insidedesk-tools` marketplace (`git@gitlab.com:insidedesk/id-claude-plugin-mono.git`).
>
> Edit skills and docs in place here. To ship a change to the team, run the repo-root
> release helper — there is **no `.plugin` build step** (the marketplace serves this
> directory directly):
>
> ```
> ./release.sh id-claude-reporting <new-version> "<changelog message>" [Added|Changed|Fixed|Removed|Security]
> ```


A Cowork plugin for InsideDesk reporting workflows. Skills automate PMS sync
reporting, Power BI data exports, GoldenEye snapshot audits, and install team
summaries — all delivered to Slack.

---

## What This Plugin Does

Focused purely on **reporting and monitoring**. No client management, no install
ticketing — just the skills that generate, format, and deliver recurring reports
for the InsideDesk CS/ops team.

---

## Plugin Structure

```
id-claude-reporting/
├── .claude-plugin/
│   └── plugin.json                # Plugin metadata and version
├── docs/
│   └── changelog.md               # Version history
└── skills/
    ├── _shared/
    │   ├── hubspot-setup.md       # AWS auth + HubSpot token retrieval
    │   ├── slack-setup.md         # Slack token retrieval
    │   └── slack-upload.py        # Slack file upload helper
    ├── aws-login/                 # SSO login — auto-triggers on credential errors
    ├── pms-oos-report/            # PMS Out-of-Sync PDF report
    ├── powerbi-export/            # Power BI Excel export
    ├── snapshot-error-report/     # GoldenEye snapshot error report
    └── install-team-summary/      # Weekday morning install team digest
```

New reporting skills go in their own folder under `skills/`.
If a skill needs AWS or HubSpot API access, reference `_shared/hubspot-setup.md`.
If a skill needs Slack, reference `_shared/slack-setup.md`.

---

## Skill Edit Workflow

Edit skill `SKILL.md` files in place under `plugins/id-claude-reporting/skills/<skill-name>/`.
There is no separate "installed copy" to keep in sync and no `.plugin` archive to
build — the `insidedesk-tools` marketplace serves this directory directly.

**To ship a skill change:**
1. Edit the skill under `plugins/id-claude-reporting/skills/<skill-name>/SKILL.md`.
2. From the monorepo root, run the release helper:
   ```
   ./release.sh id-claude-reporting <new-version> "<what changed>" Fixed
   ```
   It bumps `version` in `.claude-plugin/plugin.json`, prepends a changelog entry to
   `docs/changelog.md`, commits, and pushes.
3. Teammates receive the update on their next "Update" in Customize → Plugins.

> Your day-to-day commits to the monorepo are invisible to the team. Running
> `release.sh` (bumping the version) is the only thing that ships a change.

---

## Distribution

This plugin is distributed through the `insidedesk-tools` marketplace, which serves
it straight from `plugins/id-claude-reporting/`. **There is no `.plugin` build step** — the old
`build-plugin.sh` flow is retired and the script has been removed from the monorepo.

Releasing is handled entirely by the monorepo-root `release.sh` (see Skill Edit
Workflow above). Version resolution: the team only receives an update when `version`
in `.claude-plugin/plugin.json` changes, which `release.sh` does for you. Never ship
by hand-bumping or by building an archive.

---

## AWS

| Property | Value |
|---|---|
| Account ID | <AWS_ACCOUNT_ID> |
| Profile | `install-<AWS_ACCOUNT_ID>` |
| SSO start URL | https://<AWS_SSO_PORTAL>/start |
| SSO region | eu-west-1 |
| Default region | us-east-1 |

Always use `--profile install-<AWS_ACCOUNT_ID> --region us-east-1` on every CLI command.
Run the `aws-login` skill automatically if credentials are missing or expired.

**All AWS CLI commands must be run via Desktop Commander (`mcp__Desktop_Commander__start_process`),
never via the sandbox (`mcp__workspace__bash`).** The sandbox is an isolated Linux VM with no
AWS credentials.

**Key secrets** (all in `insidedesk-all`, region `us-east-1`):

| Key path | Contents |
|---|---|
| `hubspot.access_token` | HubSpot private app bearer token |
| `slack.bot_token` | Slack bot token (via `communication-tools/credentials`) |

---

## HubSpot

| Property | Value |
|---|---|
| Portal ID | <HUBSPOT_PORTAL_ID> |
| MCP connector | `mcp__eba53d3c-d280-4218-ba07-d9e0e4624ed7` |

Reporting skills that need HubSpot data (e.g. install pipeline) use the MCP connector
for standard objects. For the locations custom object, use the bearer token from AWS
Secrets Manager and call the API directly via Desktop Commander.

### Locations custom object

| Property | Value |
|---|---|
| Object type ID | `2-14718097` |
| Search endpoint | `POST https://api.hubapi.com/crm/v3/objects/2-14718097/search` |

---

## Client-Specific Knowledge

### MB2 Dental

MB2 is InsideDesk's first and largest client. Their OOS workflow is **different from every other client**:

- **Monday Board** is the primary communication channel for MB2 OOS issues, not email or HubSpot tickets.
  There is no direct Monday Board MCP integration — use the Claude browser to search Monday Board if needed.
- **HubSpot tickets are NOT created for routine MB2 OOS issues.** Sean only creates a HubSpot ticket for an
  MB2 location if IT involvement is required (i.e. he needs to talk directly to an IT person). If the issue
  can be resolved by calling the MB2 help desk, no ticket is created.
- **The absence of a HubSpot ticket for an MB2 OOS location is normal and expected.** Do not flag it as
  "needs investigation" solely because no ticket exists — look to Monday Board and the MB2 help desk process.
- Going forward, with Claude's help, tickets may be created for all MB2 OOS issues for better tracking —
  but this is not yet established practice.

**When reporting on MB2 OOS locations without a HubSpot ticket or email trail:**
Note "No ticket — MB2 help desk process applies" rather than "needs investigation."

---

## Skill Writing Conventions

- Every skill has a `description:` block that tells Claude exactly when to auto-trigger it.
- Shared logic lives in `_shared/` — reference it with an explicit "read this file now" instruction.
- The `aws-login` skill fires automatically on any AWS credential error.
- All AWS CLI and HubSpot API calls go through Desktop Commander — never the sandbox.
- Reporting skills should deliver their output to Slack (PDF/image) AND save an archive
  copy locally in a `reports/` subdirectory.

---

## Scheduled Tasks

Scheduled tasks that invoke skills in this plugin must follow the **thin-pointer pattern** — the task prompt delegates to the skill by its plugin:name ID and contains no inline copies of skill logic.

**Correct (thin pointer):**
```
Run the `id-claude-reporting:pms-oos-report` skill and follow all its instructions exactly.
This is a scheduled/unattended run — do not ask for confirmation before downloading the Power BI file.
```

**Wrong (inline duplication):**
```
Search Gmail for threads involving install@insidedesk.com... [200 lines of skill logic copied here]
```

**Why:** Inline logic in a task prompt drifts out of sync with the skill every time the skill is updated. The task prompt is the wrong place for logic — it belongs in the SKILL.md.

The only content that belongs in a scheduled task prompt is:
- Which skill(s) to invoke, by plugin:name ID
- Runtime context the skill can't compute itself (e.g. "use yesterday's date as dateFrom", "skip user confirmation — this is an unattended run")
- Parallelism instructions if multiple skills run together (e.g. "launch sub-agents A and B simultaneously")

The canonical example of the correct pattern is `mb2-install-ticket-scan`:
> "Run the `id-claude-ops:mb2-install-ticket` skill and follow all its instructions exactly."

---

## Git — Commit Workflow

**Always use Desktop Commander for git, never the bash sandbox.**

```bash
cd "/Users/sean/CODE/id-claude-plugin-mono"
git add .
git commit -m "type(scope): message"
git push
```

For releases, prefer `./release.sh` (from the monorepo root) — it crafts the commit message, bumps the version, updates the changelog, and pushes in one step.

### .gitignore

Generated artifacts excluded from tracking:
- `*.plugin` — built plugin archives
- `*.xlsx`, `*.xls` — data exports
- `reports/` — archived PDF reports
- `.DS_Store`, `__pycache__/`, `*.pyc`
---

## Runtime identifiers (resolve before acting)

This is a **public** repo, so operational identifiers are stored as placeholders.
Before running anything that needs a real value, resolve placeholders from
`config/insidedesk.local.json` (gitignored — copy it from `config/insidedesk.example.json`):

| Placeholder | Config key |
|---|---|
| `<AWS_ACCOUNT_ID>` | `aws_account_id` |
| `<AWS_SSO_PORTAL>` | `aws_sso_portal` |
| `<GOLDENEYE_HOST>` | `goldeneye_host` |
| `<ADMIN_API_HOST>` | `admin_api_host` |
| `<HUBSPOT_PORTAL_ID>` | `hubspot_portal_id` |
| `<SLACK_USER_SEAN>` | `slack_user_sean` |
| `<SLACK_DM_SEAN>` | `slack_dm_sean` |
| `<SLACK_CHAN_CLAIM_FEEDBACK>` | `slack_chan_claim_feedback` |

Scripts resolve these automatically (config file + env overrides). These are
**non-secret**; API tokens/keys still come from Keychain / Secrets Manager via the
`get-secret` skill.

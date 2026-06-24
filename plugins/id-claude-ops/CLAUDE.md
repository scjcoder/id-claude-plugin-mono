# ID Claude Ops Plugin

## Reference Docs

- **`misc-notes.md`** — Miscellaneous need-to-know details, clarifications, and corrected misunderstandings about GoldenEye, HubSpot, and other systems. Read before making assumptions about edge-case behavior. Located at `/Users/sean/CODE/id-sean-logs/misc-notes.md`.

---

> 📦 **This plugin lives in the InsideDesk plugin monorepo — the single source of truth.**
>
> Path: `/Users/sean/CODE/id-claude-plugin-mono/plugins/id-claude-ops/`
> Distributed via the `insidedesk-tools` marketplace (`git@gitlab.com:insidedesk/id-claude-plugin-mono.git`).
>
> Edit skills and docs in place here. To ship a change to the team, run the repo-root
> release helper — there is **no `.plugin` build step** (the marketplace serves this
> directory directly):
>
> ```
> ./release.sh id-claude-ops <new-version> "<changelog message>" [Added|Changed|Fixed|Removed|Security]
> ```


A Cowork plugin for InsideDesk client operations workflows. Skills automate HubSpot
ticketing, client onboarding/offboarding, install coordination, communications, and
AWS authentication.

---

## What This Plugin Does

Focused on **client operations and integrations**. No standalone reporting — just
the skills that manage clients, tickets, contacts, and service workflows for the
InsideDesk CS/ops team.

---

## Plugin Structure

```
id-claude-ops/
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
    ├── bitwerx-jira-ticket/       # Create Bitwerx DataCo JIRA tickets for Bitwerx-synced locations
    ├── client-comms/              # Draft emails, memos, and status updates
    ├── client-offboarding/        # Full/partial cancellation workflow from HubSpot ticket
    ├── client-pms-summary/        # PMS breakdown by count for a client
    ├── create-422-tickets/        # Create tickets from 422 Tax ID Error Report data
    ├── draft-422-client-email/    # Draft client emails for 422 tax ID errors
    ├── goldeneye-ticket/          # Create ticket from a GoldenEye facility URL
    ├── hubspot-context-note/      # Write/update Claude context note on a ticket
    ├── list-client-locations/     # List all active locations for a client
    ├── mb2-install-ticket/        # Create install tickets from Monday Board approval emails
    └── update-it-contact/         # Add/update IT contact on a HubSpot ticket
```

New skills go in their own folder under `skills/`.
If a skill needs AWS or HubSpot API access, reference `_shared/hubspot-setup.md`.
If a skill needs Slack, reference `_shared/slack-setup.md`.

---

## Skill Edit Workflow

Edit skill `SKILL.md` files in place under `plugins/id-claude-ops/skills/<skill-name>/`.
There is no separate "installed copy" to keep in sync and no `.plugin` archive to
build — the `insidedesk-tools` marketplace serves this directory directly.

**To ship a skill change:**
1. Edit the skill under `plugins/id-claude-ops/skills/<skill-name>/SKILL.md`.
2. From the monorepo root, run the release helper:
   ```
   ./release.sh id-claude-ops <new-version> "<what changed>" Fixed
   ```
   It bumps `version` in `.claude-plugin/plugin.json`, prepends a changelog entry to
   `docs/changelog.md`, commits, and pushes.
3. Teammates receive the update on their next "Update" in Customize → Plugins.

> Your day-to-day commits to the monorepo are invisible to the team. Running
> `release.sh` (bumping the version) is the only thing that ships a change.

---

## Distribution

This plugin is distributed through the `insidedesk-tools` marketplace, which serves
it straight from `plugins/id-claude-ops/`. **There is no `.plugin` build step** — the old
`build-plugin.sh` flow is retired and the script has been removed from the monorepo.

Releasing is handled entirely by the monorepo-root `release.sh` (see Skill Edit
Workflow above). Version resolution: the team only receives an update when `version`
in `.claude-plugin/plugin.json` changes, which `release.sh` does for you. Never ship
by hand-bumping or by building an archive.

---

## AWS

| Property | Value |
|---|---|
| Account ID | 982534385600 |
| Profile | `install-982534385600` |
| SSO start URL | https://seanjo.awsapps.com/start |
| SSO region | eu-west-1 |
| Default region | us-east-1 |

Always use `--profile install-982534385600 --region us-east-1` on every CLI command.
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
| Portal ID | 19834291 |
| MCP connector | `mcp__eba53d3c-d280-4218-ba07-d9e0e4624ed7` |

Skills that need HubSpot data use the MCP connector for standard objects. For the
locations custom object, use the bearer token from AWS Secrets Manager and call the
API directly via Desktop Commander.

### Locations custom object

| Property | Value |
|---|---|
| Object type ID | `2-14718097` |
| Search endpoint | `POST https://api.hubapi.com/crm/v3/objects/2-14718097/search` |

---

## Scheduled Tasks

Scheduled tasks that invoke skills in this plugin must follow the **thin-pointer pattern** — the task prompt delegates to the skill by its `plugin:name` ID and contains no inline copies of skill logic.

**Correct:** `"Run the id-claude-ops:mb2-install-ticket skill and follow all its instructions exactly."`
**Wrong:** copying the skill's steps, code, or file paths into the task prompt.

The only content that belongs in a task prompt is: which skill(s) to invoke, any runtime context the skill can't compute itself (e.g. "skip confirmation — unattended run"), and parallelism instructions if multiple skills run together. If the work isn't in a skill yet, create the skill first, then point the task at it.

---

## Skill Writing Conventions

- Every skill has a `description:` block that tells Claude exactly when to auto-trigger it.
- Shared logic lives in `_shared/` — reference it with an explicit "read this file now" instruction.
- The `aws-login` skill fires automatically on any AWS credential error.
- All AWS CLI and HubSpot API calls go through Desktop Commander — never the sandbox.
- Skills that deliver output to Slack should also save an archive copy locally in a
  `reports/` subdirectory where applicable.

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
- `reports/` — archived output files
- `.DS_Store`, `__pycache__/`, `*.pyc`

---

## Preferences
- Always CC install@insidedesk.com on all Gmail drafts

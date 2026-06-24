# ID Claude Shared Plugin

> 📦 **This plugin lives in the InsideDesk plugin monorepo — the single source of truth.**
>
> Path: `/Users/sean/CODE/id-claude-plugin-mono/plugins/id-claude-shared/`
> Distributed via the `insidedesk-tools` marketplace (`git@gitlab.com:insidedesk/id-claude-plugin-mono.git`).
>
> Edit skills and docs in place here. To ship a change to the team, run the repo-root
> release helper — there is **no `.plugin` build step** (the marketplace serves this
> directory directly):
>
> ```
> ./release.sh id-claude-shared <new-version> "<changelog message>" [Added|Changed|Fixed|Removed|Security]
> ```


Shared authentication and utility skills used across all InsideDesk Cowork plugins.
Provides canonical AWS login, OS-aware secret retrieval, and shared HubSpot/Slack
setup docs so each plugin doesn't duplicate this logic.

---

## What This Plugin Does

Focused on **shared foundations** — auth, secrets, and setup references. No client
management, no reporting. Every other InsideDesk plugin depends on this one.

---

## Plugin Structure

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
    ├── export-secrets-bundle/     # Export encrypted bundle file for sharing with new team members
    ├── get-secret/                # OS-aware secret retrieval (Keychain / Credential Manager)
    └── import-secrets-bundle/     # Import bundle on a new machine — no AWS required
```

New shared skills go in their own folder under `skills/`.

---

## Skill Edit Workflow

Edit skill `SKILL.md` files in place under `plugins/id-claude-shared/skills/<skill-name>/`.
There is no separate "installed copy" to keep in sync and no `.plugin` archive to
build — the `insidedesk-tools` marketplace serves this directory directly.

**To ship a skill change:**
1. Edit the skill under `plugins/id-claude-shared/skills/<skill-name>/SKILL.md`.
2. From the monorepo root, run the release helper:
   ```
   ./release.sh id-claude-shared <new-version> "<what changed>" Fixed
   ```
   It bumps `version` in `.claude-plugin/plugin.json`, prepends a changelog entry to
   `docs/changelog.md`, commits, and pushes.
3. Teammates receive the update on their next "Update" in Customize → Plugins.

> Your day-to-day commits to the monorepo are invisible to the team. Running
> `release.sh` (bumping the version) is the only thing that ships a change.

---

## Distribution

This plugin is distributed through the `insidedesk-tools` marketplace, which serves
it straight from `plugins/id-claude-shared/`. **There is no `.plugin` build step** — the old
`build-plugin.sh` flow is retired and the script has been removed from the monorepo.

Releasing is handled entirely by the monorepo-root `release.sh` (see Skill Edit
Workflow above). Version resolution: the team only receives an update when `version`
in `.claude-plugin/plugin.json` changes, which `release.sh` does for you. Never ship
by hand-bumping or by building an archive. Note: every other InsideDesk plugin depends
on this one, so coordinate releases that change shared auth/secret behavior.

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

## Skill Writing Conventions

- Every skill has a `description:` block that tells Claude exactly when to auto-trigger it.
- The `aws-login` skill fires automatically on any AWS credential error — in this plugin and all dependents.
- The `get-secret` skill is the canonical way to retrieve any credential. Other skills call it by name; they do not duplicate retrieval logic.
- All AWS CLI calls go through Desktop Commander — never the sandbox.

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
- `.DS_Store`, `__pycache__/`, `*.pyc`

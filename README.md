# InsideDesk Claude Plugin Marketplace

A single private marketplace that distributes all InsideDesk Claude plugins to the
team. Add it once, then keep everything up to date with a single click.

Marketplace name: **`insidedesk-tools`**
GitLab (source of truth): `git@gitlab.com:insidedesk/id-claude-plugin-mono.git`
GitHub (public mirror, used by Cowork): `https://github.com/scjcoder/id-claude-plugin-mono`

> **Why two remotes?** Cowork's marketplace installer requires a publicly accessible repo.
> GitLab stays private (source of truth); GitHub is a read-only public mirror that auto-syncs
> via GitLab's push mirror feature. Edit and push to GitLab only — GitHub updates automatically.

---

## Plugins in this marketplace

| Plugin | What it does |
|---|---|
| `id-claude-shared` | Shared foundations — AWS login, secret retrieval, secrets bundles, skill logging. Other plugins depend on it. |
| `id-claude-ops` | Client ops — offboarding, install ticketing, comms, HubSpot, Bitwerx/DataCo, sync status. |
| `id-claude-reporting` | Reporting — 422 Tax ID, PMS Out-of-Sync, Power BI export, snapshot errors, install summary, morning brief. |
| `id-claude-integrations` | Integrations — Kolla, DataCo SupportCo API, claim ticket verification. |
| `coding-quality` | Coding standards — clean-code, git, security, error-handling, testing, docs rules (MUST/SHOULD/MAY tiers) plus Python/AWS/Terraform/GitLab-CI/web overlays and pre-commit/PR/new-project checklists. |
| `opentofu-secure` | Hardened AWS toolkit — generator skill for security-baked OpenTofu/Terraform templates (S3, IAM/OIDC, Route53/ACM, observability, VPC, Lambda, DynamoDB) plus a report-only drift/cost-audit skill. |

---

## For teammates: add the marketplace (one time)

1. In Claude, open **Customize** in the left sidebar (in Cowork, open the **Cowork** tab first).
2. Go to the **Plugins** tab.
3. Under **Personal plugins**, click **"+"** → **Add marketplace** → **Add from a repository**.
4. Enter the repository: `https://github.com/scjcoder/id-claude-plugin-mono` (this is the public GitHub mirror — the GitLab repo is private and won't work directly in Cowork).
5. Install the plugins you need. Most people want `id-claude-shared` plus whichever of ops / reporting / integrations applies to their role. `coding-quality` is useful to anyone writing code with Claude. `opentofu-secure` is useful to anyone provisioning AWS infrastructure.

## For teammates: get the latest version

Open **Customize → Plugins**, find the **insidedesk-tools** marketplace, and click **Update**.
That re-pulls the latest version of every plugin. (Watch `#claude-plugins` in Slack for
release notes.)

---

## Security & configuration

This repo is **public** (via the GitHub mirror), so it is treated as public-facing:

- **No secrets in the repo.** API tokens, keys, and passwords live in AWS Secrets Manager /
  macOS Keychain and are fetched at runtime via the `get-secret` skill — never committed.
- **Runtime identifiers are placeholders.** Non-secret operational identifiers (AWS account
  id, internal hostnames, HubSpot portal id, Slack ids) appear in the source as placeholders
  like `<AWS_ACCOUNT_ID>`. The real values live only in `config/insidedesk.local.json`
  (gitignored). To set up a machine, `cp config/insidedesk.example.json config/insidedesk.local.json`
  and fill it in — see [`config/README.md`](config/README.md) (it can also be backed up to /
  restored from the macOS Keychain). Scripts resolve placeholders automatically (config file +
  env overrides); skills resolve them via the *Runtime identifiers* table in each plugin's
  `CLAUDE.md`.
- **Daily leak scan.** [`.security/scan.py`](.security/scan.py) scans the working tree **and the
  full git history** for secrets and reintroduced internal identifiers. A scheduled task runs it
  daily and DMs Sean only on new findings; run it manually any time with
  `python3 .security/scan.py`. See [`.security/README.md`](.security/README.md).

Infra-posture review docs (`SECURITY_REVIEW.md`) are gitignored and kept out of the public source.

---

## For Sean: how this repo works

This monorepo is the **single source of truth** for all InsideDesk Claude plugins.
Each plugin lives under `plugins/<name>/` and the catalog at
`.claude-plugin/marketplace.json` references them with relative paths. The former
standalone repos (`id-claude-ops`, `id-claude-reporting`, `id-claude-integrations`,
`id-claude-shared`) are deprecated — edit and release here.

**Version behavior:** the entire marketplace ships under a single version number
stored in `.claude-plugin/marketplace.json`. All plugins update together when you
push — no per-plugin version to track. All changes go in the root `CHANGELOG.md`.

### Workflow for any change

Edit the skill / files under `plugins/<plugin>/...`, then ship with the release
helper at the repo root:

```
./release.sh <version> "<message>" [type]
```

Example:

```
./release.sh 1.1.0 "add client-offboarding to id-claude-ops" Added
```

That single command bumps `version` in `.claude-plugin/marketplace.json`,
prepends a [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) entry to
the root `CHANGELOG.md`, commits as
`release(marketplace): v<version> — <message>`, and pushes.

- `<version>` must be a new semver (`x.y.z`) — the helper refuses a duplicate.
- `[type]` is one of `Added | Changed | Fixed | Removed | Security` (default `Changed`).
- Set `RELEASE_NO_PUSH=1` to commit and review locally before pushing.
- After it pushes, teammates get the update on their next "Update" click in Customize → Plugins.

**There is no `.plugin` build step.** The marketplace serves each plugin straight
from `plugins/<name>/`, so a release is just the version bump + push that
`release.sh` performs. The old per-plugin `build-plugin.sh` flow is retired.

### Per-plugin versions (frozen)

Prior to marketplace v1.0.0, each plugin had its own version number. Those are
frozen and kept for historical reference only — see `CHANGELOG.md` for the full
per-plugin history. The `version_status: frozen` field in each
`plugins/<name>/.claude-plugin/plugin.json` marks this explicitly.

### Repo layout

```
id-claude-plugin-mono/
├── .claude-plugin/
│   └── marketplace.json        # the catalog
├── .security/                  # daily leak scanner (scan.py) + baseline
├── config/                     # runtime identifiers: *.example.json (tracked) + *.local.json (gitignored)
├── README.md
└── plugins/
    ├── id-claude-shared/
    ├── id-claude-ops/
    ├── id-claude-reporting/
    ├── id-claude-integrations/
    ├── coding-quality/
    └── opentofu-secure/
```

> The per-plugin `build-plugin.sh` archive flow has been retired in this monorepo —
> the marketplace serves plugins directly from `plugins/<name>/`, so no `.plugin`
> archive is ever built. Use `release.sh` to ship.

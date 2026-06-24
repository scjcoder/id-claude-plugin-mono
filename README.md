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

---

## For teammates: add the marketplace (one time)

1. In Claude, open **Customize** in the left sidebar (in Cowork, open the **Cowork** tab first).
2. Go to the **Plugins** tab.
3. Under **Personal plugins**, click **"+"** → **Add marketplace** → **Add from a repository**.
4. Enter the repository: `https://github.com/scjcoder/id-claude-plugin-mono` (this is the public GitHub mirror — the GitLab repo is private and won't work directly in Cowork).
5. Install the plugins you need. Most people want `id-claude-shared` plus whichever of ops / reporting / integrations applies to their role.

## For teammates: get the latest version

Open **Customize → Plugins**, find the **insidedesk-tools** marketplace, and click **Update**.
That re-pulls the latest version of every plugin. (Watch `#claude-plugins` in Slack for
release notes.)

---

## For Sean: how this repo works

This monorepo is the **single source of truth** for all InsideDesk Claude plugins.
Each plugin lives under `plugins/<name>/` and the catalog at
`.claude-plugin/marketplace.json` references them with relative paths. The former
standalone repos (`id-claude-ops`, `id-claude-reporting`, `id-claude-integrations`,
`id-claude-shared`) are deprecated — edit and release here.

Version behavior: each plugin's version comes from its own
`plugins/<name>/.claude-plugin/plugin.json`. **Teammates only receive an update when you
bump that version field.** That keeps your many-times-a-day working commits from pushing
churn to the team — only a version bump is a release.

### Workflow for a plugin change

Edit the skill / files under `plugins/<plugin>/...`, then ship with the release
helper at the repo root:

```
./release.sh <plugin> <version> "<message>" [type]
```

Example:

```
./release.sh id-claude-ops 1.22.7 "kolla invite link now renders first" Fixed
```

That single command bumps `version` in `plugins/<plugin>/.claude-plugin/plugin.json`,
prepends a [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) entry to
`plugins/<plugin>/docs/changelog.md`, commits as
`release(<plugin>): v<version> — <message>`, and pushes.

- `<version>` must be a new semver (`x.y.z`) — the helper refuses a duplicate.
- `[type]` is one of `Added | Changed | Fixed | Removed | Security` (default `Changed`).
- Set `RELEASE_NO_PUSH=1` to commit and review locally before pushing.
- After it pushes, post a note in `#claude-plugins` so the team knows to hit Update.

**There is no `.plugin` build step.** The marketplace serves each plugin straight
from `plugins/<name>/`, so a release is just the version bump + push that
`release.sh` performs. The old per-plugin `build-plugin.sh` flow is retired.

### What "ships" vs. what doesn't

Your everyday commits to this monorepo are invisible to the team — they only pull
a plugin when its `version` changes. Running `release.sh` (i.e. bumping the
version) is the **only** action that ships a change. Commit working changes
freely; release deliberately.

### Repo layout

```
id-claude-plugin-mono/
├── .claude-plugin/
│   └── marketplace.json        # the catalog
├── README.md
└── plugins/
    ├── id-claude-shared/
    ├── id-claude-ops/
    ├── id-claude-reporting/
    └── id-claude-integrations/
```

> The per-plugin `build-plugin.sh` archive flow has been retired in this monorepo —
> the marketplace serves plugins directly from `plugins/<name>/`, so no `.plugin`
> archive is ever built. Use `release.sh` to ship.

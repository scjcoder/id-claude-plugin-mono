# opentofu-secure Plugin

> 📦 **This plugin lives in the InsideDesk plugin monorepo — the single source of truth.**
>
> Path: `/Users/sean/CODE/id-claude-plugin-mono/plugins/opentofu-secure/`
> Distributed via the `insidedesk-tools` marketplace (`git@gitlab.com:insidedesk/id-claude-plugin-mono.git`).
>
> Edit skills, templates, and docs in place here. To ship a change to the team, run the repo-root
> release helper — there is **no `.plugin` build step** (the marketplace serves this
> directory directly):
>
> ```
> ./release.sh opentofu-secure <new-version> "<changelog message>" [Added|Changed|Fixed|Removed|Security]
> ```

A hardened AWS toolkit with two complementary skills: **`opentofu-secure`** (generator —
scaffolds hardened OpenTofu/Terraform AWS config from security-baked templates) and
**`aws-drift-cost`** (detective — a report-only loop auditing the SCJ dev account for cost
anomalies, untagged resources, public-access/encryption drift, and idle/orphaned resources).

---

## Skill Edit Workflow

Edit `SKILL.md`, `references/`, `scripts/`, and `assets/templates/` in place under
`plugins/opentofu-secure/skills/<skill-name>/`. No separate "installed copy" to keep in
sync and no `.plugin` archive to build — the `insidedesk-tools` marketplace serves this
directory directly.

**To ship a change:**
1. Edit the skill/template under `plugins/opentofu-secure/skills/<skill-name>/`.
2. From the monorepo root, run the release helper:
   ```
   ./release.sh opentofu-secure <new-version> "<what changed>" Changed
   ```
3. Teammates receive the update on their next "Update" in Customize → Plugins.

---

## Runtime identifiers (resolve before acting)

This is a **public** repo, so operational identifiers are stored as placeholders. Both
skills' bash scripts (`skills/_shared/config-resolve.sh`) resolve these automatically —
walking up from the script to find the matching config — with env-var overrides and a
placeholder fallback if no config file exists. Resolve manually before running anything
by hand:

| Placeholder | Config key | Config file |
|---|---|---|
| `<SCJ_AWS_ACCOUNT_ID>` | `scj_aws_account_id` | `config/scj.local.json` (gitignored — copy from `config/scj.example.json`) |
| `<AWS_ACCOUNT_ID>` | `aws_account_id` | `config/insidedesk.local.json` (gitignored — copy from `config/insidedesk.example.json`) |

- `<SCJ_AWS_ACCOUNT_ID>` is Sean's personal/dev AWS account — the `aws-drift-cost` audit
  target and the default dev backend in generated `_base` configs.
- `<AWS_ACCOUNT_ID>` is the InsideDesk prod account — used only where it co-occurs with
  the SCJ account (e.g. the `_base` prod backend, dev-vs-prod guardrail notes).

These are **non-secret** operational identifiers. API tokens/keys still come from
Keychain / Secrets Manager via the `get-secret` skill (in `id-claude-shared`), never from
these config files.

---

## Git — Commit Workflow

**Always use Desktop Commander for git, never the bash sandbox.**

```bash
cd "/Users/sean/CODE/id-claude-plugin-mono"
git add .
git commit -m "type(scope): message"
git push
```

For releases, prefer `./release.sh` (from the monorepo root) — it crafts the commit
message, bumps the version, updates the changelog, and pushes in one step.

---

## Standing rules

This plugin's templates and scripts are also bound by the `coding-quality` plugin's core
rules (clean code, security, error handling, testing, documentation) — apply them to any
edit here, not just to generated output.

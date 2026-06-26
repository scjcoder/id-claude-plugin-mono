# Changelog

All notable changes to the ID Claude Shared plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.4.4] - 2026-06-26

### Added
- add Cloudflare R2 secrets to get-secret skill

## [Unreleased]

### Security
- Public-repo hardening: removed `SECURITY_REVIEW.md` from the source and from git
  history (history rewritten + force-pushed). Moved non-secret runtime identifiers
  (AWS account id, internal hostnames, HubSpot portal id, Slack ids) into a gitignored
  `config/insidedesk.local.json`; source now carries placeholders (`<AWS_ACCOUNT_ID>`,
  etc.) resolved via the *Runtime identifiers* table in `CLAUDE.md` and an auto-loading
  config in the shared scripts. Added a repo-wide daily leak scanner (`.security/scan.py`).

## [1.4.3] - 2026-06-19

### Added
- `build-plugin.sh`: name-matched reference-doc sync convention (parity with the other ID Claude plugins) — any `docs/<skill>.md` matching a `skills/<skill>/` directory is copied to `skills/<skill>/references/<skill>.md` at build time. No-op today (no matching docs); enables future per-skill reference docs to ship automatically.

### Changed
- `export-secrets-bundle`, `import-secrets-bundle`, `skill-logger`: added a "Log the run" final step (skill-logger call) to each skill.

## [1.4.2] - 2026-06-15

### Changed
- `skill-logger`: added Step 7 Chrome tab teardown convention — Chrome-using skills must close their tabs via `tabs_close_mcp` before calling skill-logger. Includes audit list of 13 skills with teardown obligation across id-claude-ops and id-claude-reporting.

## [1.4.1] - 2026-06-12

### Changed
- Added skill-logger final step to export-secrets-bundle and import-secrets-bundle

## [1.4.0] - 2026-06-11

### Added
- `skill-logger` skill: append structured run logs to a local git repo. Each entry is dual-format — human-readable summary block + fenced JSON block. Self-bootstrapping: creates the log repo and runs `git init` on first use. No remote required; pushes only if a remote is configured. Default log path `~/CODE/id-sean-logs` (GitLab remote already configured); override via `skill-logger-log-repo:` in CLAUDE.md. Designed to be called as the final step of any skill that should be logged.

## [1.3.0] - 2026-06-11

### Removed
- `populate-local-secrets` skill: replaced by the export/import bundle workflow. The bundle approach works without AWS CLI or SSO on the recipient's machine, which is simpler for Windows onboarding. Teammates who previously used `populate-local-secrets` should use `import-secrets-bundle` going forward.

## [1.2.0] - 2026-06-10

### Added
- `export-secrets-bundle` skill: exports all shared InsideDesk credentials from AWS Secrets Manager into a password-encrypted `.bundle` file on Sean's Desktop. Enables onboarding new team members without requiring them to install AWS CLI or configure SSO.
- `import-secrets-bundle` skill: companion to export-secrets-bundle. Decrypts a `.bundle` file and writes all credentials to macOS Keychain or Windows Credential Manager. No AWS access, CLI tools, or developer setup required on the recipient's machine.

## [1.1.3] - 2026-06-08

### Added
- `CLAUDE.md`: added build workflow documentation with mandatory version bump and changelog rules before every build.

### Fixed
- `get-secret`: replaced `New-StoredCredential` (requires CredentialManager module) with `cmdkey.exe` for Windows credential storage — no extra module needed.

## [1.0.0] - 2026-05-28

### Added
- `aws-login` skill: canonical SSO login for InsideDesk AWS account (<AWS_ACCOUNT_ID>), consolidated from id-claude-ops, id-claude-reporting, and id-claude-integrations.
- `get-secret` skill: OS-aware credential retrieval — macOS Keychain on Mac, Windows Credential Manager on Windows. Replaces direct AWS Secrets Manager lookups in all skills.
- `_shared/hubspot-setup.md`: canonical HubSpot API setup reference, updated to use `get-secret` instead of AWS.
- `_shared/slack-setup.md`: canonical Slack API setup reference (including file upload flow), updated to use `get-secret` instead of AWS.
- 24 InsideDesk credentials migrated from AWS Secrets Manager to macOS Keychain covering: HubSpot, Slack, GitLab, Netlify, Pinecone, Context7, Cloudflare Turnstile, Zoho, Telegram, Anthropic, Apify, Atlassian, 422 Reports signer, and secup-project variants.

## [1.1.2] - 2026-06-05

### Fixed
- `populate-local-secrets`: `insidedesk/422-reports/signer` entry was only storing `access_key_id` under the wrong keychain name (`422-reports-aws-key-id`). Now stores both `access_key_id` → `insidedesk-422-reports-signer-key-id` and `secret_access_key` → `insidedesk-422-reports-signer-secret`, matching the names expected by `draft-422-client-email`.

## [1.1.1] - 2026-06-05

### Added
- `get-secret`: added `kolla-api-key` to supported secrets table.

## [1.1.0] - 2026-05-28

### Added
- `populate-local-secrets` skill: team onboarding skill that pulls all shared InsideDesk credentials from AWS Secrets Manager and stores them in the OS-native credential store (macOS Keychain or Windows Credential Manager). Skips personal secrets (telegram, anthropic). Safe to re-run — overwrites existing entries with latest AWS values.

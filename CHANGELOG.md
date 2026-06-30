# Changelog

All notable changes to the **insidedesk-tools** marketplace are documented here.

From **v1.0.0 onwards** the entire marketplace ships under a single version number.
Per-plugin versions are frozen and no longer incremented.

| Plugin | Frozen at |
|---|---|
| `id-claude-shared` | 1.4.4 |
| `id-claude-ops` | 1.22.8 |
| `id-claude-reporting` | 1.9.5 |
| `id-claude-integrations` | 1.2.2 |
| `coding-quality` | 1.5.0 |
| `opentofu-secure` | 1.10.0 |

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.1.1] - 2026-06-30

### Changed
- fix(id-claude-ops): add client name, facility name, and facility ID to account update note template

## [1.1.0] - 2026-06-30

### Added
- feat(id-claude-ops): add hubspot-account-update-note skill

## [1.0.1] - 2026-06-30

### Fixed
- fix(hubspot-ticket-generator): add IT/Install POC label as top-priority IT contact; add prior-ticket fallback for external IT vendors

## [1.0.0] - 2026-06-29

### Changed
- Consolidated per-plugin versioning into a single marketplace version. All six
  plugins now ship together; `release.sh` no longer requires a `<plugin>` argument.
- Root `CHANGELOG.md` consolidates all per-plugin changelogs (see history below).
- Per-plugin `docs/changelog.md` files are frozen and kept for historical reference.

### Security
- Purged internal hostname (`<GOLDENEYE_HOST>`) from full git history on
  both remotes (GitLab + GitHub mirror) using `git filter-repo`. Replaced with the
  `<GOLDENEYE_HOST>` placeholder consistent with the rest of the codebase.

---

## Plugin history (pre-consolidation)

The entries below are the original per-plugin changelogs, preserved for reference.
No new entries will be added here — all future changes go in the versioned section above.

---

### id-claude-shared

#### [1.4.4] - 2026-06-29

##### Added
- add Cloudflare R2 secrets to get-secret skill

#### [Unreleased]

##### Security
- Public-repo hardening: removed `SECURITY_REVIEW.md` from the source and from git
  history (history rewritten + force-pushed). Moved non-secret runtime identifiers
  (AWS account id, internal hostnames, HubSpot portal id, Slack ids) into a gitignored
  `config/insidedesk.local.json`; source now carries placeholders (`<AWS_ACCOUNT_ID>`,
  etc.) resolved via the *Runtime identifiers* table in `CLAUDE.md` and an auto-loading
  config in the shared scripts. Added a repo-wide daily leak scanner (`.security/scan.py`).

#### [1.4.3] - 2026-06-19

##### Added
- `build-plugin.sh`: name-matched reference-doc sync convention (parity with the other ID Claude plugins) — any `docs/<skill>.md` matching a `skills/<skill>/` directory is copied to `skills/<skill>/references/<skill>.md` at build time. No-op today (no matching docs); enables future per-skill reference docs to ship automatically.

##### Changed
- `export-secrets-bundle`, `import-secrets-bundle`, `skill-logger`: added a "Log the run" final step (skill-logger call) to each skill.

#### [1.4.2] - 2026-06-15

##### Changed
- `skill-logger`: added Step 7 Chrome tab teardown convention — Chrome-using skills must close their tabs via `tabs_close_mcp` before calling skill-logger. Includes audit list of 13 skills with teardown obligation across id-claude-ops and id-claude-reporting.

#### [1.4.1] - 2026-06-12

##### Changed
- Added skill-logger final step to export-secrets-bundle and import-secrets-bundle

#### [1.4.0] - 2026-06-11

##### Added
- `skill-logger` skill: append structured run logs to a local git repo. Each entry is dual-format — human-readable summary block + fenced JSON block. Self-bootstrapping: creates the log repo and runs `git init` on first use. No remote required; pushes only if a remote is configured. Default log path `~/CODE/id-sean-logs` (GitLab remote already configured); override via `skill-logger-log-repo:` in CLAUDE.md. Designed to be called as the final step of any skill that should be logged.

#### [1.3.0] - 2026-06-11

##### Removed
- `populate-local-secrets` skill: replaced by the export/import bundle workflow. The bundle approach works without AWS CLI or SSO on the recipient's machine, which is simpler for Windows onboarding. Teammates who previously used `populate-local-secrets` should use `import-secrets-bundle` going forward.

#### [1.2.0] - 2026-06-10

##### Added
- `export-secrets-bundle` skill: exports all shared InsideDesk credentials from AWS Secrets Manager into a password-encrypted `.bundle` file on Sean's Desktop. Enables onboarding new team members without requiring them to install AWS CLI or configure SSO.
- `import-secrets-bundle` skill: companion to export-secrets-bundle. Decrypts a `.bundle` file and writes all credentials to macOS Keychain or Windows Credential Manager. No AWS access, CLI tools, or developer setup required on the recipient's machine.

#### [1.1.3] - 2026-06-08

##### Added
- `CLAUDE.md`: added build workflow documentation with mandatory version bump and changelog rules before every build.

##### Fixed
- `get-secret`: replaced `New-StoredCredential` (requires CredentialManager module) with `cmdkey.exe` for Windows credential storage — no extra module needed.

#### [1.1.2] - 2026-06-05

##### Fixed
- `populate-local-secrets`: `insidedesk/422-reports/signer` entry was only storing `access_key_id` under the wrong keychain name (`422-reports-aws-key-id`). Now stores both `access_key_id` → `insidedesk-422-reports-signer-key-id` and `secret_access_key` → `insidedesk-422-reports-signer-secret`, matching the names expected by `draft-422-client-email`.

#### [1.1.1] - 2026-06-05

##### Added
- `get-secret`: added `kolla-api-key` to supported secrets table.

#### [1.1.0] - 2026-05-28

##### Added
- `populate-local-secrets` skill: team onboarding skill that pulls all shared InsideDesk credentials from AWS Secrets Manager and stores them in the OS-native credential store (macOS Keychain or Windows Credential Manager). Skips personal secrets (telegram, anthropic). Safe to re-run — overwrites existing entries with latest AWS values.

#### [1.0.0] - 2026-05-28

##### Added
- `aws-login` skill: canonical SSO login for InsideDesk AWS account, consolidated from id-claude-ops, id-claude-reporting, and id-claude-integrations.
- `get-secret` skill: OS-aware credential retrieval — macOS Keychain on Mac, Windows Credential Manager on Windows. Replaces direct AWS Secrets Manager lookups in all skills.
- `_shared/hubspot-setup.md`: canonical HubSpot API setup reference, updated to use `get-secret` instead of AWS.
- `_shared/slack-setup.md`: canonical Slack API setup reference (including file upload flow), updated to use `get-secret` instead of AWS.
- 24 InsideDesk credentials migrated from AWS Secrets Manager to macOS Keychain covering: HubSpot, Slack, GitLab, Netlify, Pinecone, Context7, Cloudflare Turnstile, Zoho, Telegram, Anthropic, Apify, Atlassian, 422 Reports signer, and secup-project variants.

---

### id-claude-ops

#### [1.22.8] - 2026-06-26

##### Fixed
- refactor Chrome cleanup: add chrome-cleanup helper, update 13 skills to use it

#### [1.22.7] - 2026-06-26

##### Added
- add chrome-test skill to validate Chrome tool availability

##### Security
- Public-repo hardening: removed `SECURITY_REVIEW.md` from source and git
  history (history rewritten + force-pushed). Moved non-secret runtime identifiers
  (AWS account id, internal hostnames, HubSpot portal id, Slack ids) into a gitignored
  `config/insidedesk.local.json`; source now carries placeholders (`<AWS_ACCOUNT_ID>`,
  etc.) resolved via the *Runtime identifiers* table in `CLAUDE.md` and an auto-loading
  config in the shared scripts. Added a repo-wide daily leak scanner (`.security/scan.py`).

#### [1.22.6] - 2026-06-23

##### Fixed
- `create-kolla-invite`: invite link table now renders first in the HubSpot human note, above the fold. Previously the facility details table came first, burying the link. Template updated: invite link + expiry at top, facility details below.

#### [1.22.5] - 2026-06-22

##### Fixed
- `hubspot-ticket-generator`: external ticketing system detection now checks the `jobtitle` field for portal URLs (in addition to `email`). P4D HELPDESK TICKET SYSTEM stores its portal URL in `jobtitle`, causing the contact to be scored incorrectly. Added a note to fetch `jobtitle` during the scoring pass, not just after. Updated ticket body template to show the portal URL and a "do NOT use email" warning when an external ticketing system contact is selected.

#### [1.22.4] - 2026-06-19

##### Added
- `build-plugin.sh`: name-matched reference-doc sync (parity with the other ID Claude plugins) — `docs/<skill>.md` is copied into `skills/<skill>/references/<skill>.md` at build time.
- `bitwerx-jira-ticket`: bundled `references/bitwerx-jira-ticket.md` and repointed the skill's "read first" pointer from a hardcoded absolute host path to the bundled copy.
- `full-sync-status`: bundled `references/full-sync-status.md` and repointed the pointer from repo-root `docs/` to the bundled copy.

#### [1.22.3] - 2026-06-19

##### Changed
- `draft-422-client-email`: Added `mode` input parameter (`"initial"` or `"reminder"`, defaults to `"initial"`). When `mode="reminder"`: subject becomes "Following Up: Unrecognized Tax IDs on Incoming Claims", body opens with a follow-up paragraph, and Slack notification label becomes "422 Reminder Draft Created".

#### [1.22.2] - 2026-06-19

##### Changed
- `client-comms`: Added skill-logger call as Step 6 at end of workflow.
- `goldeneye-tin-normalization`: Added skill-logger call as Step 4 at end of workflow.
- `hubspot-human-note`: Added skill-logger call as Step 5 at end of workflow.

#### [1.22.1] - 2026-06-19

##### Changed
- `draft-422-client-email`: Updated email subject to "Action Needed: Unrecognized Tax IDs on Incoming Claims". Rewrote body copy to emphasize claims won't process until resolved. Added Sean Johnson signature block with InsideDesk logo (inline PNG attachment). Fixed office list extraction to read directly from `client_data` dict keys.

#### [1.22.0] - 2026-06-19

##### Changed
- `draft-422-client-email`: Replaced S3 presigned URL flow with direct PDF attachment on Gmail drafts. PDFs are now base64-encoded and attached via the Gmail MCP `create_draft` attachments parameter — no AWS S3 bucket, IAM signer user, or Secrets Manager secret required.

##### Removed
- `infra/422-reports`: Destroyed all AWS resources provisioned by this OpenTofu module — S3 bucket, IAM user/policy/access key, and Secrets Manager secret. Module marked deprecated in README.

#### [1.21.4] - 2026-06-18

##### Fixed
- `goldeneye-tin-normalization`: Added missing YAML frontmatter to SKILL.md.

#### [1.21.3] - 2026-06-18

##### Added
- `goldeneye-tin-normalization`: New skill to normalize pasted TIN lists for GoldenEye. Handles delimited and mashed-together input formats, strips non-digits, deduplicates, and outputs a comma-space separated string in a code block.

#### [1.21.2] - 2026-06-18

##### Changed
- `bitwerx-jira-ticket`: Added `[New Install]` as a distinct issue type (post-install telemetry verification, separate from `[new location]` which provisions the DataCo account pre-install).

#### [1.21.1] - 2026-06-17

##### Changed
- `create-kolla-invite`: Step 5 now delegates to `hubspot-human-note` instead of building inline HTML.
- `bitwerx-jira-ticket`: Step 7 now delegates to `hubspot-human-note`.
- `create-422-tickets`: Step 8 summary note now delegates to `hubspot-human-note`.

#### [1.21.0] - 2026-06-17

##### Added
- `hubspot-human-note`: New utility skill for posting nicely formatted HTML notes to HubSpot tickets. Supports key-value tables, free-text blocks, and dividers. Designed to be called by other skills as a companion to `hubspot-context-note`.

#### [1.20.0] - 2026-06-17

##### Added
- `create-kolla-invite`: New skill to generate a Kolla KollaConnect invite link for a new facility. Looks up facility metadata from GoldenEye, navigates the Kolla Admin Panel, captures the generated URL, posts an HTML note and a base64 Claude context note to the HubSpot install ticket, and calls skill-logger on completion.

#### [1.19.3] - 2026-06-17

##### Changed
- `bitwerx-jira-ticket`: Added Step 7 — after filing the JIRA ticket, if a HubSpot ticket URL was provided, create a formatted HTML note on the ticket with the Bitwerx ticket number(s), issue type, description, and link.

#### [1.19.2] - 2026-06-17

##### Fixed
- `hubspot-context-note`: Step 3 — added explicit dynamic timestamp generation via Python. Previously the skill said "current unix timestamp in milliseconds" without showing how, leading to hardcoded values that backdated notes to the wrong year.
- `hubspot-context-note`: Step 3 — fixed association format for new note creation. Replaced `associationTypeId: 18` with `targetObjectType` / `targetObjectId` fields.

#### [1.19.1] - 2026-06-17

##### Changed
- `draft-422-client-email`: Step 4 — email body now lists affected office names (one per line) between the greeting and the first paragraph.

#### [1.19.0] - 2026-06-15

##### Changed
- `monday-account-update`: Step 1 — added note that board groups stay collapsed after searching; you must click the group header expand arrow to reveal filtered rows within the group.
- `hubspot-ticket-generator`: Steps 5 and 10 — multiple clarity and correctness improvements including `search_crm_objects` limitation note, CONTAINS_TOKEN fallback, and context note format enforcement.
- `hubspot-ticket-generator`: Added Step 10b — optional Gmail DOS follow-up draft.

#### [1.18.0] - 2026-06-15

##### Added
- `templates/install/`: 45 HubSpot INSTALL email templates scraped from HubSpot Message Templates.
- `templates/snippets/`: 8 HubSpot Snippets owned by Sean Johnson.
- `skills/client-comms`: Added "HubSpot Template Library" reference section.

#### [1.17.0] - 2026-06-15

##### Added
- `dataco-sync-status`: New Step 6b — Suggested Actions decision matrix. After reporting status, skill recommends and offers to execute the appropriate next action.
- `bitwerx-jira-ticket`: Added `[Resend Claims]` issue type template.

#### [1.16.3] - 2026-06-15

##### Fixed
- `bitwerx-jira-ticket`: `list[0].group?.name` → `list[0].groupName` (API field name correction).
- `dataco-sync-status`: Replaced Step 3–4 with correct API usage — all stage data comes from `detail.data.practiceStatus`. Added async IIFE pattern requirement and Unix-seconds timestamp note. Fixed connectivity check to use `ps.heartbeatStale` / `ps.lastHeartbeatSuccessful`.

#### [1.16.2] - 2026-06-12

##### Changed
- Added skill-logger final step to all qualifying skills for run activity logging.

#### [1.16.1] - 2026-06-12

##### Changed
- `bitwerx-jira-ticket`: Fill Description before Summary in Step 5 to avoid "Suggested Articles" layout shift. Added `Partner ID: {GoldenEye Facility ID}` to the `[new location]` description template.

#### [1.16.0] - 2026-06-11

##### Changed
- `cancellation-ticket`: Major overhaul with 7 fixes and 3 new features including note association fix, context note format fix, duplicate check fix, PMS swap detection, DataCo name check, and termination date parsing.

#### [1.15.2] - 2026-06-11

##### Changed
- `monday-account-update`: Standardized text entry to use clipboard-paste approach. Full body text is now written to clipboard via `navigator.clipboard.writeText()` and pasted with Cmd+V — eliminates Monday autocomplete triggering on `@` characters in body text.

#### [1.15.1] - 2026-06-11

##### Fixed
- `create-422-tickets`: Overhauled duplicate detection to handle clients that generate daily 422 errors for the same locations with different TINs. `is_active()` now treats closed tickets as inactive regardless of when they were closed. Added TIN overlap requirement to Front 3. Reweighted all fronts.

#### [1.15.0] - 2026-06-09

##### Added
- `dataco-health-check`: New skill — checks https://status.dataco.vet/# for active or unresolved DataCo incidents. Returns a structured `DATACO_HEALTH_STATUS` block. Called automatically by pms-oos-report as Step 0.5.

#### [1.14.0] - 2026-06-09

##### Added
- `monday-account-update`: New skill — posts an update note on a dental office item in the MB2 Inside Desk Install List Monday Board.

#### [1.13.0] - 2026-06-09

##### Added
- `bitwerx-jira-ticket`: New skill — creates Bitwerx DataCo JIRA Service Desk tickets for Bitwerx-synced locations. Handles all issue types: [Check Sync], [Server Swap], [Disable Location], [Reactivate Location], [new location], and [Password Request].

#### [1.12.0] - 2026-06-09

##### Added
- `check-422-tax-ids`: New skill — checks whether a TIN that caused a 422 snapshot error is already in a facility's Expected TaxIds approved list.

#### [1.11.1] - 2026-06-08

##### Changed
- `mb2-install-ticket`: Added Step 10 — after writing context notes, unconditionally invoke `id-claude-ops:mb2-monday-to-ge` in unattended mode.

#### [1.11.0] - 2026-06-08

##### Added
- `mb2-monday-to-ge`: New skill — reads the MB2 Monday Board "To Be Installed" group via Chrome and creates GoldenEye facility records for any office not yet present. Supports manual and unattended modes.

#### [1.10.0] - 2026-06-08

##### Changed
- `create-422-tickets`: Replaced three-front sequential dedup with a four-front parallel scoring algorithm. All fronts always run — no short-circuiting.

#### [1.9.9] - 2026-06-08

##### Fixed
- `mb2-install-ticket`: Approval detection now uses `Approved by` in the full email body as the primary signal. In-house IT installs don't include a Vendor line and were previously skipped as false negatives.

#### [1.9.8] - 2026-06-08

##### Fixed
- `create-422-tickets`: Three dedup bugs resolved — normalize() function, Front 2 pagination for companies with 100+ tickets, and closed-ticket filter.

#### [1.9.7] - 2026-06-08

##### Changed
- `create-422-tickets`: Expanded duplicate check from single subject-match to three independent fronts: normalized subject match, company-associated open ticket search, and location overlap check.

#### [1.9.6] - 2026-06-08

##### Fixed
- `create-422-tickets`: Duplicate-check now normalizes hyphens to spaces before comparing ticket subjects.

#### [1.9.5] - 2026-06-08

##### Fixed
- `draft-422-client-email`: Fixed HubSpot email engagement creation — replaced invalid properties with `hs_email_headers` JSON blob.
- `draft-422-client-email`: Fixed ticket association — replaced v4 associations endpoint with v3 `ticket→email` endpoint.

##### Added
- `draft-422-client-email`: New Step 1a — reads and surfaces the Claude Context note from the HubSpot ticket before drafting.

#### [1.9.4] - 2026-06-08

##### Changed
- `draft-422-client-email`: Added Step 4a — after creating the Gmail draft, log the email as a HubSpot engagement on the ticket.

#### [1.9.3] - 2026-06-05

##### Refactored
- `office-ticket-history`: Replaced legacy `_shared/hubspot-setup.md` prereq with standard `get-secret` pattern.
- `draft-422-client-email`: S3 signer credentials now retrieved via `get-secret` instead of raw subprocess calls.

#### [1.9.2] - 2026-06-05

##### Fixed
- `draft-422-client-email`: Resolved `SignatureDoesNotMatch` error on pre-signed S3 URLs. Rotated the IAM access key and updated Secrets Manager.

##### Changed
- `draft-422-client-email`: Credential source for S3 operations moved from AWS Secrets Manager to local macOS Keychain. Skill now requires no AWS SSO session to run.

#### [1.9.1] - 2026-05-29

##### Changed
- `sync-status`: Step 1 now captures the **Service Date** column from the GoldenEye facility search results table. Adds `last_service_date` and `days_since_dos` fields to the `SYNC_STATUS_RESULT` block.
- `full-sync-status`: Report format now includes a **DOS Status** block.

#### [1.9.0] - 2026-05-29

##### Added
- `dataco-sync-status`: New skill — checks the Bitwerx Dataco pipeline stages for a facility via the Dataco API.
- `office-ticket-history`: New skill — searches HubSpot Install Pipeline tickets and Gmail for recent activity related to a dental office.
- `full-sync-status`: New orchestrator skill — calls `sync-status`, `dataco-sync-status` (if Bitwerx PMS), and `office-ticket-history` in sequence.

#### [1.8.0] - 2026-05-29

##### Added
- `sync-status`: New skill to check whether a facility is syncing with InsideDesk via GoldenEye snapshots.

#### [1.7.0] - 2026-05-28

##### Changed
- All skills: replaced AWS Secrets Manager token fetches with `get-secret` skill calls.
- `build-plugin.sh`: updated `get_token()` to use macOS Keychain instead of AWS Secrets Manager.

#### [1.6.0] - 2026-05-28

##### Changed
- `goldeneye-ticket` skill renamed to `hubspot-ticket-generator`.

#### [1.5.1] - 2026-05-27

##### Changed
- `insidedesk-facility-entry`: Major v2 rewrite with security, speed, and guardrail improvements — URL validation, full PMS mapping table, upfront batch confirm, duplicate detection, audit trail, and dry-run mode.

#### [1.5.0] - 2026-05-27

##### Added
- `insidedesk-facility-entry`: New skill — bulk-enter facility/office records into the InsideDesk Operations Dashboard from a spreadsheet using Claude in Chrome.

#### [1.4.0] - 2026-05-26

##### Added
- `cancellation-ticket`: New skill — create HubSpot CANCELLATIONS custom object records from Monday Board cancellation-mention emails.

#### [1.3.0] - 2026-05-19

##### Added
- `goldeneye-ticket`: New skill — create HubSpot Install Pipeline tickets from a GoldenEye facility URL.

#### [1.2.2] - 2026-05-15

##### Changed
- `hubspot-context-note`: Switched to base64-encoded JSON note body.

#### [1.2.1] - 2026-05-15

##### Changed
- `hubspot-context-note`: Improved note body format — replaced Unicode section dividers with labeled key-value lines.

#### [1.2.0] - 2026-05-15

##### Changed
- `create-422-tickets`: Added Step 3 — resolve HubSpot location records for each affected facility and batch-associate to the ticket.

---

### id-claude-reporting

#### [1.9.5] - 2026-06-26

##### Added
- `morning-brief`: add live verification step for Bitwerx JIRA tickets, HubSpot searches, and GoldenEye installs

#### [Unreleased]

##### Security
- Public-repo hardening: removed `SECURITY_REVIEW.md` from the source and from git
  history (history rewritten + force-pushed). Moved non-secret runtime identifiers
  into `config/insidedesk.local.json`; source now carries placeholders. Added a
  repo-wide daily leak scanner (`.security/scan.py`).

#### [1.9.4] - 2026-06-22

##### Fixed
- `pms-oos-report`: Step 3 split into 3a (mandatory, API-only HubSpot ticket cross-reference) and 3b (optional, browser-based deep dive). Previously ticket lookup was routed only through the heavyweight `full-sync-status`, causing locations with open tickets to be reported as "no ticket."

#### [1.9.3] - 2026-06-19

##### Added
- `build-plugin.sh`: name-matched reference-doc sync.
- `ascend-activity-report`: bundled `references/ascend-activity-report.md` and added a "read first" pointer at the top of the skill.

#### [1.9.2] - 2026-06-19

##### Changed
- `422-tax-id-report`: Step 8 overhauled with a two-tier inactivity workflow. New Step 8b sends a reminder email at 10 days with no client response. Inactivity threshold raised from 14 to 21 days throughout.

#### [1.9.1] - 2026-06-19

##### Fixed
- `snapshot-error-report`: Step 1 now requires clicking into each date field and typing today's date before relying on the JS setter. Adds a mandatory screenshot verification gate.
- `install-team-summary`: Replaced hardcoded Python path with `which python3` lookup.

#### [1.9.0] - 2026-06-19

##### Added
- `morning-brief`: New skill. Generates Sean's daily start-of-day HTML report covering today's calendar, priority inbox threads, HubSpot open install tickets cross-referenced with GoldenEye sync status and Slack #installs, and a short action-items list.

#### [1.8.4] - 2026-06-18

##### Fixed
- `422-tax-id-report`: Restored GoldenEye facility ID (Fac XXXX) to report output.

#### [1.8.3] - 2026-06-15

##### Changed
- `dos-report`: Added **Days Since Sync** column after Days Since DOS.
- `dos-report`: Report now groups rows by client with a client-header row, then sorts by Days Since DOS descending.
- `dos-report`: Page size switched to landscape.

#### [1.8.2] - 2026-06-12

##### Changed
- Added skill-logger final step to all qualifying skills for run activity logging.

#### [1.8.1] - 2026-06-12

##### Fixed
- `422-tax-id-report`: After JS force-setting date inputs, now also dispatches Enter keydown/keyup events and clicks any Search/Apply/Filter button to force a data reload.

#### [1.8.0] - 2026-06-11

##### Changed
- `pms-oos-report`: Added Step 11 — calls `skill-logger` after all primary deliverables complete.
- `422-tax-id-report`: Added Step 11 — calls `skill-logger` after HubSpot context notes.

#### [1.7.2] - 2026-06-09

##### Changed
- `full-historical-client-report`: PDF enhancements — summary stat cards row, Cancellation History section with count in header, HubSpot Tickets section grouped by pipeline.

#### [1.7.1] - 2026-06-09

##### Changed
- `full-historical-client-report`: Step 6 rewritten to use `facility=<id>` query parameter on the snapshot API — queries per-facility instead of scanning the global dataset client-side.

#### [1.7.0] - 2026-06-09

##### Added
- `full-historical-client-report`: New skill. Generates a complete client history PDF covering all locations, snapshot activity timeline, cancellation records, HubSpot tickets, key contacts, and Gmail email trail. Works for Active, At Risk, and Churned clients.

#### [1.6.1] - 2026-06-09

##### Changed
- `ascend-activity-report`: Added "About This Report" FAQ section at the end of the PDF.

#### [1.6.0] - 2026-06-09

##### Changed
- `ascend-activity-report`: **Snapshot data is now the primary billing baseline** instead of the GoldenEye Facilities page. Any facility with ≥1 snapshot in the report month is billed.

#### [1.5.0] - 2026-06-09

##### Changed
- `ascend-activity-report`: Report now has three sections — **Newly Onboarded**, **Offboarded Still Billed**, **Active Full Month** — plus the existing **No Snapshots** alert section.

#### [1.4.0] - 2026-06-09

##### Changed
- `pms-oos-report`: Added Step 0.5 — runs `id-claude-ops:dataco-health-check` before report generation.

#### [1.3.1] - 2026-06-09

##### Fixed
- `422-tax-id-report`: default date range is now today — no longer asks when no range is provided.
- `422-tax-id-report`: `generate_report.py` now handles compact `{count, ids}` taxId format.

#### [1.3.0] - 2026-06-08

##### Changed
- `422-tax-id-report`: Step 2 JS extraction now uses compact format — builds `{count, ids[≤20]}` per tax ID directly in JavaScript. Prevents buffer truncation on large datasets.

#### [1.2.2] - 2026-05-29

##### Fixed
- `pms-oos-report`: HubSpot lookback window now scales by severity (5d MEDIUM, 14d HIGH, 60d CRITICAL).
- `pms-oos-report`: After finding a HubSpot ticket, now reads full engagement/note history.
- `pms-oos-report`: MB2 OOS locations with no ticket now noted as "MB2 help desk process".

##### Added
- `CLAUDE.md`: MB2 client-specific knowledge section.

#### [1.2.1] - 2026-05-29

##### Changed
- `pms-oos-report`: Removed notes file entirely. HubSpot and Gmail are now the sole live sources of truth.
- `pms-oos-report`: Added Step 4 — if Sean provides context in chat during a run, it is used in the report.

#### [1.2.0] - 2026-05-29

##### Added
- `pms-oos-report`: New Step 4 enriches each OOS location with live data from HubSpot and Gmail.

#### [1.1.3] - 2026-05-28

##### Changed
- `pms-oos-report`: replaced aws-login/Secrets Manager Slack token prerequisite with `get-secret` skill call.

#### [1.1.2] - 2026-05-19

##### Fixed
- `snapshot-error-report` and `422-tax-id-report`: Added JavaScript force-set of date inputs after page navigation to guarantee the correct date range is applied.

##### Changed
- `install-team-summary`: Report rows are now sorted by stage in HubSpot board order.

#### [1.1.1] - 2026-05-15

##### Changed
- `422-tax-id-report`: Generalized invalid EIN detection — any EIN that fails structural validation is flagged.

#### [1.1.0] - 2026-05-15

##### Changed
- `422-tax-id-report`: Tax ID `123` flag upgraded to prominent ⚠ **Invalid EIN** warning.

#### [1.0.0] - 2026-05-14

##### Added
- **PMS OOS Report** (`skills/pms-oos-report`): Generates the PMS Out-of-Sync PDF report from a Power BI Excel export.
- **Power BI Export** (`skills/powerbi-export`): Downloads the PMS Snapshot Monitoring report from Power BI.
- **Snapshot Error Report** (`skills/snapshot-error-report`): Reads the GoldenEye Snapshots page and produces an Excel data table and PDF summary.
- **Install Team Summary** (`skills/install-team-summary`): Weekday morning digest of Gmail and HubSpot Install pipeline activity, delivered as an image to Slack.
- **AWS Login** (`skills/aws-login`): SSO login to the InsideDesk AWS account.
- **Shared utilities** (`skills/_shared`): HubSpot setup, Slack setup, and Slack upload helper.

---

### id-claude-integrations

#### [Unreleased]

##### Security
- Public-repo hardening: removed `SECURITY_REVIEW.md` from the source and from git
  history (history rewritten + force-pushed). Moved non-secret runtime identifiers
  into `config/insidedesk.local.json`; source now carries placeholders. Added a
  repo-wide daily leak scanner (`.security/scan.py`).

#### [1.2.2] - 2026-06-19

##### Added
- `build-plugin.sh`: name-matched reference-doc sync convention.

##### Changed
- `kolla-account-management`, `kolla-health-check`, `verify-claim-ticket`: added a "Log the run" final step.

#### [1.2.1] - 2026-06-12

##### Changed
- Added skill-logger final step to all qualifying skills for run activity logging.

#### [1.2.0] - 2026-06-05

##### Added
- **Kolla Health Check** (`skills/kolla-health-check`): Sweeps all ACTIVE Kolla linked accounts, pings each via the Integration Metadata API, and DMs Sean on Slack only when one or more are down. Quiet on healthy runs.

#### [1.1.0] - 2026-06-05

##### Added
- **Kolla Account Management** (`skills/kolla-account-management`): Manage Kolla linked customer accounts via the Integration Metadata API. Supports listing, pinging for health, disabling, and creating KollaConnect invite links.

#### [1.0.1] - 2026-05-28

##### Changed
- `build-plugin.sh`: updated `get_token()` to use macOS Keychain instead of AWS Secrets Manager.

#### [1.0.0] - 2026-05-14

##### Added
- **AWS Login** (`skills/aws-login`): SSO login to the InsideDesk AWS account via the install profile.
- **DataCo SupportCo API** (`skills/dataco-supportco-api`): Reference skill for looking up dental practices in Bitwerx DataCo, retrieving fingerprints.
- **Verify Claim Ticket** (`skills/verify-claim-ticket`): End-to-end verification that a Slack #claim_feedback message flowed through the SQS → Lambda pipeline to a HubSpot ticket.

---

### coding-quality

#### [1.5.0] - 2026-06-28

##### Added
- 10 new skills converted from the `aws-email-wizard` repo's Windsurf/Devin workflows: `documentation-update`, `git-release`, `git-save`, `git-hooks-setup`, `git-whitespace-hooks`, `gitlab-ci-best-practices`, `root-cleanup`, `test-suite-bootstrap`, `project-analysis`, `merge-to-production`.

##### Changed
- Migrated from the standalone `ai-coding-quality` repo into the `id-claude-plugin-mono` monorepo. Retired the per-plugin `build-plugin.sh`/`coding-quality.plugin` archive flow.

#### [1.4.1] - 2026-05-31

##### Fixed
- Corrected plugin.json version field after accidental rollback to 1.3.0 during build session; no content changes.

#### [1.4.0] - 2026-05-30

##### Added
- `skills/clean-code-pass/SKILL.md` — 13-pass systematic code review workflow.
- Enhanced `rules/02-git.md` with git-commit-workflow content: commit message format, commit types, subject line rules, body guidelines, available scopes table, submodule commit workflow.
- Expanded `stacks/gitlab-ci.md` with comprehensive GitLab CI/CD pipeline practices including OIDC authentication and AWS Secrets Manager parsing.

##### Changed
- Deprecated `scj-dev-workflows` plugin in favor of `coding-quality` plugin (all skills migrated).

#### [1.3.0] - 2026-05-30

##### Added
- `stacks/aws-environment.md`: AWS environment practices overlay.
- `resources/templates/.pre-commit-config.yaml`: Canonical pre-commit config with ruff, black, pre-commit hooks, and detect-secrets.
- `resources/templates/.gitignore`: Canonical .gitignore.
- `rules/07-agent-instructions.md`: Guidance on managing AI agent instruction files.
- Updated security, testing, and tools references.

#### [1.2.0] - 2026-05-30

##### Added
- `stacks/python-aws.md`: Python on AWS (boto3) overlay. Mandates module-scope client reuse, adaptive retries, pagination of list/describe/scan calls, and catching `botocore.exceptions.ClientError`.

#### [1.1.0] - 2026-05-30

##### Added
- `stacks/aws-lambda.md`: AWS Lambda (Node.js) overlay. Targets `nodejs24.x`, mandates AWS SDK v3, requires async handlers, per-client imports, client reuse across warm invocations.

#### [1.0.0] - 2026-05-30

##### Added
- Initial release. Packages the Coding Quality standards repo as a Claude plugin.
- `coding-quality` skill: entry point that loads the bundled rule set.
- Core rules: conventions (MUST/SHOULD/MAY tiers), clean-code, git, security, error-handling, testing, documentation.
- Stack overlays: python, terraform-aws, gitlab-ci, web-frontend.
- Checklists: pre-commit, pre-pr, new-project. Resources: tools, references.

---

### opentofu-secure

#### [1.10.0] - 2026-06-24

##### Changed
- Migrated from the standalone `opentofu-secure` repo into the `id-claude-plugin-mono` monorepo. Retired the per-plugin `build-plugin.sh`/`opentofu-secure.plugin` archive flow.

##### Security
- Replaced the literal SCJ dev AWS account id with the `<SCJ_AWS_ACCOUNT_ID>` placeholder, resolved at runtime from the gitignored `config/scj.local.json` via `skills/_shared/config-resolve.sh`.

#### [1.9.0] - 2026-06-24

##### Changed
- `untagged` check now honors an `UNTAGGED_EXCLUDE` allowlist so structurally un-taggable resources no longer inflate the count. Defaults exclude Amplify-managed CloudFormation stacks and AWS-managed billing payment-instruments.

#### [1.8.0] - 2026-06-23

##### Added
- New `out-of-region` detective check: scans every enabled region outside the home set and flags any resource found there.

#### [1.7.0] - 2026-06-23

##### Changed
- Expanded the excluded-services watchlist default to high-cost services that should normally be $0 for this account.

#### [1.6.1] - 2026-06-23

##### Changed
- Cost watchlist now triggers on **recent** spend (current + last full month) instead of the 4-month window total.

#### [1.6.0] - 2026-06-23

##### Added
- New `cost-trend` check with two long-horizon signals from monthly Cost Explorer data.

#### [1.5.0] - 2026-06-23

##### Added
- Multi-region scanning for regional checks (`untagged`, `public-encryption-drift` EBS, `idle-orphaned`).

#### [1.4.0] - 2026-06-23

##### Added
- `scripts/lib/render_html.py`: styled, email-safe HTML report. `run-loop.sh` gains `--html`.
- Notifications now use HTML: email sends the HTML body, Telegram attaches the HTML file alongside the summary message.

#### [1.3.0] - 2026-06-23

##### Added
- `scripts/notify.sh`: channel-agnostic delivery of the digest to Telegram and email via SES.

#### [1.2.0] - 2026-06-23

##### Added
- `public-encryption-drift` now correlates each S3 public-access-block finding with Route53 — DNS-backed buckets separated from review candidates.

##### Changed
- `public-encryption-drift` (perf): per-bucket public-access-block calls fan out with `xargs -P`. Per-bucket `get-bucket-encryption` call dropped (SSE-S3 is account-wide).

#### [1.1.0] - 2026-06-22

##### Added
- New `aws-drift-cost` skill: a report-only agentic loop that audits the SCJ dev account for cost anomalies, untagged resources, public-access/encryption drift, and idle/orphaned resources.

#### [1.0.0] - 2026-06-22

##### Added
- Initial release. Packages the `opentofu-secure` skill: a generator that scaffolds hardened OpenTofu/Terraform AWS configuration from security-baked templates.
- Templates: `_base`, `s3-secure-bucket`, `iam-gitlab-oidc`, `route53-acm`, `observability-baseline`, `vpc-network`, `lambda-api`, `dynamodb-table`, `state-bootstrap`.
- `scripts/new-config.sh`: assembles `_base` + chosen templates into a standalone config.
- Offline verification gate `scripts/test/selftest.sh`.

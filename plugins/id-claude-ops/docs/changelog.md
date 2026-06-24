# Changelog

All notable changes to the ID Claude Ops plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),

## [1.22.6] - 2026-06-23

### Fixed
- `create-kolla-invite`: invite link table now renders first in the HubSpot human note, above the fold. Previously the facility details table came first, burying the link. Template updated: invite link + expiry at top, facility details below.

## [1.22.5] - 2026-06-22

### Fixed
- `hubspot-ticket-generator`: external ticketing system detection now checks the `jobtitle` field for portal URLs (in addition to `email`). P4D HELPDESK TICKET SYSTEM stores its portal URL (`https://encorehelpdesk.bz/login.php`) in `jobtitle`, causing the contact to be scored incorrectly — Adam Fitzgerald (IT/Install POC) was selected instead. Added a note to fetch `jobtitle` during the scoring pass, not just after. Updated ticket body template to show the portal URL and a "do NOT use email" warning when an external ticketing system contact is selected.

## [1.22.4] - 2026-06-19

### Added
- `build-plugin.sh`: name-matched reference-doc sync (parity with the other ID Claude plugins) — `docs/<skill>.md` is copied into `skills/<skill>/references/<skill>.md` at build time.
- `bitwerx-jira-ticket`: bundled `references/bitwerx-jira-ticket.md` (renamed from `docs/bitwerx-jira.md`) and repointed the skill's "read first" pointer from a hardcoded absolute host path to the bundled copy, so the reference ships inside the installed plugin.
- `full-sync-status`: bundled `references/full-sync-status.md` (renamed from `docs/sync-status-full-process.md`) and repointed the pointer from repo-root `docs/` to the bundled copy.

## [1.22.3] - 2026-06-19

### Changed
- `draft-422-client-email`: Added `mode` input parameter (`"initial"` or `"reminder"`, defaults to `"initial"`). When `mode="reminder"`: subject becomes "Following Up: Unrecognized Tax IDs on Incoming Claims", body opens with a follow-up paragraph instead of the initial outreach copy, and Slack notification label becomes "422 Reminder Draft Created". HubSpot engagement subject updates to match. All other behavior (PDF attachment, POC lookup, engagement logging) is unchanged.

## [1.22.2] - 2026-06-19

### Changed
- `client-comms`: Added skill-logger call as Step 6 at end of workflow.
- `goldeneye-tin-normalization`: Added skill-logger call as Step 4 at end of workflow.
- `hubspot-human-note`: Added skill-logger call as Step 5 at end of workflow.

## [1.22.1] - 2026-06-19

### Changed
- `draft-422-client-email`: Updated email subject to "Action Needed: Unrecognized Tax IDs on Incoming Claims". Rewrote body copy to emphasize claims won't process until resolved. Added Sean Johnson signature block with InsideDesk logo (inline PNG attachment from `skills/draft-422-client-email/insidedesk-logo.png`). Fixed office list extraction to read directly from `client_data` dict keys. HubSpot engagement subject updated to match.

## [1.22.0] - 2026-06-19

### Changed
- `draft-422-client-email`: Replaced S3 presigned URL flow with direct PDF attachment on Gmail drafts. PDFs are now base64-encoded and attached via the Gmail MCP `create_draft` attachments parameter — no AWS S3 bucket, IAM signer user, or Secrets Manager secret required. Removed all S3/IAM prerequisites from the skill. Email body updated to reference the attached report instead of a link.

### Removed
- `infra/422-reports`: Destroyed all AWS resources provisioned by this OpenTofu module — S3 bucket (`insidedesk-422-reports-982534385600`), IAM user/policy/access key (`insidedesk-422-reports-signer`), and Secrets Manager secret (`insidedesk/422-reports/signer`). Module marked deprecated in README.

## [1.21.4] - 2026-06-18

### Fixed
- `goldeneye-tin-normalization`: Added missing YAML frontmatter to SKILL.md.

## [1.21.3] - 2026-06-18

### Added
- `goldeneye-tin-normalization`: New skill to normalize pasted TIN lists for GoldenEye. Handles delimited and mashed-together input formats, strips non-digits, deduplicates, and outputs a comma-space separated string in a code block.

## [1.21.2] - 2026-06-18

### Changed
- `bitwerx-jira-ticket`: Added `[New Install]` as a distinct issue type (post-install telemetry verification, separate from `[new location]` which provisions the DataCo account pre-install). Updated SKILL.md description, Step 1 issue type list, Step 3 data-gathering section, and Step 4 templates. Added clarifying note explaining the difference between the two types.
- `docs/bitwerx-jira.md`: Added `[New Install]` section with template and when-to-use guidance. Added disambiguation note to `[new location]` section.

## [1.21.1] - 2026-06-17

### Changed
- `create-kolla-invite`: Step 5 now delegates to `hubspot-human-note` instead of building inline HTML. Sections: facility/connector/IDs table, invite link table, next-step text block.
- `bitwerx-jira-ticket`: Step 7 now delegates to `hubspot-human-note`. Single-ticket and multi-ticket patterns use table rows per ticket with dividers between them.
- `create-422-tickets`: Step 8 summary note now delegates to `hubspot-human-note`. Plain-text note replaced with structured sections: summary stats table, per-facility breakdown table, optional unmatched-locations block, next-step text.

## [1.21.0] - 2026-06-17

### Added
- `hubspot-human-note`: New utility skill for posting nicely formatted HTML notes to HubSpot tickets. Supports key-value tables, free-text blocks, and dividers. Uses `associationTypeId: 228` (note → ticket). Designed to be called by other skills as a companion to `hubspot-context-note`. Handles both create and update (PATCH) flows.

## [1.20.0] - 2026-06-17

### Added
- `create-kolla-invite`: New skill to generate a Kolla KollaConnect invite link for a new facility. Looks up facility metadata from GoldenEye, navigates the Kolla Admin Panel to fill and submit the Create Invite Link form, captures the generated URL via JavaScript, posts an HTML note and a base64 Claude context note to the HubSpot install ticket, and calls skill-logger on completion. Timestamp always generated dynamically to avoid year-offset bug.

## [1.19.3] - 2026-06-17

### Changed
- `bitwerx-jira-ticket`: Added Step 7 — after filing the JIRA ticket, if a HubSpot ticket URL was provided, create a formatted HTML note on the ticket with the Bitwerx ticket number(s), issue type, description, and link. Uses `<p>` blocks for readable spacing. Dynamically computed timestamp.

## [1.19.2] - 2026-06-17

### Fixed
- `hubspot-context-note`: Step 3 — added explicit dynamic timestamp generation via Python (`int(datetime.datetime.now().timestamp() * 1000)`). Previously the skill said "current unix timestamp in milliseconds" without showing how, leading to hardcoded values that backdated notes to the wrong year.
- `hubspot-context-note`: Step 3 — fixed association format for new note creation. Replaced `associationTypeId: 18` (which errors with the MCP connector) with `targetObjectType` / `targetObjectId` fields.

## [1.19.1] - 2026-06-17

### Changed
- `draft-422-client-email`: Step 4 — email body now lists affected office names (one per line) between the greeting and the first paragraph, sourced from `client_data.facilities`.

## [1.19.0] - 2026-06-15

### Changed
- `monday-account-update`: Step 1 — added note that board groups stay collapsed after searching; you must click the group header expand arrow to reveal filtered rows within the group.
- `hubspot-ticket-generator`: Step 5 — clarified that `search_crm_objects` via HubSpot MCP does not support the `2-14718097` custom object type (returns VALIDATION_ERROR); must use Desktop Commander with a direct API curl call. Added CONTAINS_TOKEN fallback note for names with bracketed suffixes (e.g. `[SGA]`).
- `hubspot-ticket-generator`: Step 10 — added explicit format warning: context note MUST be the 2-line base64 v2 format per `hubspot-context-note/SKILL.md`; plain-text engagement notes via the engagements API are incorrect.
- `hubspot-ticket-generator`: Added Step 10b — optional Gmail DOS follow-up draft. When user requests it, reads `templates/install/INSTALL - Claim Dates DOS.md` for subject/body template, addresses only Account POC contacts, CCs `install@insidedesk.com`, and logs the draft as an email engagement on the ticket.

## [1.18.0] - 2026-06-15

### Added
- `templates/install/`: 45 HubSpot INSTALL email templates scraped from HubSpot Message Templates. Each file contains the template name, HubSpot ID, subject line, body text (with HubSpot variables preserved), and embedded links.
- `templates/snippets/`: 8 HubSpot Snippets owned by Sean Johnson, scraped from HubSpot. Each file includes the snippet name, ID, shortcode, and content.
- `skills/client-comms`: Added "HubSpot Template Library" reference section pointing to `templates/install/` and `templates/snippets/` so Claude automatically uses templates when drafting INSTALL emails.

## [1.17.0] - 2026-06-15

### Added
- `dataco-sync-status`: New Step 6b — Suggested Actions decision matrix. After reporting status, skill recommends and offers to execute the appropriate next action: (1) Connectivity lost → draft IT contact email via Gmail; (2) Sync stale/failed → file `[Check Sync]` Bitwerx JIRA ticket; (3) Staging/Intermediate stale → file `[Resend Claims]` Bitwerx JIRA ticket. All actions ask Sean to confirm before executing.
- `bitwerx-jira-ticket`: Added `[Resend Claims]` issue type template (fingerprint + staging/intermediate timestamps + "Please resend claims.")
- `docs/bitwerx-jira.md`: Documented `[Resend Claims]` issue type with description template and usage guidance.

## [1.16.3] - 2026-06-15

### Fixed
- `bitwerx-jira-ticket`: `list[0].group?.name` → `list[0].groupName` (API returns groupName as top-level field, not nested under group.name)
- `dataco-sync-status`: Replaced Step 3–4 with correct API usage — all stage data comes from `detail.data.practiceStatus`, not `latestruntimebyjobtype` (that endpoint returns empty data). Added async IIFE pattern requirement and Unix-seconds timestamp note (`* 1000` for JS Date). Fixed connectivity check to use `ps.heartbeatStale` / `ps.lastHeartbeatSuccessful` instead of `list[0].status.heartbeatStatus`.

## [1.16.2] - 2026-06-12

### Changed
- Added skill-logger final step to all qualifying skills for run activity logging

## [1.16.1] - 2026-06-12

### Changed
- `bitwerx-jira-ticket`: Fill Description before Summary in Step 5 to avoid "Suggested Articles" layout shift displacing the editor. Added warning note and updated `find`-tool approach for Send button. Added `Partner ID: {GoldenEye Facility ID}` to the `[new location]` description template.

## [1.16.0] - 2026-06-11

### Changed
- `cancellation-ticket`: Major overhaul with 7 fixes and 3 new features:
  - **Fix**: Note association to CANCELLATIONS custom object now uses two-step approach (create note, then `POST /crm/v4/associations/notes/2-33013991/batch/create` with `USER_DEFINED` typeId 167) — inline association was failing with 400.
  - **Fix**: Context note body now uses standard `🤖 CLAUDE CONTEXT [v2 · ...]` + base64-encoded JSON format.
  - **Fix**: Duplicate check (Step 5) and location search (Step 6a) now use top-level `query` field instead of `filterGroups` + `CONTAINS_TOKEN` — `CONTAINS_TOKEN` returns 400 on custom objects.
  - **New**: PMS swap detection — scans reason text for keywords ("switching to", "replacing", "going away", etc.). Flags as `⚠️ PMS Swap`, sets `type_of_cancellation = "No Location Cancellation"`, maps reason to `PMS Change` / `Removing Legacy PMS Connection`. Does not skip — creates record and flags in report and Slack.
  - **New**: DataCo name check for Bitwerx PMS locations (Eaglesoft, Dentrix, Dentrix Enterprise) — looks up by InsideDesk Partner ID, compares to HubSpot name. Logs discrepancy (DBA renames etc.) and continues; never blocks record creation.
  - **New**: Termination date parsing — extracts "immediately", "effective [date]", "as of [date]", "by [date]", etc. from email body using dateutil. Sets `termination_date` and `cancellation_state` (`Immediate` / `Pending`) fields on the CANCELLATIONS record.
  - **New**: `type_of_cancellation` field now set on all records (`Partial Cancellation (Some Locations, Not All)` default, `No Location Cancellation` for PMS swaps).

## [1.15.2] - 2026-06-11

### Changed
- `monday-account-update`: Standardized text entry to use clipboard-paste approach. Full body
  text is now written to clipboard via `navigator.clipboard.writeText()` and pasted with Cmd+V
  before @mentions are typed — eliminates Monday autocomplete triggering on `@` characters in
  body text (email addresses, CPU specs, etc.). Added explicit guidance for editing existing
  updates: select-all + delete + full re-paste rather than in-place line editing.

## [1.15.1] - 2026-06-11

### Fixed
- `create-422-tickets`: Overhauled duplicate detection to handle clients (e.g. Acme Dental)
  that generate daily 422 errors for the same locations with different TINs as new offices onboard.
  - `is_active()` now treats closed tickets as inactive regardless of when they were closed —
    previously a 14-day closed-ticket window caused recently-closed tickets to block new ones.
  - Front 3 (location overlap) now requires **TIN overlap** in addition to location overlap to
    score 80 pts. Parses TIN values from the existing ticket's Step 8 summary note. Falls back to
    30 pts if the note is in old format (TINs not parseable). Location overlap with different TINs
    scores 0 — same office, new TIN = new issue, new ticket.
  - Reweighted all fronts: Front 1 (20), Front 2 (20), Front 3 (80 or 30), Front 4 (15, 3-day
    window down from 7). Fronts 1+2+4 combined max at 55 (warn+create, never skip).
  - Lower warn+create threshold: 40–79 (was 50–79).
  - Step 8 summary note now includes actual TIN values per facility line so future runs can
    parse them for duplicate detection.

## [1.15.0] - 2026-06-09

### Added
- `dataco-health-check`: New skill — checks https://status.dataco.vet/# for active or
  unresolved DataCo incidents. Returns a structured `DATACO_HEALTH_STATUS` block and a
  ready-to-insert HTML alert banner for downstream report skills. Maps affected components
  (Batch API, PIMS Data, CSV Export, etc.) to expected InsideDesk sync impact. Called
  automatically by pms-oos-report as Step 0.5 before report generation.

## [1.14.0] - 2026-06-09

### Added
- `monday-account-update`: New skill — posts an update note on a dental office item in the MB2
  Inside Desk Install List Monday Board. Handles item search, panel navigation (using the hover
  expand icon to avoid triggering inline editing), and posts with the two-line format: message
  on line 1, @mentions on line 2. Defaults to tagging @Karina Mendoza, @Tye Powell, and
  @David Herrera. Enforces the no-vendor-names language rule for client-visible notes.

## [1.13.0] - 2026-06-09

### Added
- `bitwerx-jira-ticket`: New skill — creates Bitwerx DataCo JIRA Service Desk tickets for
  Bitwerx-synced locations (Dentrix, Dentrix Enterprise, Eaglesoft). Handles all issue types:
  [Check Sync], [Server Swap], [Disable Location], [Reactivate Location], [new location], and
  [Password Request]. Fetches fingerprint from DataCo SupportCo API and facility details from
  GoldenEye, fills the JIRA form, submits, and shares with David Herrera.
- `docs/bitwerx-jira.md`: New reference document covering JIRA URLs, issue type templates,
  form fields, the two Bitwerx identifiers (fingerprint vs API key), post-submission steps,
  and best practices.

## [1.12.0] - 2026-06-09

### Added
- `check-422-tax-ids`: New skill — given a GoldenEye facility ID and a TIN that caused a 422
  snapshot error, navigates to the facility details page and checks whether the TIN is already
  in the Expected TaxIds approved list. Returns a structured `TAXID_CHECK_RESULT:` block for
  use by the 422-tax-id-report workflow, plus a human-readable summary. Supports both automated
  (inputs passed by caller) and manual (AskUserQuestion) modes.

## [1.11.1] - 2026-06-08

### Changed
- `mb2-install-ticket`: Added Step 10 — after writing context notes, unconditionally invoke
  `id-claude-ops:mb2-monday-to-ge` in unattended mode to sync GoldenEye facilities from the
  Monday Board "To Be Installed" group.

## [1.11.0] - 2026-06-08

### Added
- `mb2-monday-to-ge`: New skill — reads the MB2 Monday Board "To Be Installed" group via
  Chrome and creates GoldenEye facility records for any office not yet present. Supports
  manual and unattended modes. Auto-skips duplicates in unattended mode. Maps Full/Reporting
  Only to correct GoldenEye Products selection (Full Access = settings+iq+assist, Reporting
  Only = settings+iq). Permanently excludes Smile Lodge Pediatric Dentistry rows. Designed
  to run as the second step in the scheduled mb2-install-ticket scan.

## [1.10.0] - 2026-06-08

### Changed
- `create-422-tickets`: Replaced three-front sequential dedup with a four-front parallel
  scoring algorithm. All fronts always run — no short-circuiting.
  - **Front 1** (subject match, 60 pts): now includes tickets closed within 14 days, not just open ones.
  - **Front 2** (company ticket, 50 pts): now includes tickets closed within 14 days.
  - **Front 3** (location overlap, 80 pts): now runs **independently** against all company-associated
    tickets — no longer depends on Fronts 1 or 2 finding a hit first. This was the root cause of the
    Acme Dental duplicate: all prior tickets were closed, so Fronts 1/2 found nothing, and Front 3
    never ran.
  - **Front 4** (Gmail sent email, 40 pts): new front — searches sent mail for the client name +
    "Unapproved TIN" within the last 7 days.
  - **Scoring decision**: ≥80 = skip, 50–79 = warn + create, <50 = proceed.
  - `is_active()` helper defined once — open tickets or closed within 14 days.
  - `all_ticket_ids` fetched once in Step 1a and reused by Fronts 2 and 3.

## [1.9.9] - 2026-06-08

### Fixed
- `mb2-install-ticket`: Approval detection now uses `Approved by` in the full email body as the primary signal instead of the presence of a `Vendor:` line. In-house IT installs (e.g. "MB2 IT") don't include a Vendor line and were previously skipped as false negatives.
- `mb2-install-ticket`: `it_type` parsing now also matches "MB2 IT" and "in house IT" variants (previously only matched "party IT").
- `mb2-install-ticket`: Edge case clarified — no Vendor line is normal for in-house IT, not a skip condition.
- `mb2-install-ticket`: Fixed duplicate Step 8 numbering (context note step is now Step 9).

## [1.9.8] - 2026-06-08

### Fixed
- `create-422-tickets`: Three dedup bugs resolved:
  1. **normalize()** — now replaces all dash variants (ASCII `-`, en-dash `–`, em-dash `—`) with a space, collapses runs of whitespace, and lowercases. The old function only stripped ASCII hyphens and didn't collapse whitespace, so `" – Unapproved"` normalized to `"   unapproved"` (triple space) while the expected string had a single space — causing every match to fail silently.
  2. **Front 2 pagination** — companies with many tickets (100+) had their associations truncated; the fetch now paginates through all IDs and batch-reads in chunks of 100.
  3. **Closed-ticket filter** — both Front 1 and Front 2 now exclude tickets in stage `129440439` (Closed), so a resolved prior ticket no longer blocks creating a new one for the same client.

## [1.9.7] - 2026-06-08

### Changed
- `create-422-tickets`: Expanded duplicate check from single subject-match to three independent fronts: (1) normalized subject match, (2) company-associated open ticket search via v4 associations API, (3) location overlap check — resolves location IDs for the incoming facilities and compares against locations already on candidate tickets. Any front that fires blocks ticket creation. Skip report now shows every signal that fired.

## [1.9.6] - 2026-06-08

### Fixed
- `create-422-tickets`: Duplicate-check now normalizes hyphens to spaces before comparing ticket subjects. GoldenEye client keys use hyphens (`Pearl-Street-Dental-Management`) but HubSpot subjects use spaces — without normalization the exact-match check failed and a duplicate ticket was created on subsequent runs.

## [1.9.5] - 2026-06-08

### Fixed
- `draft-422-client-email`: Fixed HubSpot email engagement creation — replaced invalid `hs_email_from_email`/`hs_email_to_email` properties with `hs_email_headers` JSON blob (HubSpot returns 400 if those are set directly).
- `draft-422-client-email`: Fixed ticket association — replaced v4 associations endpoint (fails with `USER_DOES_NOT_HAVE_PERMISSION` regardless of scopes) with v3 `ticket→email` endpoint which works with existing private app permissions.

### Added
- `draft-422-client-email`: New Step 1a — reads and surfaces the Claude Context note from the HubSpot ticket before drafting. Pauses if the note contains an unresolved flag (e.g. duplicate ticket warning).

## [1.9.4] - 2026-06-08

### Changed
- `draft-422-client-email`: Added Step 4a — after creating the Gmail draft, log the email as a HubSpot engagement on the ticket (`POST /crm/v3/objects/emails` + associate via v4 API) so it appears in the ticket activity feed.

## [1.9.3] - 2026-06-05

### Refactored
- `office-ticket-history`: Replaced legacy `_shared/hubspot-setup.md` prereq with standard `get-secret` pattern.
- `draft-422-client-email`: S3 signer credentials now retrieved via `get-secret` instead of raw `subprocess`/`security find-generic-password` calls. Replaced inline `aws secretsmanager` fallback block with `populate-local-secrets` delegation. Fixed profile name casing (`Install-` → `install-`).

## [1.9.2] - 2026-06-05

### Fixed
- `draft-422-client-email`: Resolved `SignatureDoesNotMatch` error on pre-signed S3 URLs. Root cause: `secret_access_key` was `null` in Secrets Manager (never populated correctly at Tofu apply time). Rotated the IAM access key for `insidedesk-422-reports-signer` and updated Secrets Manager with the correct value.

### Changed
- `draft-422-client-email`: Credential source for S3 operations moved from AWS Secrets Manager (required active SSO session) to local macOS Keychain via `security find-generic-password`. Skill now requires no AWS SSO session to run.
- `draft-422-client-email`: Upload and presign now use the same single S3 client (IAM signer credentials). Previously the upload used ambient SSO and the presign used IAM credentials — a split that allowed signature mismatches if credentials diverged.
- `draft-422-client-email`: Prerequisites updated — replaced `aws-login` requirement with `get-secret` calls for `insidedesk-422-reports-signer-key-id` and `insidedesk-422-reports-signer-secret`. Added fallback setup snippet for first-time machine setup.

## [1.9.1] - 2026-05-29

### Changed
- `sync-status`: Step 1 now captures the **Service Date** column from the GoldenEye facility search results table. Adds `last_service_date` and `days_since_dos` fields to the `SYNC_STATUS_RESULT` block.
- `full-sync-status`: Report format now includes a **DOS Status** block derived from `SYNC_STATUS_RESULT.days_since_dos`. Flags ⚠️ when the office is IN_SYNC but has no claims in 14+ days; ✅ if recent; ❓ if no service date on record. No DOS flag shown when office is OUT_OF_SYNC.

## [1.9.0] - 2026-05-29

### Added
- `dataco-sync-status`: New skill — checks the Bitwerx Dataco pipeline stages (Connectivity, Sync, Staging, Intermediate) for a facility via the Dataco API. Returns a structured `DATACO_STATUS_RESULT` with per-stage timestamps and an `overall` verdict (ALL_GREEN / STALE / FAILED / PARTIAL). Designed to be called as a sub-skill for Bitwerx PMS offices (Dentrix, Dentrix Enterprise, Eaglesoft).
- `office-ticket-history`: New skill — searches HubSpot Install Pipeline tickets and Gmail for recent activity related to a dental office. Returns a structured `TICKET_HISTORY_RESULT` with open ticket count, sync-related ticket flag, and Gmail thread summary. Provides context on known issues before creating new tickets.
- `full-sync-status`: New orchestrator skill — calls `sync-status`, `dataco-sync-status` (if Bitwerx PMS), and `office-ticket-history` in sequence, then synthesizes into a single `FULL_SYNC_STATUS_REPORT` with a plain-language verdict and recommended action.
- `docs/sync-status-full-process.md`: Context document explaining the full domain logic for sync status determination — GoldenEye as Step 1, PMS-based branching, Dataco stage meanings, healthy vs. out-of-sync conditions, and follow-up actions.

## [1.8.0] - 2026-05-29

### Added
- `sync-status`: New skill to check whether a facility is syncing with InsideDesk via GoldenEye snapshots. Navigates to the facility's snapshots tab with a 2-day date window, returns a structured `SYNC_STATUS_RESULT` block (IN_SYNC / OUT_OF_SYNC / NEVER_SYNCED) plus a human-readable summary. Designed to be called as a sub-skill from other workflows.

## [1.7.0] - 2026-05-28

### Changed
- All skills: replaced AWS Secrets Manager token fetches with `get-secret` skill calls (`hubspot-token`, `slack-bot-token`).
- All skills: updated `skills/_shared/hubspot-setup.md` and `skills/_shared/slack-setup.md` references to point to `id-claude-shared` plugin.
- `build-plugin.sh`: updated `get_token()` to use macOS Keychain (`security find-generic-password`) instead of AWS Secrets Manager.

## [1.6.0] - 2026-05-28

### Changed
- `goldeneye-ticket` skill renamed to `hubspot-ticket-generator`.

## [1.5.1] - 2026-05-27

### Changed
- `insidedesk-facility-entry`: Major v2 rewrite with security, speed, and guardrail improvements.
  - **Security**: URL validated against three hardcoded allowed domains (production, testing,
    UAT-staging) before any browser connection. TIN values accepted as-is (per InsideDesk 422
    workaround) but flagged in audit log if format is unusual.
  - **PMS mapping**: Full spreadsheet-label → GoldenEye-value mapping table with credential
    requirements and duplicate-name abbreviations for all supported PMS types. Dynamic PMS types
    (denticon, ascend_api, skysync_denticon, skysync_kolla) prompt for credentials before the
    browser loop starts.
  - **Speed**: Full upfront row parse and validation before browser connection. Single batch
    confirm (per-record confirmation removed). No page re-navigation between records — NEW button
    clicked from current state; reload only as fallback.
  - **Guardrails**: Upfront preview table with per-row status flags. Duplicate detection before
    each form open. Progress counter on every action. City/State/Zip parser with US state
    validation.
  - **Audit trail**: CSV audit log and PNG screenshot receipts written to
    `~/insidedesk-logs/facility-entry/YYYY-MM-DD/` after each submission. Credentials for
    dynamic PMS types are never logged.
  - **Dry-run mode**: User can trigger a parse-only run (no browser) to verify spreadsheet
    before committing.

## [1.5.0] - 2026-05-27

### Added
- `insidedesk-facility-entry`: New skill — bulk-enter facility/office records into the
  InsideDesk Operations Dashboard from a spreadsheet using Claude in Chrome. Reads an
  Excel file via pandas, parses office name, address, city/state/zip, phone, tax ID, and
  PMS type, then fills the facility form in the browser one row at a time with per-record
  user confirmation before each submit. Includes PMS type mapping (Dentrix Ascend → dentrix,
  etc.) and handles the Products multi-select (settings, iq, assist). Original skill
  authored by David; v2 enhancements spec in docs/facility-entry-skill-spec.md.

## [1.4.0] - 2026-05-26

### Added
- `cancellation-ticket`: New skill — create HubSpot CANCELLATIONS custom object
  records from Monday Board cancellation-mention emails. Reads Gmail (last 7 days),
  identifies cancellation requests by presence of "cancel" keyword and absence of
  a Vendor: line, looks up the location and company in HubSpot via direct REST API,
  maps free-text reason to the cancellation_reason enum, checks for duplicates, and
  creates a fully-associated Cancellation record (company + location) in the CS
  Investigation pipeline stage. Posts a Slack notification and attaches a Claude
  context note to each record.

## [1.3.0] - 2026-05-19

### Added
- `goldeneye-ticket`: New skill — create HubSpot Install Pipeline tickets from a
  GoldenEye facility URL. Browses the facility detail page to extract location
  metadata (name, PMS, address, phone, products), asks the user for ticket purpose
  (OOS, Account Update, Escalation, Install, Connection Issues), resolves the
  company and IT contact in HubSpot with 4-tier contact scoring (ticketing system
  portal > shared inbox > support role > Account POC), creates the ticket with all
  associations (company, location record, IT contact, Account POCs), writes a Claude
  context note, and posts a Slack summary. Supports Chrome DevTools MCP for
  authenticated GoldenEye browsing with manual fallback.

## [1.2.2] - 2026-05-15

### Changed
- `hubspot-context-note`: Switched to base64-encoded JSON note body. Note appears as a
  two-line block in HubSpot (marker + opaque encoded payload) — machine-readable only.
  Added decode instructions for when Claude reads an existing note.

## [1.2.1] - 2026-05-15

### Changed
- `hubspot-context-note`: Improved note body format — replaced Unicode section dividers
  with labeled key-value lines (ORIGIN / CHECKED / DECISIONS / NEXT) for better
  readability in HubSpot's activity timeline.

## [1.2.0] - 2026-05-15

### Changed
- `create-422-tickets`: Added Step 3 — resolve HubSpot location records for each
  affected facility using `client_id` + name matching (exact then CONTAINS_TOKEN fallback).
  Location records are batch-associated to the ticket after creation using
  v4 associations endpoint (typeId 153, USER_DEFINED). Unmatched facilities are logged
  in the summary note, Slack message, and context note. Added `locations_associated`
  and `locations_unmatched` to the Step 11 return dict.


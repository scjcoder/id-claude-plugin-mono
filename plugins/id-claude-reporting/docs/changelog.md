# Changelog

All notable changes to the ID Claude Reporting plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.9.5] - 2026-06-26

### Added
- morning-brief: add live verification step for Bitwerx JIRA tickets, HubSpot searches, and GoldenEye installs

## [Unreleased]

### Security
- Public-repo hardening: removed `SECURITY_REVIEW.md` from the source and from git
  history (history rewritten + force-pushed). Moved non-secret runtime identifiers
  (AWS account id, internal hostnames, HubSpot portal id, Slack ids) into a gitignored
  `config/insidedesk.local.json`; source now carries placeholders (`<AWS_ACCOUNT_ID>`,
  etc.) resolved via the *Runtime identifiers* table in `CLAUDE.md` and an auto-loading
  config in the shared scripts. Added a repo-wide daily leak scanner (`.security/scan.py`).

## [1.9.4] - 2026-06-22

### Fixed
- `pms-oos-report`: Step 3 split into **3a (mandatory, API-only HubSpot ticket cross-reference)** and 3b (optional, browser-based `full-sync-status` deep dive). Previously ticket lookup was routed only through the heavyweight `full-sync-status`, which unattended/scheduled runs skipped — causing locations with open tickets (e.g. Southern Oak Conway #45736938574, Starlight #45760795171) to be reported as "no ticket." A row may now only be labelled "needs investigation"/"no ticket" after the live HubSpot search returns nothing open; notes-file/memory is never a substitute. Added stage map for Status labelling and a policy reminder forbidding "no ticket" without a confirmed search.

## [1.9.3] - 2026-06-19

### Added
- `build-plugin.sh`: name-matched reference-doc sync. Any `docs/<skill>.md` whose name matches a `skills/<skill>/` directory is copied to `skills/<skill>/references/<skill>.md` before packaging, so repo-root docs ship inside the matching skill at runtime. Docs with no matching skill (e.g. `changelog.md`) are left alone.
- `ascend-activity-report`: bundled `references/ascend-activity-report.md` (full data model, snapshot-first billing rationale, historical-month edge cases) and added a "read first" pointer at the top of the skill so the methodology loads on every run.

## [1.9.2] - 2026-06-19

### Changed
- `422-tax-id-report`: Step 8 overhauled with a two-tier inactivity workflow. New Step 8b — at 10 days old with no client response and no prior reminder, invokes `draft-422-client-email` with `mode="reminder"` using the PDF already attached to the ticket, then writes `reminder_sent: true` + `reminder_date` to the Claude context note. Step 8b renamed to 8c (was "Identify inactive tickets"). Inactivity threshold raised from 14 to 21 days throughout Steps 8c, 9, and 10. Step 9 inactivity note now references the 21-day threshold and whether a 10-day reminder was sent. Step 9c closure report now includes reminder date per ticket. Step 11 outputs now include `reminder_drafts_created`.

## [1.9.1] - 2026-06-19

### Fixed
- `snapshot-error-report`: Step 1 now requires clicking into each date field and typing
  today's date (triple-click → retype) before relying on the JS setter, since URL params
  and JS alone are not sufficient to override React's cached date range. Adds a mandatory
  screenshot verification gate — Claude must confirm both fields show today's date before
  reading any data. Retries until the gate passes.
- `install-team-summary`: Replaced hardcoded `/Users/sean/scoop/shims/python3` path with
  `which python3` lookup; Scoop path does not exist on all machines.

## [1.9.0] - 2026-06-19

### Added
- `morning-brief`: New skill. Generates Sean's daily start-of-day HTML report covering
  today's calendar, priority inbox threads (last 24h), HubSpot open install tickets
  cross-referenced with GoldenEye sync status and Slack #installs, and a short action-items
  list. Delivered as a self-contained HTML file.
  Key logic documented in the skill:
  - 3rd-party IT service desk closures (e.g. Gen4 IT "install complete") are NOT install
    completion — GoldenEye snapshots + Slack #installs are the correct signals.
  - Slack #installs (C03SADVAKNC) applies to new logo installs only; reinstalls/server
    swaps/sync fixes do not post there.
  - Multi-location install tickets require per-location GoldenEye checks, not ticket-level
    assessment.
  - GoldenEye facility search works via the Client filter dropdown, not URL params.

## [1.8.4] - 2026-06-18

### Fixed
- `422-tax-id-report`: Restored GoldenEye facility ID (Fac XXXX) to report output — shown in the facility header in both HTML and PDF.

## [1.8.3] - 2026-06-15

### Changed
- `dos-report`: Added **Days Since Sync** column (from `Days Since Last PMS Snap`) after Days Since DOS — green for 0 days, orange for 1–2 days, so Sean can distinguish billing workflow issues from borderline connection cases at a glance.
- `dos-report`: Report now groups rows by client (alphabetical) with a client-header row, then sorts by Days Since DOS descending within each group. Replaced the old HIGH/MEDIUM section dividers with this layout.
- `dos-report`: Page size switched to landscape to accommodate the extra column; font size reduced to 12px.

## [1.8.2] - 2026-06-12

### Changed
- Added skill-logger final step to all qualifying skills for run activity logging

## [1.8.1] - 2026-06-12

### Fixed
- `422-tax-id-report`: After JS force-setting date inputs, now also dispatches Enter keydown/keyup events and clicks any Search/Apply/Filter button to force a data reload. Increased post-JS wait from 2s to 4s. Added hard stop if date fields don't show the correct date after the JS update — prevents scraping stale data from a previous session's date range.

## [1.8.0] - 2026-06-11

### Changed
- `pms-oos-report`: Added Step 11 — calls `skill-logger` after all primary deliverables complete. Logs skill name, status, OOS counts, archived PDF path, Slack ts, DataCo status, and client/location totals.
- `422-tax-id-report`: Added Step 11 — calls `skill-logger` after HubSpot context notes. Logs skill name, status, date range, clients reported vs filtered, total TINs/claims, tickets created, and inactive tickets closed.

## [1.7.2] - 2026-06-09

### Changed
- `full-historical-client-report`: PDF enhancements — summary stat cards row at top
  (Locations, Active, Cancellations, Tickets, Contacts, Email Threads); Cancellation History
  section header now includes count "Cancellation History (N)" and each record renders as a
  clearly bordered card with "Record N of M" header bar; HubSpot Tickets section grouped by
  pipeline (Onboarding, Support, Install, AR, Claim Feedback, Other) with a coloured sub-header
  per group and per-group count.

## [1.7.1] - 2026-06-09

### Changed
- `full-historical-client-report`: Step 6 rewritten to use `facility=<id>` query
  parameter on the snapshot API — queries per-facility instead of scanning the global
  dataset client-side. Also documents the facility detail API endpoint for name/status
  lookups. Fixes async JS syntax note (must use `(async function(){})()` wrapper).

## [1.7.0] - 2026-06-09

### Added
- `full-historical-client-report`: New skill. Generates a complete client history PDF
  covering all locations (active + inactive), snapshot activity timeline (18 months),
  cancellation records, HubSpot tickets, key contacts, and Gmail email trail.
  Works for Active, At Risk, and Churned clients. Churned clients get a Winback
  Intelligence section with talking points. Pure reporting — no side effects.
  Sources: GoldenEye · HubSpot · Gmail. Monday Board explicitly excluded (MB2-only).

## [1.6.1] - 2026-06-09

### Changed
- `ascend-activity-report`: Added "About This Report" FAQ section at the end of the PDF. Covers how
  the report is built, what counts as billed (HS1 rule), why offboarded locations still appear, and
  what "Newly Onboarded" means.

## [1.6.0] - 2026-06-09

### Changed
- `ascend-activity-report`: **Snapshot data is now the primary billing baseline** instead of the
  GoldenEye Facilities page. Any facility with ≥1 snapshot in the report month is billed — the
  facilities page is now used only as a name/status lookup. This fixes two reliability issues:
  (1) facilities onboarded after the report month no longer appear as false "No Snapshots" entries,
  (2) facilities cancelled after the report month are correctly classified as "Offboarded Still Billed"
  without requiring a separate inactive-page scrape.
- `ascend-activity-report`: Step order restructured — snapshot fetches (Steps 1 & 2) now run
  before the facilities page lookup (Step 3). Classification logic updated to use snapshot-primary model.
- `ascend-activity-report`: "No Snapshots" section redefined as facilities that had prior-month
  snapshots AND are currently active AND had zero snapshots in the report month — eliminates false
  positives from recently-onboarded facilities.
- `ascend-activity-report`: Inactive facilities page scrape removed — offboarded status is now
  inferred by absence from the current active list; snapshot data provides client/facility names directly.

## [1.5.0] - 2026-06-09

### Changed
- `ascend-activity-report`: Report now has three sections instead of two — **Newly Onboarded**, **Offboarded Still Billed**, **Active Full Month** (in that order), plus the existing **No Snapshots** alert section
- `ascend-activity-report`: Skill now fetches prior-month snapshot data to identify newly onboarded locations (in current month but not prior month)
- `ascend-activity-report`: Inactive facility check now correctly flags cancelled locations that still had current-month snapshot activity as "Offboarded — Still Billed"
- `ascend-activity-report`: `generate_report.py` updated with new JSON schema (`onboarded_locations`, `offboarded_locations`), five-stat summary cards, and color-coded sections (teal=onboarded, amber=offboarded, green=active, red=no-snapshots)
- `ascend-activity-report`: Excel Sheet 2 now shows columns for each category (Active Full Month, Newly Onboarded, Offboarded Billed, No Snapshots)
- `ascend-activity-report`: GoldenEye Snapshots API called directly via browser JS using correct param names (`page_size`, `date_from`, `date_to`, `pms_type`) — data exported via Blob download instead of page-by-page navigation

## [1.4.0] - 2026-06-09

### Changed
- `pms-oos-report`: Added Step 0.5 — runs `id-claude-ops:dataco-health-check` before
  report generation. Any active DataCo incident (Batch API, PIMS Data, CSV Export, etc.)
  produces an orange alert banner at the top of the PDF and a callout in the chat response,
  so Sean knows whether elevated OOS counts reflect real issues or a DataCo outage.

## [1.3.1] - 2026-06-09

### Fixed
- `422-tax-id-report`: default date range is now today — no longer asks when no range is provided
- `422-tax-id-report`: `generate_report.py` now handles compact `{count, ids}` taxId format; claim counts and IDs were rendering as literal "count, ids" instead of actual values

## [1.3.0] - 2026-06-08

### Changed
- `422-tax-id-report`: Step 2 JS extraction now uses compact format — builds
  `{count, ids[≤20]}` per tax ID directly in JavaScript instead of returning full
  claim arrays. Prevents buffer truncation on large datasets (e.g. 455 Lone Peak
  claims). Output is bounded regardless of claim volume.
- `422-tax-id-report`: Step 3 updated to merge per-page compact objects rather than
  parsing raw systemMessage rows. Uses `generate_report.py`'s existing `CompactClaims`
  support.

## [1.2.2] - 2026-05-29

### Fixed
- `pms-oos-report`: HubSpot lookback window now scales by severity (5d MEDIUM, 14d HIGH,
  60d CRITICAL) — previously all lookups used 5 days, causing CRITICAL tickets to be missed.
- `pms-oos-report`: After finding a HubSpot ticket, now reads full engagement/note history
  (not just the `content` field which is only the original description).
- `pms-oos-report`: MB2 OOS locations with no ticket now noted as "MB2 help desk process"
  rather than "needs investigation" — no ticket is normal for MB2.

### Added
- `CLAUDE.md`: MB2 client-specific knowledge section documenting Monday Board workflow,
  ticket creation policy, and correct reporting behavior for MB2 OOS locations.

## [1.2.1] - 2026-05-29

### Changed
- `pms-oos-report`: Removed notes file (pms_oos_notes.md) entirely — Steps 2 (load) and
  old Step 10 (update) dropped. HubSpot and Gmail are now the sole live sources of truth.
- `pms-oos-report`: Added Step 4 — if Sean provides context in chat during a run, it is
  used in the report and I offer to save it as a note on the relevant HubSpot ticket.

## [1.2.0] - 2026-05-29

### Added
- `pms-oos-report`: New Step 4 enriches each OOS location with live data from HubSpot
  (Install Pipeline tickets modified/closed within last 5 days) and Gmail (threads within
  last 5 days). Status, Waiting On, and ETA columns now prefer live signal over the static
  notes file. Recently closed HubSpot tickets are flagged as likely resolved. Notes file
  is retained as a fallback when neither connector returns recent activity.

## [1.1.3] - 2026-05-28

### Changed
- `pms-oos-report`: replaced aws-login/Secrets Manager Slack token prerequisite with `get-secret` skill call (`slack-bot-token`). Updated reference to `id-claude-shared` plugin's `skills/_shared/slack-setup.md`.
- `build-plugin.sh`: updated `get_token()` to use macOS Keychain (`security find-generic-password`) instead of AWS Secrets Manager.

## [1.1.2] - 2026-05-19

### Fixed
- `snapshot-error-report` and `422-tax-id-report`: Added JavaScript force-set of date
  inputs after page navigation to guarantee the correct date range is applied. The GoldenEye
  UI can remember stale date ranges from previous sessions; URL params alone are not always
  sufficient to override React's internal state. The fix uses `HTMLInputElement.prototype`
  `value` setter + `input`/`change` event dispatch to update React state directly.

### Changed
- `install-team-summary`: Report rows are now sorted by stage in HubSpot board order
  (New → Sync Issues → Add Loc/Reactivate → Support/Investigation → Escalated →
  Remit → Account Updates → Gmail only).

## [1.1.1] - 2026-05-15

### Changed
- `422-tax-id-report`: Generalized invalid EIN detection — flag is no longer hardcoded to
  tax ID `123`. Any EIN that fails structural validation is flagged with the amber
  ⚠ **Invalid EIN** badge. Rules: must be exactly 9 digits; all-same-digit sequences
  (e.g. `000000000`) and obvious sequences (`123456789`, `987654321`) are also flagged.
- `422-tax-id-report`: Updated SKILL.md to document EIN validation rules and the note that
  GoldenEye stores TINs as digits only (no dashes).

## [1.1.0] - 2026-05-15

### Changed
- `422-tax-id-report`: Tax ID `123` flag upgraded from generic "SUSPICIOUS" badge to
  prominent ⚠ **Invalid EIN** warning (amber styling in HTML, bold red in PDF).
- `422-tax-id-report`: Updated SKILL.md to clarify that `123` is definitively not a valid
  EIN and that it must still be added to GoldenEye config (to unblock the batch) while
  the office fixes the underlying claim in their PMS.

### Updated
- `plugin.json`: Added 422 Tax ID Error report to description and keywords.

## [1.0.0] - 2026-05-14

### Added
- **PMS OOS Report** (`skills/pms-oos-report`): Generates the PMS Out-of-Sync PDF report from a Power BI Excel export, grouped by issue type, delivered to Slack.
- **Power BI Export** (`skills/powerbi-export`): Downloads the PMS Snapshot Monitoring report from Power BI as a date-stamped Excel file.
- **Snapshot Error Report** (`skills/snapshot-error-report`): Reads the GoldenEye Snapshots page and produces an Excel data table and PDF summary of 400/422 errors, delivered to Slack.
- **Install Team Summary** (`skills/install-team-summary`): Weekday morning digest of Gmail and HubSpot Install pipeline activity, delivered as an image to Slack.
- **AWS Login** (`skills/aws-login`): SSO login to the InsideDesk AWS account (<AWS_ACCOUNT_ID>) via the install profile. Auto-triggers on credential errors.
- **Shared utilities** (`skills/_shared`): HubSpot setup, Slack setup, and Slack upload helper shared across reporting skills.

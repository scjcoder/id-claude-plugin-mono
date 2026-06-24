# Changelog

All notable changes to the ID Claude Integrations plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.2] - 2026-06-19

### Added
- `build-plugin.sh`: name-matched reference-doc sync convention (parity with the other ID Claude plugins) — any `docs/<skill>.md` matching a `skills/<skill>/` directory is copied to `skills/<skill>/references/<skill>.md` at build time. No-op today; enables future per-skill reference docs to ship automatically.

### Changed
- `kolla-account-management`, `kolla-health-check`, `verify-claim-ticket`: added a "Log the run" final step (skill-logger call) to each skill.

## [1.2.1] - 2026-06-12

### Changed
- Added skill-logger final step to all qualifying skills for run activity logging

## [1.2.0] - 2026-06-05

### Added
- **Kolla Health Check** (`skills/kolla-health-check`): Sweeps all ACTIVE Kolla linked accounts, pings each via the Integration Metadata API, and DMs Sean on Slack only when one or more are down (ping not alive, or auth_state not VALID). Quiet on healthy runs. Skips DISABLED accounts. Stdlib-only script (`kolla_healthcheck.py`, also embedded in SKILL.md). Intended to back the weekday-morning `kolla-health-check` scheduled task (thin-pointer pattern).

## [1.1.0] - 2026-06-05

### Added
- **Kolla Account Management** (`skills/kolla-account-management`): Manage Kolla linked customer accounts via the Integration Metadata API (`https://api.getkolla.com/connect/v1`). Supports listing linked accounts (with auto-pagination), pinging for health, disabling a connection, and creating KollaConnect invite links. Includes a stdlib-only Python client (`kolla_client.py`, also embedded in SKILL.md) with a CLI. Auth via the `kolla-api-key` keychain secret. Scope is account management only — the Unify data API is owned by the dev team.

## [1.0.1] - 2026-05-28

### Changed
- `build-plugin.sh`: updated `get_token()` to use macOS Keychain (`security find-generic-password`) instead of AWS Secrets Manager. No SKILL.md changes required (no AWS secrets used in skills).

## [1.0.0] - 2026-05-14

### Added
- **AWS Login** (`skills/aws-login`): SSO login to the InsideDesk AWS account (<AWS_ACCOUNT_ID>) via the install profile. Auto-triggers on credential errors.
- **DataCo SupportCo API** (`skills/dataco-supportco-api`): Reference skill for looking up dental practices in Bitwerx DataCo, retrieving fingerprints, and searching by name, practice group, or HubSpot Facility ID.
- **Verify Claim Ticket** (`skills/verify-claim-ticket`): End-to-end verification that a Slack #claim_feedback message flowed through the SQS → Lambda pipeline to a HubSpot ticket.
- **Shared utilities** (`skills/_shared`): HubSpot setup, Slack setup, and Slack upload helper shared across skills.

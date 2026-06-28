# id-claude-ops

A Cowork plugin for InsideDesk client operations workflows. Skills automate HubSpot
ticketing, client offboarding, install coordination, communications, and AWS authentication.

## Skills

| Skill | Description |
|---|---|
| `aws-login` | SSO login to the InsideDesk AWS account. Auto-triggers on credential errors. |
| `bitwerx-jira-ticket` | Create a Bitwerx DataCo JIRA Service Desk ticket for a Bitwerx-synced location (Dentrix, Dentrix Enterprise, or Eaglesoft). Handles Check Sync, Server Swap, Disable/Reactivate, New Install, and Password Request issue types. |
| `cancellation-ticket` | Create HubSpot CANCELLATIONS custom object records from Monday Board cancellation-mention emails. Reads Gmail for the last 7 days. |
| `check-422-tax-ids` | Check whether a TIN that triggered a GoldenEye 422 "Unexpected tax id" error is already in a facility's approved Expected TaxIds list. |
| `chrome-cleanup` | Helper skill to close a Chrome browser tab after use. Gracefully handles missing tabId for non-Chrome skills. |
| `chrome-test` | Test that the Claude in Chrome tool suite is available and functional. Validates browser automation capabilities. |
| `client-comms` | Draft client emails, decision memos, and status updates in Sean's voice. |
| `client-offboarding` | End-to-end cancellation workflow from a HubSpot cancellation ticket URL — full and partial, with Ascend API REMOVE tab output. |
| `client-pms-summary` | Count active locations grouped by PMS type for a client. |
| `create-422-tickets` | Create HubSpot Install Pipeline tickets from 422 Tax ID Error Report data. One ticket per client, with company/contact/location associations and PDF attachment. |
| `create-kolla-invite` | Generate a Kolla KollaConnect invite link for a new InsideDesk facility and log the result to the HubSpot install ticket. |
| `dataco-health-check` | Check the Bitwerx DataCo public status page for active or unresolved incidents. Returns a structured status block for use by downstream skills. |
| `dataco-sync-status` | Check the Bitwerx DataCo sync stage status (Connectivity, Sync, Staging, Intermediate) for a Dentrix/Eaglesoft facility. |
| `draft-422-client-email` | Draft client-facing emails to Account POCs about 422 Tax ID errors, attaching the PDF report and logging a HubSpot engagement. |
| `full-sync-status` | Get a complete sync status overview for a dental office — GoldenEye snapshots, DataCo pipeline stages, and HubSpot/Gmail ticket history. |
| `goldeneye-tin-normalization` | Normalize a pasted list of TINs (strip non-digits, deduplicate, comma-separated) for entry into GoldenEye's Expected Tax IDs field. |
| `hubspot-context-note` | Write or update a structured Claude context note on a HubSpot ticket — called as a final step by other skills. |
| `hubspot-human-note` | Add a formatted HTML note (key/value data, section tables, or free-text) to a HubSpot ticket's activity feed. |
| `hubspot-ticket-generator` | Create a HubSpot Install Pipeline ticket from a GoldenEye facility URL — extracts location data, resolves company and IT contact, creates and associates the ticket. |
| `insidedesk-facility-entry` | Bulk-enter facility/office records into the InsideDesk Operations Dashboard from a spreadsheet (Excel/CSV). |
| `list-client-locations` | Retrieve and display all active locations for a client as a formatted table with PMS info. |
| `mb2-install-ticket` | Create HubSpot Install Pipeline tickets from Monday Board approval emails, with IT c

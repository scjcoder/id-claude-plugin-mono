# Shared: HubSpot Setup for InsideDesk Skills

These steps are reused across multiple InsideDesk skills that need to query the
HubSpot locations custom object (`2-14718097`) directly via API.

---

## A. Find the client in HubSpot

Use `search_crm_objects` on `companies` with the client name as the query. Pull
these properties: `name`, `client_id`, `of_locations___active`, `pms`.

- If multiple matches: show them to the user and ask which one to use.
- Note the `client_id` — this is the key used to link locations.
- Note `of_locations___active` — use this later to verify the count.

---

## B. Retrieve the HubSpot API token

Run the **get-secret** skill with secret name `hubspot-token`.

`get-secret` will:
- Detect whether the current machine is macOS or Windows
- Retrieve the token from the OS-native credential store (Keychain or
  Credential Manager)
- Prompt the user to enter the token on first run, then store it securely

Do **not** fall back to AWS Secrets Manager unless `get-secret` explicitly
fails and you have no other option. The AWS path is the old approach and
requires SSO authentication overhead that `get-secret` avoids.

⚠️ **All Desktop Commander calls that use the token must run via
`mcp__Desktop_Commander__start_process` — NOT `mcp__workspace__bash`.**
The sandbox has no access to the host credential stores.

---

## C. PMS display rules

When presenting PMS values, always apply these substitutions:

| Raw value | Display as |
|---|---|
| `Other` | `Custom FTP` |
| `null` / blank | `Unknown` |
| Everything else | As-is (e.g. EagleSoft, Dentrix, Open Dental) |

`Custom FTP` = InsideDesk's FTP-based connector pulling data from the client's
own data warehouse.

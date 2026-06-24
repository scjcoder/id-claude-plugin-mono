# Future Skills Analysis — Azure, GoldenEye

Analysis of three repos for eventual integration as Claude plugin skills.
Written 2026-05-14. Not yet actioned — revisit when ready.

---

## Repos Reviewed

| Repo | GitLab | Status |
|---|---|---|
| `insidedesk-azure` | `git@gitlab.com:insidedesk/insidedesk-azure.git` | Reference data only — skill to build from scratch |
| `claude-goldeneye` | `git@gitlab.com:insidedesk/claude-goldeneye.git` | Proto-skill — mostly ready to port |
| `goldeneye` | `git@gitlab.com:insidedesk/goldeneye.git` | Obsolete (Selenium era) — do not port |

---

## 1. `insidedesk-azure` → `azure-onboard-user` skill

### What the repo contains
- `CLAUDE.md` — well-documented context for automation
- `azure_onboarding_reference.yaml` — canonical source of truth for all Azure/Entra ID
  object IDs: tenant info, licenses (Power BI Pro SKU), security groups (product tiers
  + ~30 per-client RLS groups), directory roles, app registrations, key service accounts

### What maps well to a skill
The client user onboarding sequence is documented and repeatable:
1. Create user in Entra ID (`insidedesk.com` domain)
2. Assign Power BI Pro license (`f8a1db68-be16-40ed-86d5-cb42ce701560`)
3. Add to **All Company** group
4. Add to product tier group (`BI_ADVANTAGE`, `BI_ESSENTIAL`, or `BI_CLASSIC`)
5. Add to client-specific RLS group (`PBI_ACCESS_<CLIENT>`)
   — create the group first if this is a new client

All required IDs are already in `azure_onboarding_reference.yaml`.

### What does NOT make sense to incorporate
- No existing automation scripts to port — skill would be built fresh using Microsoft Graph API
- The directory roles section (15 roles + member lists) is admin-reference context, not
  something a skill needs to act on
- The `PBI_ACCESS_*` group list will drift as clients are added/offboarded

### Key concerns before building
- **Auth is undefined.** The repo mentions `install@insidedesk.com` as the service account
  but doesn't specify how credentials are stored. This skill needs a different auth path
  than the AWS SSO pattern used everywhere else — likely Microsoft Graph API with a service
  principal or client secret. Unclear if those credentials currently live in AWS Secrets Manager.
- **The YAML will go stale.** As new clients are added, `azure_onboarding_reference.yaml`
  needs new `PBI_ACCESS_<CLIENT>` group entries. The skill needs a maintenance strategy for this.

### Open questions to resolve before building
1. How should the skill authenticate to Microsoft Graph? Service principal with client
   secret, or `install@insidedesk.com` credentials? Are those stored in AWS Secrets Manager
   already, or somewhere else?
2. Beyond user onboarding, what else should be covered? Candidates:
   - Check/remove group membership
   - Create new `PBI_ACCESS_<CLIENT>` group for a new client
   - User offboarding (license removal + group removal)
3. Should the skill read `azure_onboarding_reference.yaml` from the repo at runtime
   (via Desktop Commander), or embed a snapshot in SKILL.md?

---

## 2. `claude-goldeneye` → `goldeneye-facility-creator` skill

### What the repo contains
- `CLAUDE.md` — detailed and well-written skill documentation (essentially already a SKILL.md)
- `goldeneye_facility_creator.py` — production-quality Python script (~550 lines) that:
  - Reads an InsideDesk Office List `.xlsx` spreadsheet
  - Handles three template versions (new / old / oldest)
  - Normalizes phone, EIN, address, PMS, tags
  - Detects duplicate facility names
  - Prints a pre-flight report and saves parsed JSON
  - Exit code `0` = ready, `1` = blocking issues

### What maps well to a skill
This is the most plug-and-play of the three. Workflow:
1. Accept an Office List `.xlsx` attachment
2. Run `goldeneye_facility_creator.py` via Desktop Commander — review pre-flight report
3. Resolve any errors/credential requirements/duplicate names before proceeding
4. Use Claude in Chrome to create each facility in GoldenEye `/testing` one by one
5. Confirm "facility created" toast after each submit

SKILL.md = lightly adapted `CLAUDE.md` + bundle the Python script alongside it.

### What does NOT make sense to incorporate
- `dashboard/` — a standalone Eleventy web app (own `package.json`, CSS, JS components,
  Playwright tests). Early prototype monitoring UI. No role in a Claude skill.
- `docs/` — standard repo docs (changelog, contributing, installation, troubleshooting).
  Not skill content.
- `.gitlab-ci.yml` — CI pipeline config. Not relevant.

### Open questions to resolve before building
4. The Python script currently runs as `python3 goldeneye_facility_creator.py <xlsx>`.
   In the plugin it would run via Desktop Commander. Is that approach fine, or any changes wanted?
5. Beyond facility creation, what other GoldenEye operations should be covered?
   Candidates:
   - Snapshot error report (currently in the reporting plugin — move here?)
   - Edit / disable / enable facilities
   - Any other admin operations
6. Should the skill support `/production` at all (with a heavy confirmation gate),
   or is `/testing` the only environment it should ever touch?

---

## 3. `goldeneye` (old repo) → Do NOT port

### What it is
The original Selenium WebDriver-based GoldenEye automation — a full Python project
(`form_filler.py`, `test_form_filler.py`, config/data JSON, Google Apps Script normalizer,
web dashboard, `flake8`/`pyproject.toml` tooling, and AI-generated spec documents).

### Why nothing should be ported
- Selenium-based browser automation is entirely superseded by Claude in Chrome
- Field validation logic in `form_filler.py` is superseded by the more complete
  normalizer in `claude-goldeneye/goldeneye_facility_creator.py`
- Google Apps Script / Google Sheets data pipeline is superseded by the xlsx workflow
- The web dashboard is a standalone app with no role in a Claude skill
- The 9 `documentation/` files are AI-generated specs from the original design phase
  describing the Selenium architecture

### One thing to verify before fully closing
Check that `form_filler.py`'s `FieldValidator` class doesn't cover any edge cases
that `goldeneye_facility_creator.py` misses. At a glance it doesn't — the new script
is more comprehensive — but worth a quick compare.

---

## Recommended Build Order (when ready)

1. **`goldeneye-facility-creator`** — lowest effort, highest value, already mostly written.
   No auth unknowns. Start here.
2. **`azure-onboard-user`** — high value but blocked on resolving the auth question first.
   Resolve credentials storage before starting.
3. **Additional GoldenEye operations** (snapshot report migration, etc.) — after the
   facility creator is live and the scope question (Q5 above) is answered.

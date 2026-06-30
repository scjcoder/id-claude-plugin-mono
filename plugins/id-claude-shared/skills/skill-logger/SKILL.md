---
name: skill-logger
description: >
  Append a structured run log to the InsideDesk skill activity log repo.
  Call this skill as the FINAL step of any skill that should be logged.
  The caller passes a payload describing what ran, what the outcome was,
  inputs received, outputs produced, and any errors. The skill writes a
  human-readable + JSON entry to a dated markdown file in the log repo
  and commits the change. Self-bootstrapping: creates the log repo and
  runs git init on first use if the directory does not exist.
  Trigger when any other InsideDesk skill instructs you to "call skill-logger"
  or "log this run".
---

# Skill: skill-logger

Append a structured run entry to the InsideDesk skill activity log repo.
Each entry is dual-format: a human-readable summary block followed by a
fenced JSON block — readable in a text editor or git diff, and parseable
by a future Claude session without any decoding step.

The log repo is a plain local git repo. No remote is required. Any user
running this skill gets their own local log history bootstrapped automatically.

---

## Prerequisites

⚠️ **All commands must run via Desktop Commander (`mcp__Desktop_Commander__start_process`),
NOT `mcp__workspace__bash`.** The sandbox is an isolated Linux VM with no access to the
host filesystem where the log repo lives.

---

## Step 1 — Determine the log repo path

**Default path:** `~/CODE/id-sean-logs`
(expands to `/Users/<username>/CODE/id-sean-logs` on macOS)

**Override:** If the current project's `CLAUDE.md` contains a line of the form:
```
skill-logger-log-repo: /path/to/custom/log/repo
```
use that path instead. The GitLab remote is already configured in this repo — the push step in Step 6 will push automatically.

Never prompt Sean for this path unless the default fails for a clear reason.

---

## Step 2 — Bootstrap the repo (first-time setup)

Check whether the log repo exists and has been initialized:

```bash
[ -d "{LOG_REPO}/.git" ] && echo "exists" || echo "init-needed"
```

If `init-needed`:

```bash
mkdir -p "{LOG_REPO}"
cd "{LOG_REPO}"
git init
git commit --allow-empty -m "chore: initialize skill activity log repo"
echo "# InsideDesk Skill Activity Log" > README.md
git add README.md
git commit -m "docs: add README"
```

Print: `✅ Initialized new log repo at {LOG_REPO}`

This runs silently on subsequent calls (`.git` already exists → skip entirely).

---

## Step 3 — Build the log entry

Construct the entry from the payload passed by the calling skill:

| Field | Required | Description |
|---|---|---|
| `skill_name` | ✅ | Canonical skill name (e.g. `pms-oos-report`) |
| `status` | ✅ | `success`, `partial`, or `error` |
| `summary` | ✅ | 1–3 sentence plain-English description of what ran and what happened |
| `inputs` | ✅ | Key inputs the skill received (file path, client name, date range, etc.) |
| `outputs` | ✅ | What was created or changed (file path, Slack ts, ticket URL, counts, etc.) |
| `errors` | ❌ | Any failures or skipped steps (omit or `{}` if none) |
| `metadata` | ❌ | Any additional structured data worth preserving (counts, flags, external status, etc.) |

**Entry format (human-readable block + JSON block):**

```
## HH:MM — {skill_name} [{status}]

**Summary:** {summary}
**Inputs:** {inputs — key=value pairs separated by · }
**Outputs:** {outputs — key=value pairs separated by · }
{**Errors:** {errors_str} — omit this line entirely if no errors}

```json
{
  "skill": "{skill_name}",
  "status": "{status}",
  "timestamp": "{YYYY-MM-DDTHH:MM:SS}",
  "inputs": { ... },
  "outputs": { ... },
  "errors": { ... },
  "metadata": { ... }
}
```
```

Rules:
- `errors` and `metadata` keys are always present in the JSON block (use `{}` if empty).
- Keep the **Summary** line tight — one to three sentences max.
- **Inputs** / **Outputs** lines use ` · ` as separator (e.g. `file=PMS_Sync.xlsx · source=powerbi`).
- Never truncate the JSON block — include all fields passed by the caller.
- Timestamp is local time: `datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')`.

---

## Step 4 — Determine the log file path

```
{LOG_REPO}/logs/YYYY/MM/YYYY-MM-DD.md
```

Example: `/Users/sean/CODE/id-sean-logs/logs/2026/06/2026-06-11.md`

---

## Step 5 — Write (append) the entry

Use a Python script via Desktop Commander to avoid shell-escaping issues with
special characters in the JSON payload:

```bash
python3 -c "
import json, datetime, pathlib

LOG_REPO = '{LOG_REPO}'
today    = datetime.date.today()
now_str  = datetime.datetime.now().strftime('%H:%M')
ts       = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

skill_name    = '{skill_name}'
status        = '{status}'
summary       = '''{summary}'''
inputs_str    = '{inputs_str}'
outputs_str   = '{outputs_str}'
errors_str    = '{errors_str}'   # empty string if no errors
inputs_dict   = {inputs_dict}
outputs_dict  = {outputs_dict}
errors_dict   = {errors_dict}
metadata_dict = {metadata_dict}

json_block = json.dumps({
    'skill':     skill_name,
    'status':    status,
    'timestamp': ts,
    'inputs':    inputs_dict,
    'outputs':   outputs_dict,
    'errors':    errors_dict,
    'metadata':  metadata_dict,
}, indent=2)

errors_line = f'\n**Errors:** {errors_str}' if errors_dict else ''
entry = f'''
## {now_str} — {skill_name} [{status}]

**Summary:** {summary}
**Inputs:** {inputs_str}
**Outputs:** {outputs_str}{errors_line}

\`\`\`json
{json_block}
\`\`\`
'''

log_dir  = pathlib.Path(LOG_REPO) / 'logs' / today.strftime('%Y') / today.strftime('%m')
log_file = log_dir / f'{today}.md'
log_dir.mkdir(parents=True, exist_ok=True)

if not log_file.exists():
    log_file.write_text(f'# Skill Log — {today}\n' + entry)
else:
    with open(log_file, 'a') as f:
        f.write(entry)

print(f'OK: {log_file}')
"
```

Substitute all `{...}` placeholders with actual values before running. For dict values,
pass valid Python dict literals (e.g. `{'file': 'report.xlsx', 'count': 6}`).

---

## Step 6 — Commit (and push if remote exists)

```bash
cd "{LOG_REPO}" && \
git add logs/ && \
git commit -m "log({skill_name}): {status} — {YYYY-MM-DD}"
```

Then check for a remote before pushing — don't fail if there isn't one:

```bash
cd "{LOG_REPO}" && \
git remote get-url origin 2>/dev/null && \
  (git push || (git pull --rebase && git push)) || \
  echo "No remote configured — skipping push"
```

**If git fails entirely** (disk full, permissions, etc.): print the error, do NOT
surface it to Sean as a skill failure. The primary skill already succeeded. Logging is best-effort.

---

## Step 7 — Chrome tab teardown (Chrome-using callers only)

If the calling skill opened any Chrome tabs during its run, **close them before logging**.
Each new task/session creates its own tab group; tabs are not cleaned up automatically,
so they accumulate across scheduled runs.

Use `tabs_close_mcp` for each tab ID the skill opened:

```
mcp__Claude_in_Chrome__tabs_close_mcp(tabId: <id>)
```

If the skill used `tabs_context_mcp` at startup to get existing tabs, close only tabs
it **created** (not tabs that were already open). If the skill created a fresh group
(no prior tabs existed), close all tabs in the group.

Skills with a teardown obligation (audit as of 2026-06-15):
- **id-claude-ops:** bitwerx-jira-ticket, check-422-tax-ids, client-offboarding, hubspot-ticket-generator, insidedesk-facility-entry, mb2-monday-to-ge, sync-status
- **id-claude-reporting:** 422-tax-id-report, ascend-activity-report, full-historical-client-report, pms-oos-report, powerbi-export, snapshot-error-report

Skills that use Chrome but do NOT call skill-logger (handle teardown internally):
- **id-claude-ops:** dataco-health-check

---

## Step 8 — Return to calling skill

Confirm with a single line — no more detail needed:

```
✅ Logged to logs/YYYY/MM/YYYY-MM-DD.md
```

If logging failed: `⚠️ skill-logger: {error}` — then continue.

---

## Example completed entry

```markdown
## 07:43 — pms-oos-report [success]

**Summary:** Generated PMS Out-of-Sync report for 47 active locations across 12 clients. 6 locations flagged OOS (1 CRITICAL, 3 HIGH, 2 MEDIUM). PDF delivered to Sean's Slack DM and archived.
**Inputs:** file=PMS_Sync_Status_Report_2026-06-11.xlsx · source=powerbi · dataco_status=OPERATIONAL
**Outputs:** pdf=reports/pms-oos/2026/06/PMS_OOS_Report_2026-06-11.pdf · slack_ts=1749636183.123 · oos_count=6 · onboarding_count=3

```json
{
  "skill": "pms-oos-report",
  "status": "success",
  "timestamp": "2026-06-11T07:43:12",
  "inputs": {
    "file": "PMS_Sync_Status_Report_2026-06-11.xlsx",
    "source": "powerbi",
    "dataco_status": "OPERATIONAL"
  },
  "outputs": {
    "pdf": "reports/pms-oos/2026/06/PMS_OOS_Report_2026-06-11.pdf",
    "slack_ts": "1749636183.123",
    "oos_count": 6,
    "onboarding_count": 3,
    "pending_cancel_count": 8
  },
  "errors": {},
  "metadata": {
    "total_active_locations": 47,
    "total_clients": 12,
    "dataco_alert_shown": false
  }
}
```
```

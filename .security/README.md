# `.security/` — repo leak scanner

This directory holds a self-contained security scanner for **this public repo**.
It runs daily (scheduled task `repo-security-scan`) and can also gate CI.

## Run it

```bash
python3 .security/scan.py            # human summary, writes .security/reports/scan-YYYY-MM-DD.json
python3 .security/scan.py --json     # machine-readable JSON to stdout
python3 .security/scan.py --update-baseline   # accept current findings as known
```

Exit codes: `0` clean · `2` new findings · `1` scanner error.
No dependencies — Python 3 stdlib + the `git` CLI only.

## What it checks

- **Secrets** (critical/high) in the working tree **and the full git history**:
  AWS keys, Slack/GitHub/GitLab tokens, Google/OpenAI/HubSpot keys, private-key
  blocks, JWTs, and generic `secret = "literal"` assignments.
- **Internal-identifier disclosure** (medium/low) in the working tree: AWS account
  id, internal hostnames, AWS SSO portal, HubSpot portal id, Slack ids, and any
  `SECURITY_REVIEW.md` tracked on the public repo.

## Baseline

`baseline.json` lists fingerprints of **accepted** findings so routine runs stay
quiet and only *new* exposure alerts. When you intentionally add a known-safe
identifier, run `--update-baseline` and commit the change. Review baseline diffs
in PRs — a growing baseline can hide real leaks.

## Known residual exposure (accepted, see baseline)

These are operational references embedded in skill instructions; removing them
would break the skills, and none are secrets (useless without a credential):

- AWS account id `<AWS_ACCOUNT_ID>`, profile `Install-<AWS_ACCOUNT_ID>`
- Internal hostnames `<GOLDENEYE_HOST>`, `<ADMIN_API_HOST>`
- AWS SSO portal `<AWS_SSO_PORTAL>`
- HubSpot portal id `<HUBSPOT_PORTAL_ID>`, various Slack ids

**Recommended longer-term cleanup:** move these to a single ignored config file
the skills read at runtime, so the public source carries placeholders only.

## History note

`SECURITY_REVIEW.md` files were untracked and gitignored on 2026-06-24, but they
remain in earlier pushed commits. To purge them from public history entirely,
rewrite history (`git filter-repo --invert-paths --path-glob '*SECURITY_REVIEW.md'`)
and force-push **both** remotes — coordinate before doing this.

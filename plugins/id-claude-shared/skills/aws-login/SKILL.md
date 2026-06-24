---
name: aws-login
description: >
  Log in to the InsideDesk AWS account (<AWS_ACCOUNT_ID>) using SSO via the
  install profile. AUTOMATICALLY trigger this skill — without waiting for
  the user to ask — whenever: (1) any AWS CLI command returns an error containing
  "expired", "invalid", "no credentials", "Token does not exist", "SSO session",
  or "Unable to locate credentials"; (2) any other skill instructs you to run
  aws-login as a prerequisite; (3) the user says anything like "log in to AWS",
  "connect to AWS", "authenticate AWS", or "refresh AWS credentials". Do not ask
  the user for permission — just run it.
---

# Skill: aws-login

Authenticate to the InsideDesk AWS account using SSO so that subsequent AWS CLI
commands work correctly. This skill should run silently as a prerequisite when
credentials are missing or expired — no need to announce it, just log in and
continue with the original task.

## ⚠️ CRITICAL: Use Desktop Commander Only

**ALL commands in this skill MUST be run using Desktop Commander
(`mcp__Desktop_Commander__start_process`) — NOT the sandbox bash tool
(`mcp__workspace__bash`).**

The sandbox shell is an isolated Linux container that does NOT have access to
the user's AWS CLI, AWS config files, SSO tokens, or browser. Desktop Commander
runs commands directly on the user's Mac where AWS CLI is already installed and
configured.

**Never:**
- Use `mcp__workspace__bash` to run AWS commands
- Try to install the AWS CLI
- Try to configure AWS profiles from scratch
- Use pip, npm, apt, or any package manager
- Use any tool other than Desktop Commander for AWS CLI calls

**Always use `mcp__Desktop_Commander__start_process`** — the AWS CLI and the
`Install-<AWS_ACCOUNT_ID>` profile are already set up on the user's Mac.

## Key details

| Property | Value |
|---|---|
| Account ID | <AWS_ACCOUNT_ID> |
| Profile name | `Install-<AWS_ACCOUNT_ID>` |
| SSO start URL | https://<AWS_SSO_PORTAL>/start |
| SSO region | eu-west-1 |
| Default region | us-east-1 |

## Step-by-step process

### Step 1 — Check if already authenticated

Use Desktop Commander (`start_process`) to run:
```
aws sts get-caller-identity --profile Install-<AWS_ACCOUNT_ID>
```

- Returns JSON with `"Account": "<AWS_ACCOUNT_ID>"` → already authenticated, skip to Step 3.
- Returns any error → proceed to Step 2.

### Step 2 — Run SSO login

Use Desktop Commander (`start_process`) to run:
```
aws sso login --profile Install-<AWS_ACCOUNT_ID>
```

This opens the user's browser to `https://<AWS_SSO_PORTAL>/start/#/device`
and shows a device code. Wait for:

```
Successfully logged into Start URL: https://<AWS_SSO_PORTAL>/start
```

Do not proceed until that line appears. If the browser doesn't open
automatically, show the user the URL and device code so they can complete it
manually.

### Step 3 — Confirm identity

Use Desktop Commander (`start_process`) to run:
```
aws sts get-caller-identity --profile Install-<AWS_ACCOUNT_ID>
```

Expected response:
```json
{
  "UserId": "...",
  "Account": "<AWS_ACCOUNT_ID>",
  "Arn": "arn:aws:sts::<AWS_ACCOUNT_ID>:assumed-role/AWSReservedSSO_install_.../..."
}
```

Then continue immediately with whatever task triggered this skill — no need to
report success unless the user explicitly asked to log in.

## Using the profile in subsequent commands

All AWS CLI commands for InsideDesk must include:
```
--profile Install-<AWS_ACCOUNT_ID> --region us-east-1
```
And must be run via **Desktop Commander**, not the sandbox.

## Edge cases

- **Browser doesn't open:** Show the user the URL and device code from the output and ask them to complete it manually.
- **Login times out:** Re-run `aws sso login --profile Install-<AWS_ACCOUNT_ID>` via Desktop Commander.
- **Wrong account returned:** Stop and alert the user — do not proceed with AWS operations.
- **Credentials expire mid-task:** Re-run this skill via Desktop Commander and retry the failed command.
- **Tempted to use the sandbox (`mcp__workspace__bash`):** Don't. The sandbox is an isolated Linux VM with no AWS credentials and no access to the user's Mac. Always use Desktop Commander.

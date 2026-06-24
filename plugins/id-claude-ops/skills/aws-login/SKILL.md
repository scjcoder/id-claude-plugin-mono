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

> **This skill has moved.**
> The canonical implementation lives in the **id-claude-shared** plugin:
> `skills/aws-login/SKILL.md`
>
> Load and follow that skill. Do not implement the steps here.
> If id-claude-shared is not loaded, read `/Users/sean/CODE/id-claude-shared/skills/aws-login/SKILL.md` directly.

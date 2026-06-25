# Rule Conventions

How to read every rule file in this repo.

## Enforcement tiers (RFC 2119)

| Tier | Meaning | If violated |
|------|---------|-------------|
| **MUST** | Hard requirement. No exceptions without explicit human sign-off. | Block the commit/PR. Fix before proceeding. |
| **SHOULD** | Strong default. Deviate only with a documented reason. | Flag it, note the reason in the PR or a comment. |
| **MAY** | Optional / situational. Allowed, not required. | No action needed. |

When tiers conflict, the **most restrictive wins**, and a stack overlay can only
tighten a core rule (MAY→SHOULD→MUST), never loosen it.

## Rule format

Each rule reads:

> **[TIER]** The rule, stated as an imperative. *Why:* the rationale (when not obvious).

Good/bad code blocks use `❌` for the anti-pattern and `✅` for the correct form.

## Precedence order

1. Explicit human instruction in the current session.
2. Stack overlay (`stacks/*.md`) for the stack in play.
3. Core rules (`rules/*.md`).
4. Tool defaults (linter/formatter config).

A human instruction can override a SHOULD silently, but overriding a **MUST**
requires the human to say so explicitly — the agent must not self-authorize it.

## The meta-rules

- **MUST** prove changes work before declaring done — run the linter, formatter, and tests.
- **MUST** fix root causes, not symptoms.
- **MUST NOT** claim "it should work" — demonstrate it.
- **SHOULD** prefer reusable, documented systems over one-offs.

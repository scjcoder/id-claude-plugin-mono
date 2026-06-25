# Pre-Commit Checklist

Run before every commit. Maps to the `clean-code-pass` pre-commit gate.

- [ ] Code can be understood in 6 months with no extra context.
- [ ] Names are clear without needing comments.
- [ ] Each function does ONE thing, under ~20 lines.
- [ ] All files under 300 lines.
- [ ] Errors handled — no silent failures, specific exception types.
- [ ] All external input validated and sanitized.
- [ ] No secrets, keys, or PII in code or logs.
- [ ] Duplication eliminated; dead code removed.
- [ ] Dependencies injected, not hardcoded.
- [ ] Types explicit (where the language supports it).
- [ ] Comments explain WHY, not WHAT.
- [ ] Formatter ran clean; linter passes.
- [ ] Tests pass; coverage gaps noted as TODOs.
- [ ] `git status` clean — no untracked files left.
- [ ] Conventional commit message with verbose, full-context body.

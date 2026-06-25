# Pre-PR Checklist

Run before opening a pull request. Builds on the [pre-commit checklist](pre-commit.md).

## Quality

- [ ] Full `clean-code-pass` 13-pass review run on the diff.
- [ ] No file in the diff ≥ 300 lines.
- [ ] No "it should work" — every change demonstrated to work.

## Verification

- [ ] Formatter, linter, and full test suite all green locally.
- [ ] End-to-end flow tested, not just individual units.
- [ ] Regressions checked — existing tests still pass.

## Security

- [ ] `security-review` run on the diff if it touches auth, money, PII, or infra trust.
- [ ] No secrets added; trust policies pinned to stable IDs (if IaC/OIDC).

## Hygiene

- [ ] Submodules committed and pushed before the parent repo.
- [ ] Branch rebased/squashed to readable history.
- [ ] PR description: what changed, why, how it was verified.
- [ ] Test coverage gaps documented as TODOs with risk levels.

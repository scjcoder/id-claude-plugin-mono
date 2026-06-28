---
name: test-suite-bootstrap
description: >
  Scaffold a maintainable test suite for a project that has little or none —
  an app harness for side-effect-heavy integration coverage plus fast deterministic
  unit coverage for pure logic, with coverage targets scaled to codebase maturity.
  Use this skill when the user asks to "add tests", "set up a test suite", or
  "bootstrap testing" for a legacy or undertested codebase.
---

# Test suite bootstrap

Designed for codebases that need both integration-style coverage (for
side-effect-heavy modules: DOM, storage, network) and fast deterministic unit
coverage (for pure logic: parsing, validation, calculations) — not just one or the
other.

## 1. Confirm test runner and structure

Check what's already in place before adding anything:

```bash
cat package.json | grep -A5 '"scripts"'   # existing test script?
ls tests/ test/ __tests__/ 2>/dev/null     # existing test directory convention?
```

If nothing exists, create the directories:

```bash
mkdir -p tests/helpers src
```

## 2. Build the app harness

Create `tests/helpers/appHarness.js` (or the project's equivalent language/runner) —
a single setup module that test files import, rather than each test file
duplicating its own fixture setup. It should:

- Build/teardown whatever DOM, fixture data, or mock storage the app's
  integration tests need (forms, lists, modals, status indicators — whatever
  surfaces the actual app has)
- Stay generic — fixture *shape*, not project-specific assertions. Assertions
  belong in the test files that use the harness, not in the harness itself.
- Expose its real storage/session keys as constants at the top of the file so
  tests reference the constant, not a hardcoded string, if the app's auth or
  state persistence uses storage keys.

## 3. Write the integration test file

`tests/app.integration.test.js`, importing the harness and the project's real
primary module. Cover the actual flows that exist in the app, not generic
placeholders:

- Startup / auth, if the app has it
- Data persistence (save, reload, survive a refresh)
- Destructive actions (delete, reset, irreversible state changes)
- Event-driven UI paths (user triggers X, Y should follow)

Keep these tests behavior-focused — assert on outcomes the user would notice, not
on internal implementation details that'll break on a harmless refactor.

## 4. Write the unit test file

`tests/logic.test.js`, importing the project's actual pure-logic module(s) from
`src/`. Prioritize edge cases: parsing boundary conditions, normalization,
numeric thresholds, guard clauses. Pure-logic tests should run fast with zero
mocking — if a "unit" test needs a mock, it's testing something with a side
effect and belongs in the integration file instead.

## 5. Wire up the test runner

Add to `package.json` (or the project's config file): a `test` script, a
`test:coverage` script, and whatever `devDependencies` the chosen test runner
needs. Resolve any version conflicts using whatever dependency strategy the
project already follows — don't introduce a second package manager or a
conflicting major version of an existing dependency.

## 6. Run and iterate by coverage

```bash
npm install
npm test
npm run test:coverage
```

Target high-risk *uncovered* branches first — don't chase percentage with
low-value assertions on code that's already simple and unlikely to break.

## Coverage targets by maturity

| Codebase state | Target |
|---|---|
| Legacy / monolith, just starting | 75–85% |
| Mature, modular | 85–95% |

Raise the threshold as the architecture becomes more testable — don't set a high
bar before the code is structured to meet it.

## Keep test infrastructure reusable

If this harness pattern is being extracted into a shared template for reuse across
projects, keep the shared version generic (fixture shape, not project assertions)
and treat each project's actual tests as usage examples, not as the source of
truth for what the shared harness should contain.

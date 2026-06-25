---
name: clean-code-pass
description: >
  A 13-pass systematic code review and refactoring workflow that transforms code
  from rough to production-ready. Covers pre-flight scoping, naming, function design,
  complexity + file length enforcement, error handling, security, DRY, dead code
  elimination, dependency decoupling, type safety, comments, formatting, test coverage
  awareness, and a post-flight verification pass that actually runs linter/tests.
  Use this skill whenever the user asks to review, clean up, or refactor code, mentions
  "code quality", "clean code", "refactor this", "review my code", or wants to prepare
  code for production. Also invoke before pull requests, after a spike/prototype phase,
  or when the user says the code "feels messy", "needs a cleanup", or "is getting hard
  to maintain". Language-agnostic — works on any codebase.
---

# Clean Code Pass

A 13-pass systematic review that builds progressively:
**Scope → Readability → Robustness → Architecture → Hygiene → Presentation → Awareness → Verification**

## Order of execution

Run passes in this exact order — each builds on the previous:

| Phase | Passes | Purpose |
|-------|--------|---------|
| Pre-flight | 0 | Define scope, establish baseline metrics |
| Readability | 1 – 3 | Naming, function design, complexity + file length |
| Robustness | 4 – 5 | Error handling, security |
| Architecture | 6 – 8 | DRY, dead code, dependencies |
| Hygiene | 9 – 10 | Type safety, comments |
| Presentation | 11 | Formatting |
| Awareness | 12 | Test coverage gaps |
| Post-flight | — | Run linter/formatter/tests, verify green |

Unless the user asks for specific passes, run all 13.

**Checkpoints** — commit or note a rollback point after:
- Passes 1–3 (readability foundation)
- Passes 4–5 (robustness)
- Passes 6–8 (architecture)
- Passes 9–11 (hygiene + presentation)
- Pass 12 + post-flight (awareness + verification)

---

## Pass 0 — Pre-flight
**Goal:** Understand scope before touching a single line.

Before starting any pass, take inventory:

- List every file in scope (get explicit confirmation from the user if unclear)
- Check line counts — flag any file ≥ 300 lines immediately and note it for Pass 3
- Identify the language(s) and toolchain (Python/pyenv, Node/npm, Go, etc.)
- Note which linter/formatter/test runner is configured, if any
- Record baseline metrics where available: line count per file, function count, any existing complexity scores
- Identify obvious high-risk areas (auth, payments, data ingestion, external API calls)

Document your findings in a brief pre-flight summary before proceeding:

```
PRE-FLIGHT SUMMARY
Files in scope: X files, Y total lines
Files ≥ 300 lines: [list or "none"]
Language/toolchain: [e.g., Python 3.13 / uv / pytest / ruff]
Linter: [e.g., ruff, eslint, golint — or "none detected"]
High-risk areas: [e.g., "auth.py — handles JWT verification"]
```

---

## Pass 1 — Naming
**Goal:** Make code self-documenting through intent-revealing names.

- Fix unclear variables, functions, and classes — the name should say *what* it represents without needing a comment
- Remove abbreviations and shorthand (`d` → `SECONDS_PER_DAY`, `usr` → `user`)
- Eliminate misleading names (`userList` that holds a map, `is_valid` that mutates state)
- Use consistent conventions throughout (camelCase vs snake_case — pick one and stay consistent)
- Prefer domain language that a non-engineer familiar with the business could recognize

```
❌ const d = 86400;
✅ const SECONDS_PER_DAY = 86400;

❌ def proc(r):
✅ def process_claim_record(record):
```

---

## Pass 2 — Function Design
**Goal:** Small, focused functions that do exactly one thing.

- Break up long functions — aim for < 20 lines
- One level of abstraction per function: don't mix high-level orchestration with low-level detail in the same function
- Extract nested logic into named helpers
- Limit parameters to ≤ 3; if you need more, introduce a config object or dataclass
- Ensure consistent return types — a function shouldn't return `str` sometimes and `None` other times

```
❌ function processUserData(user) {
    // validate, transform, save, send email — all 80 lines of it
}
✅ function processUserData(user) {
    validateUser(user);
    const transformed = transformUserData(user);
    saveUser(transformed);
    sendWelcomeEmail(transformed);
}
```

---

## Pass 3 — Complexity + File Length
**Goal:** Reduce cognitive load AND enforce the 300-line file limit.

**Complexity:**
- Flag deeply nested conditionals (> 3 levels) — extract guard clauses to fail fast
- Target cyclomatic complexity < 10 per function
- Replace complex conditional expressions with named boolean variables
- Consider polymorphism or strategy pattern over long switch/case chains

**File length (≤ 300 lines — hard limit per project standards):**
- If any file flagged in Pre-flight is still ≥ 300 lines after Passes 1–2, plan a split now
- Identify natural seams: group by responsibility, data layer vs. logic layer, etc.
- Create the new files and move code — don't just split arbitrarily
- Update all imports after the split

```
❌ if (user) { if (user.active) { if (user.verified) { ... } } }
✅ if (!user || !user.active || !user.verified) return;
   // main logic here

❌ auth_utils.py — 580 lines mixing JWT, session, OAuth, and password logic
✅ jwt.py, session.py, oauth.py, passwords.py — each ≤ 150 lines
```

---

## Pass 4 — Error Handling
**Goal:** Predictable, observable failure with no silent surprises.

- Never swallow exceptions — log or rethrow with context
- Use specific exception types, not bare `Exception` / `Error`
- Validate inputs at system boundaries (API endpoints, public function params)
- Fail fast with clear messages; don't let bad state propagate deep
- Log errors with enough context to diagnose (what, when, why) — never log sensitive data
- Handle errors at the right level — don't catch what you can't meaningfully recover from

```
❌ try { processPayment(amount); } catch (e) {}

✅ try {
    validateAmount(amount);
    processPayment(amount);
} catch (PaymentError e) {
    logger.error(`Payment failed for amount=${amount}: ${e.message}`);
    throw new PaymentProcessingException(e);
}
```

---

## Pass 5 — Security
**Goal:** Prevent common vulnerabilities before they reach production.

- Sanitize and validate all external input before use
- Use parameterized queries — never interpolate user input into SQL
- Remove hardcoded secrets, credentials, API keys — move to environment variables
- Verify authentication and authorization checks are in place at every boundary
- Never log passwords, tokens, or PII
- Use cryptographically secure RNGs for anything security-sensitive
- Escape output appropriately to prevent XSS (web contexts)

```
❌ db.query(`SELECT * FROM users WHERE id = ${userId}`);
❌ const API_KEY = "sk_live_12345";

✅ db.query("SELECT * FROM users WHERE id = ?", [userId]);
✅ const API_KEY = process.env.API_KEY;
```

Pay extra attention to code in areas flagged as high-risk during Pre-flight.

---

## Pass 6 — DRY (Don't Repeat Yourself)
**Goal:** Single source of truth — every piece of knowledge lives in one place.

- Hunt for duplicated logic blocks, especially copy-paste code across files
- Extract repeated patterns into reusable functions or utilities
- Centralize repeated constant values into a config or constants file
- Watch for structural duplication (same logic, different variable names)
- Don't over-abstract — duplication that appeared once is usually fine; three times is a pattern

```
❌ function calculateUserDiscount(user) { ... }   // 12 lines
   function calculateAdminDiscount(admin) { ... } // same 12 lines
✅ function calculateDiscount(person, role) { ... }
```

---

## Pass 7 — Dead Code
**Goal:** Remove code that is never executed, never imported, or no longer relevant.

Dead code is invisible cognitive tax — it misleads readers and hides real logic.

- Remove unused imports and `require` statements
- Delete functions, methods, or classes with no callers (verify with a grep/search before deleting)
- Remove unused variables and parameters
- Delete commented-out code blocks — version control is the history, not the file
- Remove stale feature flags, deprecated branches, and `TODO: remove this` blocks that were never removed
- Check for unreachable code after `return`, `raise`, or `throw` statements

```
❌ import pandas as pd  # never used
   # old_function() — removed 2024-Q3, keeping just in case
   def legacy_sync(): ...  # no callers

✅ (all of the above deleted)
```

---

## Pass 8 — Dependencies
**Goal:** Loose coupling, easy testability, no hidden surprises.

- Identify tight coupling — classes that instantiate their own dependencies
- Replace with dependency injection so tests can swap implementations
- Depend on abstractions (interfaces/protocols), not concrete classes
- Detect and break circular dependencies
- Keep the dependency list minimal and explicit — every `import` you don't need is risk you don't carry
- Check for outdated or vulnerable dependencies if a manifest (`requirements.txt`, `package.json`) is in scope

```
❌ class UserService:
       def __init__(self):
           self.db = PostgresDB()   # tight coupling, untestable

✅ class UserService:
       def __init__(self, db: Database):  # injected, swappable
           self.db = db
```

---

## Pass 9 — Type Safety
**Goal:** Make the type contract explicit so tools, IDEs, and future readers don't have to guess.

This pass is language-sensitive — apply it where the language supports types:

**Python (mypy / pyright):**
- Add type hints to all function signatures (params + return type)
- Use `Optional[T]` / `T | None` where `None` is a valid return
- Replace bare `dict` / `list` with typed equivalents (`dict[str, int]`, `list[ClaimRecord]`)
- Add `from __future__ import annotations` if using forward references

**TypeScript:**
- Eliminate implicit `any` — if something is truly unknown, use `unknown` and narrow it
- Add return types to all functions
- Replace `Object` with specific interfaces or types

**Go, Rust, Java, etc.:**
- Ensure generics/type params are specified, not wildcarded
- Verify interface implementations are explicit

If the codebase has no type system (plain JS, shell scripts), skip this pass and note it in the report.

```
❌ def process(record, config):
       return record["amount"] * config["rate"]

✅ def process(record: ClaimRecord, config: ProcessingConfig) -> Decimal:
       return record.amount * config.rate
```

---

## Pass 10 — Comments
**Goal:** Comments explain *why*, not *what* — the code already shows what.

- Delete comments that just restate the code (`# increment counter` above `counter += 1`)
- Add WHY comments where business rules or trade-offs aren't obvious to a reader
- Document non-obvious decisions: performance choices, workarounds, known limitations, regulatory requirements
- Ensure all public APIs have docstrings / JSDoc
- Delete commented-out code (belongs in version control, not the file)
- Format TODOs with owner and deadline: `# TODO(sean): remove after claims migration — 2026-Q3`

```
❌ # increment counter
   counter += 1

✅ # Batch every 100 requests to stay under the API rate limit (Waystar: 100 req/min)
   if request_count >= 100:
       flush_batch()
```

---

## Pass 11 — Formatting
**Goal:** Consistent, readable visual structure — ideally enforced by a tool, not a human.

- Run the project's auto-formatter first if one exists: `ruff format`, `black`, `prettier`, `gofmt`, `rustfmt`
- Verify indentation and spacing are consistent throughout
- Keep lines ≤ 120 characters
- Group related code together (vertical proximity signals logical relationship)
- Organize imports: stdlib → third-party → local, alphabetically within groups
- If no auto-formatter exists, note it in the report as a tech debt item

```
❌ def save(user):return db.save(validate(user))

✅ def save(user: User) -> User:
       validated = validate(user)
       return db.save(validated)
```

---

## Pass 12 — Test Coverage Awareness
**Goal:** Surface untested public interfaces so the user can make an informed decision — not write tests, just flag gaps.

This pass does not write tests. It identifies the risk surface:

- List every public function, method, class, and API endpoint in scope
- For each, note whether a test exists (search for the function name in test files)
- Flag anything with no test as a TODO — especially code touched during this review
- Pay particular attention to: error handling paths, security boundaries, business-critical calculations
- Note the testing framework in use (pytest, jest, go test, etc.) so any future tests follow the pattern

Document findings as TODOs in the report, not in the code:

```
TEST COVERAGE GAPS (from Pass 12)
- process_claim_record() — no test found. Touches payment logic. HIGH priority.
- validate_npi() — no test found. Regulatory boundary. HIGH priority.
- format_output() — no test found. Low risk, format-only. LOW priority.
```

---

## Post-flight Verification
**Goal:** Prove the code is still correct and tools agree it's clean.

After all 13 passes, verify the work:

1. **Run the formatter** (if available): `ruff format .` / `black .` / `prettier --write .`
2. **Run the linter** (if available): `ruff check .` / `eslint .` / `golint ./...`
3. **Run the tests** (if a suite exists): `pytest` / `npm test` / `go test ./...`
4. **Check for regressions**: if tests fail, identify which pass introduced the issue and fix it before declaring done

If any step fails, fix it before reporting complete. "Done" means green, not just reviewed.

---

## Pre-commit checklist

Before marking the review complete, verify:

- [ ] Can I understand this code in 6 months without extra context?
- [ ] Are names clear without needing comments?
- [ ] Is each function doing ONE thing, under 20 lines?
- [ ] Are all files under 300 lines?
- [ ] Are errors handled — no silent failures?
- [ ] Is all external input validated and sanitized?
- [ ] Is duplication eliminated?
- [ ] Is dead code removed?
- [ ] Are dependencies injected, not hardcoded?
- [ ] Are types explicit (where the language supports it)?
- [ ] Do comments explain WHY, not WHAT?
- [ ] Is formatting consistent (auto-formatted where possible)?
- [ ] Are test coverage gaps documented as TODOs?
- [ ] Did linter, formatter, and tests all pass?

---

## Report format

After completing all passes, deliver a structured summary:

```
CLEAN CODE REPORT
=================
Files reviewed: X
Total lines (before): Y  →  (after): Z

PASSES WITH CHANGES
- Pass 0 (Pre-flight): [summary of scope, flagged files, toolchain]
- Pass 1 (Naming): [N renames — examples of most impactful]
- Pass 3 (Complexity + File Length): [files split, functions simplified]
- Pass 7 (Dead Code): [N unused imports removed, N dead functions deleted]
- Pass 9 (Type Safety): [N annotations added]
- Pass 12 (Test Coverage): [N gaps flagged — see TODOs below]
... (only list passes that produced changes)

PASSES WITH NO CHANGES
- Pass 2, 4, 5, 6, 8, 10, 11 — no issues found

POST-FLIGHT
- Formatter: ✅ passed / ❌ [error]
- Linter: ✅ passed / ❌ [error]
- Tests: ✅ X passed / ❌ [failing tests]

TECH DEBT NOTED (not addressed — user decision required)
- [item]: [why it was left, suggested action]

TEST COVERAGE TODOS
- [function name] — [risk level] — [reason]
```

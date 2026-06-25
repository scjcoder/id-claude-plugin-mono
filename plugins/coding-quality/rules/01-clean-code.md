# Clean Code

Standing rules distilled from the 13-pass `clean-code-pass` review. The review is the
*audit*; these are the *rules* you write to from the start so the audit finds less.

## Naming

- **MUST** use intent-revealing names — the name says *what* it represents without a comment.
- **MUST NOT** ship abbreviations or shorthand. `d` → `SECONDS_PER_DAY`, `usr` → `user`.
- **MUST NOT** use misleading names (`userList` holding a map; `is_valid` that mutates).
- **MUST** keep one convention per language (snake_case for Python, camelCase for JS/TS) and stay consistent.
- **SHOULD** prefer domain language a non-engineer on the team would recognize.

## Function design

- **MUST** keep each function doing exactly one thing.
- **SHOULD** keep functions under 20 lines; extract nested logic into named helpers.
- **MUST** keep one level of abstraction per function — don't mix orchestration with low-level detail.
- **SHOULD** limit parameters to ≤ 3; beyond that, pass a config object / dataclass.
- **MUST** keep return types consistent — never `str` sometimes, `None` other times for the same path.

```
❌ def proc(r): ...            # 80 lines, validates+transforms+saves+emails
✅ def process_claim(record):
       validate(record)
       saved = save(transform(record))
       send_confirmation(saved)
```

## Complexity

- **SHOULD** keep cyclomatic complexity < 10 per function.
- **MUST** use guard clauses to fail fast instead of nesting > 3 levels deep.
- **SHOULD** name complex boolean expressions: `is_eligible = user.active and user.verified`.

```
❌ if (user) { if (user.active) { if (user.verified) { ... } } }
✅ if (!user || !user.active || !user.verified) return;
   // main logic
```

## File length

- **MUST** keep files under 300 lines. This is a hard project standard.
- **MUST** split a file by responsibility (data layer vs logic, distinct concerns), not arbitrarily, and update all imports.

```
❌ auth_utils.py — 580 lines: JWT + session + OAuth + passwords
✅ jwt.py, session.py, oauth.py, passwords.py — each ≤ 150 lines
```

## DRY

- **SHOULD** extract logic duplicated three or more times into a shared function/util.
- **MUST** centralize repeated constants in one config/constants location.
- **MUST NOT** over-abstract — duplication appearing once is usually fine.

## Dead code

- **MUST** remove unused imports, variables, parameters, and uncalled functions (verify with a search first).
- **MUST NOT** leave commented-out code — version control is the history.
- **MUST** remove unreachable code after `return`/`raise`/`throw` and stale feature flags.

## Dependencies

- **SHOULD** inject dependencies rather than instantiating them inside a class — keeps code testable.
- **SHOULD** depend on abstractions (interfaces/protocols), not concretes.
- **MUST** break circular dependencies.
- **MUST** keep the dependency list minimal and explicit — every unused import is unearned risk.

```
❌ class UserService:
       def __init__(self): self.db = PostgresDB()   # untestable
✅ class UserService:
       def __init__(self, db: Database): self.db = db  # injected
```

## Formatting

- **MUST** run the project auto-formatter (ruff/black/prettier/gofmt) before committing.
- **SHOULD** keep lines ≤ 120 chars and order imports stdlib → third-party → local.

See the full audit procedure in the `clean-code-pass` skill. Run it before every PR.

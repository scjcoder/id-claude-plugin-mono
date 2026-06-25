# Stack Overlay — Python

Layered on top of all core rules. Adds Python-specific requirements.

## Environment

- **MUST** use `pyenv` to pin the interpreter version (`.python-version` committed to the repo).
- **MUST** manage envs and dependencies with `uv`; commit `uv.lock` for reproducible builds.
- **SHOULD** use `hatchling` as the build backend in `pyproject.toml` for packaged projects.
- **MUST** pass `--break-system-packages` only when a system-level `pip install` is truly
  unavoidable — prefer `uv` in all other cases.

See `resources/templates/pyproject.toml` for the canonical project config.

## Type safety

- **MUST** add type hints to every function signature (params + return).
- **MUST** use `T | None` where `None` is a valid value (not bare `T`).
- **MUST** use built-in generics (`dict`, `list`, `tuple`, `set`) and `X | None` — not the
  `typing` aliases (`Dict`, `List`, `Optional`, `Tuple`). The project targets py312; the
  aliases are legacy.
- **SHOULD** delete `from typing import Dict/List/Optional/Tuple` imports when touching a file;
  keep `typing` only for constructs with no builtin equivalent (`Any`, `Protocol`, `TypeVar`,
  `Callable`, etc.).
- **SHOULD** replace bare `dict`/`list` with typed forms (`dict[str, int]`, `list[ClaimRecord]`).
- **SHOULD** pass `mypy`/`pyright` clean.

```
❌ from typing import Dict, List, Optional
   def process(record, config) -> Optional[Dict[str, int]]: ...
   def collect(items: List[str]) -> None: ...

✅ def process(record: ClaimRecord, config: ProcessingConfig) -> Decimal:
       return record.amount * config.rate
   def collect(items: list[str]) -> None: ...
   x: dict[str, int] | None = None
```

## Logging

- **MUST NOT** call `logging.basicConfig(...)` at module/import scope in library code — it
  hijacks the root logger for every importer.
- **MUST** use `logger = logging.getLogger(__name__)` at the top of each module.
- **SHOULD** configure handlers and levels only in entrypoints: `if __name__ == "__main__":`,
  a CLI `main()`, or the Lambda/app bootstrap function.

```
❌ # top of an imported module
   import logging
   logging.basicConfig(level=logging.INFO)  # poisons root logger

✅ import logging
   logger = logging.getLogger(__name__)     # module-scoped, no side-effects

   # entrypoint only:
   if __name__ == "__main__":
       logging.basicConfig(level=logging.INFO)
       main()
```

## Tooling

- **MUST** format with `ruff format` and lint with `ruff check` before committing.
- **SHOULD** test with `pytest`; keep fixtures small and deterministic.

## Idioms

- **SHOULD** prefer dataclasses/pydantic models over passing loose dicts across boundaries.
- **SHOULD** use context managers for resources (files, connections, locks).
- **MUST** keep modules under 300 lines — split by responsibility.

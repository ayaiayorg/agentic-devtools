# Data Model — Spec 005: Resolve Test Suite Warnings

No new data models are introduced by this specification. The changes are
limited to:

- A version-guarded kwarg addition to an existing `tar.extract()` call
- Test pattern refactoring (no schema or state changes)
- A `filterwarnings` list added to `pyproject.toml` `[tool.pytest.ini_options]`

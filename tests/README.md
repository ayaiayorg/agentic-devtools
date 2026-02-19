# Test Organization Policy

This document defines the strict 1:1:1 test organization policy for `agentic-devtools`.
All new tests **must** follow this policy. No exceptions are allowed.

## Policy

- **One folder per source file under test** — the test directory structure mirrors the source structure.
- **One test file per function under test** — each test file covers exactly one function.

## Directory Structure

```text
tests/unit/{module_path}/{source_file_name}/test_{function_name}.py
```

### Example

| Source | Test |
|--------|------|
| `agentic_devtools/cli/git/core.py` → `get_current_branch()` | `tests/unit/cli/git/core/test_get_current_branch.py` |
| `agentic_devtools/state.py` → `get_value()` | `tests/unit/state/test_get_value.py` |
| `agentic_devtools/cli/jira/config.py` → `get_jira_url()` | `tests/unit/cli/jira/config/test_get_jira_url.py` |

## Rules

1. The path under `tests/unit/` **must** mirror the path under `agentic_devtools/` exactly
   (drop the `agentic_devtools/` prefix and strip the `.py` extension to form the folder name).
2. The test file **must** be named `test_{function_name}.py` where `{function_name}` is the
   name of the single function under test.
3. **Each test file tests exactly one function.** If a source file has ten functions, it will
   have ten corresponding test files inside its folder.
4. Every directory in the hierarchy **must** contain an `__init__.py` file so pytest can
   resolve imports correctly.

## Enforcement

A CI validation script (`scripts/validate_test_structure.py`) automatically checks that
every file inside `tests/unit/` obeys the rules above. The script exits with a non-zero
status if any violation is found, causing the CI build to fail.

To run the validator locally:

```bash
python scripts/validate_test_structure.py
```

## Existing Tests

Tests outside `tests/unit/` (e.g., `tests/azure_devops/`, `tests/e2e_smoke/`, and the
flat `tests/test_*.py` files) were written before this policy was introduced. They are
**not** validated by the 1:1:1 script and do not need to be migrated immediately.
New test code, however, **must** be placed under `tests/unit/`.

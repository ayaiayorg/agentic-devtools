# Test Organization Policy

This document defines the strict 1:1:1 test organization policy for `agentic-devtools`.
All new tests **must** follow this policy. No exceptions are allowed.

## Rationale

The 1:1:1 policy enforces a strict, predictable mapping between source code and tests:

- **Discoverability**: Given any symbol (function or class), you can immediately find its tests and vice versa without
  searching — just follow the path convention.
- **Isolation**: Each test file has exactly one responsibility. Tests for `get_value()` never
  interfere with tests for `set_value()`.
- **Incremental coverage**: Adding tests for a new symbol (function or class) means creating one new file in a
  predictable location — no hunting for where tests "should go".
- **CI enforcement (structure only)**: The automated validator (`scripts/validate_test_structure.py`)
  checks the folder↔source-file mapping and required `__init__.py` files. Structural violations fail the
  build immediately, before review. It does **not** verify per-symbol coverage — that is enforced by convention and code review.
- **AI-agent friendly**: AI coding agents can deterministically locate and create test files by following
  the path convention, even though CI only validates directory structure.

## Policy

- **One folder per source file under test** — the test directory structure mirrors the source structure.
- **One test file per symbol (function or class) under test** — each test file covers exactly one symbol.

## Directory Structure

```text
tests/unit/{module_path}/{source_file_name}/test_{symbol_name}.py
```

where `{symbol_name}` is:

- **Functions**: the exact snake\_case function name (e.g., `get_current_branch` → `test_get_current_branch.py`)
- **Classes / dataclasses / enums**: the class name lowercased **without** additional underscores
  (e.g., `WorktreeSetupResult` → `test_worktreesetupresult.py`, `ChecklistItem` → `test_checklistitem.py`)

### Example

| Source symbol | Test file |
|---|---|
| `agentic_devtools/cli/git/core.py` → `get_current_branch()` | `tests/unit/cli/git/core/test_get_current_branch.py` |
| `agentic_devtools/state.py` → `get_value()` | `tests/unit/state/test_get_value.py` |
| `agentic_devtools/cli/jira/config.py` → `get_jira_url()` | `tests/unit/cli/jira/config/test_get_jira_url.py` |
| `agentic_devtools/cli/workflows/worktree_setup.py` → `WorktreeSetupResult` | `tests/unit/cli/workflows/worktree_setup/test_worktreesetupresult.py` |
| `agentic_devtools/cli/workflows/checklist.py` → `ChecklistItem` | `tests/unit/cli/workflows/checklist/test_checklistitem.py` |

## Rules

1. The path under `tests/unit/` **must** mirror the path under `agentic_devtools/` exactly
   (drop the `agentic_devtools/` prefix and strip the `.py` extension to form the folder name).
2. The test file **must** be named `test_{symbol_name}.py` where `{symbol_name}` is:
   - For **functions**: the exact snake\_case function name.
   - For **classes / dataclasses / enums**: the class name lowercased without added underscores
     (e.g., `WorktreeSetupResult` → `test_worktreesetupresult.py`).
3. **Each test file tests exactly one symbol (function or class).** If a source file has ten
   public symbols, it will have ten corresponding test files inside its folder.
4. Every directory in the hierarchy **must** contain an `__init__.py` file so pytest can
   resolve imports correctly.

## How to Add New Tests

Follow these steps whenever you add a new function or class to a source file:

1. **Identify the source file path**, e.g. `agentic_devtools/cli/git/core.py`.
2. **Determine the test folder**: drop the `agentic_devtools/` prefix and strip the `.py`
   extension → `tests/unit/cli/git/core/`.
3. **Create the folder** (and any missing intermediate folders) plus an `__init__.py`
   in every new directory:

   ```bash
   mkdir -p tests/unit/cli/git/core
   touch tests/unit/cli/git/core/__init__.py
   # Also ensure parent dirs have __init__.py:
   touch tests/unit/cli/git/__init__.py tests/unit/cli/__init__.py tests/unit/__init__.py
   ```

4. **Create the test file** named `test_{symbol_name}.py`:
   - Functions: `test_get_current_branch.py`
   - Classes/dataclasses/enums: `test_worktreesetupresult.py` (lowercase, no added underscores)
5. **Write your tests** in the new file. A minimal example:

   ```python
   from agentic_devtools.cli.git.core import get_current_branch


   def test_returns_branch_name():
       # arrange / act / assert
       ...
   ```

6. **Run the validator** to confirm the structure is correct:

   ```bash
   python scripts/validate_test_structure.py
   ```

7. **Run only the new test file** to confirm it passes:

   ```bash
   agdt-test-pattern tests/unit/cli/git/core/test_get_current_branch.py -v
   ```

## How to Run Specific Tests

```bash
# Run one test file
agdt-test-pattern tests/unit/cli/git/core/test_get_current_branch.py -v

# Run all tests for a source file's folder
agdt-test-pattern tests/unit/cli/git/core/ -v

# Run a specific test function
agdt-test-pattern tests/unit/state/test_get_value.py::TestGetValue::test_get_nonexistent_key_returns_none -v

# Run full test suite with coverage (background task, ~55 s)
agdt-test
agdt-task-wait

# Run tests for a specific source file with 100% coverage requirement
# NOTE: agdt-test-file infers a legacy tests/test_<module>.py path and does NOT
# support the tests/unit/ 1:1:1 layout. Use agdt-test-pattern for 1:1:1 tests
# (see examples above), and reserve agdt-test-file for modules that still have
# a matching legacy flat test file (tests/test_<module>.py). If no such file
# exists the command will fail with "Test file not found".
```

## Enforcement

`scripts/validate_test_structure.py` runs in CI and **fails the build** when it finds structural
issues in `tests/unit/`: incorrect source-file folder mapping, or missing `__init__.py` files.
It does **not** verify that every symbol has a test file or that `test_<symbol>.py` corresponds
to a real symbol — those parts of the policy are enforced by convention and code review.

To run the validator locally:

```bash
python scripts/validate_test_structure.py
```

## Top-Level Source Files

Source files directly inside `agentic_devtools/` (e.g., `state.py`, `background_tasks.py`)
map to `tests/unit/{source_file_name}/test_{function_name}.py`. The `module_path` part is
simply empty.

| Source | Test |
|--------|------|
| `agentic_devtools/state.py` → `get_workflow_state()` | `tests/unit/state/test_get_workflow_state.py` |
| `agentic_devtools/background_tasks.py` → `run_function_in_background()` | `tests/unit/background_tasks/test_run_function_in_background.py` |

> **Do NOT** create proxy/stub source files (e.g., `agentic_devtools/root/state.py`) just to
> add a path component. The validator supports 2-component minimum paths, so top-level
> source files are handled correctly without any workaround.

## Linting Requirements

All test files under `tests/unit/` must pass `ruff` linting. Common pitfalls to avoid:

1. **No unused imports (F401):** Each test file should only import what it actually uses.
   Ruff will flag any import that is never referenced in the file. Run `ruff check tests/unit/`
   or `ruff check tests/unit/ --fix` to auto-remove them.
   This is especially important when migrating tests from old flat files: the original preamble
   carries every import the old file needed, but the new per-function file may only need a subset.

2. **Sorted imports (I001):** Imports must be sorted (isort-style). The project uses
   `known-first-party = ["agentic_devtools", "agdt_ai_helpers"]`. Run `ruff check tests/unit/ --fix`
   to auto-sort them.

3. **No trailing whitespace:** Blank lines inside function/class bodies must not contain
   spaces. Ruff's `W291`/`W293` rules catch this. Use `ruff format` or `ruff check --fix` to clean up.

4. **Do not commit `agentic_devtools/_version.py`:** This file is auto-generated by
   setuptools-scm and must never be committed. It is **untracked by git** and listed in
   `.gitignore`, so `git add .` will never stage it. No manual cleanup is needed — you
   should **not** run `git checkout -- agentic_devtools/_version.py` or
   `git update-index --skip-worktree`; those older instructions are obsolete now that
   `_version.py` is untracked and ignored by `.gitignore`.

5. **Verify the source file path before placing tests:** The test location must mirror the
   *actual* source file path. For example, a function defined in `review_helpers.py` belongs
   under `tests/unit/cli/azure_devops/review_helpers/`, **not** `review_prompts/`. Always
   check the `from ... import` statement to confirm the correct source module.

6. **Always call `mkdir()` when a test needs an existing-but-empty directory:** When writing
   tests for code that checks whether a directory exists, make sure to actually create the
   directory with `tmp_path / "subdir"` followed by `.mkdir()`. Skipping the call means
   the test exercises the *missing-directory* code path instead of the *empty-directory* code
   path, leading to a misleading test name and untested branch.

7. **Remove unused fixture parameters:** Fixtures like `capsys` capture output but only add
   overhead when the test body never calls them (e.g., `capsys.readouterr()`). Code reviewers
   will flag unused parameters. Remove any fixture from the signature that the test body does
   not use.

**Run these commands before every push to catch all issues:**

```bash
ruff check tests/unit/ --fix    # fix unused imports and import sorting
ruff format tests/unit/         # fix formatting
python scripts/validate_test_structure.py  # verify 1:1:1 structure
```

## Existing Tests

Tests outside `tests/unit/` (e.g., `tests/azure_devops/`, `tests/e2e_smoke/`, and the
flat `tests/test_*.py` files) were written before this policy was introduced. They are
**not** validated by the 1:1:1 script and do not need to be migrated immediately.
New test code, however, **must** be placed under `tests/unit/`.

## Platform-Specific Tests

Some modules contain code that only runs on a specific operating system (e.g., `fcntl`
on Unix, `msvcrt` on Windows). Tests for this code use platform markers so they are
automatically skipped on incompatible platforms.

### Available Markers

| Marker | Meaning |
|--------|---------|
| `@pytest.mark.linux_only` | Test runs only on Linux/macOS (skipped on Windows) |
| `@pytest.mark.windows_only` | Test runs only on Windows (skipped on Linux/macOS) |

These markers are processed in `tests/conftest.py` via `pytest_collection_modifyitems`,
which adds `pytest.mark.skip` to incompatible tests at collection time.

### Usage

```python
import pytest
from agentic_devtools.file_locking import _lock_file_unix

@pytest.mark.linux_only
def test_lock_file_unix_exclusive(tmp_path):
    """Test fcntl-based locking (Linux/macOS only)."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    with open(test_file, "r+") as f:
        _lock_file_unix(f, exclusive=True, timeout=1.0)
```

For tests that mock the OS-specific module entirely (e.g., replacing `msvcrt` in
`sys.modules`), **no platform marker is needed** since the real module is never imported:

```python
import sys
from unittest.mock import MagicMock, patch

def test_lock_file_windows_timeout(tmp_path):
    """Test msvcrt timeout path — works on any platform via sys.modules mock."""
    from agentic_devtools.file_locking import _lock_file_windows, FileLockError

    mock_msvcrt = MagicMock()
    mock_msvcrt.LK_NBLCK = 2
    mock_msvcrt.locking.side_effect = OSError("busy")

    with patch.dict(sys.modules, {"msvcrt": mock_msvcrt}):
        with open(tmp_path / "f.txt", "w+") as f:
            with pytest.raises(FileLockError):
                _lock_file_windows(f, timeout=0.05)
```

### Coverage Exclusions

Coverage is enforced at **100%** (`--cov-fail-under=100`) in CI. All code must be either
tested or explicitly excluded with `# pragma: no cover`.

#### When to use `# pragma: no cover`

Only use `# pragma: no cover` for code that **genuinely cannot be tested** in the CI
environment. Valid reasons include:

- **External infrastructure dependencies** that require real API endpoints (e.g.,
  Azure DevOps API calls, Jira REST endpoints, VPN toggle operations).
- **CLI argparse thin wrappers** that only parse arguments and delegate to tested
  implementations.
- **Signal/interrupt handlers** (e.g., `KeyboardInterrupt` catches).
- **`ImportError` fallbacks** for optional modules.

#### When NOT to use `# pragma: no cover`

Do **not** use `# pragma: no cover` on:

- **OS-specific code that can be mocked** — functions like `_lock_file_windows` that
  import `msvcrt` are testable on any platform using `patch.dict(sys.modules, ...)`.
  See the `TestWindowsFileLocking` examples above.
- **Deterministic logic** that can be exercised by setting state values, providing mock
  inputs, or calling the function directly. For example, string coercion in
  `get_pypi_dry_run()` is testable by calling `set_value("pypi.dry_run", "true")`.
- **Pure functions** or **data transformations** — these should always be tested.
- **Error paths** that can be triggered by mocking dependencies to raise exceptions.
- **Jinja2 / template engine internals** — custom `Undefined` subclasses and syntax
  error fallbacks are straightforward to test directly.

#### Platform-specific exclusion patterns

- Branches guarded by `if sys.platform == "win32":` are automatically excluded via the
  `exclude_also` pattern in `pyproject.toml` — no per-line pragma needed.

### CI Platform Matrix

The CI pipeline (`test.yml`) currently runs on **Ubuntu Linux** only. Windows CI support
can be added when needed by expanding the `runs-on` matrix in `.github/workflows/test.yml`.
Platform-specific tests are already properly skipped through marker-based collection hooks,
so no additional CI changes are required for correct skip behaviour.

# Test Organization Policy

> **⚠️ AI AGENTS: ALWAYS use `agdt-test` commands — NEVER run `pytest` directly!**
>
> ```bash
> agdt-test          # Full suite with coverage (background, ~55s)
> agdt-task-wait     # Wait for completion (REQUIRED)
>
> agdt-test-quick    # Quick run without coverage (background)
> agdt-task-wait
>
> agdt-test-pattern tests/unit/cli/git/core/test_get_current_branch.py -v  # Specific test (synchronous)
> ```
>
> Running `pytest` directly bypasses the background task system and workflow integration.
> See [How to Run Specific Tests](#how-to-run-specific-tests) for the full command reference.

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

## Test Anatomy

New test files in `tests/unit/` should follow the same internal structure.
Use the following preferred structure as a template when writing a new test file:

```python
"""Tests for agentic_devtools.cli.git.core.get_current_branch."""

# 1. Standard-library imports first
from unittest.mock import MagicMock

# 2. Third-party imports
import pytest

# 3. First-party imports (the symbol under test plus any helpers it needs)
from agentic_devtools.cli.git import core


class TestGetCurrentBranch:
    """Tests for get_current_branch function.

    One class per test file; the class name is Test + PascalCase symbol name.
    """

    # ── happy-path tests ──────────────────────────────────────────────────

    def test_returns_branch_name(self, mock_run_safe):
        """Test that the current branch name is returned."""
        # Arrange
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="feature/my-branch\n", stderr="")

        # Act
        branch = core.get_current_branch()

        # Assert
        assert branch == "feature/my-branch"

    # ── error-path tests ──────────────────────────────────────────────────

    def test_detached_head_exits(self, mock_run_safe):
        """Test that detached HEAD state causes SystemExit(1)."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="HEAD\n", stderr="")

        with pytest.raises(SystemExit) as exc_info:
            core.get_current_branch()

        assert exc_info.value.code == 1
```

### Key conventions

| Item | Convention |
|------|-----------|
| Module docstring | `"""Tests for {fully.qualified.module.symbol}."""` |
| Class name | `Test` + PascalCase symbol name, e.g. `TestGetCurrentBranch` |
| Class docstring | Short phrase describing what is being tested |
| Test method name | `test_{behaviour_under_test}` — describe what the test verifies, not how |
| Test method docstring | One sentence stating the expected outcome |
| Arrange / Act / Assert | Three logical blocks; separate with a blank line when the body is non-trivial |
| Imports | Use module-level imports; avoid `from x import y` inline inside test methods |

## Available Fixtures

This section catalogs the shared fixtures defined in the root- and unit-level `conftest.py` files,
plus the most commonly used per-subpackage fixtures. Use the narrowest-scoped fixture that satisfies
your test's needs.

### Root fixtures — `tests/conftest.py`

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mock_jira_vpn_context` | `function` (**autouse**) | Auto-mocks `JiraVpnContext` and `get_vpn_url_from_state` so no real VPN operations occur. Add `@pytest.mark.real_vpn` to opt out for tests that explicitly exercise VPN logic. |

### Unit fixtures — `tests/unit/conftest.py`

| Fixture | Scope | Description |
|---------|-------|-------------|
| `temp_state_dir` | `function` | Patches `state.get_state_dir()` to return a fresh `tmp_path`. **Required for any test that reads or writes state.** |
| `clear_state_before` | `function` | Depends on `temp_state_dir`; calls `state.clear_state()` before the test. Use this when a test writes state values and should start from a clean slate. |
| `mock_background_and_state` | `function` | Patches both state directories *and* `subprocess.Popen` so background-task commands can be called without spawning a real process. Yields `{"state_dir": tmp_path, "mock_popen": mock_popen}`. |

### Git fixtures — `tests/unit/cli/git/conftest.py`

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mock_run_safe` | `function` | Patches `core.run_safe` with a `MagicMock` that returns `returncode=0, stdout="", stderr=""` by default. Use for tests that should not execute real git commands. |
| `temp_git_repo` | `function` | Creates a real but temporary git repository (with an initial commit). Use for tests that must run git commands against an actual repo. |

### Azure DevOps fixtures — `tests/unit/cli/azure_devops/conftest.py`

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mock_azure_devops_env` | `function` | Sets `AZURE_DEV_OPS_COPILOT_PAT=test-pat` via `patch.dict`. Required for any test that calls an Azure DevOps helper that reads the PAT. |
| `mock_git_remote_detection` | `function` (**autouse**) | Stubs `get_repository_name_from_git_remote` to return `None`. Prevents git remote inspection from interfering with mocks. Skip via `TestRepositoryDetection` class name. |

### Jira fixtures — `tests/unit/cli/jira/conftest.py`

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mock_jira_env` | `function` | Sets `JIRA_COPILOT_PAT=test-token` and `JIRA_SSL_VERIFY=0`. **Always combine with `mock_requests_module`** when calling Jira commands in tests. |
| `mock_requests_module` | `function` | Patches `_get_requests` in all Jira implementation modules (`create_commands`, `comment_commands`, `get_commands`, `update_commands`, `role_commands`) and returns a pre-configured `MagicMock` HTTP client. |

### Helper factory functions — `tests/helpers.py`

Import from `tests.helpers` when you need to construct common test objects:

```python
from tests.helpers import create_git_repo, make_mock_popen, make_mock_response, make_mock_task
```

| Function | Returns | When to use |
|----------|---------|-------------|
| `create_git_repo(repo_dir)` | `None` | Initialize a bare-minimum git repo with one commit inside a `tmp_path` subdirectory. |
| `make_mock_popen(pid=12345)` | `MagicMock` | Create a fake `subprocess.Popen` return value with a fixed `.pid`. |
| `make_mock_response(json_data=None, status_code=200)` | `MagicMock` | Create a fake HTTP response with `.json()`, `.status_code`, and a no-op `.raise_for_status()`. |
| `make_mock_task(task_id=…, command=…)` | `MagicMock` | Create a fake `BackgroundTask` object with `.id` and `.command`. |

## Common Test Patterns

The following patterns cover the most frequently encountered testing scenarios.
Copy the relevant pattern as a starting point, then adapt it to your symbol.

### Pattern 1 — Testing a state-dependent function

Use when the function under test calls `get_value()` or `set_value()`:

```python
from agentic_devtools import state


class TestGetValue:
    def test_returns_stored_value(self, temp_state_dir):
        # Arrange — write the expected value into the temporary state store
        state.set_value("commit_message", "feat: add new feature")

        # Act
        result = state.get_value("commit_message")

        # Assert
        assert result == "feat: add new feature"

    def test_returns_none_when_not_set(self, temp_state_dir):
        result = state.get_value("nonexistent")
        assert result is None
```

### Pattern 2 — Testing CLI command output with `capsys`

Use when the function under test prints to stdout or stderr:

```python
import pytest

from agentic_devtools.cli.tasks import commands


class TestListTasks:
    def test_prints_no_tasks_message(self, mock_background_and_state, capsys):
        # Act
        commands.list_tasks()

        # Assert — check what was printed
        captured = capsys.readouterr()
        assert "No background tasks found" in captured.out

    def test_exits_on_missing_task_id(self, temp_state_dir, capsys):
        with pytest.raises(SystemExit) as exc_info:
            commands.task_status()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: No task ID specified." in captured.out
```

### Pattern 3 — Testing git operations

Use `mock_run_safe` to intercept all git subprocess calls.
Configure the mock's return value before the call under test:

```python
from unittest.mock import MagicMock

import pytest

from agentic_devtools.cli.git import core


class TestGetCurrentBranch:
    def test_returns_branch_name(self, mock_run_safe):
        # Arrange — configure the fake git output
        mock_run_safe.return_value = MagicMock(
            returncode=0, stdout="feature/DFLY-1234/my-feature\n", stderr=""
        )

        # Act
        branch = core.get_current_branch()

        # Assert
        assert branch == "feature/DFLY-1234/my-feature"

    def test_git_failure_exits(self, mock_run_safe):
        mock_run_safe.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: not a git repo")

        with pytest.raises(SystemExit):
            core.get_current_branch()
```

Use `temp_git_repo` only when the test must exercise the git binary itself
(e.g., tests for `create_git_repo` or integration scenarios):

```python
import subprocess

from tests.helpers import create_git_repo


class TestCreateGitRepo:
    def test_initial_commit_exists(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        create_git_repo(repo)

        result = subprocess.run(
            ["git", "log", "--oneline"], cwd=repo, capture_output=True, text=True
        )
        assert "Initial commit" in result.stdout
```

### Pattern 4 — Testing commands that spawn background tasks

Use `mock_background_and_state` to intercept `subprocess.Popen` and verify
both the spawned process and the background-task state. This pattern applies
to any `*_async` CLI wrapper that calls `run_function_in_background`:

```python
from agentic_devtools import state
from agentic_devtools.cli.github import async_commands as gh_async


class TestCreateAgdtIssueAsync:
    def test_spawns_background_task(self, mock_background_and_state):
        # Arrange — set required state for the command
        state.set_value("issue.title", "Test issue")
        state.set_value("issue.description", "Details")

        # Act
        gh_async.create_agdt_issue_async()

        # Assert — Popen was called once to spawn the background process
        mock_background_and_state["mock_popen"].assert_called_once()

    def test_task_id_stored_in_state(self, mock_background_and_state):
        state.set_value("issue.title", "Test issue")
        state.set_value("issue.description", "Details")

        gh_async.create_agdt_issue_async()

        # The command should store the task ID in state so the agent can poll it
        task_id = state.get_value("background.task_id")
        assert task_id is not None
```

### Pattern 5 — Testing error paths

Use `pytest.raises` for `SystemExit`, `KeyError`, `ValueError`, and other
expected exceptions.  Always assert both the exception type and the exit code
(or message) so the test is specific:

```python
from unittest.mock import MagicMock

import pytest
import requests

from agentic_devtools import state
from agentic_devtools.cli.jira import comment_commands


class TestAddComment:
    def test_missing_issue_key_exits(self, temp_state_dir, clear_state_before):
        # Arrange — comment is set but issue_key is not
        state.set_value("jira.comment", "Test comment")

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            comment_commands.add_comment()

        assert exc_info.value.code == 1

    def test_api_error_is_handled(
        self, temp_state_dir, clear_state_before, mock_jira_env, mock_requests_module
    ):
        state.set_value("jira.issue_key", "DFLY-1234")
        state.set_value("jira.comment", "Test comment")

        # Configure the mock to simulate an HTTP error
        mock_requests_module.post.return_value = MagicMock(
            status_code=500,
            raise_for_status=MagicMock(side_effect=requests.HTTPError("500 Server Error")),
        )

        with pytest.raises(SystemExit):
            comment_commands.add_comment()
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

## TDD Workflow

All implementation work **must** follow the red-green-refactor TDD cycle.
Write tests **before** implementation code.

### Cycle Overview

```text
RED   → Write a failing test that defines the desired behaviour
GREEN → Write the minimal code to make the test pass
REFACTOR → Tidy the code while keeping tests green
```

### Step-by-Step Example

```bash
# Step 1 — RED: create the test file first (no source changes yet)
# Create tests/unit/cli/git/core/test_new_function.py

# Confirm it fails:
agdt-test-pattern tests/unit/cli/git/core/test_new_function.py -v
# Expected: FAILED

# Step 2 — GREEN: write minimal implementation in source file
# Edit agentic_devtools/cli/git/core.py

# Confirm tests pass:
agdt-test-pattern tests/unit/cli/git/core/test_new_function.py -v
# Expected: PASSED

# Step 3 — REFACTOR: improve code quality and re-run the test folder
# NOTE: use agdt-test-pattern, NOT agdt-test-file — agdt-test-file only supports
# legacy flat test files (tests/test_<module>.py) and will fail for 1:1:1 tests
agdt-test-pattern tests/unit/cli/git/core/ -v

# Step 4 — FULL SUITE: run the complete suite after all items are done
agdt-test
agdt-task-wait
```

### TDD Rules

- **Never write implementation code before a failing test exists.** If you cannot
  write a meaningful test first, reconsider the design.
- **Keep each RED → GREEN cycle small** — one function or one behaviour at a time.
- **Never skip the RED step.** A test that passes without any implementation means
  it does not actually test anything useful.

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

8. **When writing a `temp_git_repo` fixture, always disable GPG signing:** Creating a
   real commit inside a temporary repo will fail if the developer's or CI global Git config
   has `commit.gpgsign=true`. Set `commit.gpgsign=false` in the temp repo **before** committing,
   and pass `--no-verify` to skip commit hooks:

   ```python
   subprocess.run(["git", "config", "commit.gpgsign", "false"],
                  cwd=repo_dir, check=True, capture_output=True)
   subprocess.run(["git", "commit", "--no-verify", "-m", "Initial commit"],
                  cwd=repo_dir, check=True, capture_output=True)
   ```

   The same pattern applies to any other fixture that creates a real git commit in a
   temporary repository.

9. **Always set `JIRA_SSL_VERIFY=0` in Jira mock environment fixtures:** Jira commands call
   `_get_ssl_verify()` internally. Without `JIRA_SSL_VERIFY=0`, that function attempts to
   run `openssl s_client` / open socket connections to fetch certificates before falling back
   to `verify=False`, making tests slow and network-dependent. Always include it alongside
   `JIRA_COPILOT_PAT` in any Jira environment fixture:

   ```python
   with patch.dict("os.environ", {"JIRA_COPILOT_PAT": "test-token", "JIRA_SSL_VERIFY": "0"}):
       yield
   ```

10. **Patch `_get_requests` in every Jira module the test exercises:** The `_get_requests`
    function is imported into `create_commands`, `comment_commands`, `get_commands`,
    `update_commands`, and `role_commands`. A `mock_requests_module` fixture must patch the
    function in all modules that will be called by the test, otherwise the real `requests`
    library will be invoked. Use `patch.object(<module>, "_get_requests", return_value=mock)`
    for each module.

**Run these commands before every push to catch all issues:**

```bash
ruff check tests/unit/ --fix    # fix unused imports and import sorting
ruff format tests/unit/         # fix formatting
python scripts/validate_test_structure.py  # verify 1:1:1 structure
```

## Integration and End-to-End Tests

Integration or end-to-end tests that exercise **multiple functions, modules, or workflow steps**
together cannot follow the 1:1:1 policy (they are not testing a single symbol). These tests
must **not** be placed under `tests/unit/` — doing so will cause the structure validator to fail.

Instead, place them in a dedicated top-level directory that reflects the area under test:

| Directory | Use for |
|-----------|---------|
| `tests/workflows/` | End-to-end workflow lifecycle tests (e.g., planning → completion) |
| `tests/azure_devops/` | Multi-function Azure DevOps integration tests |
| `tests/e2e_smoke/` | Full smoke tests requiring live or mocked external services |

Directories outside `tests/unit/` are **not** checked by the 1:1:1 validator.

## Existing Tests

Tests outside `tests/unit/` (e.g., `tests/azure_devops/`, `tests/e2e_smoke/`, `tests/workflows/`,
and the flat `tests/test_*.py` files) are **not** validated by the 1:1:1 script.
New **unit** tests must be placed under `tests/unit/`; new **integration** tests must be placed
in the appropriate directory outside `tests/unit/` (see the table above).

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

# PR Merge Instructions (Python-Heavy PRs)

## Quick Start

```text
/agdt.pr-merge-manager https://github.com/ayaiayorg/agentic-devtools/pull/{{prId}}

max iterations 49

use rebase merge strategy
```

## Subagent Testing & Coverage Rules

Instruct each `agdt.address-copilot-review` subagent to follow this **exact procedure**
before running `agdt-git-save-work` or amending/pushing any changes.
Do NOT skip or abbreviate these steps.

### The Rule

**No push until:**

1. **All tests pass** — the full test suite must be green.
2. **Every changed `agentic_devtools/**/*.py` file has 100% branch coverage** —
   verified with `--cov-fail-under=100`.
   Excludes `__init__.py` and `_version.py` (auto-generated / no testable logic).

### For AI Agents (Recommended)

AI agents **must** use `agdt-test` commands — never run `pytest` directly.

1. **Run the full test suite:**

   ```bash
   agdt-test
   agdt-task-wait
   ```

2. **Verify per-file 100% coverage** for each changed source file:

   ```bash
   agdt-test-file --source-file agentic_devtools/path/to/changed_file.py
   agdt-task-wait
   ```

   Repeat for every changed `agentic_devtools/**/*.py` file.

**Both steps must pass before pushing.**

### For Humans / CI Pipelines

Run the combined check script from the repo root:

```bash
bash scripts/check-pr-test-coverage.sh
# or equivalently:
python3 scripts/check-pr-test-coverage.py
```

The shell script is a thin wrapper that delegates to the Python implementation.
This script:

1. Lists all `agentic_devtools/*.py` and `agentic_devtools/**/*.py` files changed vs `origin/main`.
2. Runs the **full test suite** and fails immediately if any test is broken.
3. For each changed source file, runs its matching tests with
   `--cov-branch --cov-fail-under=100` and reports missing lines.

**Exit code 0 = safe to push. Non-zero = fix issues first.**

### Fixing Failures

- If the **full suite fails** (Step 1 in the script), fix the broken tests before
  anything else.
- If a file shows **< 100% coverage**, the `term-missing` column prints the exact
  line numbers missing coverage (e.g., `Missing: 42-45, 78`). Write tests to cover
  those lines, then re-run the script.
- If a file has **no matching test directory or file**, the script prints a `FAIL`
  message and returns a non-zero exit code. Create the test file following the
  [1:1:1 test structure](tests/README.md) and add coverage.

### Manual Per-File Check (Alternative)

If you need to check a single file interactively:

```bash
# Using agdt-test commands (preferred for AI agents)
agdt-test-file --source-file agentic_devtools/cli/git/core.py
agdt-task-wait

# Or for a specific test pattern (synchronous)
agdt-test-pattern tests/unit/cli/git/core/ -v
```

For humans or CI pipelines, the raw pytest equivalent:

```bash
# 1. Convert source path to module
SOURCE_MODULE="agentic_devtools.cli.git.core"

# 2. Find the test path (try 1:1:1 first, then legacy)
TEST_PATH="tests/unit/cli/git/core/"   # 1:1:1
# or: TEST_PATH="tests/test_core.py"   # legacy

# 3. Run with coverage
python -m pytest "$TEST_PATH" -v --tb=short \
  -o addopts= \
  --cov="$SOURCE_MODULE" \
  --cov-branch \
  --cov-report=term-missing \
  --cov-fail-under=100
```

### Test Path Convention

| Source file | 1:1:1 test path (preferred) | Legacy test path |
|---|---|---|
| `agentic_devtools/state.py` | `tests/unit/state/` | `tests/test_state.py` |
| `agentic_devtools/cli/git/core.py` | `tests/unit/cli/git/core/` | `tests/test_core.py` |
| `agentic_devtools/cli/azure_devops/commands.py` | `tests/unit/cli/azure_devops/commands/` | `tests/test_commands.py` |

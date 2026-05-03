# Implementation Plan: Windows [WinError 32] Retry for agdt-copilot-auto-start

## 1. Technical Context

- **Language/Runtime**: Python 3.10+, installed via pip/pipx
- **Module**: `agentic_devtools/cli/copilot/auto_start.py`
- **Call site**: `subprocess.run(copilot_args, cwd=worktree_path)` at line ~458
- **Error**: `OSError` with `winerror=32` (`ERROR_SHARING_VIOLATION`) — Windows-only attribute
- **Test framework**: pytest, 1:1:1 test structure under `tests/unit/`
- **Existing test file**: `tests/unit/cli/copilot/auto_start/test_copilot_auto_start_cmd.py` (70+ KB, covers current OSError paths)

## 2. Research Summary

Research findings on:

- Windows `ERROR_SHARING_VIOLATION` mechanics and the `winerror` attribute
- Exponential backoff parameter selection rationale
- Why a classifier-based approach (not platform-gating) is the correct design

Key decisions:

1. **Retry scope**: Only the `subprocess.run` call site (lines 457–483 in `copilot_auto_start_cmd`)
2. **Classifier approach**: Check `OSError.winerror == 32`; absent attribute → not retryable
3. **Constants as module-level names**: No config/env var surface area
4. **No retry in cleanup**: `_cleanup_auto_start_task` remains best-effort, no retry

## 3. Design Overview

### Architecture

```text
copilot_auto_start_cmd()
  └─ step 6: _run_copilot_with_retry(copilot_args, worktree_path)
       ├─ _is_retryable_win_error(exc) → bool
       │    └─ checks hasattr(exc, 'winerror') and exc.winerror == 32
       ├─ on retryable: log, sleep with backoff, retry
       ├─ on non-retryable OSError: raise immediately
       ├─ on FileNotFoundError: raise immediately
       ├─ on KeyboardInterrupt during sleep: raise immediately
       └─ on budget exhaustion: raise last exception
```

The retry loop is encapsulated in a helper function `_run_copilot_with_retry()` that returns a `subprocess.CompletedProcess` on success or raises the terminal exception. The caller
(`copilot_auto_start_cmd`) retains all existing exception handling (unmark, exit codes) unchanged.

### Module-Level Constants

```python
_RETRY_MAX_ATTEMPTS = 5        # retries (6 total tries)
_RETRY_INITIAL_DELAY_S = 0.5   # first backoff delay
_RETRY_BACKOFF_FACTOR = 2.0    # doubling
_RETRY_MAX_DELAY_S = 4.0       # cap per delay
```

### Key Functions

| Function | Responsibility |
|----------|---------------|
| `_is_retryable_win_error(exc)` | Pure classifier: `True` iff `exc` has `winerror == 32` |
| `_run_copilot_with_retry(args, cwd)` | Retry loop around `subprocess.run`; re-raises terminal exceptions |

## 4. Implementation Phases

### Phase 1: Add Retry Infrastructure (Source Changes)

**File**: `agentic_devtools/cli/copilot/auto_start.py`

**Steps**:

1. Add `import time` to imports
2. Add module-level retry constants after existing constants (line ~49):

   ```python
   _RETRY_MAX_ATTEMPTS = 5
   _RETRY_INITIAL_DELAY_S = 0.5
   _RETRY_BACKOFF_FACTOR = 2.0
   _RETRY_MAX_DELAY_S = 4.0
   ```

3. Add `_is_retryable_win_error(exc: OSError) -> bool` function:
   - Return `getattr(exc, 'winerror', None) == 32`
4. Add `_run_copilot_with_retry(copilot_args: list[str], cwd: str) -> subprocess.CompletedProcess` function:
   - Loop up to `_RETRY_MAX_ATTEMPTS + 1` total tries
   - On `FileNotFoundError`: re-raise immediately (not retryable)
   - On `OSError` where `_is_retryable_win_error` is `True`:
     - If attempts remaining: log retry info to stderr, sleep with backoff, continue
     - If budget exhausted: log summary, re-raise
   - On `OSError` where not retryable: re-raise immediately
   - On `KeyboardInterrupt` during `time.sleep`: re-raise immediately
   - On success: return `CompletedProcess`
5. Replace the `subprocess.run` call in `copilot_auto_start_cmd` (lines 457–459) with a call to `_run_copilot_with_retry(copilot_args, worktree_path)`. The surrounding try/except for
   `FileNotFoundError`, `OSError`, `KeyboardInterrupt` remains unchanged — `_run_copilot_with_retry` re-raises terminal exceptions.

**Deliverable**: Modified `auto_start.py` with retry logic.

### Phase 2: Add Tests (1:1:1 Structure)

**New test files** under `tests/unit/cli/copilot/auto_start/`:

1. **`test__is_retryable_win_error.py`** — Tests for the classifier function:
   - `OSError` with `winerror=32` → `True`
   - `OSError` with `winerror=5` (access denied) → `False`
   - `OSError` without `winerror` attribute (non-Windows) → `False`
   - `FileNotFoundError` (subclass of `OSError`, no `winerror`) → `False`
   - `OSError` with `winerror=None` → `False`

2. **`test__run_copilot_with_retry.py`** — Tests for the retry loop:
   - Succeeds on first try (no retry needed)
   - Transient failure then success after 1 retry
   - Transient failure then success after N retries (N=2, N=5)
   - Exhausts all 6 tries, raises last `OSError`
   - Non-retryable `OSError` (no `winerror`) fails immediately, no retry
   - Non-retryable `OSError` (`winerror=5`) fails immediately
   - `FileNotFoundError` fails immediately, no retry
   - Error type changes mid-retry: `winerror=32` → `FileNotFoundError` on attempt 3
   - `KeyboardInterrupt` during `time.sleep` propagates immediately
   - Verify retry log messages contain attempt number, delay, and winerror code
   - Verify final failure log contains retry count summary
   - Verify backoff delays: 0.5, 1.0, 2.0, 4.0, 4.0

3. **Update `test_copilot_auto_start_cmd.py`** — Integration-level adjustments:
   - Existing `OSError` tests continue to pass (non-retryable OSErrors still fail immediately)
   - Add test: `winerror=32` OSError triggers retry and succeeds after transient failure
   - Add test: `winerror=32` exhaustion → exit 1, unmark called
   - Add test: `KeyboardInterrupt` during retry backoff → exit 130, unmark called

**Ensure `__init__.py`** exists in all new test directories (already exists for `tests/unit/cli/copilot/auto_start/`).

**Deliverable**: Complete test coverage for all scenarios from the spec.

### Phase 3: Validation

1. Run `python scripts/validate_test_structure.py` — verify 1:1:1 compliance
2. Run `agdt-test` + `agdt-task-wait` — full suite passes
3. Run `bash scripts/run-pr-checks.sh` — all CI checks pass
4. Run `ruff check . && ruff format --check .` — lint clean

**Deliverable**: All checks green.

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Existing OSError tests break due to new retry path | Medium | High | Non-retryable OSErrors (no `winerror` attr) bypass retry loop entirely — existing mocks produce plain `OSError()` which has no `winerror` |
| `time.sleep` mock interferes with other tests | Low | Medium | Mock `time.sleep` only in `_run_copilot_with_retry` tests; use module-level patch path |
| Backoff timing makes tests slow | Low | Low | All `time.sleep` calls are mocked in tests |
| Retry masks a persistent error | Low | Medium | Budget is capped at 6 tries / ~11.5s; exhaustion produces clear diagnostic |

## 6. Dependencies

- **Internal**: `agentic_devtools.cli.copilot.auto_start` (existing module being modified)
- **Stdlib only**: `time.sleep` for backoff — no new third-party dependencies
- **No state schema changes**: Retry is entirely within the subprocess call; no new state keys

---
*Generated by Copilot SDK (claude-opus-4.6)*

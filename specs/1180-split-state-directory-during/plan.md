# Implementation Plan: Pin File for State Directory Resolution (#1180)

## 1. Technical Context

- **Language / Runtime**: Python 3.10+, pip-installable CLI package
- **State Management**: JSON files under `.agdt/workflows/{identity}/{worktree_key}/`
- **Resolution Chain (current)**:
  1. `AGENTIC_DEVTOOLS_STATE_DIR` env var (explicit override)
  2. `.agdt/workflows/{identity}/{worktree_key}/` via git root — identity from `.agdt/identity.json` (or legacy `runtime-bootstrap.json`), worktree_key from `runtime-bootstrap.json`
  3. `.agdt/workflows/_unscoped/` fallback (when identity or worktree_key is missing)
  4. `.agdt-temp/` in CWD (when not in a git repo)
- **Background Tasks**: Spawned via `run_in_background()` / `run_function_in_background()` using `subprocess.Popen` with `os.environ.copy()`
- **Atomic Writes**: Existing pattern in `review_state.py` uses temp-file + `os.replace()`
- **Testing**: 2000+ tests, 100% coverage policy, 1:1:1 test structure under `tests/unit/`

## 2. Research Summary

Key decisions from the design research:

1. **Pin file at `.agdt/pinned-state-dir.json`** — repo-root-level, discoverable without knowing the state dir first (avoids circular dependency)
2. **Atomic writes via `os.replace()`** — consistent with existing patterns
3. **TTL-based expiration** with explicit renewal on workflow progress — balances cleanup of abandoned sessions vs. long-running reviews
4. **Environment variable inheritance** via `os.environ.copy()` — already in place; just needs the parent to set `AGENTIC_DEVTOOLS_STATE_DIR` before spawning

## 3. Design Overview

```text
┌─────────────────────────────────────────────────────┐
│            get_state_dir() Resolution Chain          │
│                                                      │
│  1. AGENTIC_DEVTOOLS_STATE_DIR env var  ──► return   │
│  2. .agdt/pinned-state-dir.json         ──► validate │
│     └─ workflow field matches?                       │
│     └─ TTL not expired?                              │
│     └─ path inside repo root?                        │
│     └─ path exists or creatable?                     │
│     └─ valid JSON?                                   │
│     YES ──► return pinned state_dir                  │
│     NO  ──► fall through with diagnostic             │
│  3. runtime-bootstrap.json (existing)   ──► return   │
│  4. _unscoped fallback                  ──► return   │
│  5. .agdt-temp/ CWD fallback            ──► return   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│        initiate_pull_request_review_workflow()       │
│                                                      │
│  1. Resolve state_dir (once)                         │
│  2. Write .agdt/pinned-state-dir.json (atomic)       │
│  3. Set AGENTIC_DEVTOOLS_STATE_DIR = state_dir       │
│  4. Spawn background tasks (inherit env)             │
│  5. Later independent CLI invocations read pin file   │
│     (child processes use env var fast-path instead)   │
└─────────────────────────────────────────────────────┘
```

## 4. Implementation Phases

### Phase 1: Pin File Infrastructure (Core)

**Deliverables**: Pin file read/write/validate functions in `state.py`

#### Tasks

1. **Add pin file constants and schema**
   - File: `agentic_devtools/state.py`
   - Add `PIN_FILENAME = "pinned-state-dir.json"`
   - Add `RECOGNIZED_PIN_WORKFLOWS = frozenset({"pull-request-review"})`
   - Add `DEFAULT_PIN_TTL_HOURS = 24`

2. **Implement `write_pin_file(state_dir, workflow, ttl_hours=24)`**
   - File: `agentic_devtools/state.py`
   - Locate `.agdt/` via `_get_git_repo_root()`
   - **Resolve `state_dir` to an absolute path** (via `Path.resolve()`) before writing —
     this ensures later independent CLI invocations are not CWD-dependent
   - Write JSON with `state_dir` (absolute), `workflow`, `created_utc` (ISO-8601 UTC), `ttl_hours`
   - Use write-to-temp-then-`os.replace()` pattern
   - Return the pin file path

3. **Implement `read_and_validate_pin_file(git_root)`**
   - File: `agentic_devtools/state.py`
   - Read `.agdt/pinned-state-dir.json`
   - Validate: parseable JSON, required fields present, `workflow` in `RECOGNIZED_PIN_WORKFLOWS`,
     `created_utc` + `ttl_hours` not expired, **`state_dir` is an absolute path** (reject relative
     values with a diagnostic — do not silently resolve them, as the CWD context is unknown),
     `state_dir` inside repo root, `state_dir` exists or creatable
   - Return `state_dir` Path on success, `None` on failure
   - Emit `[agdt]` diagnostics to stderr on validation failure

4. **Implement `delete_pin_file(git_root=None)`**
   - File: `agentic_devtools/state.py`
   - Delete `.agdt/pinned-state-dir.json` if it exists
   - Silent no-op if absent

5. **Implement `refresh_pin_file_ttl()`**
   - File: `agentic_devtools/state.py`
   - Read existing pin file, update `created_utc` to current UTC time, write atomically
   - No-op if pin file doesn't exist or is invalid

6. **Write tests for all pin file functions** (TDD — write tests first)
   - Files: `tests/unit/state/test_write_pin_file.py`, `test_read_and_validate_pin_file.py`,
     `test_delete_pin_file.py`, `test_refresh_pin_file_ttl.py`
   - Cover: happy path, expired TTL, invalid JSON, missing fields, path traversal,
     non-existent path, unrecognized workflow, concurrent overwrite,
     relative `state_dir` rejected by `read_and_validate_pin_file`

### Phase 2: Modify `get_state_dir()` Resolution Chain

**Deliverables**: Pin file as step 2 in resolution chain

#### Tasks

1. **Insert pin file check between env var and bootstrap**
   - File: `agentic_devtools/state.py`, function `get_state_dir()`
   - After env var check (line ~503), before git-based resolution (line ~509)
   - Call `read_and_validate_pin_file(git_root)` — requires getting `git_root` first
   - If valid, `mkdir` + return the pinned `state_dir`
   - Add diagnostic log: `[agdt] State dir resolved via pin file: <path>`

2. **Add diagnostic logging for resolution path (scoped to avoid noise)**
   - File: `agentic_devtools/state.py`, function `get_state_dir()`
   - Log which resolution path was used (env var, pin file, bootstrap, fallback)
   - Use `print(..., file=sys.stderr)` with `[agdt]` prefix
   - **Scope to avoid noise** — `get_state_dir()` is called many times per process
     (via `get_state_file_path()`, `get_value()`, etc.); unconditional logging would
     flood stderr. Emit diagnostics only when:
     (a) the pin file is used (pin resolution path hit), or
     (b) pin validation fails (explains why pin was skipped), or
     (c) `AGDT_DEBUG=1` env var is set (explicit opt-in for full resolution tracing)
   - For (a) and (b), use a module-level `_pin_logged` flag to emit at most once per process

3. **Write tests for modified `get_state_dir()`**
   - File: `tests/unit/state/test_get_state_dir.py` (extend existing)
   - Cover: pin file honored, pin file expired → fallback, env var still takes priority,
     no pin file → bootstrap as before, invalid pin → bootstrap

### Phase 3: Workflow Initiation — Write Pin + Set Env Var

**Deliverables**: PR review workflow writes pin file and propagates env var

#### Tasks

1. **Write pin file in `initiate_pull_request_review_workflow()`**
    - File: `agentic_devtools/cli/workflows/commands.py`
    - After bootstrap scope is set (around line ~320) and state dir is resolved
    - Resolve once: `state_dir = get_state_dir()` (returns `Path`)
    - Pass the `Path` directly: `write_pin_file(state_dir, workflow="pull-request-review")`
      (`write_pin_file` accepts `Path | str` and normalizes internally)
    - Stringify only for the env var: `os.environ["AGENTIC_DEVTOOLS_STATE_DIR"] = str(state_dir)`
    - Note: the env var propagates to immediate child processes (background tasks)
      via `os.environ.copy()`; the pin file serves later *independent* CLI invocations
      that do not inherit the env (e.g., after the initiating process exits)

2. **Modify `setup_pull_request_review()` to skip bootstrap when env var set**
    - File: `agentic_devtools/cli/azure_devops/review_commands.py`
    - Guard the `set_bootstrap_state(worktree_key=...)` call (line ~758) with
      `if not os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR"):`
    - This implements FR-004

3. **Write tests for workflow initiation changes**
    - Files: `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py` (extend),
      `tests/unit/cli/azure_devops/review_commands/test_setup_pull_request_review.py` (extend)

### Phase 4: Background Task Environment Propagation

**Deliverables**: Background tasks inherit `AGENTIC_DEVTOOLS_STATE_DIR`

#### Tasks

1. **Verify `run_in_background()` inherits env var**
    - File: `agentic_devtools/background_tasks.py`
    - Both `run_in_background()` and `run_function_in_background()` already do
      `env = _os.environ.copy()` — this naturally inherits `AGENTIC_DEVTOOLS_STATE_DIR`
    - **No code changes expected** — just verify with a test

2. **Write test confirming env var inheritance**
    - File: `tests/unit/background_tasks/test_run_in_background.py` (extend)
    - Mock `subprocess.Popen`, assert `env` dict contains `AGENTIC_DEVTOOLS_STATE_DIR`
      when parent has it set

### Phase 5: Pin File Cleanup

**Deliverables**: Pin file deleted on workflow completion and `agdt-clear-workflow`

#### Tasks

1. **Delete pin file in `clear_workflow_cmd()`**
    - File: `agentic_devtools/cli/state.py`, function `clear_workflow_cmd()`
    - Call `delete_pin_file()` unconditionally before or after clearing workflow state

2. **Delete pin file on workflow completion (conditional)**
    - File: `agentic_devtools/state.py` or workflow completion handler
    - When workflow completes, delete pin file only if `workflow` field matches
    - Locate the completion handler (likely in `clear_workflow_state()` or the
      workflow advancement code)

3. **Refresh pin TTL in `advance_workflow_cmd()`**
    - File: `agentic_devtools/cli/workflows/__init__.py`, function `advance_workflow_cmd()`
    - Call `refresh_pin_file_ttl()` after successfully advancing the workflow step
    - Implements FR-010

4. **Write tests for cleanup and TTL refresh**
    - Files: `tests/unit/cli/state/test_clear_workflow_cmd.py` (extend),
      `tests/unit/state/test_refresh_pin_file_ttl.py` (already created in Phase 1)

### Phase 6: Integration Testing & Edge Cases

**Deliverables**: Full coverage of edge cases, passing test suite

#### Tasks

1. **Test edge cases from spec**
    - Empty `AGENTIC_DEVTOOLS_STATE_DIR` string → treated as unset, falls through
    - Non-existent pin `state_dir` that can be created → created and used
    - Non-existent pin `state_dir` that cannot be created → ignored
    - Pin `state_dir` outside repo root → ignored
    - Concurrent overwrite of pin file → last writer wins (acceptable)
    - Stale pin after crash → TTL expiration handles cleanup
    - Truncated/corrupt pin file → ignored with diagnostic

2. **Run full test suite and fix regressions**
    - Run `bash scripts/run-pr-checks.sh`
    - Verify zero existing test failures
    - Verify 100% coverage on modified files

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Pin file creates new race condition (concurrent writes) | Low | Medium | `os.replace()` is atomic; last writer wins is acceptable per spec |
| TTL too short for very long reviews | Low | Low | Default 24h; `agdt-advance-workflow` refreshes TTL |
| Non-review commands use wrong state dir when pin active | Medium | Low | By design — pin is intentionally global during review; TTL-bounded |
| `_get_git_repo_root()` called twice in `get_state_dir()` (perf) | Medium | Low | Cache git root within the function; it's already called for bootstrap |
| Pin file left stale after system crash | Medium | Low | 24h TTL auto-expiry; `agdt-clear-workflow` manual cleanup |

## 6. Dependencies

- **Internal**: `state.py` (`get_state_dir`, `set_bootstrap_state`), `background_tasks.py` (`run_in_background`, `run_function_in_background`), `cli/workflows/commands.py`,
  `cli/azure_devops/review_commands.py`, `cli/state.py`
- **External**: None — uses only Python stdlib (`json`, `os`, `pathlib`, `datetime`)
- **Test infrastructure**: Existing `pytest` + `unittest.mock` patterns

---
*Generated by Copilot SDK (claude-opus-4.6)*

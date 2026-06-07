# Implementation Plan: Prevent Duplicate Copilot Sessions During PR Review Workflow

**Branch**: `speckit/1912/phase-3-plan` | **Date**: 2026-06-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/1912-bug-duplicate-copilot-sessions/spec.md`

## 1. Technical Context

**Language/Version**: Python 3.10+ (type hints, dataclasses, ctypes for Windows interop)
**Primary Dependencies**: `agentic-devtools` — pip-installable CLI package; `agentic_devtools/state.py`, `file_locking.py`, `subprocess.Popen`, `os`, `ctypes`
**Storage**: JSON state file with file-locking (`agentic_devtools/state.py`, `file_locking.py`)
**Testing**: pytest with 100% branch coverage requirement per file
**Target Platform**: Windows (primary developer environment) + Linux/macOS (CI)
**Project Type**: single

### Key Dependencies (All Existing)

- `agentic_devtools/state.py` — `get_state_dir()`, `get_value()`, `set_value()`, `get_workflow_state()`
- `agentic_devtools/cli/copilot/session.py` — `start_copilot_session()`, `_persist_session_state()`
- `agentic_devtools/cli/copilot/auto_start.py` — `copilot_auto_start_cmd()`
- `agentic_devtools/cli/workflows/__init__.py` — `advance_workflow_cmd()`
- `agentic_devtools/cli/workflows/worktree_setup.py` — `_run_auto_execute_command()`
- `agentic_devtools/file_locking.py` — `locked_state_file()`, `FileLockError`

### Architecture Decisions

1. **Guard function pattern** — `_check_session_mutex()` as a private guard called at the top of `start_copilot_session()`
2. **Environment variable for state alignment** — `AGENTIC_DEVTOOLS_STATE_DIR` set by auto-execute before invoking nested workflow
3. **Grace period in auto-start** — polling loop within `copilot_auto_start_cmd()`, not in generic advance logic
4. **ctypes for Windows PID liveness** — `kernel32.OpenProcess` + `CloseHandle`, no process name matching
5. **No new dependencies** — standard library only (`os`, `ctypes`, `time`)

## 2. Research Summary

See [research.md](research.md) for detailed technical decisions on:

- PID liveness verification (cross-platform)
- Grace period implementation strategy
- State directory alignment approach
- Advance-workflow error message taxonomy

Key decisions:

- Use `os.kill(pid, 0)` on Unix and `ctypes` `kernel32.OpenProcess` on Windows
- Grace period lives in `copilot_auto_start_cmd()` with 2s interval / 10s timeout defaults
- Auto-execute sets `AGENTIC_DEVTOOLS_STATE_DIR` (existing priority 1 in resolution)
- Advance-workflow distinguishes "no state file" vs "workflow cleared" vs "workflow completed"

## 3. Design Overview

### Component Interaction (Happy Path)

```text
┌─────────────────────┐       ┌───────────────────────┐       ┌──────────────────────┐
│  Originating Repo   │       │   Target Worktree     │       │   VS Code Auto-Start │
│  (auto-execute)     │       │   (state file)        │       │   Task (46s delay)   │
└─────────┬───────────┘       └───────────┬───────────┘       └──────────┬───────────┘
          │                               │                              │
          │ 1. Set AGENTIC_DEVTOOLS_      │                              │
          │    STATE_DIR → target path    │                              │
          │ 2. Invoke workflow cmd        │                              │
          │    (--skip-copilot-session)   │                              │
          │─────────────────────────────>│ 3. Write workflow state       │
          │                               │    + copilot.model_id        │
          │                               │                              │
          │                               │       4. VS Code opens       │
          │                               │<─────────────────────────────│
          │                               │                              │
          │                               │  5. Grace period poll (10s)  │
          │                               │<─────────────────────────────│
          │                               │     Finds workflow active    │
          │                               │                              │
          │                               │  6. Persist auto-start       │
          │                               │     session marker           │
          │                               │                              │
          │                               │  7. Later duplicate start    │
          │                               │     sees marker/PID → BLOCK  │
          │                               │────────────────────────────>│ Exit 0 (no dup)
          │                               │                              │
```

### Defense-in-Depth Layers

| Layer | Component | Purpose |
|-------|-----------|---------|
| L1 | State directory alignment (FR-002) | Both contexts resolve to same state path |
| L2 | Grace period polling (FR-007) | Auto-start waits for state to appear |
| L3 | Session mutex (FR-001, FR-004) | Persisted auto-start session marker and PID liveness block duplicate starts |
| L4 | Advance-workflow guard (FR-003) | No fallback re-initiation on missing state |
| L5 | Agent prompt hardening (FR-006) | Agent instructed never to re-initiate |

## 4. Implementation Phases

### Phase 1: Session Mutex Guard (FR-001, FR-004, FR-005, FR-008)

**Deliverable**: `_check_session_mutex()` in `session.py` that honors both cross-platform PID liveness and the auto-start session marker persisted while `agdt-copilot-auto-start` is running.

**Files to create/modify**:

| File | Action | Description |
|------|--------|-------------|
| `agentic_devtools/cli/copilot/session.py` | Modify | Add `_check_session_mutex()`, `_is_process_alive()`, call guard at top of `start_copilot_session()` |
| `tests/unit/cli/copilot/session/test__check_session_mutex.py` | Create | Unit tests for guard function |
| `tests/unit/cli/copilot/session/test__is_process_alive.py` | Create | Unit tests for PID liveness (mock ctypes on Windows) |

**Implementation details**:

1. Add `_is_process_alive(pid: int) -> bool`:
   - Unix: `os.kill(pid, 0)` — catches `ProcessLookupError` (dead) and `PermissionError` (alive but not owned)
   - Windows: use `ctypes.WinDLL("kernel32", use_last_error=True)`; explicitly set `argtypes`/`restype` on
     `kernel32.OpenProcess` and `kernel32.CloseHandle` before calling them (avoids 64-bit handle truncation);
     aligns with the existing `_is_owner_alive()` pattern in `agentic_devtools/segments/cleanup.py`
   - Returns `True` if process exists, `False` otherwise

2. Add `_check_session_mutex(requested_mode: str) -> dict[str, Any] | None` (existing-session snapshot or no active session):
   - Wrap the entire read/decision/cleanup sequence in `read_modify_write_state()` to hold a single
     exclusive file lock throughout; do NOT use `load_state_locked()` — it silently falls back to an
     unlocked read on `FileLockError`, making deduplication fail open under contention
   - Catch `FileLockError` from `read_modify_write_state()` and fail closed: emit a stderr warning and
     return a structured placeholder snapshot with the fields required for a no-op `CopilotSessionResult`,
     e.g. `{"session_id": "lock-unavailable", "mode": requested_mode, "prompt_file": "", "start_time": "unknown", "pid": None, "log_file": None, "lock_unavailable": True}`;
     the caller treats any non-`None` return as "session active" and returns a lock-safe no-op result
   - Do NOT call `get_value()` per-key inside the guard (avoids TOCTOU races between concurrent processes)
   - From the locked snapshot, read `copilot.pid`, `copilot.start_time`, `copilot.session_id`, and the
     auto-start session marker key `copilot.auto_start_session_marker`
   - If neither a PID nor an active auto-start marker is present → return `None` (no session to dedupe)
   - Parse PID as int; if parse fails → clear the stale PID field inside the `read_modify_write_state()`
     callback and continue evaluating the marker
   - Call `_is_process_alive(pid)` when a PID is available
   - If PID is alive **or** auto-start marker is still active → print a warning to stderr with
     PID/start_time/session_id context and return the same locked snapshot fields needed for a no-op
     `CopilotSessionResult` (`session_id`, `mode`, `prompt_file`, `start_time`, `pid`, optional `log_file`)
   - If PID is dead and marker is stale/cleared → clear stale mutex fields inside the same callback and
     return `None` (allow new session)

3. Insert `_check_session_mutex(requested_mode)` at the top of `start_copilot_session()` (after docstring,
   after computing `requested_mode`, and before session_id generation); if it returns any non-`None` value,
   return a no-op result with `process=None`:
   - If the returned dict is a live-session snapshot, populate `CopilotSessionResult` directly from
     snapshot keys (`session_id`, `mode`, `prompt_file`, `start_time`, `pid`, `log_file` when present)
   - If the returned dict has `lock_unavailable=True`, populate `CopilotSessionResult` directly from that
     structured placeholder snapshot (concrete string fields already supplied, `pid`/`log_file` may be
     `None`) — no second state read is performed in either path
   Do not generate a new `session_id` or prompt file, and do not overwrite `copilot.*` metadata in this
   path. CLI entry points may decide whether to convert that no-op into `sys.exit(0)`.

**Test strategy**: Mock `os.kill`; mock `ctypes.WinDLL` via `unittest.mock.patch("ctypes.WinDLL")` and
configure the returned mock `kernel32` object's `OpenProcess`/`CloseHandle` attributes; test
alive/dead/stale/missing scenarios.

---

### Phase 2: State Directory Alignment (FR-002)

**Deliverable**: Auto-execute command sets `AGENTIC_DEVTOOLS_STATE_DIR` to target worktree's state path.

**Files to modify**:

| File | Action | Description |
|------|--------|-------------|
| `agentic_devtools/cli/workflows/worktree_setup.py` | Modify | Ensure `_run_auto_execute_command()` sets env var correctly |
| `tests/unit/cli/workflows/worktree_setup/test__run_auto_execute_command.py` | Modify | Add test for env var propagation |

**Implementation details**:

The exploration revealed that `_run_auto_execute_command()` (line 2133 in `worktree_setup.py`) already
"pins `AGENTIC_DEVTOOLS_STATE_DIR` to the target worktree's identity-scoped state dir." This means
FR-002 may already be partially or fully implemented. The phase focuses on:

1. **Verification**: Confirm the env var is set to the *exact* path that `get_state_dir()` would resolve
   when called from within the target worktree (with bootstrap).
2. **Test hardening**: Add explicit assertions that the env var value matches the path produced by
   resolving the target worktree's bootstrap configuration.
3. **Edge case**: If the target worktree lacks `runtime-bootstrap.json` (first-time setup), ensure
   the auto-execute still resolves a stable path (e.g., `_unscoped` fallback) and documents this.

---

### Phase 3: Grace Period Polling in Auto-Start (FR-007)

**Deliverable**: `copilot_auto_start_cmd()` polls for workflow state availability before
proceeding, invokes the same `_check_session_mutex()` guard used by
`start_copilot_session()`, and persists the session marker needed by that mutex while
the auto-start-launched session is active.

**Files to modify**:

| File | Action | Description |
|------|--------|-------------|
| `agentic_devtools/cli/copilot/auto_start.py` | Modify | Add grace period polling loop and auto-start session marker lifecycle before copilot execution |
| `tests/unit/cli/copilot/auto_start/test__wait_for_workflow_state.py` | Create | Tests for grace period behavior |
| `tests/unit/cli/copilot/auto_start/test_copilot_auto_start_cmd.py` | Modify | Extend command-level tests to cover setting/clearing the auto-start session marker |

**Implementation details**:

1. Add constants:

   ```python
   _GRACE_PERIOD_INTERVAL_S = 2.0
   _GRACE_PERIOD_TIMEOUT_S = 10.0
   ```

2. Add `_wait_for_workflow_state(state_file_path: Path, timeout: float, interval: float) -> bool`:
   - Poll loop: acquire `locked_state_file(state_file_path)` on each iteration, read a consistent snapshot,
     and check for `workflow` key with `active` field
   - Return `True` if found within timeout, `False` if timeout expires
   - Handle `FileNotFoundError`, `FileLockError`, and `json.JSONDecodeError` gracefully (retry) so
     transient lock contention or partial writes do not make the grace-period poll flaky

3. Insert grace period call in `copilot_auto_start_cmd()` after state file path resolution (line ~498)
   and before the run-ID deduplication check:
   - Call `_wait_for_workflow_state(state_file_path, _GRACE_PERIOD_TIMEOUT_S, _GRACE_PERIOD_INTERVAL_S)`
   - If returns `False`: print error to stderr with prescribed message, `sys.exit(1)`

4. Persist an auto-start session marker immediately before invoking the Copilot CLI and clear it on every exit path:
   - Use dedicated key `copilot.auto_start_session_marker` (distinct from `copilot.auto_start_triggered_runs`)
     with schema `{session_id, start_time, auto_start_run_id, pid, active}`, where `pid` is the current
     `agdt-copilot-auto-start` process PID from `os.getpid()`
   - `_check_session_mutex()` should treat the marker as stale when the marker PID is missing, unparseable,
     or no longer alive, and clear stale marker fields inside the same locked update
   - Clear the marker in the success, failure, and interrupt cleanup paths so stale state does not block later sessions

5. Add CLI args `--grace-period-timeout` and `--grace-period-interval` (optional, for testing)

**Test strategy**: Mock `time.sleep`, test timeout expiry, test early detection, test corrupt JSON handling,
and verify the auto-start session marker is written before launch and cleared on all exit paths.

---

### Phase 4: Advance-Workflow Guard (FR-003)

**Deliverable**: `advance_workflow_cmd()` provides actionable errors without fallback initiation.

**Files to modify**:

| File | Action | Description |
|------|--------|-------------|
| `agentic_devtools/cli/workflows/__init__.py` | Modify | Enhance error messages in `advance_workflow_cmd()` |
| `tests/unit/cli/workflows/__init__/test_advance_workflow_cmd.py` | Modify/Create | Test error message taxonomy (migrate coverage from existing `tests/unit/cli/workflows/commands/test_advance_workflow_cmd.py`) |
| `tests/unit/cli/workflows/commands/test_advance_workflow_cmd.py` | Retire | Remove or redirect legacy duplicate tests after migration to keep a single source of truth |

**Implementation details**:

1. Replace the existing error block (line 51-53):

   ```python
   if not workflow:
       print("ERROR: No workflow is currently active.", file=sys.stderr)
       sys.exit(1)
   ```

   With a richer diagnostic based on a best-effort lock-protected state read rather than
   `state_file.exists()`:

   ```python
   if not workflow or workflow.get("status") == "completed":
       state_dir = get_state_dir()
       state = load_state(use_locking=True)
       workflow_state = state.get("workflow") if isinstance(state, dict) else None
       workflow_status = (
           workflow_state.get("status") if isinstance(workflow_state, dict) else None
       )
       if workflow_status == "completed":
           print(
               "ERROR: Workflow is already completed.\n"
               f"  State directory: {state_dir}\n"
               "  Action: Run `agdt-show` to inspect current state values. "
               "Do NOT re-initiate the workflow.",
               file=sys.stderr,
           )
       elif not isinstance(state, dict) or not state:
           print(
               "ERROR: No workflow state found.\n"
               f"  State directory: {state_dir}\n"
               "  This suggests the state directory may not match "
               "the one written by the auto-execute command.\n"
               "  Action: Verify the AGENTIC_DEVTOOLS_STATE_DIR environment variable "
               "matches the path above. "
               "Do NOT re-initiate the workflow.",
               file=sys.stderr,
           )
       elif "workflow" not in state:
           print(
               "ERROR: Workflow state was cleared.\n"
               f"  State directory: {state_dir}\n"
               "  Action: Run `agdt-show` to inspect current state values. "
               "Do NOT re-initiate the workflow.",
               file=sys.stderr,
           )
       else:
           # Workflow payload exists, but no active workflow can be advanced
           print(
               "ERROR: Workflow state exists but no active workflow found.\n"
               f"  State directory: {state_dir}\n"
               "  The workflow may have been cleared.\n"
               "  Action: Run `agdt-show` to check current state values. "
               "Do NOT re-initiate the workflow.",
               file=sys.stderr,
           )
       sys.exit(1)
   ```

2. Ensure the exit code is non-zero (already `sys.exit(1)`)

**Test strategy**: Test with missing state file, empty `{}` state, state file with no workflow key, and
state file with completed workflow status. Missing/empty cases should produce "No workflow state
found", no-workflow-key should produce "Workflow state was cleared", and completed workflow status
should produce "Workflow is already completed".

---

### Phase 5: Agent Prompt Hardening (FR-006)

**Deliverable**: Updated agent prompts with explicit no-reinitiation instructions.

**Files to modify**:

| File | Action | Description |
|------|--------|-------------|
| `.github/agents/agdt.copilot-auto-start.agent.md` | Modify | Add no-reinitiation guardrails |
| `.github/agents/agdt.advance-workflow.agent.md` | Modify | Add no-reinitiation guardrails |

**Implementation details**:

1. Update `agdt.copilot-auto-start.agent.md`:
   - Add prerequisite: "An active workflow MUST already exist in the state directory"
   - Add explicit rule: "If `agdt-copilot-auto-start` fails or no workflow is found, do NOT call
     `@agdt.pull-request-review.initiate`. Report the error and await human intervention."

2. Update `agdt.advance-workflow.agent.md`:
   - Add explicit rule: "If `agdt-advance-workflow` fails with 'No active workflow found', do NOT
     fall back to initiating a new workflow. Report the error and wait for resolution."
   - Add troubleshooting: "Use the `State directory: ...` value printed in
     `agdt-advance-workflow` errors to verify the resolved state path, then run `agdt-show` to
     inspect state contents."

---

### Phase 6: Integration Testing & Validation

**Deliverable**: End-to-end tests and documentation updates.

**Files to create/modify**:

| File | Action | Description |
|------|--------|-------------|
| `tests/unit/cli/copilot/session/test__is_process_alive.py` | Verify | Ensure cross-platform coverage |
| `.github/copilot-instructions.md` | Modify | Document new behavior and state keys |
| Test suite validation | Run | `agdt-test` full suite, targeted checks |

**Validation steps**:

1. Run `agdt-test` — full suite passes
2. Run `bash scripts/targeted-checks.sh` — lint, format, mypy, coverage pass
3. Manual verification: simulate cross-repo initiation timing scenario

## 5. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Grace period too short (state not ready in 10s) | Auto-start fails, no session starts | Low | Configurable timeout via CLI arg; 10s is generous for file I/O |
| PID recycling on Windows causes false positive mutex | Blocks legitimate session start | Very Low | Short time window (seconds); user can `agdt-delete copilot.pid` to recover |
| `_run_auto_execute_command` env var logic already correct | Wasted Phase 2 effort | Medium | Phase 2 is primarily verification/test hardening — low cost if already working |
| Interactive session (pid=None) leaves no mutex | Duplicate non-interactive session alongside interactive | Low | Interactive sessions block caller; only non-interactive sessions write PID |
| Breaking existing single-repo workflows | Regression for common case | Low | NFR-002 explicitly preserves existing behavior when env var not set |

## 6. Dependencies

### Internal Dependencies (Phase Order)

- Phase 1 (mutex) is independent — can be implemented first
- Phase 2 (state alignment) is independent — can be parallelized with Phase 1
- Phase 3 (grace period) depends on understanding Phase 2's state file path
- Phase 4 (advance-workflow guard) is independent
- Phase 5 (prompts) is independent
- Phase 6 (integration) depends on all prior phases

### External Dependencies

- None — all implementation uses Python standard library
- No new pip packages required
- No changes to `pyproject.toml` entry points needed (existing commands are being hardened)

### Files Requiring `__init__.py` Creation (1:1:1 Test Policy)

```text
tests/unit/cli/copilot/session/__init__.py  (if not exists)
tests/unit/cli/copilot/auto_start/__init__.py  (if not exists)
tests/unit/cli/workflows/__init__.py  (if not exists — may already exist)
tests/unit/cli/workflows/__init__/__init__.py  (new directory for advance_workflow_cmd tests)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*

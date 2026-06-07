# Implementation Plan: PR Review Workflow State Directory Mismatch

**Branch**: `speckit/1913/phase-3-plan` | **Date**: 2026-06-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/1913-bug-review-workflow-state/spec.md`

## 1. Technical Context

**Stack**: Python >=3.10 CLI package (`agentic-devtools`), installed globally via pip/pipx.  
**Key modules**: `agentic_devtools/state.py`, `agentic_devtools/cli/workflows/worktree_setup.py`, `agentic_devtools/cli/workflows/commands.py`.  
**Mechanism**: Pin file (`pinned-state-dir.json`) introduced by #1180 for atomic state directory resolution across independent CLI invocations.

### Architecture Summary

The cross-worktree workflow has three stages:

1. **Source repo invocation** — user runs `agdt-initiate-*-workflow` from the main repo
2. **Auto-execute subprocess** — `_run_auto_execute_command` re-runs the workflow init inside the target worktree with `AGENTIC_DEVTOOLS_STATE_DIR` set
3. **VS Code auto-start** — `copilot_auto_start_cmd` fires via `runOn: folderOpen`, clears env vars, resolves state via `get_state_dir()` (pin file → bootstrap → fallback)

## 2. Research Summary

Detailed root cause analysis is summarized in this section.

**Key finding**: The pin file is never written to the target worktree's `.agdt/` directory:

- In stage 1 (source repo), the pin file is written to the *source* repo's `.agdt/` — wrong location for the auto-start task which operates in the target worktree context.
- In stage 2 (subprocess), `AGENTIC_DEVTOOLS_STATE_DIR` is set by `_run_auto_execute_command`, causing `commands.py` L376–378 to skip the `write_pin_file()` call entirely.
- In stage 3, `copilot_auto_start_cmd` clears the env var and calls `get_state_dir()`. With no pin file in the target worktree, resolution falls through to bootstrap-based paths, which may resolve a
  different physical directory.

**Decision**: Write the pin file inside `_run_auto_execute_command` after state dir resolution and before the subprocess spawns. This is the single choke point where all cross-worktree workflows pass
through, and it executes before VS Code opens.

## 3. Design Overview

```text
┌─────────────────────────────────┐
│ Source Repo                     │
│ agdt-initiate-*-workflow        │
│   ├─ write_pin_file (source)    │  ← existing, stays
│   ├─ preflight fails            │
│   └─ perform_auto_setup()       │
│       └─ setup_worktree_...()   │
│           └─ _run_auto_execute_ │
│              command()          │
│              ├─ resolve state   │
│              │  dir from target │
│              │  worktree        │
│              ├─ write_pin_file  │  ← NEW: writes to TARGET worktree
│              │  (target)        │
│              ├─ spawn subprocess│
│              └─ (Phase 4 adds:  │
│                  subprocess     │
│                  also writes    │
│                  pin — belt &   │
│                  suspenders)    │
│                                 │
│   ┌─── VS Code opens ──────┐   │
│   │ auto-start task fires   │   │
│   │ clears env var          │   │
│   │ get_state_dir():        │   │
│   │   1. env var (cleared)  │   │
│   │   2. pin file ✓ FOUND   │   │ ← reads pin from target worktree
│   │   3. bootstrap fallback │   │
│   └─────────────────────────┘   │
└─────────────────────────────────┘
```

### Changes at a Glance

| File | Change |
|------|--------|
| `state.py` | Expand `RECOGNIZED_PIN_WORKFLOWS`; add `target_git_root` param to `write_pin_file()` |
| `worktree_setup.py` | Add `workflow` param to `_run_auto_execute_command`; write pin file after state dir resolution |
| `commands.py` | Write pin file in the `env_override` branch (L376–378) as belt-and-suspenders |
| Tests | New unit tests for each changed function |

## 4. Implementation Phases

### Phase 1 — Expand `RECOGNIZED_PIN_WORKFLOWS` (state.py)

**Deliverable**: All cross-worktree workflows are recognized for pin file operations.

**Changes**:

1. Update `RECOGNIZED_PIN_WORKFLOWS` frozenset at L44 to include all 9 workflow names used by `perform_auto_setup()`:

```python
RECOGNIZED_PIN_WORKFLOWS: frozenset[str] = frozenset({
    "pull-request-review",
    "work-on-jira-issue",
    "create-jira-issue",
    "create-jira-epic",
    "create-jira-subtask",
    "update-jira-issue",
    "apply-pull-request-review-suggestions",
    "optimize-issue-for-ai-agent",
    "break-down-issue-into-subtasks",
})
```

**Tests**: Update any existing tests that assert the contents of `RECOGNIZED_PIN_WORKFLOWS`. Add a test that verifies all workflow names passed to `perform_auto_setup()` are present in the frozenset.

**Files**:

- `agentic_devtools/state.py` (L44)
- `tests/unit/state/test_write_pin_file.py` — update assertions on ValueError for unrecognized workflows
- `tests/unit/state/test_read_and_validate_pin_file.py` — update assertions if any test hardcodes the set
- `tests/unit/state/test_refresh_pin_file_ttl.py` — update L136 area (test for unrecognized workflow)

---

### Phase 2 — Add `target_git_root` Parameter to `write_pin_file()` (state.py)

**Deliverable**: `write_pin_file()` can write to an explicit git root instead of auto-detecting via CWD.

**Changes**:

1. Add optional `target_git_root: Path | None = None` parameter to `write_pin_file()`.
2. When `target_git_root` is provided and is an existing directory, use it directly instead of calling `_get_git_repo_root()`.
3. When `target_git_root` is `None` (default), preserve existing auto-detection behavior.

```python
def write_pin_file(
    state_dir: str | Path,
    workflow: str,
    ttl_hours: int = DEFAULT_PIN_TTL_HOURS,
    target_git_root: Path | None = None,
) -> Path | None:
    # ... validation unchanged ...

    git_root = (
        target_git_root
        if (target_git_root is not None and target_git_root.is_dir())
        else _get_git_repo_root()
    )
    if git_root is None:
        return None
    # ... rest unchanged ...
```

**Tests**: Add test cases for:

- `target_git_root` provided and exists → pin written to that location
- `target_git_root=None` → existing auto-detect behavior preserved
- `target_git_root` pointing to a non-existent dir → `.is_dir()` guard fails, falls back to auto-detection

**Files**:

- `agentic_devtools/state.py` (L505–564)
- `tests/unit/state/test_write_pin_file.py` — new test cases

---

### Phase 3 — Write Pin File in `_run_auto_execute_command` (worktree_setup.py)

**Deliverable**: The canonical state directory is pinned in the target worktree before the subprocess runs, ensuring the auto-start task resolves the same directory.

**Changes**:

1. Add `workflow: str | None = None` parameter to `_run_auto_execute_command()`.

2. After resolving `state_dir` and setting `env["AGENTIC_DEVTOOLS_STATE_DIR"]` (after L2210), write the pin file to the target worktree:

   ```python
   # Write pin file to target worktree so the VS Code auto-start task
   # resolves the same state directory (fixes #1913).
   if workflow:
       try:
           from agentic_devtools.state import write_pin_file
           pin_result = write_pin_file(
               state_dir,
               workflow=workflow,
               target_git_root=Path(worktree_path),
           )
           if pin_result:
               print(f"   Pinned state dir: {state_dir!s}")
       except (ValueError, OSError) as e:
           print(f"WARNING: Failed to write pin file: {e}", file=sys.stderr)
   ```

3. Add diagnostic logging for the resolved state directory (after L2210):

   ```python
   print(f"   Resolved state directory: {state_dir!s}")
   ```

4. Thread `workflow_name` through the two call sites in `setup_worktree_in_background_sync()`:
   - L3436: `_run_auto_execute_command(auto_execute_command, existing_path, auto_execute_timeout, workflow=workflow_name)`
   - L3500: `_run_auto_execute_command(auto_execute_command, result.worktree_path, auto_execute_timeout, workflow=workflow_name)`

**Tests**: Add test cases for:

- Pin file is written to target worktree's `.agdt/` when `workflow` is provided
- Pin file content matches the resolved state dir
- Pin file is NOT written when `workflow` is `None` (backward compat)
- Graceful handling when pin file write fails (subprocess still runs)
- Diagnostic log output includes resolved state directory

**Files**:

- `agentic_devtools/cli/workflows/worktree_setup.py` (L2133–2267, L3436, L3500)
- `tests/unit/cli/workflows/worktree_setup/test__run_auto_execute_command.py` — new/updated tests

---

### Phase 4 — Belt-and-Suspenders: Pin File in Subprocess (commands.py)

**Deliverable**: The subprocess's `env_override` branch also writes the pin file as a defense-in-depth measure.

**Changes**:

In `commands.py` L374–385, modify the `if env_override:` branch to also write a pin file:

```python
env_override = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR", "").strip()
if env_override:
    resolved_state_dir = Path(env_override)
    resolved_state_dir.mkdir(parents=True, exist_ok=True)
    # Belt-and-suspenders: write pin file even when env var is set.
    # When running as an auto-execute subprocess, the parent already wrote
    # the pin, but re-writing here ensures consistency if the parent's
    # write was skipped or if the resolved dir changed.
    try:
        write_pin_file(resolved_state_dir, workflow="pull-request-review")
    except (ValueError, OSError):
        pass  # Non-fatal; env var already provides the correct dir
```

**Important**: This change is specific to the `pull-request-review` workflow initiation function. Other workflow initiation functions in `commands.py` that also have `env_override` branches should
receive the same treatment, each with their own workflow name string. Identify all workflow init functions that have the same `env_override` pattern (L375 area) and apply the same fix.

**Scope check**: In `commands.py`, the `env_override` + `write_pin_file(...)` block currently exists **only**
in `initiate_pull_request_review_workflow` (L375). The other two references to `AGENTIC_DEVTOOLS_STATE_DIR`
in that file (L109 and L140) are inside the helper functions `_ensure_bootstrap_identity()` and
`_ensure_bootstrap_identity_and_clear()`, which use `os.getenv("AGENTIC_DEVTOOLS_STATE_DIR")` and simply
return early without writing a pin file — these helpers do not need updating. To find all workflow
initiation functions that skip pin writing, search for both `os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR"`
**and** `os.getenv("AGENTIC_DEVTOOLS_STATE_DIR"` (note: `os.getenv` is used in the helpers,
`os.environ.get` is used in `initiate_pull_request_review_workflow`).

**Tests**: Verify pin file is written in the `env_override` branch.

**Files**:

- `agentic_devtools/cli/workflows/commands.py` (L374–385 and parallel patterns in other workflow init functions)
- Tests for workflow initiation commands

---

### Phase 5 — Logging and Diagnostics (FR-005)

**Deliverable**: Both stages emit the resolved canonical state directory in logs for debugging.

**Changes**:

1. In `_run_auto_execute_command` (Phase 3 already adds this): print resolved state dir.

2. In `copilot_auto_start_cmd` (`auto_start.py` L498 area), after `get_state_file_path()` resolves, print a diagnostic:

```python
state_file_path = get_state_file_path()
print(f"[agdt-auto-start] Resolved state: {state_file_path.parent!s}", file=sys.stderr)
```

**Tests**: Verify diagnostic output is emitted (capture stderr).

**Files**:

- `agentic_devtools/cli/copilot/auto_start.py` (~L498)
- `agentic_devtools/cli/workflows/worktree_setup.py` (covered by Phase 3)

---

### Phase 6 — Cleanup Contract Verification

**Deliverable**: Ensure `clear_workflow_state` handles expanded workflow names correctly.

**Changes**:

1. Verify `clear_workflow_state(completing_workflow=...)` works for all newly recognized workflows. The existing code at L1673–1681 compares `data["workflow"] == completing_workflow`, which should
   work for any string. **No code change expected** — just test verification.

2. Add tests confirming:
   - `clear_workflow_state(completing_workflow="work-on-jira-issue")` deletes pin when pin was written for `work-on-jira-issue`
   - `clear_workflow_state(completing_workflow="work-on-jira-issue")` does NOT delete pin when pin was written for `pull-request-review`
   - `clear_workflow_state(force_delete=True)` deletes pin regardless of workflow

**Files**:

- `tests/unit/state/test_clear_workflow_state.py` — new test cases

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Expanding `RECOGNIZED_PIN_WORKFLOWS` causes unexpected pin file writes in non-cross-worktree scenarios | Low | Low | Pin file write only happens in `_run_auto_execute_command` (new code) and the existing `commands.py` initiation. Single-repo workflows don't call `_run_auto_execute_command`. The `env_override` branch belt-and-suspenders is non-fatal (`try/except`). |
| Changing `write_pin_file` signature breaks existing callers | Low | Medium | The `target_git_root` parameter is optional with default `None`, preserving backward compatibility. Existing callers pass no value → identical behavior. |
| Pin file written by `_run_auto_execute_command` gets stale if subprocess changes state dir | Very Low | Low | Belt-and-suspenders: subprocess also writes pin (Phase 4). Last writer wins (atomic `os.replace`). |
| Tests relying on exact `RECOGNIZED_PIN_WORKFLOWS` contents fail | Medium | Low | Phase 1 explicitly addresses test updates. |
| Windows path normalization issues with `target_git_root` | Low | Medium | `write_pin_file` already calls `Path(state_dir).resolve()` for the pinned path. `target_git_root` is used only to locate `.agdt/` — no cross-root comparison needed. |

## 6. Dependencies

### Internal Dependencies

| Dependency | Used By |
|------------|---------|
| `state.py` → `write_pin_file()` | Phase 2 modifies, Phase 3 calls from `worktree_setup.py` |
| `state.py` → `RECOGNIZED_PIN_WORKFLOWS` | Phase 1 expands; Phases 3–4 rely on expanded set |
| `state.py` → `read_and_validate_pin_file()` | No changes needed — validation logic handles new workflows automatically via the frozenset membership check |
| `state.py` → `clear_workflow_state()` | Phase 6 verifies — no code changes expected |
| `worktree_setup.py` → `_run_auto_execute_command()` | Phase 3 modifies signature and body |
| `worktree_setup.py` → `setup_worktree_in_background_sync()` | Phase 3 updates call sites |
| `commands.py` → workflow initiation functions | Phase 4 modifies `env_override` branches |
| `auto_start.py` → `copilot_auto_start_cmd()` | Phase 5 adds diagnostic logging |

### External Dependencies

None. All changes are internal to the `agentic-devtools` package.

### Phase Dependencies

```text
Phase 1 ─┬─► Phase 3 ──► Phase 4
Phase 2 ─┘         │
                    └──► Phase 5
                         Phase 6 (independent)
```

- Phases 1 and 2 are independent prerequisites for Phase 3
- Phase 4 depends on Phase 1 (expanded workflows) and can be done after Phase 3
- Phase 5 can be done in parallel with Phase 4
- Phase 6 is independent verification

---
*Generated by Copilot SDK (claude-opus-4.6)*

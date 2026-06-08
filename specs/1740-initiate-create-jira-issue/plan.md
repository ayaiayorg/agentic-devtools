# Implementation Plan: Create-Jira-Issue Stale State Fix

**Issue**: [#1740](https://github.com/ayaiayorg/agentic-devtools/issues/1740)

## 1. Technical Context

- **Language/Framework**: Python 3, pip-installable CLI package (`agentic-devtools`)
- **Key modules**:
  - `agentic_devtools/cli/workflows/commands.py` — workflow entry points (3500+ lines)
  - `agentic_devtools/cli/workflows/base.py` — shared `clear_state_for_workflow_initiation()`
  - `agentic_devtools/state.py` — JSON state CRUD (`get_value`, `set_value`, `delete_value`)
- **Test framework**: pytest, 1:1:1 test structure under `tests/unit/`
- **Existing test file**: `tests/unit/cli/workflows/commands/test_initiate_create_jira_issue_workflow.py`

## 2. Research Summary

See [research.md](research.md) for detailed analysis. Key decisions:

| Decision | Choice |
| --- | --- |
| Scope of fix | Create-jira-issue entry point only (not `clear_state_for_workflow_initiation`) |
| Stale key handling | Delete from state (not ignore-only) |
| Keys to clear | Both `issue_key` and `jira.issue_key` |
| Logging | `print(..., file=sys.stderr)` with emoji prefix |

## 3. Design Overview

The fix is a **5-line insertion** in `initiate_create_jira_issue_workflow()` at line ~1416,
immediately after `_ensure_scoped_bootstrap_and_clear(issue_key)` returns and before the
issue-key resolution at line 1438.

```text
Flow BEFORE fix:
  _ensure_scoped_bootstrap_and_clear(issue_key)  # preserves jira.issue_key
  ...
  resolved_issue_key = issue_key or get_value("jira.issue_key")  # ← picks up stale key

Flow AFTER fix:
  _ensure_scoped_bootstrap_and_clear(issue_key)
  if not issue_key:                         # NEW: CLI --issue-key was not provided
      _clear_stale_issue_keys_for_create()  # NEW: delete issue_key + jira.issue_key
  ...
  resolved_issue_key = issue_key or get_value("jira.issue_key")  # ← now returns None
```

### Helper Function

A small private helper `_clear_stale_issue_keys_for_create()` encapsulates:

1. Check if `issue_key` or `jira.issue_key` exist in state
2. Delete both if present
3. Emit an informational stderr message listing which keys were cleared

This helper is also reusable by `initiate_create_jira_epic_workflow()` and
`initiate_create_jira_subtask_workflow()` which have the same pattern, though
those are out of scope for this issue unless trivially applicable.

## 4. Implementation Phases

### Phase 1: Add `_clear_stale_issue_keys_for_create()` helper

**File**: `agentic_devtools/cli/workflows/commands.py`

**Location**: Near line 150, before `_ensure_scoped_bootstrap_and_clear()` (among other
private helpers).

```python
def _clear_stale_issue_keys_for_create() -> None:
    """Delete stale issue-selection keys when starting a create-new-issue flow.

    Called by create-jira-issue (and similar create workflows) when ``--issue-key``
    is not provided.  Removes ``issue_key`` and ``jira.issue_key`` from state so
    that downstream resolution does not accidentally reuse a key from a prior
    workflow.

    Emits an informational message to stderr when stale keys are found and cleared.
    """
    from ...state import delete_value, get_value

    cleared: list[str] = []
    for key in ("issue_key", "jira.issue_key"):
        if get_value(key) is not None:
            delete_value(key)
            cleared.append(key)
    if cleared:
        keys_label = "/".join(cleared)
        print(
            f"ℹ️  Cleared stale issue selection state ({keys_label}) "
            "from prior workflow — creating fresh issue.",
            file=sys.stderr,
        )
```

### Phase 2: Insert guard in `initiate_create_jira_issue_workflow()`

**File**: `agentic_devtools/cli/workflows/commands.py`

**Location**: After line 1415 (`issue_key = _ensure_scoped_bootstrap_and_clear(issue_key)`)
and before line 1416 (`set_value("copilot.model_id", model)`).

```python
    issue_key = _ensure_scoped_bootstrap_and_clear(issue_key)

    # When --issue-key is not provided, clear stale issue-selection state
    # from prior workflows so the create flow always starts fresh (FR-002).
    if not issue_key:
        _clear_stale_issue_keys_for_create()

    set_value("copilot.model_id", model)
```

No other lines in the function need modification. The existing resolution at line 1438
(`resolved_issue_key = issue_key or get_value("jira.issue_key")`) will now correctly
return `None` when `--issue-key` is absent, falling through to the "No issue key" branch
at line 1519.

### Phase 3: Write tests (TDD — these should be written first in practice)

**File**: `tests/unit/cli/workflows/commands/test_initiate_create_jira_issue_workflow.py`
(append to existing file)

New test class: `TestCreateJiraIssueStaleStateClearance`

| Test method | Validates |
| --- | --- |
| `test_stale_jira_issue_key_cleared_when_no_issue_key_arg` | SC-001, SC-005: Both `jira.issue_key` and `issue_key` are deleted from state when `--issue-key` absent |
| `test_stale_state_emits_stderr_message` | SC-002, FR-005: Stderr contains the expected informational message |
| `test_no_stale_state_no_stderr_message` | Negative: No stderr message when no stale keys exist |
| `test_explicit_issue_key_preserves_state` | SC-004, FR-006: `--issue-key PROJ-123` does not trigger clearing or warning |
| `test_project_key_preserved_after_stale_clear` | SC-003: `jira.project_key` survives the clear |
| `test_only_issue_key_stale_clears_single_key` | Partial: Only `issue_key` exists (not `jira.issue_key`) — only it is cleared |
| `test_only_jira_issue_key_stale_clears_single_key` | Partial: Only `jira.issue_key` exists — only it is cleared |

New test class (for the helper): `TestClearStaleIssueKeysForCreate`

**File**: `tests/unit/cli/workflows/commands/test__clear_stale_issue_keys_for_create.py` (new)

| Test method | Validates |
| --- | --- |
| `test_clears_both_keys` | Both keys deleted when both present |
| `test_clears_only_issue_key` | Only `issue_key` deleted when `jira.issue_key` absent |
| `test_clears_only_jira_issue_key` | Only `jira.issue_key` deleted when `issue_key` absent |
| `test_no_keys_no_message` | No stderr output when neither key exists |
| `test_stderr_message_format` | Message matches expected emoji-prefixed format |
| `test_stderr_lists_cleared_keys` | Message includes the specific key names that were cleared |

### Phase 4: Validate

1. `agdt-test-pattern tests/unit/cli/workflows/commands/test__clear_stale_issue_keys_for_create.py -v`
2. `agdt-test-pattern tests/unit/cli/workflows/commands/test_initiate_create_jira_issue_workflow.py -v`
3. `agdt-test` + `agdt-task-wait` (full suite)
4. `bash scripts/targeted-checks.sh` (lint, format, mypy, coverage)

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Clearing keys breaks create-jira-epic/subtask flows | Low | Medium | Those flows have the same `issue_key or get_value(...)` pattern; they benefit from the same fix but are not in scope. Guard is scoped to create-jira-issue only. |
| `delete_value` calls cause extra disk I/O | Very Low | Low | Two small JSON writes; negligible compared to Jira API calls. Could optimize to single load/save but not worth the complexity. |
| Helper import cycle | Very Low | Low | Uses late imports (`from ...state import ...`) consistent with existing patterns in the file. |
| Tests mock too broadly, hiding real bugs | Low | Medium | Tests will mock at the narrowest boundary (`delete_value`, `get_value`) and verify call args, not just absence of errors. |

## 6. Dependencies

- **Internal**: `agentic_devtools.state.delete_value` — already exists (line 1426 of `state.py`)
- **Internal**: `agentic_devtools.state.get_value` — already exists
- **No external dependencies** — no new packages, no API changes, no CLI signature changes

---
*Generated by Copilot SDK (claude-opus-4.6)*

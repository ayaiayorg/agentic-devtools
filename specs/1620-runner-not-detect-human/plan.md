# Implementation Plan: Runner Human-in-the-Loop Pause Detection

## Technical Context

- **Language**: Python 3.x
- **Package**: `agentic-devtools` (pip-installable CLI)
- **Target file**: `agentic_devtools/orchestration/runner.py` (144 lines)
- **State schema**: `agentic_devtools/orchestration/state_schema.py` — `WorkOnIssueState` TypedDict with `status` field
- **Test file**: `tests/unit/orchestration/runner/test_run_langchain_workflow.py` (268 lines, 3 test classes)
- **Test policy**: 1:1:1 structure under `tests/unit/`, 100% branch coverage required
- **LangGraph behavior**: With `SqliteSaver` checkpointer, `invoke()` returns state dict instead of raising `GraphInterrupt`

## Research Summary

See [research.md](research.md) for detailed analysis. Key decisions:

1. Extract `_is_workflow_paused(result)` helper — keeps runner main flow ≤5 new lines (SC-005)
2. State inspection uses only `result.get("status") != "completed"` — no gate-node-name hardcoding (NFR-004)
3. `None`/unexpected-type handling exits with code 1 — consistent with existing error pattern
4. New tests go in `tests/unit/orchestration/runner/test__is_workflow_paused.py` (1:1:1 policy)

## Design Overview

```text
invoke() returns
       │
       ▼
┌──────────────────┐
│ result is None   │──► stderr error + sys.exit(1)
│ or not a dict?   │
└──────────────────┘
       │ no
       ▼
┌──────────────────┐
│ _is_workflow_paused│──► True: _print_pause_message() + return (exit 0)
│ (status != done) │
└──────────────────┘
       │ False (status == "completed")
       ▼
   print "Workflow completed" (existing behavior)
```

Both the fresh-run path and the resume path share the same post-`invoke()` logic.

## Implementation Phases

### Phase 1: Add `_is_workflow_paused` Helper (RED → GREEN)

**Deliverable**: New helper function + unit tests

1. Create test file `tests/unit/orchestration/runner/test__is_workflow_paused.py`
2. Write failing tests:
   - `test_returns_true_when_status_active` — `{"status": "active"}` → `True`
   - `test_returns_true_when_status_missing` — `{"step": "planning"}` → `True`
   - `test_returns_true_when_status_empty` — `{"status": ""}` → `True`
   - `test_returns_false_when_status_completed` — `{"status": "completed"}` → `False`
   - `test_returns_true_for_none_result` — `None` → raises/returns truthy error signal
   - `test_returns_true_for_non_dict` — `"string"` → raises/returns truthy error signal
3. Implement `_is_workflow_paused(result: dict | None) -> bool` in `runner.py`
4. Handle `None`/non-dict: return a sentinel or raise `TypeError` (caller handles exit)

**Implementation detail** — the function signature and behavior:

```python
def _is_workflow_paused(result: dict | None) -> bool:
    """Return True if the workflow is paused (not completed).

    Raises TypeError if result is None or not a dict.
    """
    if not isinstance(result, dict):
        raise TypeError(f"Workflow returned unexpected result type: {type(result).__name__}")
    return result.get("status") != "completed"
```

### Phase 2: Integrate Into Runner Main Flow (RED → GREEN)

**Deliverable**: Runner correctly prints pause vs. completion messages

1. Write failing tests in `test_run_langchain_workflow.py`:
   - `test_fresh_invocation_pauses_when_status_not_completed` — invoke returns `{"step": "planning", "status": "active"}` → pause message printed, no completion message
   - `test_resume_pauses_when_status_not_completed` — same for resume path
   - `test_fresh_invocation_exits_1_when_invoke_returns_none` — invoke returns `None` → exit 1 with diagnostic
2. Replace the current "Report completion" block (lines 125-128) with:

   ```python
           # Determine outcome: pause or completion.
           if result is None or not isinstance(result, dict):
               print(
                   f"ERROR: Workflow returned unexpected result type: {type(result).__name__}",
                   file=sys.stderr,
               )
               sys.exit(1)

           if _is_workflow_paused(result):
               _print_pause_message(issue_key)
               return

           # True completion.
           final_step = result.get("step", "unknown")
           final_status = result.get("status", "unknown")
           print(f"[langchain] Workflow completed: step={final_step}, status={final_status}")
   ```

3. Verify existing tests still pass (backward compat for `GraphInterrupt` path)

### Phase 3: Update Existing Test Assertions

**Deliverable**: All existing tests remain green; no false positives

1. `test_fresh_invocation_calls_graph_invoke` already returns `status: "completed"` — should still pass ✓
2. `test_resume_with_existing_checkpoint_invokes_command` already returns `status: "completed"` — should still pass ✓
3. No test changes needed for passing tests (they already use terminal states)

### Phase 4: Regression Test Coverage (SC-006)

**Deliverable**: ≥3 new regression tests as specified

Add to `test_run_langchain_workflow.py`:

| Test | Scenario | Expected |
| --- | --- | --- |
| `test_fresh_run_pauses_at_gate_with_checkpointer` | invoke returns `{"step": "planning", "status": "active"}` | stderr contains "paused", stdout does NOT contain "completed" |
| `test_resume_pauses_when_not_completed` | resume invoke returns `{"step": "commit", "status": "active"}` | stderr contains "paused", exit 0 |
| `test_true_completion_prints_completed` | invoke returns `{"step": "completion", "status": "completed"}` | stdout contains "Workflow completed" |
| `test_invoke_returns_none_exits_1` | invoke returns `None` | stderr contains "unexpected result type", exit 1 |

### Phase 5: Targeted Checks & Coverage Verification

**Deliverable**: CI passes, 100% branch coverage on new logic

```bash
agdt-test-file --source-file agentic_devtools/orchestration/runner.py
agdt-task-wait
bash scripts/targeted-checks.sh
```

### Phase 6: Documentation (P3 — CLI Help)

**Deliverable**: Updated `--help` text for pause/resume behavior

1. Locate the argparse setup for `agdt-initiate-work-on-jira-issue-workflow`
2. Add epilog or description text explaining pause/resume lifecycle
3. Verify with `agdt-initiate-work-on-jira-issue-workflow --help`

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- |
| Existing tests break due to new None-guard | Medium | Low | Existing tests all return valid dicts with `status: "completed"` |
| `_is_workflow_paused` called before `result` assigned (exception path) | High | Low | Exception handlers `return` early; state inspection only runs after successful invoke |
| Future LangGraph changes return different state shape | Medium | Low | Using only `result.get("status")` — minimal surface area, forward-compatible |
| SC-005 budget exceeded (>5 lines in main flow) | Low | Low | Guard (3 lines) + pause check (3 lines) = 6 lines; helper extraction keeps it within budget |

## Dependencies

- **Internal**: No new module dependencies; helper added to existing `runner.py`
- **External**: No new pip dependencies (NFR-004 satisfied)
- **Test infra**: Existing `pytest` + `unittest.mock` — no new test tooling
- **CI**: Existing `scripts/targeted-checks.sh` validates coverage

---
*Generated by Copilot SDK (claude-opus-4.6)*

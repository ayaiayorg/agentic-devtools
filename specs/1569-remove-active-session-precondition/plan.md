# Implementation Plan: Remove Active Session Precondition from ResolveThreadsAction

## Technical Context

- **Language/Framework**: Python 3, pip-installable CLI package (`agentic-devtools`)
- **Source file**: `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py`
- **Test file**: `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_resolvethreadsaction.py`
- **Companion spec**: `specs/1559-refactor-loop-into-idempotent/spec.md`
- **Test policy**: 1:1:1 structure, 100% line coverage on target file
- **Testing tool**: `agdt-test-pattern` for synchronous runs and focused coverage checks

## Research Summary

No external research needed. This is a targeted removal of a precondition guard with well-defined
before/after states. The decision rationale is captured in this plan's technical context, design
overview, and implementation phases.

## Design Overview

The change is surgical: remove lines 33–41 from `evaluate()`, update the docstring, update the companion spec, and fix tests. The remaining precondition evaluation chain (CI → pending review →
unresolved threads) is untouched.

```text
Before: active_session → CI → pending_review → unresolved_threads → EXECUTE
After:                    CI → pending_review → unresolved_threads → EXECUTE
```

## Implementation Phases

### Phase 1 — Update Tests (RED step of TDD)

**Deliverable**: Failing tests that assert the new expected behaviour.

1. Open `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_resolvethreadsaction.py`
2. **Modify `test_skip_when_active_session`** → Rename to `test_execute_when_active_session` and assert `ActionDecision.EXECUTE` instead of `SKIP`. Add `ci_status="passing"` and
   `copilot_review_pending=False` to the snapshot (required to pass remaining preconditions).
3. **Add `test_no_active_session_key_in_preconditions`** → Assert that `"no_active_session"` is NOT present in `result.preconditions` for any evaluate call.
4. **Add `test_skip_when_active_session_and_ci_failing`** → Assert SKIP with reason CI failing (edge case from spec).
5. **Add `test_skip_when_active_session_and_pending_review`** → Assert SKIP with reason pending review.
6. **Add `test_skip_when_no_prior_reviews_race_condition`** → Assert SKIP in `execute()` when `prior_reviews` is empty (covers the race-condition branch for 100% coverage).
7. Run `agdt-test-pattern tests/unit/cli/ci/pipeline/actions/resolve_threads/` → confirm tests FAIL (RED).

### Phase 2 — Modify Source Code (GREEN step)

**Deliverable**: `resolve_threads.py` passes all tests.

1. **Remove lines 33–41** (the `no_active_session` precondition block) from `evaluate()`.
2. **Update class docstring** (lines 15–23): Remove "No active Copilot coding session" from Preconditions list. Keep "No pending Copilot review on HEAD" and "Unresolved threads exist from prior
   commits".
3. Run `agdt-test-pattern tests/unit/cli/ci/pipeline/actions/resolve_threads/` → confirm all tests PASS (GREEN).

### Phase 3 — Verify Coverage

**Deliverable**: 100% line coverage on `resolve_threads.py`.

1. Run `agdt-test-pattern tests/unit/cli/ci/pipeline/actions/resolve_threads/ -o addopts= --cov=agentic_devtools.cli.ci.pipeline.actions.resolve_threads --cov-report=term-missing
   --cov-fail-under=100`.
2. Confirm 100% coverage. If any lines are uncovered (particularly the exception handler in `execute()`), add targeted tests.

### Phase 4 — Update Companion Spec 1559

**Deliverable**: `specs/1559-refactor-loop-into-idempotent/spec.md` FR-005 reworded; acceptance scenarios updated.

1. **FR-005 (line 246)**: Reword to state that only squash and dispatch-repair MUST NOT execute when a session is active. Thread resolution is not session-gated — it only requires no pending review on
   HEAD.
2. **User Story 2, acceptance scenario 1 (lines 93–94)**: Remove "resolve-threads" from the list of actions skipped when a session is active, leaving only "dispatch-repair and squash".
3. **User Story 3, acceptance scenario 2 (line 121)**: Rewrite to state that thread resolution proceeds regardless of session state (only gated by no pending review, unresolved threads exist, and CI
   passing).

### Phase 5 — Full Suite Validation

**Deliverable**: No regressions anywhere.

1. Run `agdt-test` then `agdt-task-wait` — full suite must pass.
2. Run `bash scripts/run-pr-checks.sh` — all PR checks must pass.

## Risk Assessment

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Removing session guard allows thread resolution during active commit push | Low — `execute()` already filters by `r.commit_sha != snapshot.head_sha` | FR-005 of this spec preserves the implicit gate |
| Test coverage drops below 100% | Medium — CI blocks | Phase 3 explicitly verifies; add tests for uncovered branches |
| Spec 1559 edits accidentally break cross-references | Low | Phase 4 limits companion spec changes to 3 explicitly enumerated locations |

## Dependencies

- **Internal**: No other action classes are modified. `SquashAction` and `DispatchRepairAction` retain their `no_active_session` guards unchanged.
- **External**: None. No new packages, APIs, or services required.

---
*Generated by Copilot SDK (claude-opus-4.6)*

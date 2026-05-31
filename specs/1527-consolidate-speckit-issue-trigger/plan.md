# Implementation Plan: Consolidate SpecKit Issue Trigger into Phase Progression Pipeline

## Technical Context

- **Stack**: GitHub Actions YAML workflows, shell scripts (bash), Python 3.12 CLI (`agentic_devtools`)
- **Key Files**:
  - `.github/workflows/speckit-issue-trigger.yml` — current Phase 1 trigger (to become thin dispatcher)
  - `.github/workflows/speckit-phase-progression.yml` — progression workflow (to accept phase=1)
  - `agentic_devtools/cli/ci/speckit_trigger.py` — Python orchestrator (commit/push/PR logic to remove)
  - `agentic_devtools/cli/ci/commands.py` — CLI entry point `speckit_trigger_command()`
  - `.github/scripts/speckit-trigger/*.sh` — shared shell scripts (generate, PR creation, idempotency)
- **Architecture**: Single-job workflow with conditional steps gated by `steps.extract.outputs.*`
- **Token strategy**: `SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN` for PR creation; `GITHUB_TOKEN` for dispatch and labeling

## Research Summary

See [research.md](research.md) for detailed decisions on:

- Token usage for dispatch vs. PR creation
- Concurrency group strategy (dual-layer)
- Phase 1 input option addition approach
- Python stub vs. full removal trade-offs

## Design Overview

```text
┌─────────────────────────────────────────────────────────────┐
│ speckit-issue-trigger.yml (THIN DISPATCHER)                  │
│                                                              │
│  Trigger: issues:labeled / workflow_dispatch                  │
│  Logic: Validate label → POST workflow_dispatch to           │
│         speckit-phase-progression.yml (phase=1)              │
│  Token: GITHUB_TOKEN (permissions: actions: write)           │
│  Concurrency: speckit-trigger-${{ github.event.issue.number || inputs.issue_number }}│
└──────────────────────────────┬──────────────────────────────┘
                               │ workflow_dispatch
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ speckit-phase-progression.yml (UNIFIED, Phases 1–5)          │
│                                                              │
│  Triggers: pull_request:closed / workflow_dispatch            │
│  Phase 1 additions:                                          │
│   - Extract step: phase=1 → completed=0, next=1, name=specify│
│   - Token preflight: fail if no SPECKIT_PR_TOKEN/COPILOT_*   │
│   - Same generate/commit/push/PR steps as phases 2–5         │
│   - PR token: SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN       │
│  Concurrency: speckit-progression (global, cancel=false)     │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase A: Extend Progression Workflow to Accept Phase 1 (FR-001, FR-002, FR-003, FR-011, FR-014, FR-015)

**Deliverables:**

1. Add `'1'` to `workflow_dispatch.inputs.phase.options` in `speckit-phase-progression.yml`
2. Verify the extract step already handles `phase=1` correctly (it does — `completedPhase = nextPhase - 1 = 0`)
3. Update the "Validate Tokens" step to enforce both `SPECKIT_PR_TOKEN` and `COPILOT_GITHUB_TOKEN` check for all phases (currently only checks `COPILOT_GITHUB_TOKEN`); add `SPECKIT_PR_TOKEN` to the
   check with fallback logic and explicit failure if both are missing
4. Verify `GH_TOKEN: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}` in the "Create Pull Request" step already applies to phase 1 (it does — no phase-specific gating)
5. Verify feature flags (`SPECKIT_CREATE_BRANCH`, `SPECKIT_CREATE_PR`, `SPECKIT_CRITICAL_GATE_MODE`) already apply universally (they do)

**Validation:** Manually dispatch `speckit-phase-progression.yml` with `phase=1` and verify full artifact generation + PR creation with human-identity token.

### Phase B: Convert Issue Trigger to Thin Dispatcher (FR-004, FR-005)

**Deliverables:**

1. Replace the entire `speckit-trigger` job in `speckit-issue-trigger.yml` with a minimal dispatcher:
   - Keep `on: issues: [labeled]` and `workflow_dispatch` triggers
   - Keep the label filter (`speckit` or `SPECKIT_TRIGGER_LABEL`)
   - Keep the per-issue concurrency group
   - Change `permissions` to `actions: write, issues: write` (drop `contents: write`, `pull-requests: write`)
   - Remove `AGDT_USE_PYTHON_ORCHESTRATOR` env var
   - Remove Python setup, pip install, `agdt-speckit-trigger` call
   - Remove the "Add ai-auto-merge-allowed" step (now handled by progression workflow)
   - Keep "Add Processing Label" step (or move to progression — see research)
   - Add a single step: `gh api /repos/{owner}/{repo}/actions/workflows/speckit-phase-progression.yml/dispatches` with `{"ref":"main","inputs":{"issue_number":"N","phase":"1"}}`
   - Keep failure handling (comment + `speckit:failed` label)
2. Ensure the dispatcher is < 30 lines of workflow logic (excluding failure handling)

**Validation:** Add `speckit` label to a test issue → verify `speckit-phase-progression.yml` is triggered with correct inputs.

### Phase C: Update Auto-Merge Label Logic in Progression Workflow (FR-008)

**Deliverables:**

1. The existing "Add ai-auto-merge-allowed label (non-clarify phases)" step already excludes `clarify` but includes all other phases. Verify it works for `phase=1` (the step's condition
   `steps.extract.outputs.next_phase != '0'` and `!= '6'` already passes for phase 1).
2. No changes needed — the progression workflow's existing auto-merge-allowed step covers phase 1.

### Phase D: Remove Python Orchestrator Logic (FR-006)

**Deliverables:**

1. Delete `_commit_and_push_phase_branch()` and `_create_phase_pull_request()` from `agentic_devtools/cli/ci/speckit_trigger.py`
2. Delete `process_speckit_label_event()` (the main orchestration function)
3. Remove supporting private functions that are only used by the deleted functions (`_load_issue_context_from_event`, `_set_issue_labels`, `_run_script_with_outputs`, `_parse_key_value_file`,
   `_run_checked`, `_require_repository`, `_IssueContext` dataclass)
4. Replace `speckit_trigger_command()` in `commands.py` with a stub:

   ```python
   def speckit_trigger_command() -> None:
       print("agdt-speckit-trigger has been removed.")
       print("Use workflow_dispatch on speckit-phase-progression.yml with phase=1 and issue_number=N instead.")
       raise SystemExit(1)
   ```

5. Update/remove tests in `tests/unit/cli/ci/commands/test_speckit_trigger_command.py`
6. Remove or update any tests for `process_speckit_label_event` and related functions
7. Retain the `agdt-speckit-trigger` entry point in `pyproject.toml` (points to the stub)

**Validation:** Run `agdt-speckit-trigger` → expect informative message + exit code 1. Run full test suite.

### Phase E: Documentation Updates (FR — User Story 6)

**Deliverables:**

1. Update `.github/workflows/README.md` (if it exists) to describe the consolidated architecture
2. Update any references to `speckit-issue-trigger.yml` as a Phase 1 executor
3. Ensure the feature spec summary in `specs/` reflects the final implementation

### Phase F: Integration Testing & Verification

**Deliverables:**

1. End-to-end test: label an issue → dispatcher fires → progression runs phase 1 → PR created with human identity
2. Idempotency test: re-trigger same issue → skipped
3. Failure test: remove tokens → clear error before PR creation
4. Draft mode test: set `SPECKIT_CRITICAL_GATE_MODE=draft` → PR created as draft

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| `GITHUB_TOKEN` lacks `actions: write` by default | Dispatcher fails with 403 | Medium | Explicitly grant `permissions: actions: write` in dispatcher workflow |
| Phase 1 artifacts differ from current implementation | Regression | Low | The same `generate-spec-from-issue.sh` script is used; progression workflow already runs it |
| Concurrency race between dispatcher and progression | Duplicate PRs | Low | Dual concurrency groups + idempotency check in progression workflow |
| Both `SPECKIT_PR_TOKEN` and `COPILOT_GITHUB_TOKEN` secrets are unset/deleted, leaving the resolved token empty | PR creation fails with unhelpful auth error | Low | Add explicit preflight step that validates the resolved token is non-empty and fails with a clear message |
| Removing Python orchestrator breaks other code paths | Test failures | Medium | Search all imports of `speckit_trigger.py` functions; update/remove callers |

## Dependencies

- **Internal**: `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` must support `--phase 1` (already does)
- **Internal**: `.github/scripts/speckit-trigger/create-spec-pr.sh` must support `--phase-number 1 --phase-name specify` (already does)
- **External**: `SPECKIT_PR_TOKEN` or `COPILOT_GITHUB_TOKEN` secret must be configured in the repository
- **External**: GitHub Actions `actions: write` permission for `GITHUB_TOKEN` to dispatch workflows on the same repo

---
*Generated by Copilot SDK (claude-opus-4.6)*

# Implementation Plan: Review All Files Every Run

## 1. Technical Context

**Technology Stack:**

- Python 3.x package (`agentic-devtools`) with CLI entry points
- Azure DevOps REST API for PR threads, iterations, file change detection
- JSON-based state persistence (`review-state.json`, `queue.json`)
- Dataclass-based domain model (`FileEntry`, `ReviewState`, `SkippedFile`, etc.)
- Multi-model review via `ReviewModelsConfig` and `ModelVerdict`

**Key Files:**

| File | Role |
| --- | --- |
| `review_state.py` | Domain model: `FileEntry`, `ReviewState`, `SkippedFile`, etc. |
| `review_scaffold.py` | Thread scaffolding, change detection, session management |
| `review_commands.py` | Prompt generation, queue building, skip logic |
| `review_prompts.py` | Alternate prompt generation path |
| `review_helpers.py` | `build_reviewed_paths_set()`, path utilities |
| `review_templates.py` | Overall summary rendering (skipped files section) |
| `file_review_commands.py` | File approve/request-changes, queue management |
| `status_cascade.py` | Status aggregation and cascade |
| `verdict_protocol.py` | Multi-model verdict recording and effective status |

## 2. Research Summary

See [research.md](research.md) for detailed analysis of:

- The two independent `already_reviewed` mechanisms and how to dismantle each
- Change detection approach for determining "unchanged" files
- Multi-model inheritance semantics
- Backward-compatible deserialization strategy for `processingPath`

## 3. Design Overview

### Current Flow (Skip-Based)

```text
scaffold_review_threads() → fresh/incremental scaffold
                          ↓
generate_review_prompts() → for each file:
  ├─ if in reviewed_paths → SkippedFile("already_reviewed"), no prompt
  ├─ if not on branch     → SkippedFile("not_on_branch"), no prompt
  └─ else                 → write file-<hash>.md prompt, add to queue
```

### Target Flow (Review-All)

```text
scaffold_review_threads() → fresh/incremental scaffold (unchanged files get threads too)
                          ↓
generate_review_prompts() → for each file:
  ├─ if not on branch     → SkippedFile("not_on_branch"), no prompt
  ├─ if changed/new       → full prompt (processingPath="reviewed")
  ├─ if unchanged + valid prior → simplified prompt (processingPath="inherited")
  └─ if unchanged + no prior   → full prompt (processingPath="reviewed-no-prior")
                          ↓
queue.json includes ALL files (with processingPath metadata)
```

### Key Design Decisions

1. **`processingPath` on `FileEntry`**: New optional `str | None` field, defaults to `None` for backward compat
2. **`already_reviewed` removal**: Remove from prompt-generation skip logic; retain `SkippedFile` dataclass for `not_on_branch`
3. **Unchanged file prompts**: Simplified scaffold — `### Commit: [<hash>](<url>)` + `no changes since last review`
4. **Inheritance logic**: Centralized in a new function that validates prior state completeness
5. **Multi-model inheritance**: Global per-file — all models must have terminal verdicts matching prior state

## 4. Implementation Phases

### Phase 1: Data Model Extension (FR-010, FR-011, NFR-003)

**Deliverables:** `processingPath` field on `FileEntry`, backward-compatible serialization

**Tasks:**

1. Add `processingPath: str | None = None` field to `FileEntry` dataclass in `review_state.py`
2. Update `FileEntry.to_dict()` to include `processingPath` (omit when `None` for compact JSON)
3. Update `FileEntry.from_dict()` to deserialize `processingPath` with `None` default
4. Add `PROCESSING_PATH_REVIEWED = "reviewed"`, `PROCESSING_PATH_INHERITED = "inherited"`, `PROCESSING_PATH_REVIEWED_NO_PRIOR = "reviewed-no-prior"` constants
5. Write tests for serialization roundtrip, `None` default on old state files, all three label values

### Phase 2: Inheritance Validation Logic (FR-004, FR-005, FR-006, EC-001, EC-004)

**Deliverables:** Pure functions for determining inheritance eligibility

**Tasks:**

1. Create `is_valid_prior_state(file_entry: FileEntry) -> bool` in `review_state.py`:
   - Returns `True` only when: `status` ∈ `COMPLETE_STATUSES`, `threadId` is truthy, `commentId` is truthy, `folder` is non-empty
2. Create `can_inherit_file(file_entry: FileEntry, is_unchanged: bool) -> bool`:
   - Returns `True` when `is_unchanged` and `is_valid_prior_state(file_entry)` both hold
3. Create `can_inherit_multi_model(file_entry: FileEntry, is_unchanged: bool) -> bool`:
   - Returns `True` when `can_inherit_file()` and all `modelVerdicts` have terminal status
4. Write comprehensive tests covering:
   - Valid terminal state → eligible
   - Non-terminal status → ineligible
   - Missing `threadId`/`commentId`/`folder` → ineligible
   - Changed file → ineligible regardless of state
   - Multi-model: all terminal → eligible; any non-terminal → ineligible

### Phase 3: Remove `already_reviewed` Skip from Prompt Generation (FR-002)

**Deliverables:** All files get prompts; `already_reviewed` no longer used for skipping

**Tasks:**

1. In `review_commands.py` → `generate_review_prompts()`:
   - Remove the `if not include_reviewed and normalized_path.lower() in reviewed_paths` block (lines 477–481)
   - Remove `reviewed_paths` variable and `build_reviewed_paths_set()` call (line 439)
   - Remove `include_reviewed` parameter from function signature
   - Remove `skipped_reviewed_count` counter and return value adjustment
2. In `review_prompts.py` → `generate_review_prompts()`:
   - Remove the parallel `already_reviewed` skip block (line 224)
3. In `review_commands.py` → `setup_pull_request_review()`:
   - Remove `include_reviewed` state key usage (line 774)
   - Remove conditional `set_value("include_reviewed", ...)` (lines 818–819)
   - Update call to `generate_review_prompts()` (remove `include_reviewed` arg, line 964)
4. In `async_commands.py`:
   - Remove `False` literal for `include_reviewed` parameter (line 1540)
5. In `review_commands.py` → `print_review_instructions()`:
   - Remove `skipped_reviewed_count` parameter and related output
6. Update `review_helpers.py`:
   - Deprecate or remove `build_reviewed_paths_set()` (no longer called)
7. Update `review_templates.py` → `render_overall_summary()`:
   - Remove `already_reviewed` count from skipped files section (lines 321–327)
   - Only show `not_on_branch` count if any exist
8. Write/update tests for all modified functions

### Phase 4: Change Detection Integration (FR-003)

**Deliverables:** `generate_review_prompts()` receives and uses file change information

**Tasks:**

1. Add `unchanged_files: set[str] | None = None` parameter to `generate_review_prompts()`
2. Pass `FileChangeResult.unchanged_files` from scaffold into prompt generation:
   - In `setup_pull_request_review()`, after scaffold returns, pass unchanged file set downstream
   - For first-run (no prior state), `unchanged_files` is empty set (all files treated as changed)
3. Load prior `ReviewState` in `generate_review_prompts()` for inheritance checks
4. For each file in the loop, determine `processingPath`:
   - If file is in `unchanged_files` and `can_inherit_file(prior_entry)` → `"inherited"`
   - If file is in `unchanged_files` and no valid prior → `"reviewed-no-prior"`
   - Otherwise → `"reviewed"`
5. Store `processingPath` in queue entry metadata for downstream consumption
6. Write tests for change-detection integration

### Phase 5: Simplified Unchanged-File Prompts (FR-007, FR-008)

**Deliverables:** Unchanged files get simplified scaffolding instead of full diff prompts

**Tasks:**

1. Create `_write_unchanged_file_prompt()` in `review_commands.py`:
   - Generates minimal prompt: `### Commit: [<hash>](<url>)` + blank line + `no changes since last review`
   - Includes prior review status and summary for context
   - For `inherited` files: include prior status + model verdicts
   - For `reviewed-no-prior` files: include note that no prior context exists
2. Modify `generate_review_prompts()` file loop:
   - Changed/new files → existing `_write_file_prompt()` (full diff)
   - Unchanged files with prior → `_write_unchanged_file_prompt()` (simplified)
   - Unchanged files without prior → `_write_file_prompt()` (full diff, needs fresh review)
3. Update `review_prompts.py` → `build_file_prompt_content()` to support an `unchanged` mode
4. Write tests for:
   - Changed file → full prompt content
   - Unchanged + prior → simplified prompt with `no changes since last review`
   - Unchanged + no prior → full prompt content

### Phase 6: Persist `processingPath` and Update State (FR-011, FR-009)

**Deliverables:** `processingPath` persisted on every `FileEntry` after each run

**Tasks:**

1. After prompt generation, update `ReviewState.files` entries:
   - Set `processingPath` on each `FileEntry` based on determination from Phase 4
   - For `inherited` files: carry forward `status`, `summary`, `suggestions`, `modelVerdicts`
   - For `inherited` files: skip new review submission (FR-009)
2. In `file_review_commands.py` → `approve_file()` and `request_changes()`:
   - Set `processingPath = "reviewed"` when updating file status from active review
3. Ensure `save_review_state()` persists `processingPath` (handled by Phase 1 serialization)
4. Write tests verifying:
   - Inherited files retain prior status and `processingPath = "inherited"`
   - Actively reviewed files get `processingPath = "reviewed"`
   - Files reviewed without prior get `processingPath = "reviewed-no-prior"`

### Phase 7: Multi-Model Inheritance (FR-005 multi-model, EC-005)

**Deliverables:** Global per-file inheritance for multi-model reviews

**Tasks:**

1. In the inheritance check path (Phase 4 logic), use `can_inherit_multi_model()`:
   - All model verdicts must be terminal for inheritance
   - If any non-terminal → all models must freshly evaluate
2. For inherited multi-model files:
   - Carry forward `modelVerdicts` list unchanged
   - Set `processingPath = "inherited"`
3. For non-inherited multi-model files:
   - Reset model verdicts via `initialize_model_verdicts()`
   - Generate full prompt for fresh evaluation
4. Write tests:
   - All models terminal + unchanged → inherits globally
   - One model non-terminal + unchanged → no inheritance, all models re-evaluate
   - Changed file with terminal verdicts → no inheritance

### Phase 8: Scaffold Session Logic Update

**Deliverables:** Remove scaffold-level `already_reviewed` session skip

**Tasks:**

1. In `review_scaffold.py` → `scaffold_review_threads()`:
   - When `_check_session_status()` returns `"already_reviewed"`, change behavior:
     - Instead of skipping entirely, proceed with the review but pass unchanged-file context
     - Create a new session record for audit trail
   - Alternatively: keep session-level `already_reviewed` as a distinct concept (same commit+model completed) but still generate prompts for all files
2. In `_incremental_rescaffold()`:
   - Ensure unchanged files from `detect_file_changes()` get their `FileEntry` preserved (already the case — current code does "no action" for unchanged files)
   - Pass `FileChangeResult` back to caller for use in prompt generation
3. Update `_check_session_status()` tests for new behavior

### Phase 9: Output Clarity and CLI (FR-010, NFR-002)

**Deliverables:** Clear CLI output with `processingPath` labels

**Tasks:**

1. Update `print_review_instructions()` in `review_commands.py`:
   - Show counts: `N reviewed, N inherited, N reviewed-no-prior`
   - Remove "skipped (already reviewed)" messaging
2. Update `render_overall_summary()` in `review_templates.py`:
   - Add `processingPath` breakdown to summary
   - Remove `already_reviewed` skip count
3. Update `status_cascade.py` → `derive_overall_status()`:
   - Include inherited file statuses in aggregation (they're already in `files` dict)
4. Ensure log output uses canonical labels consistently
5. Write tests for output formatting

### Phase 10: Edge Cases and Deleted Files (FR-012, EC-003, EC-006)

**Deliverables:** Safe handling of deleted files, file transitions

**Tasks:**

1. Deleted files (in prior state but not current scope):
   - Do NOT include in current run output
   - Do NOT report as `inherited`
   - Leave in prior state file for audit (already handled by `_incremental_rescaffold`)
2. File transitions (previously inherited, now changed):
   - Detect via `detect_file_changes()` → `modified_files`
   - Treat as normal review (`processingPath = "reviewed"`)
3. Write tests:
   - Deleted file not in output
   - Previously-inherited file now changed → full review
   - File appears for first time (new) → `processingPath = "reviewed"`

### Phase 11: Performance Validation and Integration Tests (NFR-001, NFR-004, SC-001–SC-005)

**Deliverables:** Comprehensive test coverage, performance baseline

**Tasks:**

1. Create integration test fixtures under `tests/fixtures/ci_events/`:
   - Fixture with prior review history (changed + unchanged files)
   - Fixture with no prior state (first run)
   - Fixture with multi-model verdicts
2. Write integration tests validating:
   - SC-001: 100% of in-scope files in results
   - SC-002: ≥95% unchanged files inherit expected status
   - SC-003: 100% files without prior state processed without inheritance
   - SC-004: 100% files have `processingPath` in output
   - SC-005: One scenario per edge case + user story
3. Performance regression test:
   - Baseline: run against CI fixtures with skip-based flow
   - New: run against same fixtures with review-all flow
   - Assert ≤20% runtime increase (NFR-001)
4. Run full test suite: `agdt-test && agdt-task-wait`

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Breaking existing review state files | Medium | High | Backward-compat deserialization with `None` default for `processingPath`; retain `SkippedFile` for `not_on_branch` |
| Performance regression from reviewing all files | Medium | Medium | Unchanged files get simplified prompts (minimal I/O); measure with NFR-001 baseline |
| Multi-model inheritance edge cases | Low | Medium | Comprehensive unit tests per Phase 7; deterministic global-per-file rule |
| Azure DevOps API changes affecting iteration detection | Low | High | Existing `detect_file_changes()` is already production-proven; git diff cross-check provides fallback |
| Session-level `already_reviewed` conflicts with file-level changes | Medium | Medium | Clearly separate session idempotency (same commit+model) from file-level processing |

## 6. Dependencies

**Internal:**

- `detect_file_changes()` — already exists in `review_scaffold.py`, reuse as-is
- `compute_aggregate_status()` — unchanged, works with inherited statuses
- `FileEntry`, `ReviewState` dataclasses — extended, not replaced

**External:**

- Azure DevOps iterations API — unchanged usage
- No new external dependencies introduced

**Phase Dependencies:**

```text
Phase 1 (data model) ← Phase 2 (inheritance logic) ← Phase 4 (change detection)
Phase 3 (remove skip) ← Phase 5 (simplified prompts) ← Phase 6 (persist state)
Phase 2 + Phase 4 ← Phase 7 (multi-model)
Phase 3 ← Phase 8 (scaffold session)
Phase 6 ← Phase 9 (output)
Phase 4 ← Phase 10 (edge cases)
All phases ← Phase 11 (integration tests)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*

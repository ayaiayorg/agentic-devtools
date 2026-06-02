# Tasks: Review All Files Every Run with Simplified Scaffolding

## Phase Mapping: Plan → Tasks

Phases are 1:1 aligned with plan.md — no mapping needed.

## Phase 1: Setup — Project scaffolding and constants

- [ ] T001 Define `processingPath` constants in `agentic_devtools/cli/azure_devops/review_state.py`
  - Add module-level constants: `PROCESSING_PATH_REVIEWED = "reviewed"`, `PROCESSING_PATH_INHERITED = "inherited"`, `PROCESSING_PATH_REVIEWED_NO_PRIOR = "reviewed-no-prior"`
  - Place after existing `COMPLETE_STATUSES` constant (line ~36)

- [ ] T002 Add `processingPath` field to `FileEntry` dataclass in `agentic_devtools/cli/azure_devops/review_state.py`
  - Add `processingPath: str | None = None` field to the `FileEntry` class (after `consolidationStatus`)
  - Ensures backward-compatible deserialization (absent key → `None`)

- [ ] T003 Update `FileEntry.to_dict()` in `agentic_devtools/cli/azure_devops/review_state.py`
  - Include `processingPath` in serialized output only when not `None` (compact JSON)

- [ ] T004 Update `FileEntry.from_dict()` in `agentic_devtools/cli/azure_devops/review_state.py`
  - Deserialize `processingPath` with `data.get("processingPath")` defaulting to `None`

## Phase 2: Foundational — Inheritance validation logic (blocking prerequisite)

- [ ] T005 Create `is_valid_prior_state()` function in `agentic_devtools/cli/azure_devops/review_state.py`
  - Signature: `is_valid_prior_state(file_entry: FileEntry, prior_commit_hash: str | None) -> bool`
  - Returns `True` only when: `status` in `COMPLETE_STATUSES`, `threadId` is truthy, `commentId` is truthy, `folder` is non-empty string, and `prior_commit_hash` is truthy
  - Depends on: T001, T002

- [ ] T006 Create `can_inherit_file()` function in `agentic_devtools/cli/azure_devops/review_state.py`
  - Signature: `can_inherit_file(file_entry: FileEntry, is_unchanged: bool, prior_commit_hash: str | None) -> bool`
  - Returns `True` when both `is_unchanged` and `is_valid_prior_state(file_entry, prior_commit_hash)` are True
  - Depends on: T005

- [ ] T007 Create `can_inherit_multi_model()` function in `agentic_devtools/cli/azure_devops/review_state.py`
  - Signature: `can_inherit_multi_model(file_entry: FileEntry, is_unchanged: bool, prior_commit_hash: str | None) -> bool`
  - Returns `True` when `can_inherit_file(file_entry, is_unchanged, prior_commit_hash)` is True AND all `modelVerdicts` have status in `COMPLETE_STATUSES`
  - Depends on: T006

- [ ] T008 Create `determine_processing_path()` function in `agentic_devtools/cli/azure_devops/review_state.py`
  - Signature: `determine_processing_path(file_entry: FileEntry | None, is_unchanged: bool, prior_commit_hash: str | None, has_model_verdicts: bool) -> str`
  - Returns one of the three constants based on inheritance eligibility
  - Central logic for Phase 4+ consumption
  - Depends on: T006, T007

## Phase 3: User Story 1 — Review all in-scope files every run [P1]

- [ ] T009 [US1] Write unit tests for `processingPath` serialization roundtrip in `tests/unit/cli/azure_devops/review_state/test_fileentry.py`
  - Test `to_dict()` omits field when `None`, includes when set
  - Test `from_dict()` handles missing key (old state files) → `None`
  - Test all three label values serialize/deserialize correctly
  - Depends on: T002, T003, T004

- [ ] T010 [P] [US1] Write unit tests for `is_valid_prior_state()` in `tests/unit/cli/azure_devops/review_state/test_is_valid_prior_state.py`
  - Valid terminal state → `True`
  - Non-terminal status (`in-progress`, `unreviewed`) → `False`
  - Missing `threadId` → `False`
  - Missing `commentId` → `False`
  - Empty `folder` → `False`
  - Depends on: T005

- [ ] T011 [P] [US1] Write unit tests for `can_inherit_file()` in `tests/unit/cli/azure_devops/review_state/test_can_inherit_file.py`
  - Unchanged + valid → `True`
  - Changed + valid → `False`
  - Unchanged + invalid → `False`
  - Depends on: T006

- [ ] T012 [P] [US1] Write unit tests for `can_inherit_multi_model()` in `tests/unit/cli/azure_devops/review_state/test_can_inherit_multi_model.py`
  - All terminal verdicts + unchanged + valid → `True`
  - One non-terminal verdict → `False`
  - No model verdicts (empty list) → `True` (vacuously)
  - Depends on: T007

- [ ] T013 [P] [US1] Write unit tests for `determine_processing_path()` in `tests/unit/cli/azure_devops/review_state/test_determine_processing_path.py`
  - Changed file → `"reviewed"`
  - Unchanged + valid prior → `"inherited"`
  - Unchanged + no prior (None entry) → `"reviewed-no-prior"`
  - Unchanged + invalid prior → `"reviewed-no-prior"`
  - Depends on: T008

- [ ] T014 [US1] Remove `already_reviewed` skip block from `generate_review_prompts()` in `agentic_devtools/cli/azure_devops/review_commands.py`
  - Remove `reviewed_paths` variable and `build_reviewed_paths_set()` call (line ~439-440)
  - Remove `if not include_reviewed and normalized_path.lower() in reviewed_paths` block (lines ~477-481)
  - Remove `SkippedFile(path=file_path, reason="already_reviewed")` append
  - Depends on: T001

- [ ] T015 [US1] Remove `include_reviewed` parameter from `generate_review_prompts()` signature in `agentic_devtools/cli/azure_devops/review_commands.py`
  - Remove parameter from function definition (line ~379)
  - Remove from docstring (line ~391)
  - Update all callers to remove the argument
  - Depends on: T014

- [ ] T016 [US1] Remove `already_reviewed` skip from `generate_review_prompts()` in `agentic_devtools/cli/azure_devops/review_prompts.py`
  - Remove the block at line ~224 that creates `{"reason": "already_reviewed"}` entries
  - Depends on: T014

- [ ] T017 [US1] Remove `include_reviewed` state key usage from `setup_pull_request_review()` in `agentic_devtools/cli/azure_devops/review_commands.py`
  - Remove `include_reviewed = str(get_value(...))` (line ~774)
  - Remove conditional `set_value("include_reviewed", "true")` (lines ~818-819)
  - Remove `include_reviewed` argument from `generate_review_prompts()` call (line ~964)
  - Depends on: T015

- [ ] T018 [US1] Remove `False` literal for `include_reviewed` in `agentic_devtools/cli/azure_devops/async_commands.py`
  - Update call at line ~1540 to remove the argument
  - Depends on: T015

- [ ] T019 [US1] Deprecate `build_reviewed_paths_set()` in `agentic_devtools/cli/azure_devops/review_helpers.py`
  - Add deprecation docstring noting it is no longer called by the review workflow
  - Retain function body for backward compatibility but mark with `# DEPRECATED`
  - Depends on: T014

- [ ] T020 [US1] Remove `skipped_reviewed_count` from `print_review_instructions()` in `agentic_devtools/cli/azure_devops/review_commands.py`
  - Remove parameter and related output lines referencing "skipped (already reviewed)"
  - Depends on: T014

- [ ] T021 [US1] Write unit tests verifying no files skipped with `already_reviewed` reason in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
  - Test that all in-scope files produce prompts regardless of prior review history
  - Test that `SkippedFile` with `not_on_branch` reason still works
  - Depends on: T014, T015, T016

## Phase 4: User Story 2 — Reuse prior status for unchanged files [P1]

- [ ] T022 [US2] Add `unchanged_files: set[str] | None = None` parameter to `generate_review_prompts()` in `agentic_devtools/cli/azure_devops/review_commands.py`
  - Add parameter to function signature
  - Document in docstring
  - Default `None` treated as empty set (all files considered changed)
  - Depends on: T015

- [ ] T023 [US2] Load prior `ReviewState` in `generate_review_prompts()` in `agentic_devtools/cli/azure_devops/review_commands.py`
  - Call `load_review_state()` to get prior file entries for inheritance checks
  - Handle case where no prior state exists (first run)
  - Depends on: T022

- [ ] T024 [US2] Implement `processingPath` determination loop in `generate_review_prompts()` in `agentic_devtools/cli/azure_devops/review_commands.py`
  - For each file in the processing loop, call `determine_processing_path()`
  - Pass `is_unchanged = normalized_path in unchanged_files`
  - Pass prior `FileEntry` from loaded state (or `None` if absent)
  - Store result on the generated queue entry
  - Depends on: T008, T022, T023

- [ ] T025 [US2] Pass `FileChangeResult.unchanged_files` from scaffold to prompt generation in `agentic_devtools/cli/azure_devops/review_commands.py`
  - In `setup_pull_request_review()`, after scaffold returns `FileChangeResult`, convert `unchanged_files` list to a set
  - Pass to `generate_review_prompts()` via new parameter
  - For first-run (no prior `commitHash`), pass empty set
  - Depends on: T022

- [ ] T026 [US2] For inherited files, carry forward prior `status`, `summary`, `suggestions`, `modelVerdicts` in `agentic_devtools/cli/azure_devops/review_commands.py`
  - When `processingPath == "inherited"`, copy fields from prior `FileEntry` to current state
  - Skip new review submission for these files (FR-009)
  - Depends on: T024

- [ ] T027 [US2] Write unit tests for inheritance with valid prior state in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts_inheritance.py`
  - Unchanged file + terminal prior status → `processingPath = "inherited"`, status carried forward
  - Unchanged file + non-terminal prior → `processingPath = "reviewed-no-prior"`, full review
  - Changed file + terminal prior → `processingPath = "reviewed"`, full review
  - Depends on: T024, T025, T026

- [ ] T028 [US2] Write unit tests for missing/invalid prior state in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts_no_prior.py`
  - No prior `FileEntry` → `processingPath = "reviewed-no-prior"`
  - Prior entry missing `threadId` → `processingPath = "reviewed-no-prior"`
  - Prior entry missing `commentId` → `processingPath = "reviewed-no-prior"`
  - Prior entry with empty `folder` → `processingPath = "reviewed-no-prior"`
  - Depends on: T024

- [ ] T029 [US2] Write unit tests for first-run behavior in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts_first_run.py`
  - No prior state file → all files get `processingPath = "reviewed"`
  - Empty `unchanged_files` set → all files get `processingPath = "reviewed"`
  - Depends on: T024, T025

- [ ] T030 [US2] Write unit tests for multi-model inheritance in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts_multi_model.py`
  - All model verdicts terminal + unchanged → `"inherited"`, verdicts carried forward
  - One model non-terminal + unchanged → `"reviewed-no-prior"`, all models re-evaluate
  - Changed file with terminal verdicts → `"reviewed"`, fresh evaluation
  - Depends on: T024, T026

## Phase 5: User Story 3 — Use simpler scaffolding [P2]

- [ ] T031 [US3] Implement unchanged-file scaffold content generation during scaffolding in `agentic_devtools/cli/azure_devops/review_scaffold.py`
  - Post/update the file summary thread *before the AI agent session begins* with: `### Commit: [<hash>](<url>)` + blank line + `no changes since last review`
  - Add/keep a `_write_unchanged_file_prompt()` helper in `agentic_devtools/cli/azure_devops/review_commands.py` so prompt generation can reuse the same minimal scaffold for `"inherited"` files
  - Include prior status/model verdict summary in the prompt content for inherited files
  - Depends on: T024

- [ ] T032 [US3] Modify file loop in `generate_review_prompts()` to route unchanged files in `agentic_devtools/cli/azure_devops/review_commands.py`
  - Changed/new files → existing `_write_file_prompt()` (full diff)
  - Unchanged + valid prior (`"inherited"`) → `_write_unchanged_file_prompt()` (simplified)
  - Unchanged + no prior (`"reviewed-no-prior"`) → existing `_write_file_prompt()` (full diff)
  - Depends on: T024, T031

- [ ] T033 [US3] Update `build_file_prompt_content()` in `agentic_devtools/cli/azure_devops/review_prompts.py` to support unchanged mode
  - Add optional `unchanged: bool = False` parameter
  - When `unchanged=True`, emit simplified scaffold instead of full diff
  - Emit: `### Commit: [<hash>](<url>)` + blank line + `no changes since last review`
  - Depends on: T031

- [ ] T034 [US3] Write unit tests for `_write_unchanged_file_prompt()` in `tests/unit/cli/azure_devops/review_commands/test_write_unchanged_file_prompt.py`
  - Output contains `### Commit: [<hash>](<url>)` header
  - Output contains `no changes since last review` text
  - Prior status and summary are included when available
  - Depends on: T031

- [ ] T035 [P] [US3] Write unit tests for prompt routing in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts_routing.py`
  - Changed file → full diff prompt generated
  - Unchanged + prior → simplified prompt with `no changes since last review`
  - Unchanged + no prior → full diff prompt generated
  - Depends on: T032

- [ ] T036 [P] [US3] Write unit tests for `build_file_prompt_content()` unchanged mode in `tests/unit/cli/azure_devops/review_prompts/test_build_file_prompt_content.py`
  - `unchanged=False` → full content with diff
  - `unchanged=True` → minimal scaffold content
  - Depends on: T033

## Phase 6: User Story 4 — Prompt appropriately for unchanged files [P2]

- [ ] T037 [US4] Ensure inherited files skip new review submission in `agentic_devtools/cli/azure_devops/file_review_commands.py`
  - In `approve_file()` and `request_changes()`, check `processingPath`
  - If file is `"inherited"` and assessment matches prior, skip API submission
  - If assessment differs from prior, proceed with submission and update `processingPath` to `"reviewed"`
  - Depends on: T026

- [ ] T038 [US4] Set `processingPath = "reviewed"` when actively reviewing in `agentic_devtools/cli/azure_devops/file_review_commands.py`
  - In `approve_file()`: set `file_entry.processingPath = PROCESSING_PATH_REVIEWED`
  - In `request_changes()`: set `file_entry.processingPath = PROCESSING_PATH_REVIEWED`
  - Ensures actively reviewed files always get the correct label
  - Depends on: T002

- [ ] T039 [US4] Write unit tests for conditional submission in `tests/unit/cli/azure_devops/file_review_commands/test_approve_file_inheritance.py`
  - Inherited file with same assessment → no new API call
  - Inherited file with different assessment → API call made, `processingPath` updated
  - Depends on: T037

- [ ] T040 [P] [US4] Write unit tests for `processingPath` set on active review in `tests/unit/cli/azure_devops/file_review_commands/test_processing_path_on_review.py`
  - `approve_file()` → `processingPath = "reviewed"`
  - `request_changes()` → `processingPath = "reviewed"`
  - Depends on: T038

## Phase 7: User Story 2 (continued) — Multi-model inheritance [P1]

- [ ] T041 [US2] Integrate `can_inherit_multi_model()` in inheritance check path in `agentic_devtools/cli/azure_devops/review_commands.py`
  - When file has `modelVerdicts`, use `can_inherit_multi_model()` instead of `can_inherit_file()`
  - If inheritance fails for multi-model, call `initialize_model_verdicts()` to reset
  - Generate full prompt for fresh multi-model evaluation
  - Depends on: T007, T024

- [ ] T042 [US2] For inherited multi-model files, carry forward `modelVerdicts` unchanged in `agentic_devtools/cli/azure_devops/review_commands.py`
  - When `processingPath == "inherited"` and multi-model, preserve entire `modelVerdicts` list
  - Do not call `initialize_model_verdicts()` for inherited files
  - Depends on: T026, T041

- [ ] T043 [US2] Write integration test for multi-model inheritance end-to-end in `tests/unit/cli/azure_devops/review_commands/test_multi_model_inheritance_e2e.py`
  - Scenario: 3 models, all terminal verdicts, file unchanged → inherits globally
  - Scenario: 3 models, one non-terminal, file unchanged → all models re-evaluate
  - Scenario: models terminal but file changed → no inheritance
  - Depends on: T041, T042

## Phase 8: User Story 1 (continued) — Scaffold session logic update [P1]

- [ ] T044 [US1] Update `_check_session_status()` behavior for `already_reviewed` in `agentic_devtools/cli/azure_devops/review_scaffold.py`
  - When status is `"already_reviewed"` (same commit+model completed), still proceed with review
  - Create new session record for audit trail instead of returning early
  - Pass unchanged-file context to downstream for inheritance decision
  - Depends on: T014

- [ ] T045 [US1] Ensure `_incremental_rescaffold()` returns `FileChangeResult` to caller in `agentic_devtools/cli/azure_devops/review_scaffold.py`
  - Verify `FileChangeResult` is returned from `scaffold_review_threads()` for prompt generation use
  - Ensure `unchanged_files` list is populated correctly from `detect_file_changes()`
  - Depends on: T025

- [ ] T046 [US1] Write unit tests for updated session status behavior in `tests/unit/cli/azure_devops/review_scaffold/test_check_session_status.py`
  - `already_reviewed` status → proceeds with review (not skipped)
  - New session record created for audit
  - `FileChangeResult` propagated to caller
  - Depends on: T044, T045

## Phase 9: User Story 5 — Produce clear output for users [P3]

- [ ] T047 [US5] Update `print_review_instructions()` in `agentic_devtools/cli/azure_devops/review_commands.py`
  - Show counts: `N reviewed, N inherited, N reviewed-no-prior`
  - Remove "skipped (already reviewed)" messaging entirely
  - Keep "skipped (not on branch)" if any exist
  - Depends on: T020, T024

- [ ] T048 [US5] Update `render_overall_summary()` in `agentic_devtools/cli/azure_devops/review_templates.py`
  - Remove `already_reviewed` count from skipped files section (lines ~321-327)
  - Add `processingPath` breakdown showing count per label
  - Only show `not_on_branch` skip count if non-zero
  - Depends on: T014

- [ ] T049 [US5] Verify `derive_overall_status()` includes inherited files in `agentic_devtools/cli/azure_devops/status_cascade.py`
  - Confirm inherited files (which are in `ReviewState.files`) participate in status aggregation
  - No code change expected if `compute_aggregate_status()` already reads all entries from `files` dict
  - Depends on: T026

- [ ] T050 [US5] Ensure log output uses canonical labels consistently across modules
  - Audit all `print()` and `logging` calls in `review_commands.py`, `review_scaffold.py`, `review_templates.py`
  - Replace any ad-hoc labeling with constants from T001
  - Depends on: T001, T047, T048

- [ ] T051 [P] [US5] Write unit tests for output formatting in `tests/unit/cli/azure_devops/review_commands/test_print_review_instructions.py`
  - Output contains count for each `processingPath` label
  - Output does not contain "skipped (already reviewed)"
  - Output still shows "not on branch" skips when present
  - Depends on: T047

- [ ] T052 [P] [US5] Write unit tests for `render_overall_summary()` in `tests/unit/cli/azure_devops/review_templates/test_render_overall_summary_processing_path.py`
  - Summary includes `processingPath` breakdown
  - No `already_reviewed` reference in output
  - Depends on: T048

## Phase 10: User Story 1 & 2 — Edge cases and deleted files [P1]

- [ ] T053 [US1] Handle deleted files (in prior state but not current scope) in `agentic_devtools/cli/azure_devops/review_commands.py`
  - In `generate_review_prompts()`, only process files in the current PR file list
  - Prior state entries for deleted files remain in `review-state.json` for audit
  - Deleted files do NOT appear in output or get `processingPath`
  - Depends on: T024

- [ ] T054 [US2] Handle file transitions (previously inherited, now changed) in `agentic_devtools/cli/azure_devops/review_commands.py`
  - Files in `FileChangeResult.modified_files` always get `processingPath = "reviewed"`
  - Prior inherited status is not carried forward for changed files
  - Depends on: T024

- [ ] T055 [P] [US1] Write unit tests for deleted files in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts_deleted.py`
  - File in prior state but not in current PR files → not in output
  - File in prior state but not in current PR files → no error raised
  - Prior state entry preserved in `review-state.json`
  - Depends on: T053

- [ ] T056 [P] [US2] Write unit tests for file transitions in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts_transitions.py`
  - Previously inherited file now in `modified_files` → `"reviewed"`, full prompt
  - New file (first appearance) → `"reviewed"`, full prompt
  - Depends on: T054

## Phase 11: Final Phase — Integration tests, performance, and polish

- [ ] T057 Create integration test fixture with prior review history in `tests/fixtures/ci_events/review_all_files_prior_history.json`
  - Contains: changed files, unchanged files with valid prior, unchanged files without prior, deleted files
  - Includes multi-model verdict data
  - Depends on: T024, T026

- [ ] T058 Create integration test fixture for first-run scenario in `tests/fixtures/ci_events/review_all_files_first_run.json`
  - No prior `review-state.json` exists
  - All files treated as changed
  - Depends on: T024

- [ ] T059 Write SC-001 integration test: 100% of in-scope files in results in `tests/unit/cli/azure_devops/review_commands/test_review_all_files_sc001.py`
  - Run workflow against fixture with prior history
  - Assert every in-scope file has an entry in output
  - Assert no file is missing from results
  - Depends on: T057

- [ ] T060 Write SC-002 integration test: ≥95% unchanged files inherit in `tests/unit/cli/azure_devops/review_commands/test_review_all_files_sc002.py`
  - Run workflow against fixture with unchanged files having valid prior
  - Assert ≥95% get `processingPath = "inherited"`
  - Any exceptions must have explicit override reason
  - Depends on: T057

- [ ] T061 Write SC-003 integration test: 100% files without prior processed without inheritance in `tests/unit/cli/azure_devops/review_commands/test_review_all_files_sc003.py`
  - Run workflow against fixture with files lacking prior state
  - Assert all get `processingPath = "reviewed-no-prior"`
  - Depends on: T057

- [ ] T062 Write SC-004 integration test: 100% files have `processingPath` in output in `tests/unit/cli/azure_devops/review_commands/test_review_all_files_sc004.py`
  - Run workflow against any fixture
  - Assert every file entry has non-None `processingPath`
  - Assert value is one of the three canonical labels
  - Depends on: T057, T058

- [ ] T063 Write SC-005 integration test: one scenario per edge case in `tests/unit/cli/azure_devops/review_commands/test_review_all_files_edge_cases.py`
  - EC-001: Missing prior state → `"reviewed-no-prior"`
  - EC-002: First run → all `"reviewed"`
  - EC-003: Deleted file → not in output
  - EC-004: Invalid partial prior → `"reviewed-no-prior"`
  - EC-005: Multi-model deterministic inheritance
  - EC-006: File transitions unchanged→changed → `"reviewed"`
  - Depends on: T057, T058

- [ ] T064 Write NFR-001 performance regression test in `tests/unit/cli/azure_devops/review_commands/test_review_all_files_performance.py`
  - Measure wall-clock time of review-all flow against CI fixtures
  - Assert ≤20% increase vs baseline (mocked LLM, no network)
  - Depends on: T057, T058

- [ ] T065 Run full test suite and validate no regressions
  - Execute `agdt-test && agdt-task-wait`
  - Verify all existing tests pass
  - Verify new tests pass
  - Depends on: T009–T064

- [ ] T066 Run `ruff check` and `ruff format` on all modified files
  - Fix any lint violations
  - Ensure import ordering compliance
  - Depends on: T065

- [ ] T067 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 compliance
  - Verify all new test files follow path convention
  - Verify all `__init__.py` files are present
  - Depends on: T065

- [ ] T068 Update `SkippedFile` docstring in `agentic_devtools/cli/azure_devops/review_state.py`
  - Update `reason` field docstring to note `already_reviewed` is deprecated
  - Document that only `not_on_branch` is actively used
  - Retain class for backward-compatible deserialization
  - Depends on: T014

## Dependency Graph Summary

```text
T001 ← T002 ← T003, T004, T005
T005 ← T006 ← T007 ← T008
T008 ← T024
T014 ← T015 ← T016, T017, T018, T019, T020
T015 ← T022 ← T023 ← T024
T024 ← T025, T026, T031, T032, T041, T053, T054
T026 ← T037, T042, T049
T031 ← T032, T033
T014 ← T044, T048
T025 ← T045
T024 ← T047
All phases ← T065 ← T066, T067
```

---
*Generated by Copilot SDK (claude-opus-4.6)*

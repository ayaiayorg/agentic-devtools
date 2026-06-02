# Tasks: Review All Files Every Run with Simplified Scaffolding

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup & Scaffolding | Phase 1: Data Model Extension | Add `processingPath` field, constants, and serialization tests to `FileEntry` |
| Phase 2: Foundational — Inheritance Validation Logic | Phase 2: Inheritance Validation Logic | Pure helper functions for determining inheritance eligibility |
| Phase 3: User Story 1 — Review All In-Scope Files Every Run | Phases 3–4: Remove Skip + Change Detection | Remove `already_reviewed` skip and wire in `unchanged_files` detection |
| Phase 4: User Story 2 — Reuse Prior Status for Unchanged Files | Phases 6–7: Persist State + Multi-Model Inheritance | Carry forward prior status and model verdicts for inherited files |
| Phase 5: User Story 3 — Simplified Scaffolding | Phases 5, 8: Simplified Prompts + Scaffold Session | Simplified prompt for unchanged files; scaffold session logic update |
| Phase 6: User Story 4 — Prompt Appropriately for Unchanged Files | Phases 5–6 (partial): Conditional Prompts + Submission Suppression | Conditional prompt routing and FR-009 submission suppression |
| Phase 7: User Story 5 — Produce Clear Output for Users | Phase 9: Output Clarity and CLI | CLI output showing `processingPath` counts; remove skip-oriented messaging |
| Phase 8: Polish & Cross-Cutting — Edge Cases, Performance, Integration | Phases 10–11: Edge Cases + Performance Validation | Deleted files, file transitions, integration tests, performance regression |

## Phase 1: Setup & Scaffolding

- [ ] T001 Define `PROCESSING_PATH_REVIEWED`, `PROCESSING_PATH_INHERITED`, `PROCESSING_PATH_REVIEWED_NO_PRIOR` constants in `agentic_devtools/cli/azure_devops/review_state.py`
- [ ] T002 [US2] Write unit tests for `FileEntry` serialization/default behavior with `processingPath` field in `tests/unit/cli/azure_devops/review_state/test_fileentry.py`
- [ ] T003 Add `processingPath: str | None = None` field to `FileEntry` dataclass in `agentic_devtools/cli/azure_devops/review_state.py` (FR-011)
- [ ] T004 Update `FileEntry.to_dict()` to serialize `processingPath` (omit when `None`) in `agentic_devtools/cli/azure_devops/review_state.py`
- [ ] T005 Update `FileEntry.from_dict()` to deserialize `processingPath` with `None` default for backward compat (NFR-003) in `agentic_devtools/cli/azure_devops/review_state.py`

## Phase 2: Foundational — Inheritance Validation Logic

- [ ] T006 [US2] [P] Write unit tests for `is_valid_prior_state` covering terminal/non-terminal status, missing `threadId`/`commentId`/`folder`, and missing prior `commitHash` in `tests/unit/cli/azure_devops/review_state/test_is_valid_prior_state.py`
- [ ] T007 [US2] [P] Write unit tests for `can_inherit_file` covering changed/unchanged + valid/invalid prior in `tests/unit/cli/azure_devops/review_state/test_can_inherit_file.py`
- [ ] T008 [US2] [P] Write unit tests for `can_inherit_multi_model` covering all-terminal/mixed verdicts in `tests/unit/cli/azure_devops/review_state/test_can_inherit_multi_model.py`
- [ ] T009 Create `is_valid_prior_state(file_entry: FileEntry, prior_commit_hash: str | None) -> bool` function in
  `agentic_devtools/cli/azure_devops/review_state.py` — checks terminal status, truthy `threadId`/`commentId`,
  non-empty `folder`, and present prior `commitHash` (FR-004, FR-005, EC-004)
- [ ] T010 Create `can_inherit_file(file_entry: FileEntry, is_unchanged: bool, prior_commit_hash: str | None) -> bool` function in
  `agentic_devtools/cli/azure_devops/review_state.py` — combines unchanged check with
  `is_valid_prior_state` (FR-005, FR-006)
- [ ] T011 Create `can_inherit_multi_model(file_entry: FileEntry, is_unchanged: bool, prior_commit_hash: str | None) -> bool` function in
  `agentic_devtools/cli/azure_devops/review_state.py` — confirms all `modelVerdicts` are
  terminal (FR-005, EC-005)
- [ ] T012 [US2] [P] Write unit tests for `safe_load_file_entry` covering missing `threadId`, missing `commentId`,
  missing `folder`, and valid all-fields-present case in
  `tests/unit/cli/azure_devops/review_state/test_safe_load_file_entry.py`
- [ ] T013 [P] Create `safe_load_file_entry(raw: dict) -> FileEntry | None` in
  `agentic_devtools/cli/azure_devops/review_state.py` — tolerant deserialization that returns `None` when required
  fields (`threadId`, `commentId`, `folder`) are absent, preventing `FileEntry.from_dict()` failures from
  surfacing as errors instead of falling back to normal review (FR-005, EC-004)

## Phase 3: User Story 1 — Review All In-Scope Files Every Run (P1)

**Story Goal**: Ensure every in-scope file is reviewed on every run, regardless of prior review history.

**Independent Test Criteria**: Run prompt generation with prior history and verify all in-scope files are included and none are skipped as already reviewed.

- [ ] T014 [US1] Write tests verifying `generate_review_prompts()` no longer skips files with `already_reviewed` reason (FR-001, FR-002) in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T015 [US1] Remove `build_reviewed_paths_set()` call and `reviewed_paths` variable from `generate_review_prompts()` in `agentic_devtools/cli/azure_devops/review_commands.py` (FR-002)
- [ ] T016 [US1] Remove the `already_reviewed` skip block (`if normalized_path.lower() in reviewed_paths`) from `generate_review_prompts()` in `agentic_devtools/cli/azure_devops/review_commands.py`
  (FR-001, FR-002)
- [ ] T017 [US1] Remove `include_reviewed` parameter from `generate_review_prompts()` signature and all callers in `agentic_devtools/cli/azure_devops/review_commands.py` (FR-002)
- [ ] T018 [US1] Remove the `already_reviewed` skip block, `build_reviewed_paths_set()` import/call, and `reviewed_paths` variable from
  `generate_review_prompts()` in `agentic_devtools/cli/azure_devops/review_prompts.py` (FR-002)
- [ ] T019 [US1] Remove `include_reviewed` state key usage from `setup_pull_request_review()` in `agentic_devtools/cli/azure_devops/review_commands.py` (FR-002)
- [ ] T020 [US1] Remove `False` literal for `include_reviewed` parameter in `agentic_devtools/cli/azure_devops/async_commands.py` (FR-002)
- [ ] T021 [US1] Deprecate `build_reviewed_paths_set()` in `agentic_devtools/cli/azure_devops/review_helpers.py` (FR-002)
- [ ] T022 [US1] Remove `skipped_reviewed_count` parameter from `print_review_instructions()` in `agentic_devtools/cli/azure_devops/review_commands.py` (FR-001)
- [ ] T023 [US1] Write integration test confirming all in-scope files appear in results after a run with prior history (FR-001, SC-001) in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T024 [US1] Write happy-path unit tests for `generate_review_prompts()` verifying every in-scope file is included in results regardless of prior review history (FR-001, FR-002, FR-003) in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T025 [US1] Write tests for change detection integration — first run (all changed), subsequent run (mixed) in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T026 [US1] Add `unchanged_files: set[str] | None = None` parameter to `generate_review_prompts()` in `agentic_devtools/cli/azure_devops/review_commands.py` (FR-003)
- [ ] T027 [US1] Integrate `FileChangeResult.unchanged_files` from scaffold into `generate_review_prompts()` call in `setup_pull_request_review()` in
  `agentic_devtools/cli/azure_devops/review_commands.py` (FR-003)
- [ ] T028 [US1] Implement first-run detection: when no prior `commitHash` exists, treat all files as changed (FR-003, EC-002) in `agentic_devtools/cli/azure_devops/review_commands.py`

## Phase 4: User Story 2 — Reuse Prior Status for Unchanged Files (P1)

**Story Goal**: Reuse valid prior review state for unchanged files while preserving correctness and fallback behavior.

**Independent Test Criteria**: Run with mixed changed/unchanged files and validate unchanged files
with valid prior state inherit status/processing path, while invalid prior entries fall back to
normal review.

- [ ] T029 [US2] Write tests for inheritance determination logic in prompt generation loop in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T030 [US2] Write happy-path unit tests verifying that a valid unchanged prior state successfully inherits `status` and `processingPath` via
  `can_inherit_file()` (FR-004, FR-005, FR-006, FR-011) in `tests/unit/cli/azure_devops/review_state/test_can_inherit_file.py`
- [ ] T031 [US2] Load prior `ReviewState` in `generate_review_prompts()` for inheritance checks (FR-004) in `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T032 [US2] Implement `processingPath` assignment in the file loop: `inherited` when unchanged + valid prior,
  `reviewed-no-prior` when unchanged + no valid prior state (missing or invalid), `reviewed` otherwise (FR-005, FR-006,
  FR-010, FR-011) in `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T033 [US2] For `inherited` files: carry forward `status`, `summary`, `suggestions`, `modelVerdicts` from prior state (FR-005) in `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T034 [US2] For `inherited` files: persist prior assessment context needed for downstream FR-009 submission decisions, without suppressing in prompt generation (FR-009) in `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T035 [US2] Set `processingPath = "reviewed"` in `approve_file()` and `request_changes()` in `agentic_devtools/cli/azure_devops/file_review_commands.py` (FR-011)
- [ ] T036 [US2] Store `processingPath` in queue entry metadata for downstream consumption in `agentic_devtools/cli/azure_devops/review_commands.py` (FR-011)
- [ ] T037 [US2] Write tests verifying inherited files retain prior status and `processingPath = "inherited"` (SC-002) in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T038 [US2] Write tests verifying files without prior state get `processingPath = "reviewed-no-prior"` (SC-003, EC-001) in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T039 [US2] Implement multi-model inheritance: use `can_inherit_multi_model()`, carry forward `modelVerdicts` only when all match prior terminal (FR-005, EC-005) in
  `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T040 [US2] For non-inherited multi-model files: reset verdicts via `initialize_model_verdicts()` and generate full prompt in `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T041 [US2] Write tests for multi-model inheritance — all terminal inherits, any non-terminal forces re-evaluate in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T042 [US2] Write test for partial/invalid prior state entries (missing threadId/commentId/folder) falling back to normal review (EC-004) in `tests/unit/cli/azure_devops/review_state/test_is_valid_prior_state.py`

## Phase 5: User Story 3 — Simplified Scaffolding (P2)

**Story Goal**: Provide minimal unchanged-file scaffolding content before the AI session while keeping changed-file review context complete.

**Independent Test Criteria**: Verify scaffolding posts/updates minimal unchanged-file summary
content and prompt routing preserves full prompts for changed files and unchanged files without
valid prior state.

- [ ] T043 [US3] Write tests for simplified unchanged-file prompt format in `tests/unit/cli/azure_devops/review_commands/test__write_unchanged_file_prompt.py`
- [ ] T044 [US3] Create `_write_unchanged_file_prompt()` helper in `agentic_devtools/cli/azure_devops/review_commands.py`
  — generates `### Commit: [<hash>](<url>)` + blank line + `no changes since last review` (FR-007, FR-008)
- [ ] T045 [US3] For `inherited` files: include prior status and model verdicts in simplified prompt context (FR-007) in `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T046 [US3] Modify file loop in `generate_review_prompts()`: route unchanged+prior files to `_write_unchanged_file_prompt()`, unchanged+no-prior to full `_write_file_prompt()` (FR-007, FR-008) in
  `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T047 [US3] Write test for `_post_file_summary_thread()` verifying unchanged-file content is posted to the file summary thread during scaffolding (FR-008) in `tests/unit/cli/azure_devops/review_scaffold/test__post_file_summary_thread.py`
- [ ] T048 [US3] Implement `_post_file_summary_thread()` in `review_scaffold.py` to post or update the file summary thread with minimal unchanged-file
  content during scaffolding, before the AI agent session begins (FR-008) in `agentic_devtools/cli/azure_devops/review_scaffold.py`
- [ ] T049 [US3] Remove obsolete skip-oriented scaffolding instructions from prompt generation output (FR-007) in `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T050 [US3] Write tests for `_write_unchanged_file_prompt()` verifying changed file → full prompt, unchanged+prior → simplified prompt, unchanged+no-prior → full prompt in `tests/unit/cli/azure_devops/review_commands/test__write_unchanged_file_prompt.py`
- [ ] T051 [US3] Write symbol-level tests for `build_file_prompt_content()` unchanged mode in `tests/unit/cli/azure_devops/review_prompts/test_build_file_prompt_content.py` (FR-008)
- [ ] T052 [US3] Update `build_file_prompt_content()` in `agentic_devtools/cli/azure_devops/review_prompts.py` to support an `unchanged` mode (FR-008)
- [ ] T053 [US3] Update scaffold session logic in `review_scaffold.py`: when `_check_session_status()` returns `already_reviewed`, still proceed with review but pass unchanged-file context in
  `agentic_devtools/cli/azure_devops/review_scaffold.py`
- [ ] T054 [US3] Ensure `_incremental_rescaffold()` passes `FileChangeResult` back to caller for prompt generation in `agentic_devtools/cli/azure_devops/review_scaffold.py`
- [ ] T055 [US3] Write tests for updated `_check_session_status()` behavior in `tests/unit/cli/azure_devops/review_scaffold/test__check_session_status.py`

## Phase 6: User Story 4 — Prompt Appropriately for Unchanged Files (P2)

**Story Goal**: Prompt unchanged files with valid prior state in a way that enables independent reassessment and correct conditional submission behavior.

**Independent Test Criteria**: Verify unchanged+prior prompts include prior-status context and independent-review instruction, and submission occurs only when current assessment differs from prior.

- [ ] T056 [US4] Write tests for conditional prompt behavior: unchanged+prior includes `no changes since last review`, unchanged+no-prior gets full context (FR-008) in
  `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T057 [US4] Implement conditional prompt logic: unchanged files with valid prior include prior status reference and
  instruct the AI to independently review the file, submitting only when its own assessment differs from the prior
  status (FR-008, FR-009) in `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T058 [US4] Implement conditional prompt logic: unchanged files without prior presented for normal review handling (FR-008) in `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T059 [US4] Write tests verifying no submission for unchanged+matching assessment, submission for differing assessment in
  `tests/unit/cli/azure_devops/file_review_commands/test_approve_file.py` and `tests/unit/cli/azure_devops/file_review_commands/test_request_changes.py`
- [ ] T060 [US4] Implement submission suppression: no new review output emitted for unchanged files when current assessment matches prior (FR-009) in
  `agentic_devtools/cli/azure_devops/file_review_commands.py`

## Phase 7: User Story 5 — Produce Clear Output for Users (P3)

**Story Goal**: Make CLI/template output clearly communicate reviewed, inherited, and reviewed-no-prior processing outcomes.

**Independent Test Criteria**: Verify review instruction and summary output consistently show processing-path counts and remove skip-oriented messaging.

- [ ] T061 [US5] Write tests for CLI output showing `processingPath` labels and counts (FR-010) in `tests/unit/cli/azure_devops/review_commands/test_print_review_instructions.py`
- [ ] T062 [US5] Update `print_review_instructions()` to show counts: `N reviewed, N inherited, N reviewed-no-prior` and remove "skipped (already reviewed)" messaging (FR-010) in
  `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T063 [US5] Update tests for `print_review_instructions()` in `review_prompts.py` to verify `processingPath` counts are shown and skip-oriented output is removed (FR-010) in
  `tests/unit/cli/azure_devops/review_prompts/test_print_review_instructions.py`
- [ ] T064 [US5] Update `print_review_instructions()` in `agentic_devtools/cli/azure_devops/review_prompts.py` to show `processingPath` counts and remove "skipped (already reviewed)" messaging (FR-010)
- [ ] T065 [US5] Write tests verifying `derive_overall_status()` in `status_cascade.py` includes inherited file statuses in aggregation (FR-010) in `tests/unit/cli/azure_devops/status_cascade/test_derive_overall_status.py`
- [ ] T066 [US5] Ensure `derive_overall_status()` in `agentic_devtools/cli/azure_devops/status_cascade.py` includes inherited file statuses in aggregation (FR-010)
- [ ] T067 [US5] Write tests verifying output labels consistency across CLI and templates (NFR-002, SC-004) in `tests/unit/cli/azure_devops/review_templates/test_render_overall_summary.py`

## Phase 8: Polish & Cross-Cutting — Edge Cases, Performance, Integration

- [ ] T068 [P] Write test for deleted files: present in prior state but not current scope → not in output (FR-012, EC-003) in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T069 [P] Implement deleted file handling: files in prior state but not current scope excluded from output without error (FR-012, EC-003) in `agentic_devtools/cli/azure_devops/review_commands.py`
- [ ] T070 [US2] [P] Write test for file transition: previously inherited file now changed → full review with `processingPath = "reviewed"` (EC-006) in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T071 [US1] [P] Write test for first-run edge case: no prior state → all files `processingPath = "reviewed"` (EC-002) in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T072 [US2] Create integration test fixture with prior review history (changed + unchanged files) in `tests/fixtures/ci_events/review-all-files-prior-mixed.json`
- [ ] T073 [US1] Create integration test fixture with no prior state (first run) in `tests/fixtures/ci_events/review-all-files-first-run.json`
- [ ] T074 [US2] Create integration test fixture with multi-model verdicts in `tests/fixtures/ci_events/review-all-files-multi-model.json`
- [ ] T075 [US1] Write integration test validating SC-001: 100% of in-scope files in results in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T076 [US2] Write integration test validating SC-002: ≥95% unchanged files inherit expected status in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T077 [US2] Write integration test validating SC-003: 100% files without prior state processed without inheritance in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T078 [US5] Write integration test validating SC-004: 100% files have `processingPath` in output in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T079 [US1] Write performance regression test asserting ≤20% runtime increase vs baseline (NFR-001) in `tests/unit/cli/azure_devops/review_commands/test_generate_review_prompts.py`
- [ ] T080 [US1] Run full test suite with `agdt-test && agdt-task-wait` and fix any regressions
- [ ] T081 Update `agentic_devtools/cli/azure_devops/__init__.py` exports for new public functions (`is_valid_prior_state`, `can_inherit_file`, `can_inherit_multi_model`)

## Dependencies

```text
T001 → T002 → T003 → T004, T005
T006 → T009
T007 → T010
T008 → T011
T014 → T015 → T016 → T017, T018, T019, T020, T021, T022
T025 → T026 → T027 → T028
T009, T010, T026, T013 → T031 → T032 → T033, T034, T035, T036
T011, T032 → T039 → T040 → T041
T032, T043 → T044 → T045, T050 → T046 → T049, T051 → T052
T046 → T053, T054 → T055
T046 → T057, T058 → T059 → T060
T032 → T062, T063, T066 → T067
T061 → T062, T063 → T064
T065 → T066
T032 → T068, T069, T070, T071
T069 → T072, T073, T074 → T075, T076, T077, T078, T079 → T080
T014 → T024
T007 → T030
T046, T047 → T048
T004, T005 → T012 → T013
```

## FR Traceability Matrix

| FR | Tasks |
| --- | --- |
| FR-001 | T014, T016, T022, T023, T024 |
| FR-002 | T014–T021, T024 |
| FR-003 | T025–T028, T024 |
| FR-004 | T006, T009, T031, T030, T013 |
| FR-005 | T006–T011, T032, T033, T039, T030, T013 |
| FR-006 | T007, T010, T032, T038, T030 |
| FR-007 | T044–T049 |
| FR-008 | T044, T046, T047, T048, T051, T052, T056–T058 |
| FR-009 | T034, T057, T060 |
| FR-010 | T032, T061–T067 |
| FR-011 | T002, T003, T032, T035, T036, T030 |
| FR-012 | T068, T069 |

## Parallel Opportunities

- Phase 2 tests can be written in parallel: T006, T007, T008.
- Phase 3 cleanup tasks can be parallelized after T016 where independent: T018, T020, T021, T022.
- Phase 7 output updates can run in parallel once processing-path assignment exists: T062, T063, T066.
- Phase 8 fixture creation can run in parallel after deleted-file handling baseline: T072, T073, T074.

## Parallel Example

```bash
# After T016 is complete, run independent cleanup tasks in parallel:
Task: "Remove review_prompts skip path (T018)"
Task: "Remove async include_reviewed argument (T020)"
Task: "Deprecate build_reviewed_paths_set helper (T021)"
Task: "Update print_review_instructions signature (T022)"
```

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 and Phase 2 prerequisites.
2. Deliver Phase 3 so every in-scope file is always reviewed.
3. Validate with T023 and T024 before expanding scope.

### Incremental Delivery

1. Add inheritance behavior (Phase 4) and validate SC-002/SC-003 paths.
2. Add simplified scaffolding/prompt routing (Phases 5–6) with FR-008/FR-009 checks.
3. Finalize user-facing output and edge/performance coverage (Phases 7–8).

---
*Generated by Copilot SDK (claude-opus-4.6)*

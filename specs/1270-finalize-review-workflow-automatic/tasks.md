# Tasks: Finalize Review Workflow — Automatic PR Comment Repair/Finalization

## Task Markers

- `[P]` — Parallelizable: this task may run concurrently with other `[P]`-marked tasks in the same phase.
- `[USN]` — User story reference: traces the task to a specific user story.

## Phase 1: Setup

- [ ] T001 Create module directory `agentic_devtools/cli/azure_devops/finalization/` with `__init__.py`
- [ ] T002 [US1] Create test directories under `tests/unit/cli/azure_devops/finalization/` — one subfolder per source module
  (`models/`, `identity/`, `classification/`, `orchestrator/`, `convergence/`, `repair/`, `verification/`, `reporting/`) — with `__init__.py` at each level
- [ ] T003 Define data classes (`EligibleComment`, `EligibleComments`, `ConvergenceResult`, `BatchRepairResult`, `TargetedRepairResult`, `FinalizationReport`) in
  `agentic_devtools/cli/azure_devops/finalization/models.py`

## Phase 2: Foundational

- [ ] T004 Add `strip_marker_line(content: str) -> str` public helper to `agentic_devtools/cli/azure_devops/marker.py` using `parse_marker()` internally
- [ ] T005 [US3] Write tests for `strip_marker_line` in `tests/unit/cli/azure_devops/marker/test_strip_marker_line.py` (FR-012)
- [ ] T006 [US3] Audit existing `classify_agdt_threads()`, `parse_marker()`, `has_agdt_marker()`, `build_marker()` APIs for importability and completeness; record any gaps (FR-004, FR-012)

## Phase 3: User Story 1 — Automatic Finalization After Review Completion (P1) + User Story 2 — Safe Authorship Scoping (P1)

### Identity Resolution (FR-008, FR-009)

- [ ] T007 [US2] Write failing tests for `resolve_pat_identity()` in
  `tests/unit/cli/azure_devops/finalization/identity/test_resolve_pat_identity.py` — covers successful GUID return (FR-008), network failure
  returns None, insufficient data returns None (FR-009)
- [ ] T008 [US2] Implement `resolve_pat_identity(organization, headers) -> str | None` in `agentic_devtools/cli/azure_devops/finalization/identity.py` — calls `/_apis/connectionData`, returns
  `authenticatedUser.id` GUID (FR-008); returns None on failure so no mutations occur (FR-009)

### Comment Classification (FR-004, FR-005, FR-006, FR-007, FR-020)

- [ ] T009 [US2] Write failing tests for `classify_eligible_comments()` in `tests/unit/cli/azure_devops/finalization/classification/test_classify_eligible_comments.py` — covers: eligible
  file-summary/overall-summary/activity-log-entry detection (FR-004), authorship filtering (FR-005), skipping unclassified comments (FR-006), skipping other-author comments with reason (FR-007),
  activity-log session scoping (FR-020)
- [ ] T010 [US2] [P] Implement `classify_eligible_comments(threads, pat_user_id, review_state) -> EligibleComments` in `agentic_devtools/cli/azure_devops/finalization/classification.py` — uses
  `classify_agdt_threads()` + `parse_marker()` for FR-004/FR-012; filters by `author.id == pat_user_id` for FR-005; skips unclassified (FR-006) and other-author comments with skip reason (FR-007);
  scans thread replies for activity-log-entry markers with session-ID matching (FR-020)

### Orchestrator Shell (FR-001, FR-002, FR-019)

- [ ] T011 [US1] Write failing tests for `run_finalization_pass()` shell in
  `tests/unit/cli/azure_devops/finalization/orchestrator/test_run_finalization_pass.py` — covers: runs during completion step (FR-001),
  no new workflow state introduced (FR-002), missing review-state returns no-op success (FR-019), exception results in non-blocking failure
- [ ] T012 [US1] Implement `run_finalization_pass(review_state, pr_id, config, headers, dry_run) -> FinalizationReport` skeleton in
  `agentic_devtools/cli/azure_devops/finalization/orchestrator.py` — orchestrates phases 0–9 per design; catches exceptions for non-blocking
  behavior (FR-001, FR-002); handles missing/corrupt review-state as no-op (FR-019)

## Phase 4: User Story 3 — Batch-First Repair Strategy (P2)

### Convergence Computation (FR-012, FR-013, FR-014, FR-022, FR-023)

- [ ] T013 [US3] [P] Write failing tests for `compute_expected_content()` in
  `tests/unit/cli/azure_devops/finalization/convergence/test_compute_expected_content.py` — covers file-summary, overall-summary, and
  activity-log-entry rendering; verifies body-only output without marker line
- [ ] T014 [US3] [P] Write failing tests for `normalize_for_comparison()` in
  `tests/unit/cli/azure_devops/finalization/convergence/test_normalize_for_comparison.py` — covers stripping marker line, passthrough
  when no marker present
- [ ] T015 [US3] [P] Write failing tests for `check_convergence()` in `tests/unit/cli/azure_devops/finalization/convergence/test_check_convergence.py` — covers exact match (FR-013/FR-014 already-correct
  detection), mismatch detection, intermediate model-progress rows flagged as non-converged (FR-022), stale file links in overall summary flagged (FR-022), activity-log intermediate status flagged
  (FR-023); uses marker-based classification per FR-012
- [ ] T016 [US3] Implement `compute_expected_content(comment, review_state) -> str` in `agentic_devtools/cli/azure_devops/finalization/convergence.py` — dispatches to `render_file_summary()`,
  `render_overall_summary()`, or a wrapper around `_format_activity_log_entry(status_emoji, status_text, timestamp, model_name, short_hash, session_id, detail_message, sequence_number)` based on marker
  type; the wrapper supplies the required timestamp/model/hash/session/detail/sequence fields from review-state context and strips the leading marker line (since `_format_activity_log_entry` prepends
  the AGDT marker) to return body-only content (FR-012, FR-022, FR-023)
- [ ] T017 [US3] Implement `normalize_for_comparison(content: str) -> str` in `agentic_devtools/cli/azure_devops/finalization/convergence.py` — strips leading marker line using `strip_marker_line()`
  for convergence comparison (FR-012)
- [ ] T018 [US3] Implement `check_convergence(comment, expected) -> bool` in `agentic_devtools/cli/azure_devops/finalization/convergence.py` — compares normalized observed vs expected; returns True
  when content matches (FR-013 skip already-correct), False otherwise; satisfies FR-012 marker-based + rendered-content comparison, FR-014 unchanged counting, FR-022/FR-023 convergence definition

### Batch Repair (FR-003, FR-010, FR-021, FR-011)

- [ ] T019 [US3] Write failing tests for `batch_repair_pass()` in
  `tests/unit/cli/azure_devops/finalization/repair/test_batch_repair_pass.py` — covers: single cascade at end (FR-010), preserves file verdicts
  (FR-021), batch-only success path (FR-003 scenario 1), partial convergence triggers fallback signal (FR-003 scenario 2), activity-log repair via `_complete_active_session()` (FR-011), SystemExit
  caught as non-blocking failure
- [ ] T020 [US3] Implement `batch_repair_pass(eligible, review_state, config, headers, pr_id, dry_run) -> BatchRepairResult` in `agentic_devtools/cli/azure_devops/finalization/repair.py` — drives
  file-summary convergence through `submit_reviews()` (or its underlying parallel file-processing and single-cascade logic) per FR-003/FR-010, rather than PATCHing file-summary comments directly;
  single `execute_cascade()` at end (FR-010), preserves existing verdicts (FR-021), calls `_complete_active_session()` for activity-log (FR-011), catches SystemExit; content rendered from
  authoritative review-state to prevent drift (FR-011). Direct PATCH is reserved for targeted fallback only (FR-011)

## Phase 5: User Story 4 — Verified Convergence (P2)

### Verification and Targeted Fallback (FR-015, FR-016, FR-017)

- [ ] T021 [US4] [P] Write failing tests for `verify_convergence()` in
  `tests/unit/cli/azure_devops/finalization/verification/test_verify_convergence.py` — covers: all converged returns success (FR-016), partial
  convergence detected (FR-017), re-fetches from API not cache (FR-015)
- [ ] T022 [US4] [P] Write failing tests for `targeted_repair()` in
  `tests/unit/cli/azure_devops/finalization/repair/test_targeted_repair.py` — covers: only non-converged comments targeted (FR-003 scenario
  3), content rendered from authoritative state (FR-011), marker prepended before PATCH (FR-011), activity-log entries use `_update_activity_log_comment_status()` (FR-011)
- [ ] T023 [US4] Implement convergence re-fetch pass in `agentic_devtools/cli/azure_devops/finalization/verification.py` — exposes
  `verify_convergence(eligible, expected_map, config, headers, pr_id) -> list[ConvergenceResult]`; re-fetches individual comments via GET API (FR-015), compares against expected terminal content,
  returns per-comment convergence status; full convergence = success (FR-016), partial = partial success (FR-017)
- [ ] T024 [US4] Implement `targeted_repair(non_converged, expected_map, config, headers, pr_id, review_state, dry_run) -> TargetedRepairResult` in
  `agentic_devtools/cli/azure_devops/finalization/repair.py` — PATCHes only non-converged comments with `build_marker()` + rendered body (FR-011); uses `_update_activity_log_comment_status()` for
  activity-log entries (FR-011); only targets comments still non-converged after batch (FR-003)
- [ ] T025 [US4] Implement retry logic in orchestrator: up to 2 additional rounds, 5s fixed delay between rounds (NFR-001); each round targets only remaining non-converged comments; caps retry
  overhead at 10s total

## Phase 6: User Story 5 — Actionable Reporting (P3)

### Reporting (FR-018)

- [ ] T026 [US5] [P] Write failing tests for finalization-report assembly in `tests/unit/cli/azure_devops/finalization/reporting/test_build_finalization_report.py` — targets
  `build_finalization_report()`; covers: repaired/skipped/unchanged/failed counts (FR-018), distinguishes full/partial/no-op/failure status, dry-run report shows intended actions without mutations
- [ ] T027 [US5] Implement `build_finalization_report(status, repaired, skipped, unchanged, failed, details, duration_ms) -> FinalizationReport` in
  `agentic_devtools/cli/azure_devops/finalization/reporting.py` — structures output report (FR-018)
- [ ] T028 [US5] Implement report persistence: write JSON to `finalization-report-{commit_hash_short}.json` in workflow state directory and emit human-readable summary to stdout (FR-018)
- [ ] T029 [US5] Implement dry-run mode into orchestrator: when `dry_run=True`, run classification + convergence check, skip all mutations, report what would change (NFR-003, FR-018)

## Phase 7: Integration into Completion Step

- [ ] T030 [US1] Write/extend tests for completion-step integration in `tests/unit/cli/workflows/commands/test_advance_pull_request_review_workflow.py` — covers: finalization called after cascade
  (FR-001), no new workflow state (FR-002), decision re-derived after finalization, non-blocking on exception (NFR-002)
- [ ] T031 [US1] Modify `advance_pull_request_review_workflow()` in `agentic_devtools/cli/workflows/commands.py` to call `run_finalization_pass()` after `execute_cascade()` and before
  `save_review_state()` so post-finalization state is persisted in a single save; re-derive `decision` from post-finalization `overallSummary.status`; wrap in try/except for non-blocking behavior
  (FR-001, FR-002, NFR-002)
- [ ] T032 [US1] Wire `is_dry_run()` detection into the completion-step call to `run_finalization_pass()` (NFR-003)

## Phase 8: Polish & Cross-Cutting

- [ ] T033 Export public API from `agentic_devtools/cli/azure_devops/finalization/__init__.py` (`run_finalization_pass`, `FinalizationReport`)
- [ ] T034 Update `.github/copilot-instructions.md` — document finalization behavior, new module, and report file location
- [ ] T035 Update `CHANGELOG.md` with finalization feature entry
- [ ] T036 Run full PR checks (`bash scripts/run-pr-checks.sh`) and fix any failures
- [ ] T037 [US1] Verify idempotency: run completion step twice on same converged state, confirm no duplicate mutations and no-op report (NFR-004)
- [ ] T038 [US1] Verify 60-second timeout enforcement with simulated large PR (NFR-001)

## Dependency Graph

```text
T001 → T003, T004
T002 → T007, T009, T011, T013–T015, T019, T021–T022, T026
T003 → T008, T010, T012, T016–T018, T020, T023–T025, T027–T029
T004 → T005 → T017
T007 → T008
T008 → T010, T012
T009 → T010
T010 → T012, T020
T011 → T012
T012 → T025, T031
T013 → T016
T014 → T017
T015 → T018
T016–T018 → T020, T023
T019 → T020
T020 → T023, T025
T021 → T023
T022 → T024
T023–T024 → T025
T025 → T029, T031
T026 → T027
T027 → T028–T029
T029 → T031
T030 → T031
T031 → T032 → T033 → T034–T038
```

## FR Coverage Matrix

| FR | Tasks |
|---|---|
| FR-001 | T011, T012, T030, T031 |
| FR-002 | T011, T012, T030, T031 |
| FR-003 | T019, T020, T022, T024 |
| FR-004 | T006, T009, T010 |
| FR-005 | T009, T010 |
| FR-006 | T009, T010 |
| FR-007 | T009, T010 |
| FR-020 | T009, T010 |
| FR-008 | T007, T008 |
| FR-009 | T007, T008 |
| FR-010 | T019, T020 |
| FR-021 | T019, T020 |
| FR-011 | T019, T020, T022, T024 |
| FR-012 | T005, T006, T010, T015, T016, T017, T018 |
| FR-013 | T015, T018 |
| FR-014 | T015, T018 |
| FR-015 | T021, T023 |
| FR-022 | T013, T015, T016 |
| FR-023 | T013, T015, T016 |
| FR-016 | T021, T023 |
| FR-017 | T021, T023 |
| FR-018 | T026, T027, T028, T029 |
| FR-019 | T011, T012 |

---
*Generated by Copilot SDK (claude-opus-4.6)*

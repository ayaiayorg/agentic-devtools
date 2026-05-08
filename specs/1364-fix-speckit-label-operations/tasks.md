# Tasks: SpecKit Label Operations Token Fix

**Feature Branch**: `speckit/1364/phase-4-tasks`
**Source Issue**: [#1364](https://github.com/ayaiayorg/agentic-devtools/issues/1364)

---

## Phase 1: Setup

- [ ] T001 Read and understand current label operation code in `.github/scripts/speckit-trigger/create-spec-pr.sh` (lines 572–605)
- [ ] T002 Read and understand existing retry library in `.github/scripts/speckit-trigger/lib/retry.sh`
- [ ] T003 Read and understand workflow env blocks in `.github/workflows/speckit-issue-trigger.yml` (line ~326) and `.github/workflows/speckit-phase-progression.yml` (line ~541)
- [ ] T004 [US1] Create test file scaffold at `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

---

## Phase 2: Foundational — Token Resolution & Retry Infrastructure

- [ ] T005 Add `LABEL_TOKEN` documentation to script header comment in `.github/scripts/speckit-trigger/create-spec-pr.sh` (line 27 `Environment:` block)
- [ ] T006 Add effective label token resolution block after `GH_TOKEN` validation (after line 129) in `.github/scripts/speckit-trigger/create-spec-pr.sh` — resolve `LABEL_TOKEN` with `GH_TOKEN`
  fallback and warning (FR-001, FR-010)
- [ ] T007 Add `_is_transient_label_error` helper function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — classify HTTP errors as transient (429, 500, 502, 503, 504) vs. non-transient
  (FR-005, FR-006)
- [ ] T008 Add `_log_label_error` helper function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — structured error logging with operation, HTTP status, and remediation advice per NFR-002
  (FR-004)

---

## Phase 3: User Story 1 — Labels Applied Successfully (P1)

### Tests

- [ ] T009 [US1] Write test: token resolution uses `LABEL_TOKEN` when set (FR-001, happy-path) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T010 [US1] Write test: token resolution falls back to `GH_TOKEN` with warning when `LABEL_TOKEN` unset (FR-001, FR-010, happy-path) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T011 [US1] Write test: label deduplication removes duplicates from combined label list (FR-008) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T012 [US1] Write test: batch comma-separated label string construction (FR-007) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T013 [US1] Write test: `gh label create --force` is called per-label using effective token (FR-001, FR-008, happy-path) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T014 [US1] Write test: `gh pr edit --add-label` batch call uses comma-separated labels (FR-007, happy-path) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T069 [US1] Write test: workflow env passes `LABEL_TOKEN` to label operation functions (FR-002, happy-path) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

### Implementation

- [ ] T015 Add `_create_label_with_retry` function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — wraps `gh label create --force` with `EFFECTIVE_LABEL_TOKEN`, uses `call_with_retry` and
  `_RETRY_ABORT_CODE` for non-transient errors (FR-001, FR-005, FR-008)
- [ ] T016 Add `_apply_labels_batch_with_retry` function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — wraps `gh pr edit --add-label` with comma-separated labels, retry, and
  `EFFECTIVE_LABEL_TOKEN` (FR-005, FR-007)
- [ ] T017 Add `_apply_label_single_with_retry` function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — wraps single `gh pr edit --add-label` for individual fallback (FR-007)
- [ ] T018 Add `_apply_all_labels` orchestrator function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — deduplicates labels, ensures existence via `_create_label_with_retry`, batch applies
  via `_apply_labels_batch_with_retry`, falls back to individual on batch failure (FR-007, FR-008)
- [ ] T019 Replace current label application block (lines 572–605) with call to `_apply_all_labels` in `.github/scripts/speckit-trigger/create-spec-pr.sh` — combine source issue labels + phase/speckit
  label into unified flow (FR-001, FR-007, FR-008, FR-011)

### Workflow YAML

- [ ] T020 [P] [US1] Add `LABEL_TOKEN: ${{ secrets.GITHUB_TOKEN }}` to the `env:` block of the "Create Pull Request" step in `.github/workflows/speckit-issue-trigger.yml` (FR-002)
- [ ] T021 [P] [US1] Add `LABEL_TOKEN: ${{ secrets.GITHUB_TOKEN }}` to the `env:` block of the "Create Pull Request" step in `.github/workflows/speckit-phase-progression.yml` (FR-002)
- [ ] T022 [P] [US1] Add inline YAML comment explaining `LABEL_TOKEN` vs. `GH_TOKEN` purpose in `.github/workflows/speckit-issue-trigger.yml`
- [ ] T023 [P] [US1] Add inline YAML comment explaining `LABEL_TOKEN` vs. `GH_TOKEN` purpose in `.github/workflows/speckit-phase-progression.yml`

---

## Phase 4: User Story 2 — Actionable Error Diagnostics (P1)

### Tests

- [ ] T024 [US2] Write test: `_log_label_error` outputs structured message with operation, label, stderr content (FR-004, happy-path) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T025 [US2] Write test: `_log_label_error` includes 403 remediation advice (FR-004) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T026 [US2] Write test: `_log_label_error` includes 404 remediation advice (FR-004) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T027 [US2] Write test: `_log_label_error` includes 422 remediation advice (FR-004) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T028 [US2] Write test: `2>/dev/null` is not present on any `gh label` or `gh pr edit --add-label` call (FR-003) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T070 [US2] Write test: stderr from failed label operation is captured and visible in log output (FR-003, happy-path) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

### Implementation

- [ ] T029 [US2] Remove all `2>/dev/null` redirections from label operations in `.github/scripts/speckit-trigger/create-spec-pr.sh` — 7 locations identified in lines 577, 583, 584, 595, 596, 601, 602
  (FR-003)
- [ ] T030 [US2] Integrate `_log_label_error` calls into `_create_label_with_retry` and `_apply_labels_batch_with_retry` failure paths in `.github/scripts/speckit-trigger/create-spec-pr.sh` (FR-004)

---

## Phase 5: User Story 3 — Resilient Retry Logic (P2)

### Tests

- [ ] T031 [US3] Write test: `_is_transient_label_error` returns 0 (true) for 502 stderr (FR-005) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T032 [US3] Write test: `_is_transient_label_error` returns 0 (true) for 429 stderr (FR-005) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T033 [US3] Write test: `_is_transient_label_error` returns 1 (false) for 403 stderr (FR-006) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T034 [US3] Write test: `_is_transient_label_error` returns 1 (false) for 422 stderr (FR-006) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T035 [US3] Write test: `_create_label_with_retry` retries on transient error and succeeds on 2nd attempt (FR-005, happy-path) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T036 [US3] Write test: `_create_label_with_retry` does NOT retry on 403 non-transient error (FR-006, happy-path) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T037 [US3] Write test: `_create_label_with_retry` logs all attempt details when retries exhausted (FR-005) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T038 [US3] Write test: retry uses exponential backoff with 2s initial delay (2s, 4s) (FR-005) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

### Implementation

- [ ] T039 [US3] Wire `_is_transient_label_error` into `_create_label_with_retry` to return `_RETRY_ABORT_CODE` for non-transient errors in `.github/scripts/speckit-trigger/create-spec-pr.sh` (FR-005,
  FR-006)
- [ ] T040 [US3] Wire `_is_transient_label_error` into `_apply_labels_batch_with_retry` to return `_RETRY_ABORT_CODE` for non-transient errors in `.github/scripts/speckit-trigger/create-spec-pr.sh`
  (FR-005, FR-006)
- [ ] T041 [US3] Configure retry parameters: `max_attempts=3`, `initial_delay=2` for all label operations in `.github/scripts/speckit-trigger/create-spec-pr.sh` (NFR-003)

---

## Phase 6: User Story 4 — Batch Label Application (P2)

### Tests

- [ ] T042 [US4] Write test: batch call constructs correct comma-separated label string from 3 labels (FR-007) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T043 [US4] Write test: batch failure triggers individual fallback for each label (FR-007) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T044 [US4] Write test: individual fallback identifies which specific label failed (FR-007) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T045 [US4] Write test: all labels exist (created via `--force`) before batch apply is attempted (FR-008) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

### Implementation

- [ ] T046 [US4] Implement batch-then-fallback logic in `_apply_all_labels` in `.github/scripts/speckit-trigger/create-spec-pr.sh` — single `gh pr edit --add-label` call, fallback to per-label on
  failure (FR-007)
- [ ] T047 [US4] Add label existence loop (per-label `gh label create --force`) before batch apply in `_apply_all_labels` in `.github/scripts/speckit-trigger/create-spec-pr.sh` (FR-008)

---

## Phase 7: User Story 5 — Early Token Permission Validation (P3)

### Tests

- [ ] T048 [US5] Write test: `_preflight_label_token` passes silently with valid token (FR-009, happy-path) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T049 [US5] Write test: `_preflight_label_token` returns 1 (hard fail) on 401/403 auth error (FR-009) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T050 [US5] Write test: `_preflight_label_token` returns 0 (soft fail) on transient/network error (FR-009) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T051 [US5] Write test: preflight failure exits script with non-zero code while still outputting PR results (FR-009) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T052 [US5] Write test: preflight uses effective token (not raw `LABEL_TOKEN`) after fallback resolution (FR-009, FR-010) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

### Implementation

- [ ] T053 [US5] Add `_preflight_label_token` function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — calls `gh label list --limit 1` with `EFFECTIVE_LABEL_TOKEN`, classifies auth vs.
  transient errors (FR-009)
- [ ] T054 [US5] Add preflight invocation before label operations in `.github/scripts/speckit-trigger/create-spec-pr.sh` — on hard failure, output PR results and exit 1 (FR-009)
- [ ] T055 [US5] Ensure preflight runs after token resolution (FR-010 fallback applied first) in `.github/scripts/speckit-trigger/create-spec-pr.sh` (FR-009, FR-010)

---

## Phase 8: Polish & Cross-Cutting

### Edge Cases

- [ ] T056 Add label deduplication via `jq -r '.[]' | sort -u` for `LABELS_JSON` input in `.github/scripts/speckit-trigger/create-spec-pr.sh`
- [ ] T057 [US1] Write test: duplicate labels in `LABELS_JSON` are deduplicated before application (FR-008) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T058 [US1] Write test: labels with special characters (colons, spaces) are properly quoted (FR-007) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T059 [US1] Write test: empty `LABEL_TOKEN` (set but empty string) falls back to `GH_TOKEN` (FR-001, FR-010) in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T060 Add elapsed-time short-circuit to `_apply_all_labels` — skip remaining retries if cumulative time exceeds 45s (NFR-001)

### Integration Verification

- [ ] T061 [US3] Verify existing test `test_retry_lib.sh` still passes after changes by running `.github/scripts/speckit-trigger/tests/test_retry_lib.sh`
- [ ] T062 [US1] Run full test suite `test_label_operations.sh` end-to-end to verify all label operation tests pass (FR-011)
- [ ] T063 [US1] Verify `create-spec-pr.sh` preserves all non-label functionality (PR creation, branch management, artifact linking) unchanged (FR-011, happy-path)
- [ ] T064 [US1] Verify `GH_TOKEN` is NOT modified for `gh pr create` calls — only label operations use `EFFECTIVE_LABEL_TOKEN` (FR-011)

### Documentation

- [ ] T065 [P] Verify `create-spec-pr.sh` header comment (line 27) documents `LABEL_TOKEN` environment variable (added in T005)
- [ ] T066 [P] [US1] Verify both workflow YAML files have consistent `LABEL_TOKEN` env variable configuration (FR-002)

### Final Validation

- [ ] T067 [US1] Run `bash scripts/run-pr-checks.sh` to verify all CI checks pass (FR-011)
- [ ] T068 Run `ruff check --fix . && ruff format .` for any Python files touched (if applicable)

---

## Dependency Graph

```text
T001–T004 (Setup) → T005–T008 (Foundational)
T006 → T015–T019 (token resolution needed by all label functions)
T007 → T039, T040 (transient error classifier needed by retry wiring)
T008 → T030 (error logger needed by integration)
T015–T018 → T019 (helper functions needed before orchestrator replacement)
T019 → T029 (replacement removes old code including 2>/dev/null)
T020, T021 → T069 (workflow LABEL_TOKEN env needed for integration test)
T029 → T070 (stderr capture requires 2>/dev/null removal)
T020, T021 → T053–T055 (workflow LABEL_TOKEN needed for preflight to work)
T039, T040 → T046, T047 (retry wiring needed before batch logic)
T046, T047 → T053, T054 (batch logic needed before preflight gate)
T061–T064 → T067 (integration checks before final PR checks)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*

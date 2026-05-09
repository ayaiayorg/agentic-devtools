# Tasks: SpecKit Label Operations Token Fix

**Feature Branch**: `speckit/1364/phase-4-tasks`
**Source Issue**: [#1364](https://github.com/ayaiayorg/agentic-devtools/issues/1364)

---

## Phase 1: Setup & Scaffolding

- [ ] T001 Verify `lib/retry.sh` is sourced in `create-spec-pr.sh` — already present at line 37
  (`source "$SCRIPT_DIR/lib/retry.sh"`); confirm no additional sourcing is needed after `GH_TOKEN` validation
- [ ] T002 Create test file `.github/scripts/speckit-trigger/tests/test_label_operations.sh` with test harness boilerplate (shebang, sourcing helpers, test counter, pass/fail reporter)

---

## Phase 2: Foundational — Token Resolution & Error Infrastructure

- [ ] T003 Add `LABEL_TOKEN` documentation to the script header comment (line 27) in `.github/scripts/speckit-trigger/create-spec-pr.sh` — document the `LABEL_TOKEN` environment variable alongside
  `GH_TOKEN`
- [ ] T004 Add effective label token resolution block after line 129 in `.github/scripts/speckit-trigger/create-spec-pr.sh` — resolve `EFFECTIVE_LABEL_TOKEN` from `LABEL_TOKEN` with fallback to
  `GH_TOKEN` and logged warning (FR-001, FR-010)
- [ ] T005 Add `_is_transient_label_error` function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — classify stderr output as transient (429, 500, 502, 503, 504) vs non-transient (FR-005,
  FR-006)
- [ ] T006 Add `_log_label_error` function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — structured error logging with operation, label, stderr output, and remediation hint per NFR-002
  (FR-004)
- [ ] T007 Write unit test for token resolution: `LABEL_TOKEN` set → used as effective token, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T008 Write unit test for token resolution: `LABEL_TOKEN` unset → falls back to `GH_TOKEN` with warning on stderr, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T009 Write unit test for `_is_transient_label_error`: returns 0 for 502/429/500/503/504 stderr patterns, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T010 Write unit test for `_is_transient_label_error`: returns 1 for 401/403/404/422 stderr patterns, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T011 Write unit test for `_log_label_error`: verify output includes operation, label name, stderr content, and correct remediation for 403/404/422, in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

---

## Phase 3: User Story 1 — Labels Applied Successfully (P1)

> **Covers**: FR-001, FR-002, FR-007, FR-008, FR-011

### Tests

- [ ] T012 [US1] Write test: label deduplication removes duplicate entries from combined label list, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T013 [US1] Write test: batch comma-separated label string is constructed correctly from deduplicated list, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T014 [US1] Write test: `_create_label_with_retry` calls `gh label create --force` with `EFFECTIVE_LABEL_TOKEN` (mock `gh`), in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T015 [US1] Write test: `_apply_labels_batch` calls `gh pr edit --add-label` with comma-separated labels using `EFFECTIVE_LABEL_TOKEN`, in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T016 [US1] Write test: batch failure triggers individual fallback — each label applied separately, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T017 [US1] Write test: existing labels are reused (gh label create --force is idempotent), in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T018 [US1] Write test: phase label (`speckit:phase-N`) is included in the combined label set, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T019 [US1] Write test: when no phase number, `speckit:spec` label is included in the combined label set, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

### Implementation

- [ ] T020 [US1] Add `_deduplicate_labels` function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — takes newline-separated labels, outputs sorted unique list via `sort -u`
- [ ] T021 [US1] Add `_create_label_with_retry` function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — wraps `gh label create --force` using `EFFECTIVE_LABEL_TOKEN`, returns
  `_RETRY_ABORT_CODE` for non-transient errors (FR-005, FR-006, FR-008)
- [ ] T022 [US1] Add `_apply_labels_batch` function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — single `gh pr edit --add-label` with comma-separated labels using `EFFECTIVE_LABEL_TOKEN`
  and retry (FR-007)
- [ ] T023 [US1] Add `_apply_label_individually` function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — single-label `gh pr edit --add-label` with retry, used as fallback (FR-007)
- [ ] T024 [US1] Add `_apply_all_labels` orchestrator function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — collects source + phase labels, deduplicates, ensures existence, batch applies
  with individual fallback (FR-007, FR-008)
- [ ] T025 [US1] Replace lines 572–605 in `.github/scripts/speckit-trigger/create-spec-pr.sh` — remove old per-label loop and phase label block, call `_apply_all_labels` instead (FR-011)

### Workflow YAML

- [ ] T026 [P] [US1] Add `LABEL_TOKEN: ${{ secrets.GITHUB_TOKEN }}` to the `env:` block of the "Create Pull Request" step in `.github/workflows/speckit-issue-trigger.yml` (line ~327) (FR-002)
- [ ] T027 [P] [US1] Add `LABEL_TOKEN: ${{ secrets.GITHUB_TOKEN }}` to the `env:` block of the "Create Pull Request" step in `.github/workflows/speckit-phase-progression.yml` (line ~542) (FR-002)
- [ ] T028 [P] [US1] Add inline YAML comment in `.github/workflows/speckit-issue-trigger.yml` explaining `LABEL_TOKEN` vs `GH_TOKEN` purpose
- [ ] T029 [P] [US1] Add inline YAML comment in `.github/workflows/speckit-phase-progression.yml` explaining `LABEL_TOKEN` vs `GH_TOKEN` purpose

### Integration

- [ ] T030 [US1] Write integration test: end-to-end `_apply_all_labels` with mocked `gh` — verifies source labels + phase label are all applied via batch call, in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T031 [US1] Write test: PR creation output (`pr_url`, `pr_number`) still emitted after label operations complete (FR-011 preservation), in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

---

## Phase 4: User Story 2 — Actionable Error Diagnostics (P1)

> **Covers**: FR-003, FR-004

### Tests

- [ ] T032 [US2] Write test: `_create_label_with_retry` does NOT suppress stderr — verify stderr contains `gh` error output when label create fails, in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T033 [US2] Write test: `_apply_labels_batch` does NOT suppress stderr — verify stderr contains `gh` error output when `gh pr edit` fails, in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T034 [US2] Write test: 403 error produces remediation message "Ensure LABEL_TOKEN uses GITHUB_TOKEN with permissions: issues: write", in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T035 [US2] Write test: 404 error produces remediation message "Verify the repository and PR number are correct", in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T036 [US2] Write test: 422 error produces remediation message "Check that the label name is valid and not a duplicate", in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

### Implementation

- [ ] T037 [US2] Remove all `2>/dev/null` redirections from label operations in `.github/scripts/speckit-trigger/create-spec-pr.sh` (FR-003): 6 `gh` command locations (lines 583, 584, 595,
  596, 601, 602) and 1 `jq` location (line 577 — `jq -r '.[]' 2>/dev/null` hides JSON parsing errors, also within FR-003 scope) — already handled by T025 replacement, verify no residual
  suppressions remain
- [ ] T038 [US2] Integrate `_log_label_error` calls into `_create_label_with_retry` and `_apply_label_individually` failure paths in `.github/scripts/speckit-trigger/create-spec-pr.sh` (FR-004)

---

## Phase 5: User Story 3 — Resilient Retry Logic (P2)

> **Covers**: FR-005, FR-006

### Tests

- [ ] T039 [US3] Write test: `_create_label_with_retry` retries on 502 error up to 2 additional times (3 total attempts), in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T040 [US3] Write test: `_create_label_with_retry` does NOT retry on 403 error (returns `_RETRY_ABORT_CODE`), in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T041 [US3] Write test: `_apply_labels_batch` retries on 429 rate limit error, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T042 [US3] Write test: retry backoff uses 2s initial delay with exponential growth (verify `calculate_backoff_delay` values: 2, 4), in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T043 [US3] Write test: after all retries exhausted, failure is logged with attempt details and script continues with remaining labels, in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

### Implementation

- [ ] T044 [US3] Wire `call_with_retry 3 2` (3 attempts, 2s initial delay) into `_create_label_with_retry` in `.github/scripts/speckit-trigger/create-spec-pr.sh` (FR-005, NFR-003)
- [ ] T045 [US3] Wire `call_with_retry 3 2` into `_apply_labels_batch` and `_apply_label_individually` in `.github/scripts/speckit-trigger/create-spec-pr.sh` (FR-005, NFR-003)
- [ ] T046 [US3] Add non-transient error detection in retry wrappers — return `_RETRY_ABORT_CODE` (99) for 401/403/404/422 to skip retries (FR-006)
- [ ] T047 [US3] Add elapsed wall-clock time tracking in `_apply_all_labels` — skip remaining retries if cumulative time exceeds 45s (NFR-001 safety cap)

---

## Phase 6: User Story 4 — Batch Label Application (P2)

> **Covers**: FR-007, FR-008

### Tests

- [ ] T048 [US4] Write test: 3+ labels produce a single `gh pr edit --add-label "label1,label2,label3"` call (verify mock `gh` call count), in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T049 [US4] Write test: all labels ensured via per-label `gh label create --force` before batch apply, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T050 [US4] Write test: batch failure triggers individual fallback — verify each label gets its own separate
  `gh pr edit --add-label` call (assert mock `gh` call count equals label count, distinct from T016 which tests
  the fallback trigger at the orchestrator level without verifying per-label call isolation), in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T051 [US4] Write test: individual fallback identifies which specific label failed, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

### Verification

- [ ] T052 [US4] Verify `_apply_all_labels` constructs comma-separated label CSV and passes to `_apply_labels_batch` in `.github/scripts/speckit-trigger/create-spec-pr.sh` — already implemented in
  T024, validate behavior (FR-007)
- [ ] T053 [US4] Verify individual fallback path in `_apply_all_labels` logs which labels failed and which succeeded in `.github/scripts/speckit-trigger/create-spec-pr.sh` (FR-007)

---

## Phase 7: User Story 5 — Early Token Validation (P3)

> **Covers**: FR-009, FR-010

### Tests

- [ ] T054 [US5] Write test: preflight `gh label list --limit 1` succeeds → label operations proceed silently, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T055 [US5] Write test: preflight returns 401 → script exits with non-zero code and clear error message, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T056 [US5] Write test: preflight returns 403 → script exits with non-zero code and remediation hint, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T057 [US5] Write test: preflight returns 5xx/network error → warning logged, label operations proceed, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T058 [US5] Write test: `LABEL_TOKEN` unset → fallback applied before preflight, preflight uses `GH_TOKEN` (no exit on unset), in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`

### Implementation

- [ ] T059 [US5] Add `_preflight_label_token` function in `.github/scripts/speckit-trigger/create-spec-pr.sh` — runs `gh label list --limit 1` with `EFFECTIVE_LABEL_TOKEN`, exits on 401/403, warns on
  transient/network errors (FR-009)
- [ ] T060 [US5] Call `_preflight_label_token` before `_apply_all_labels` in `.github/scripts/speckit-trigger/create-spec-pr.sh` — on hard failure, still output `pr_url`/`pr_number` then exit 1
  (FR-009)
- [ ] T061 [US5] Verify preflight runs after token resolution (T004) so `LABEL_TOKEN` unset scenario uses fallback `GH_TOKEN` (FR-009, FR-010 interaction)

---

## Phase 8: Polish & Cross-Cutting

- [ ] T062 Write integration test: full label flow end-to-end with mocked `gh` — PR created, preflight passes, labels created, batch applied, output emitted (FR-011 regression), in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T063 Write integration test: verify non-label operations (`gh pr create`) still use `GH_TOKEN` not `EFFECTIVE_LABEL_TOKEN` (FR-011), in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T064 Write integration test: verify PR creation output (`pr_url`, `pr_number`) is preserved when label operations fail entirely (FR-011), in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T065 Write test: labels with special characters (colons, spaces) are properly quoted in shell arguments, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T066 Write test: empty `LABELS_JSON` (`[]`) produces only the phase/spec label — no errors, in `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T067 Write test: duplicate labels within the `LABELS_JSON` input array itself are deduplicated before
  application (distinct from T012 which tests deduplication of the combined source + phase label list;
  T067 targets the upstream parsing path where `LABELS_JSON` contains repeated entries), in
  `.github/scripts/speckit-trigger/tests/test_label_operations.sh`
- [ ] T068 Run existing SpecKit tests (`test_retry_lib.sh`, `test_check_analysis_gate.sh`, `test_content_preservation.sh`, etc.) to verify no regressions — all must pass
- [ ] T069 Verify `.github/workflows/speckit-issue-trigger.yml` diff is minimal — only `LABEL_TOKEN` env addition and comment (FR-002 scope check)
- [ ] T070 Verify `.github/workflows/speckit-phase-progression.yml` diff is minimal — only `LABEL_TOKEN` env addition and comment (FR-002 scope check)
- [ ] T071 Run shellcheck on `.github/scripts/speckit-trigger/create-spec-pr.sh` and fix any warnings introduced by the changes
- [ ] T072 Run shellcheck on `.github/scripts/speckit-trigger/tests/test_label_operations.sh` and fix any warnings

---

## Dependency Graph

```text
T001 ──► T004 ──► T005, T006
T002 ──► T007–T011 (foundational tests)
T004 ──► T020–T025 (US1 implementation)
T005, T006 ──► T021, T022, T023 (retry + error wrappers)
T020–T024 ──► T025 (integration point — replaces old code)
T025 ──► T037 (2>/dev/null removal verification)
T025 ──► T030, T031 (US1 integration tests)
T026, T027 ──► T069, T070 (YAML verification)
T021, T022 ──► T044, T045 (retry wiring)
T044, T045 ──► T046, T047 (abort codes + time cap)
T024 ──► T052, T053 (batch verification)
T004 ──► T059, T060 (preflight depends on token resolution)
T059, T060 ──► T061 (preflight interaction verification)
T025, T059 ──► T062–T064 (integration tests depend on full impl)
T068–T072 ──► (final validation, depends on all implementation tasks)
```

## Requirements Coverage Matrix

| Requirement | Tasks |
| --- | --- |
| FR-001 | T004, T021, T022, T023, T024, T025 |
| FR-002 | T026, T027, T028, T029, T069, T070 |
| FR-003 | T025, T032, T033, T037 |
| FR-004 | T006, T011, T034, T035, T036, T038 |
| FR-005 | T005, T021, T022, T039, T041, T044, T045 |
| FR-006 | T005, T010, T040, T046 |
| FR-007 | T015, T016, T022, T023, T024, T048, T050, T052 |
| FR-008 | T014, T021, T024, T049 |
| FR-009 | T054, T055, T056, T057, T059, T060, T061 |
| FR-010 | T004, T008, T058, T061 |
| FR-011 | T025, T031, T062, T063, T064 |
| NFR-001 | T047 |
| NFR-002 | T006, T011, T034, T035, T036 |
| NFR-003 | T042, T044, T045 |
| NFR-004 | T026, T027 (uses `secrets.GITHUB_TOKEN`, no new secrets) |
| NFR-005 | T025, T026, T027 (same script, env-only YAML changes) |

---
*Generated by Copilot SDK (claude-opus-4.6)*

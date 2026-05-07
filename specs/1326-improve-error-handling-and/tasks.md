# Tasks: Resilient Error Handling and Retry Logic for SpecKit Pipeline Scripts

**Feature Branch**: `speckit/1326/phase-4-tasks`
**Source Issue**: [#1326](https://github.com/ayaiayorg/agentic-devtools/issues/1326)

---

## Phase 1: Setup

- [ ] T001 Create directory structure `.github/scripts/speckit-trigger/lib/`
- [ ] T002 Create empty `lib/retry.sh` file with shebang, header comment, and sourcing guard at `.github/scripts/speckit-trigger/lib/retry.sh`
- [ ] T003 [US1] Create test directory `.github/scripts/speckit-trigger/tests/` for new test scripts and update CI runner/harness to discover and execute scripts in this subdirectory (FR-012)

---

## Phase 2: Foundational — Shared Retry Library

- [ ] T004 Implement `calculate_backoff_delay` function in `lib/retry.sh` — accepts retry_number (1-based) and initial_delay, outputs `initial_delay × 2^(retry_number-1)` to stdout (FR-007)
- [ ] T005 Implement `call_with_retry` function in `lib/retry.sh` — accepts max_attempts, initial_delay, command; uses `calculate_backoff_delay` internally; logs attempt/total/delay per FR-009; logs
  command name and exit code per FR-010; returns 0 on success, 1 on exhaustion (FR-007)
- [ ] T006 Add `BASH_SOURCE[0]`-relative path resolution pattern in `lib/retry.sh` header comment as usage example for consuming scripts (FR-007)
- [ ] T007 [US3] Verify `lib/retry.sh` is compatible with Bash 4.x+ and `set -euo pipefail` (NFR-004)

---

## Phase 3: User Story 1 — PR Creation Failure Surfaces as Failed Step (P1)

- [ ] T008 [US1] Write test script `tests/test_create_spec_pr_retry.sh` — stub `gh` to simulate transient failures, non-retryable patterns, exit code 127, and "already exists" scenarios; include
  happy-path test (successful `gh pr create` on first attempt returns PR URL); verify exit codes and GITHUB_OUTPUT content (FR-001, FR-002, FR-012)
- [ ] T009 [US1] Add `source` statement in `create-spec-pr.sh` to load `lib/retry.sh` via `BASH_SOURCE[0]`-relative path (FR-012)
- [ ] T010 [US1] Implement non-retryable pattern detection function `_is_non_retryable` in `create-spec-pr.sh` — checks exit code 127 and greps stderr for "not found", "does not exist", "permission
  denied", "authentication", "command not found" (FR-002)
- [ ] T011 [US1] Implement wrapper function `_create_pr_with_retry` in `create-spec-pr.sh` — captures stdout+stderr from `gh pr create`, applies `_is_non_retryable` check, returns appropriate exit
  code for `call_with_retry` (FR-001, FR-002, FR-012)
- [ ] T012 [US1] Replace direct `gh pr create` call (line 371) with `call_with_retry 3 5 _create_pr_with_retry` — ensure non-zero exit propagates when all retries exhausted (FR-001, FR-012)
- [ ] T013 [US1] Implement "already exists" recovery path (FR-013) — detect pattern in stderr, attempt `gh pr list --head <branch> --json url,number --jq '.[0]'` wrapped in `call_with_retry`, treat
  empty output as failure to force retries
- [ ] T014 [US1] Ensure empty `pr_url=` and `pr_number=` are written to `GITHUB_OUTPUT` on all failure paths including recovery failure (NFR-005)
- [ ] T015 [US1] Preserve `GITHUB_OUTPUT` fallback to `/dev/stdout` for local testing (NFR-005)
- [ ] T016 [US1] Verify structural acceptance scenario US1-S7 — `create-spec-pr.sh` sources lib, does not define own `call_with_retry`, invokes it wrapping `gh pr create`

---

## Phase 4: User Story 2 — Issue Comment HTTP Validation and Retry (P1)

- [ ] T017 [US2] Write test script `tests/test_post_issue_comment_retry.sh` — mock HTTP endpoint for 201 (happy-path: successful POST returns 201 Created), 5xx, 429, 403±Retry-After, 4xx,
  transport errors (exit codes 6,7,28,35,52,56), redirects (301/302/303), and non-retryable transport errors (exit code 3, 60) (FR-003, FR-005, FR-006)
- [ ] T018 [US2] Add `source` statement in `post-issue-comment.sh` to load `lib/retry.sh` via `BASH_SOURCE[0]`-relative path
- [ ] T019 [US2] Implement `curl_with_retry` function in `post-issue-comment.sh` — uses `curl -s -o <tmpfile> -D <headerfile> -w '%{http_code}' -L --post301 --post302 --post303` to capture
  HTTP status, body, and response headers separately; headers captured via `-D <headerfile>` for deterministic `Retry-After` parsing in T022 (FR-003, FR-011)
- [ ] T020 [US2] Implement HTTP status classification in `curl_with_retry` — 2xx=success, 5xx=retryable, 429=retryable with Retry-After, 403+Retry-After=retryable, 403 without=fail, other 4xx=fail
  (FR-005, FR-006)
- [ ] T021 [US2] Implement transport error classification in `curl_with_retry` — retryable codes: 6,7,28,35,52,56; all other non-zero=immediate failure (FR-005)
- [ ] T022 [US2] Implement `Retry-After` header parsing in `curl_with_retry` — use `max(Retry-After, calculated_backoff)`; fail immediately if `Retry-After > 60` (FR-006, NFR-002)
- [ ] T023 [US2] Integrate `calculate_backoff_delay` from shared library into `curl_with_retry` delay computation (FR-005)
- [ ] T024 [US2] Add retry observability logging in `curl_with_retry` — log attempt/total/delay/command/status to stderr (FR-009, FR-010)
- [ ] T025 [US2] Replace bare `curl -s` call (line 69-73) with `curl_with_retry` invocation; ensure non-zero exit on persistent failure (FR-003, FR-004)
- [ ] T026 [US2] Verify structural acceptance scenario US2-S17 — `post-issue-comment.sh` sources lib, does not define own `calculate_backoff_delay`, uses it inside `curl_with_retry`

---

## Phase 5: User Story 3 — Shared Retry Helper Library (P2)

- [ ] T027 [US3] Write test script `tests/test_retry_lib.sh` — test `calculate_backoff_delay` arithmetic (retry 1 → 5, retry 2 → 10), `call_with_retry` success after failures, exhaustion, enhanced
  error messages with command name/exit code (FR-007, FR-008)
- [ ] T028 [US3] Test `BASH_SOURCE[0]`-relative sourcing from different working directories (FR-007 portability — US3-S6)
- [ ] T029 [US3] Remove inline `call_with_retry` function from `generate-spec-from-issue.sh` (around line 273-295) (FR-008)
- [ ] T030 [US3] Add `source` statement in `generate-spec-from-issue.sh` to load `lib/retry.sh` via `BASH_SOURCE[0]`-relative path (FR-008)
- [ ] T031 [US3] Verify all existing `call_with_retry` call sites in `generate-spec-from-issue.sh` still work after migration
- [ ] T032 [US3] Verify SC-004 — `grep -rE 'call_with_retry[[:space:]]*(\(|\{)' .github/scripts/` returns exactly one match (the definition in `lib/retry.sh`)

---

## Phase 6: User Story 4 — Audit and Harden Remaining Scripts (P3)

- [ ] T033 [P] [US4] Audit `sanitize-branch-name.sh` — verify `set -euo pipefail` and proper exit-code propagation on invalid input
- [ ] T034 [P] [US4] Audit `validate-label.sh` — verify `set -euo pipefail` and proper exit-code propagation on invalid input
- [ ] T035 [P] [US4] Audit `check-idempotency.sh` — verify `set -euo pipefail` and proper exit-code propagation on error conditions
- [ ] T036 [P] [US4] Audit `check-analysis-gate-cli.sh` / `check-analysis-gate.sh` — verify exit-code propagation for external command failures
- [ ] T037 [US4] Write test script `tests/test_exit_code_propagation.sh` — for each audited script, introduce error condition and verify non-zero exit
- [ ] T038 [US4] Fix any scripts found to mask failures during audit (if applicable)

---

## Phase 7: Polish & Cross-Cutting

- [ ] T039 [US3] Run all existing test scripts (`test_markdownlint_validation.sh`, `test_content_preservation.sh`, `test_check_analysis_gate.sh`, `test_sc004_regression.sh`) to verify no
  regressions (SC-005, FR-007, FR-008)
- [ ] T040 [US3] Run full pipeline dry-run to verify end-to-end compatibility (SC-006, NFR-005)
- [ ] T041 [US3] Verify NFR-001 defaults — 3 attempts, initial delay 5s, backoff 5s→10s across all scripts (NFR-001)
- [ ] T042 [US3] Verify NFR-003 — all retry error messages go to stderr, normal output stays on stdout (NFR-003)
- [ ] T043 [P] Add shellcheck validation for `lib/retry.sh` and modified scripts
- [ ] T044 Update any inline documentation/comments in modified scripts to reference the shared library

---

## Dependencies

| Task | Depends On |
|------|-----------|
| T004 | T002 |
| T005 | T004 |
| T008 | T003, T005 |
| T009 | T005 |
| T010 | T009 |
| T011 | T010 |
| T012 | T011 |
| T013 | T012 |
| T014 | T013 |
| T015 | T014 |
| T016 | T015 |
| T017 | T003, T005 |
| T018 | T005 |
| T019 | T018 |
| T020 | T019 |
| T021 | T020 |
| T022 | T021 |
| T023 | T022 |
| T024 | T023 |
| T025 | T024 |
| T026 | T025 |
| T027 | T003, T005 |
| T028 | T027 |
| T029 | T005 |
| T030 | T029 |
| T031 | T030 |
| T032 | T031, T016 |
| T033 | — |
| T034 | — |
| T035 | — |
| T036 | — |
| T037 | T003, T033–T036 |
| T038 | T037 |
| T039 | T016, T026, T031, T038 |
| T040 | T039 |
| T041 | T039 |
| T042 | T039 |
| T043 | T039 |
| T044 | T039 |

---

## FR Coverage Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T008, T011, T012 |
| FR-002 | T010, T011 |
| FR-003 | T017, T019, T025 |
| FR-004 | T025 |
| FR-005 | T019, T020, T021, T023 |
| FR-006 | T020, T022 |
| FR-007 | T004, T005, T006, T028, T039 |
| FR-008 | T027, T029, T030, T039 |
| FR-009 | T005, T024 |
| FR-010 | T005, T024 |
| FR-011 | T019 |
| FR-012 | T003, T009, T011, T012 |
| FR-013 | T013, T014 |

---
*Generated by Copilot SDK (claude-opus-4.6)*

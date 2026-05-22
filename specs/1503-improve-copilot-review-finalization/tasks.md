# Tasks: Improve Copilot Review Finalization

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup & Scaffolding | — | Test scaffolding tasks that prepare validation structure. |
| Phase 2: Foundational — Data Models & Result Structure | Phase 1: Data Models & Result Structure | Core model/result primitives shared by all user stories. |
| Phase 3: User Story 1 — Commit Change Guard (P1) | Phase 2: Commit Guard | Commit SHA guard and early-skip behavior. |
| Phase 4: User Story 2 — Per-Comment SDK Verification (P1) | Phase 3: Diff Context Extraction; Phase 4: SDK Verification Call; Phase 5: Per-Comment Verification Loop | Diff context assembly, SDK verdicting, and selective reply/resolve flow. |
| Phase 5: User Story 3 — Multi-Review Processing (P2) | Phase 6: Multi-Review Processing | Process all Copilot reviews with unresolved comments. |
| Phase 6: User Story 4 — Finalization Outcome Reporting (P3) | Phase 7: Dry-Run Mode & Reporting | Structured outcomes and dry-run handling. |
| Phase 7: Integration & Regression | Phase 8: Integration & Regression Validation | Orchestrator integration and end-to-end validation. |

## Phase 1: Setup & Scaffolding

- [ ] T001 Create testing directory `tests/unit/cli/ci/models/` and ensure parent directories contain `__init__.py` ([US1], FR-001)
- [ ] T002 Create verification-context test module `tests/unit/cli/ci/github_provider/test_verification_context_helper.py`; ensure parent directories contain `__init__.py` ([US2], FR-003)
- [ ] T003 Create SDK-verification test module `tests/unit/cli/ci/github_provider/test_verify_comment_via_sdk.py` ([US2], FR-004)

## Phase 2: Foundational — Data Models & Result Structure

- [ ] T004 [P] Write failing tests for `VerificationVerdict` enum (`COMMENT_RESOLVE`, `COMMENT_UNRESOLVE`) in `tests/unit/cli/ci/models/test_verificationverdict.py` (FR-005)
- [ ] T005 [P] Write failing tests for `FinalizationResult` dataclass (resolved count, unresolved count, skipped flag, errors list) in `tests/unit/cli/ci/models/test_finalizationresult.py` (FR-011)
- [ ] T006 [P] Write failing tests for `CommentResolution` dataclass (comment_id, thread_id, verdict, error) in `tests/unit/cli/ci/models/test_commentresolution.py` (FR-011)
- [ ] T007 Implement `VerificationVerdict` enum in `agentic_devtools/cli/ci/models.py` (FR-005)
- [ ] T008 Implement `FinalizationResult` frozen dataclass in `agentic_devtools/cli/ci/models.py` (FR-011, FR-012)
- [ ] T009 Implement `CommentResolution` frozen dataclass in `agentic_devtools/cli/ci/models.py`
- [ ] T010 Extend `ReviewCommentInfo` with optional `line`, `position`, `diff_hunk` fields in `agentic_devtools/cli/ci/models.py`
- [ ] T011 Update `list_review_comments` to parse `line`, `position`, `diff_hunk` from API response
  in `agentic_devtools/cli/ci/github_provider.py`; update `tests/unit/cli/ci/github_provider/test_list_review_comments.py` (FR-003, FR-004)

## Phase 3: User Story 1 — Commit Change Guard (P1)

- [ ] T012 [US1] Write failing happy-path tests for commit guard: HEAD SHA == review commit SHA → skip finalization with warning (FR-001, FR-002) in
  `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`
- [ ] T013 [US1] Write failing happy-path tests for commit guard fail-safe: null/empty review commit SHA → skip with error log (FR-014) in `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`
- [ ] T014 [US1] Write failing happy-path tests for commit guard proceed case: HEAD SHA != review commit SHA → proceed to verification loop (FR-001) in `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`
- [ ] T015 [US1] Update `finalize_post_repair` return type from `None` to `FinalizationResult` in `agentic_devtools/cli/ci/provider.py` abstract signature
- [ ] T016 [US1] Update `finalize_post_repair` in `agentic_devtools/cli/ci/ado_provider.py` to return `FinalizationResult` (stub)
- [ ] T017 [US1] Implement commit guard logic at top of `finalize_post_repair()` in `agentic_devtools/cli/ci/github_provider.py`: compare `review.commit_sha` vs `head_sha`, skip when equal (FR-001,
  FR-002), error-log when null/empty (FR-014), return early `FinalizationResult(skipped=True)`

## Phase 4: User Story 2 — Per-Comment SDK Verification (P1)

- [ ] T018 [US2] Write failing happy-path tests for verification-context helper behavior: line-anchored comment with ±50 lines context (FR-003, FR-004) in
  `tests/unit/cli/ci/github_provider/test_verification_context_helper.py`
- [ ] T019 [US2] Write failing happy-path tests for verification-context helper behavior: PR-level comment with full diff up to 4000-token budget and deterministic truncation (FR-004) in
  `tests/unit/cli/ci/github_provider/test_verification_context_helper.py`
- [ ] T020 [US2] Write failing happy-path tests for `_verify_comment_via_sdk()`: returns `COMMENT_RESOLVE` on addressed comment (FR-004, FR-006) in
  `tests/unit/cli/ci/github_provider/test_verify_comment_via_sdk.py`
- [ ] T021 [US2] Write failing happy-path tests for `_verify_comment_via_sdk()`: returns `COMMENT_UNRESOLVE` on unaddressed comment (FR-007) in `tests/unit/cli/ci/github_provider/test_verify_comment_via_sdk.py`
- [ ] T022 [US2] Write failing happy-path tests for `_verify_comment_via_sdk()`: unexpected SDK response treated as `COMMENT_UNRESOLVE` with warning (FR-005) in
  `tests/unit/cli/ci/github_provider/test_verify_comment_via_sdk.py`
- [ ] T023 [US2] Write failing happy-path tests for `_verify_comment_via_sdk()`: SDK timeout/error → `COMMENT_UNRESOLVE` fail-safe (FR-007, FR-008) in
  `tests/unit/cli/ci/github_provider/test_verify_comment_via_sdk.py`
- [ ] T024 [US2] Write failing happy-path tests for `_verify_comment_via_sdk()`: HTTP 429 rate-limit → stop loop, leave remaining unresolved (FR-008) in
  `tests/unit/cli/ci/github_provider/test_verify_comment_via_sdk.py`
- [ ] T025 [US2] Implement `_build_verification_context()` in `agentic_devtools/cli/ci/github_provider.py`: extract ±50 lines for line-anchored comments, full diff with 4k-token budget for PR-level
  comments (FR-003, FR-004)
- [ ] T026 [US2] Implement per-comment SDK verdict helper in `agentic_devtools/cli/ci/github_provider.py`: Copilot SDK call with `COPILOT_GITHUB_TOKEN`, parse `COMMENT_RESOLVE`/`COMMENT_UNRESOLVE`,
  handle errors (FR-004, FR-005, FR-007, FR-008)
- [ ] T027 [US2] Write failing tests for per-comment verification loop: already-resolved threads skipped silently (NFR-002), only `COMMENT_RESOLVE` triggers reply+resolve (FR-006) in
  `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`
- [ ] T028 [US2] Implement per-comment verification loop in `finalize_post_repair()` in `agentic_devtools/cli/ci/github_provider.py`: check thread status, build payload, call SDK, reply+resolve only
  on `COMMENT_RESOLVE` (FR-006), accumulate `CommentResolution` into `FinalizationResult`

## Phase 5: User Story 3 — Multi-Review Processing (P2)

- [ ] T029 [US3] Write failing tests for multi-review iteration: all Copilot reviews with unresolved comments are processed (FR-009) in `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`
- [ ] T030 [US3] Write failing tests for multi-review iteration: reviews with no unresolved comments skipped without error (FR-010) in `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`
- [ ] T031 [US3] Write failing tests for multi-review processing: diff computed per unique `review.commit_sha` (FR-003, FR-009) in `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`
- [ ] T032 [US3] Update `finalize_post_repair` signature: `review_id: int | None` (None = all reviews) in `agentic_devtools/cli/ci/provider.py` and `agentic_devtools/cli/ci/ado_provider.py` (FR-009)
- [ ] T033 [US3] Implement multi-review iteration in `finalize_post_repair()` in `agentic_devtools/cli/ci/github_provider.py`: iterate all Copilot reviews, skip empty reviews (FR-009, FR-010), cache
  diff per unique commit SHA

## Phase 6: User Story 4 — Finalization Outcome Reporting (P3)

- [ ] T034 [US4] Write failing tests for `--dry-run` mode: SDK calls run, verdicts classified, but no resolve API calls executed (FR-012) in
  `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`
- [ ] T035 [US4] Write failing tests for structured `FinalizationResult` output: resolved IDs, unresolved IDs, skipped reason, errors (FR-011) in
  `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`
- [ ] T036 [US4] Implement dry-run conditional in `finalize_post_repair()`: read `is_dry_run()` state, skip resolve API calls when active, still return full `FinalizationResult` (FR-012) in
  `agentic_devtools/cli/ci/github_provider.py`
- [ ] T037 [US4] Add structured JSON logging of `FinalizationResult` at end of `finalize_post_repair()` (FR-011) in `agentic_devtools/cli/ci/github_provider.py`

## Phase 7: Integration & Regression

- [ ] T038 Update orchestrator call site (line ~1106) in `agentic_devtools/cli/ci/orchestrator.py`: handle `FinalizationResult` return, inspect `skipped` flag, do NOT set `finalized=True` when
  `skipped=True`
- [ ] T039 Update orchestrator call site (line ~1169) in `agentic_devtools/cli/ci/orchestrator.py`: handle `FinalizationResult` return for prior-commit review path
- [ ] T040 Update orchestrator summary/reporting logic to consume `FinalizationResult` fields (`resolved_count`, `unresolved_count`, `errors`) in `agentic_devtools/cli/ci/orchestrator.py`
- [ ] T041 Update existing tests in `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py` to cover new return type and verify no regressions (FR-013, SC-004)
- [ ] T042 Run full validation suite (`agdt-test` + `agdt-task-wait`) — verify 100% coverage for new/modified code paths (FR-013, SC-003)
- [ ] T043 Run `bash scripts/run-pr-checks.sh` — verify all CI-blocking checks pass (FR-013)

## Dependencies

```text
T001–T003 → T004–T011 (scaffolding before tests/models)
T007–T011 → T012–T017 (models before guard implementation)
T015–T017 → T018–T028 (guard before verification loop)
T025–T028 → T029–T033 (single-review loop before multi-review)
T028–T033 → T034–T037 (loop complete before dry-run/reporting)
T017, T028, T033, T036 → T038–T043 (all features before integration)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
